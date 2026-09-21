from __future__ import annotations

import io
import json
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException, status
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.domains.rule_planner.services.travel_estimate import haversine_distance_km
from app.domains.trips.schemas import (
    ExpenseCreate,
    ExpenseCreateResponse,
    ExpenseItem,
    ExpenseListData,
    ExpenseSummaryData,
    ShareLinkCreateRequest,
    ShareLinkResponse,
    TripCategoryBreakdownItem,
    TripCreate,
    TripFavoriteUpdate,
    TripReportResponse,
    TripRetrospectiveUpdate,
)
from app.models.expense import Expense
from app.models.itinerary import ItineraryItem
from app.models.trip import Trip

SHARE_TOKEN_BYTES = 32

DESTINATIONS_DIR = Path(__file__).resolve().parents[4] / "app" / "data" / "destinations"
TIME_SLOT_ORDER = {"morning": 0, "afternoon": 1, "evening": 2}
TIME_SLOT_LABELS = {"morning": "오전", "afternoon": "오후", "evening": "저녁"}
# Fewer than this many matched-and-adjacent legs isn't enough to call a
# total distance meaningful - see _compute_trip_distance().
MIN_DISTANCE_SEGMENTS = 2

# ReportLab's built-in fonts (Helvetica etc.) have no Korean glyphs and
# silently render Korean text as blank/garbled boxes.
#
# A UnicodeCIDFont (e.g. "HYSMyeongJo-Medium") was tried first, but it
# doesn't embed any font data - it just references a standard CID font
# name and relies on the *viewer* to substitute a local Korean font at
# render time. `pdffonts` on the generated PDF confirms this: the font
# shows up with "emb no", and poppler has to log a substitution ("Couldn't
# find a font for 'HYSMyeongJo-Medium', subst is 'Batang'"). That
# substitution only works if the machine opening the PDF happens to have
# a Korean font installed - on a plain Linux server/container without one,
# poppler (and many other viewers) render the text as nothing at all,
# leaving only the table borders visible.
#
# TTFont actually embeds the font program's glyph outlines into the PDF
# (subset to only the glyphs used), so every viewer can render the text
# correctly with zero dependency on the host's installed fonts. Nanum
# Gothic (SIL Open Font License 1.1 - see app/assets/fonts/OFL.txt) is
# vendored here for that reason rather than relying on a system font.
PDF_FONT_NAME = "NanumGothic"
PDF_FONT_PATH = Path(__file__).resolve().parents[4] / "app" / "assets" / "fonts" / "NanumGothic-Regular.ttf"
pdfmetrics.registerFont(TTFont(PDF_FONT_NAME, str(PDF_FONT_PATH)))


def _compute_share_expires_at(expires_in: str, *, now: datetime | None = None) -> datetime | None:
    """1d/7d -> a concrete UTC expiry; "unlimited" -> None (no expiry)."""
    reference = now or datetime.now(timezone.utc)
    if expires_in == "1d":
        return reference + timedelta(days=1)
    if expires_in == "7d":
        return reference + timedelta(days=7)
    return None


def _is_share_link_expired(expires_at: datetime | None, *, now: datetime | None = None) -> bool:
    """None means "no expiry" (unlimited), never expired.

    SQLite (used for local/dev DBs) doesn't preserve tzinfo on
    DateTime(timezone=True) columns, so a value read back from the DB can
    be naive even though it was written as timezone-aware - comparing it
    against an aware "now" would raise TypeError. Match awareness instead
    of assuming either side.
    """
    if expires_at is None:
        return False
    if now is not None:
        reference = now
    else:
        reference = datetime.now(timezone.utc) if expires_at.tzinfo else datetime.utcnow()
    return expires_at < reference


def _normalize_place_name(name: str) -> str:
    """Whitespace-insensitive, case-insensitive comparison key - mirrors
    external_clients.py's _collapse_whitespace(), same rationale (our data
    and catalog data don't always agree on spacing for the same place)."""
    return re.sub(r"\s+", "", name).lower()


def _load_city_place_coordinates(city: str) -> dict[str, tuple[float, float]]:
    """Best-effort {normalized_name: (lat, lng)} for one destination_catalog
    city file. Returns {} if the file doesn't exist (city isn't one of our
    catalog cities, or is simply unrecognized free text - Trip.destination
    has no enum/foreign-key constraint) or fails to parse - never raises,
    matching this codebase's established graceful-degradation pattern."""
    path = DESTINATIONS_DIR / f"{city}.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    coordinates: dict[str, tuple[float, float]] = {}
    for place in payload.get("places", []):
        name = place.get("name")
        latitude = place.get("latitude")
        longitude = place.get("longitude")
        if not name or latitude is None or longitude is None:
            continue
        coordinates[_normalize_place_name(name)] = (float(latitude), float(longitude))
    return coordinates


def _compute_trip_distance(
    itinerary_items: list[ItineraryItem], city: str
) -> tuple[float | None, int, int]:
    """Returns (total_km, matched_place_count, total_place_count).

    total_km is None ("정보 없음") whenever fewer than MIN_DISTANCE_SEGMENTS
    consecutive pairs (in visit order) both matched a catalog place - a
    single lucky matched pair isn't a trustworthy "total distance", and
    reporting 0km for an unmatched trip would be a false claim rather
    than an honest "we don't know". Items are ordered by (day_number,
    time_slot, id) to approximate actual visit order; a gap where either
    side of a pair is unmatched simply contributes no distance for that
    leg (not an error - matched_place_count/total_place_count tell the
    caller how much of the trip that covers).
    """
    total_place_count = len(itinerary_items)
    coordinates = _load_city_place_coordinates(city)
    if not coordinates or total_place_count == 0:
        return None, 0, total_place_count

    ordered_items = sorted(
        itinerary_items,
        key=lambda item: (item.day_number, TIME_SLOT_ORDER.get(item.time_slot, 3), item.id),
    )
    matched_points = [coordinates.get(_normalize_place_name(item.place_name)) for item in ordered_items]
    matched_place_count = sum(1 for point in matched_points if point is not None)

    total_km = 0.0
    segment_count = 0
    for previous_point, point in zip(matched_points, matched_points[1:]):
        if previous_point is None or point is None:
            continue
        total_km += haversine_distance_km(previous_point[0], previous_point[1], point[0], point[1])
        segment_count += 1

    if segment_count < MIN_DISTANCE_SEGMENTS:
        return None, matched_place_count, total_place_count
    return round(total_km, 1), matched_place_count, total_place_count


def _compute_category_breakdown(expenses: list[Expense]) -> list[TripCategoryBreakdownItem]:
    """Shared by get_trip_report() and the PDF export so both surfaces
    agree on the same numbers from the same expense rows."""
    category_totals: dict[str, int] = {}
    for expense in expenses:
        category_totals[expense.category] = category_totals.get(expense.category, 0) + expense.amount_krw
    return [
        TripCategoryBreakdownItem(category=category, amount_krw=amount) for category, amount in category_totals.items()
    ]


def _build_report_insights(
    *,
    budget: int,
    total_spent: int,
    visited_count: int,
    distance_km: float | None,
    category_breakdown: list[TripCategoryBreakdownItem],
) -> list[str]:
    """Rule-based sentence templates over real computed numbers - no LLM
    call, per this project's "no external AI at request time" principle.
    Each insight only appears when its underlying data actually exists;
    never padded out to hit a target count with fabricated content."""
    insights: list[str] = []

    if budget > 0:
        usage_pct = round((total_spent / budget) * 100)
        insights.append(f"예산의 {usage_pct}%를 사용했어요.")

    if visited_count > 0:
        insights.append(f"총 {visited_count}곳을 방문했어요.")

    if distance_km is not None:
        insights.append(f"총 {distance_km}km를 이동했어요.")

    if category_breakdown:
        top_category = max(category_breakdown, key=lambda item: item.amount_krw)
        insights.append(f"'{top_category.category}' 항목에 가장 많이 지출했어요 ({top_category.amount_krw:,}원).")

    return insights


def _build_trip_pdf_bytes(
    *,
    trip: Trip,
    itinerary_items: list[ItineraryItem],
    total_spent: int,
    category_breakdown: list[TripCategoryBreakdownItem],
) -> bytes:
    """Renders the trip's saved itinerary + budget summary to an A4 PDF.

    Only fields that actually exist on Trip/ItineraryItem are used - no
    address, operating hours, contact info, or accommodation, since none
    of that is stored anywhere yet (see this feature's scope note).
    """
    title_style = ParagraphStyle("Title", fontName=PDF_FONT_NAME, fontSize=20, leading=26)
    meta_style = ParagraphStyle("Meta", fontName=PDF_FONT_NAME, fontSize=10, textColor=colors.grey, leading=14)
    heading_style = ParagraphStyle(
        "Heading", fontName=PDF_FONT_NAME, fontSize=14, leading=20, spaceBefore=14, spaceAfter=6
    )
    day_style = ParagraphStyle("Day", fontName=PDF_FONT_NAME, fontSize=12, leading=16, spaceBefore=8, spaceAfter=4)
    body_style = ParagraphStyle("Body", fontName=PDF_FONT_NAME, fontSize=10, leading=14)

    elements = [
        Paragraph(trip.title, title_style),
        Paragraph(f"{trip.destination} · {trip.start_date.isoformat()} ~ {trip.end_date.isoformat()}", meta_style),
        Spacer(1, 10 * mm),
        Paragraph("일정", heading_style),
    ]

    if not itinerary_items:
        elements.append(Paragraph("저장된 일정이 없습니다.", body_style))
    else:
        items_by_day: dict[int, list[ItineraryItem]] = {}
        for item in itinerary_items:
            items_by_day.setdefault(item.day_number, []).append(item)

        for day_number in sorted(items_by_day):
            elements.append(Paragraph(f"Day {day_number}", day_style))
            day_items = sorted(items_by_day[day_number], key=lambda item: TIME_SLOT_ORDER.get(item.time_slot, 3))
            rows = [["시간대", "장소", "카테고리"]] + [
                [TIME_SLOT_LABELS.get(item.time_slot, item.time_slot), item.place_name, item.category]
                for item in day_items
            ]
            table = Table(rows, colWidths=[25 * mm, 90 * mm, 35 * mm])
            table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), PDF_FONT_NAME),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            elements.append(table)

    elements.append(Paragraph("예산 요약", heading_style))
    budget_rows = [["총 예산", f"{trip.budget:,}원"], ["총 지출", f"{total_spent:,}원"]]
    if trip.budget:
        diff_pct = round(((total_spent - trip.budget) / trip.budget) * 100, 1)
        budget_rows.append(["예산 대비", f"{diff_pct:+.1f}%"])
    budget_table = Table(budget_rows, colWidths=[40 * mm, 60 * mm])
    budget_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), PDF_FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ]
        )
    )
    elements.append(budget_table)

    if category_breakdown:
        elements.append(Spacer(1, 4 * mm))
        category_rows = [["카테고리", "금액"]] + [
            [item.category, f"{item.amount_krw:,}원"] for item in category_breakdown
        ]
        category_table = Table(category_rows, colWidths=[40 * mm, 60 * mm])
        category_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), PDF_FONT_NAME),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ]
            )
        )
        elements.append(category_table)
    else:
        elements.append(Paragraph("기록된 지출이 없습니다.", body_style))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title=trip.title,
    )
    doc.build(elements)
    return buffer.getvalue()


class TripService:
    def create_trip(self, *, db: Session, request: TripCreate) -> Trip:
        db_trip = Trip(
            title=request.title or f"{request.destination} 여행",
            destination=request.destination,
            start_date=request.start_date,
            end_date=request.end_date,
            budget=request.budget,
            travel_style=request.travel_style,
            companion_type=request.companion_type,
        )
        db.add(db_trip)
        db.commit()
        db.refresh(db_trip)
        return db_trip

    def list_trips(self, *, db: Session) -> list[Trip]:
        return db.query(Trip).order_by(Trip.id.desc()).all()

    def get_trip_or_404(self, *, db: Session, trip_id: int) -> Trip:
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
        return trip

    def update_trip_favorite(
        self,
        *,
        db: Session,
        trip_id: int,
        payload: TripFavoriteUpdate,
    ) -> Trip:
        trip = self.get_trip_or_404(db=db, trip_id=trip_id)

        if payload.is_favorite and not trip.is_favorite:
            favorite_count = db.query(func.count(Trip.id)).filter(Trip.is_favorite.is_(True)).scalar() or 0
            if favorite_count >= 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="즐겨찾기 여행은 최대 3개까지 등록할 수 있어요.",
                )

        trip.is_favorite = payload.is_favorite
        db.commit()
        db.refresh(trip)
        return trip

    def create_share_link(
        self,
        *,
        db: Session,
        trip_id: int,
        payload: ShareLinkCreateRequest,
    ) -> ShareLinkResponse:
        """Issues (or re-issues) this trip's single share link. Read-only
        only for this MVP - there's no permission column, every link
        grants read-only access. Overwriting share_token in place is what
        makes the previous link stop working: it's no longer stored
        anywhere, so a lookup by the old value simply finds no row."""
        trip = self.get_trip_or_404(db=db, trip_id=trip_id)

        token = secrets.token_urlsafe(SHARE_TOKEN_BYTES)
        expires_at = _compute_share_expires_at(payload.expires_in)

        trip.share_token = token
        trip.share_expires_at = expires_at
        db.commit()
        db.refresh(trip)

        return ShareLinkResponse(
            share_url=f"{settings.frontend_base_url}/share/{token}",
            token=token,
            expires_at=expires_at,
        )

    def get_trip_by_share_token(self, *, db: Session, token: str) -> Trip:
        trip = db.query(Trip).filter(Trip.share_token == token).first()
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공유 링크를 찾을 수 없습니다.")
        if _is_share_link_expired(trip.share_expires_at):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="링크가 만료되었습니다.")
        return trip

    def update_trip_retrospective(
        self,
        *,
        db: Session,
        trip_id: int,
        payload: TripRetrospectiveUpdate,
    ) -> Trip:
        trip = self.get_trip_or_404(db=db, trip_id=trip_id)
        trip.satisfaction_rating = payload.satisfaction_rating
        trip.retrospective_note = payload.retrospective_note
        db.commit()
        db.refresh(trip)
        return trip

    def _total_spent(self, *, db: Session, trip_id: int) -> int:
        return db.query(func.coalesce(func.sum(Expense.amount_krw), 0)).filter(Expense.trip_id == trip_id).scalar() or 0

    def create_expense(self, *, db: Session, trip_id: int, payload: ExpenseCreate) -> ExpenseCreateResponse:
        trip = self.get_trip_or_404(db=db, trip_id=trip_id)

        db_expense = Expense(
            trip_id=trip_id,
            category=payload.category,
            amount_krw=payload.amount,
            currency=payload.currency,
            note=payload.note,
            spent_at=payload.spent_at,
        )
        db.add(db_expense)
        db.commit()
        db.refresh(db_expense)

        total_spent = self._total_spent(db=db, trip_id=trip_id)
        remaining_budget = trip.budget - total_spent
        budget_usage_pct = round((total_spent / trip.budget) * 100, 1) if trip.budget else 0.0

        return ExpenseCreateResponse(
            expense_id=db_expense.id,
            category=db_expense.category,
            amount_krw=db_expense.amount_krw,
            remaining_budget=remaining_budget,
            budget_usage_pct=budget_usage_pct,
        )

    def list_expenses(self, *, db: Session, trip_id: int) -> ExpenseListData:
        self.get_trip_or_404(db=db, trip_id=trip_id)
        expenses = db.query(Expense).filter(Expense.trip_id == trip_id).order_by(Expense.id.desc()).all()
        return ExpenseListData(
            expenses=[
                ExpenseItem(expense_id=e.id, category=e.category, amount_krw=e.amount_krw, note=e.note)
                for e in expenses
            ]
        )

    def get_expense_summary(self, *, db: Session, trip_id: int) -> ExpenseSummaryData:
        trip = self.get_trip_or_404(db=db, trip_id=trip_id)
        total_spent = self._total_spent(db=db, trip_id=trip_id)
        remaining = trip.budget - total_spent
        usage_pct = round((total_spent / trip.budget) * 100, 1) if trip.budget else 0.0

        return ExpenseSummaryData(
            total_budget=trip.budget,
            total_spent=total_spent,
            remaining=remaining,
            usage_pct=usage_pct,
            is_over_budget=total_spent > trip.budget,
        )

    def get_trip_report(self, *, db: Session, trip_id: int) -> TripReportResponse:
        """F14 retrospective report. Deliberately no LLM call - see
        _build_report_insights()."""
        trip = self.get_trip_or_404(db=db, trip_id=trip_id)

        if trip.end_date >= date.today():
            return TripReportResponse(ready=False, message="여행이 아직 종료되지 않았습니다.")

        expenses = db.query(Expense).filter(Expense.trip_id == trip_id).all()
        total_spent = sum(e.amount_krw for e in expenses)
        category_breakdown = _compute_category_breakdown(expenses)

        budget_diff_pct = round(((total_spent - trip.budget) / trip.budget) * 100, 1) if trip.budget else None

        # Item count, not a real "visited" check-in concept - see this
        # method's docstring on TripReportResponse.visited_count.
        itinerary_items = db.query(ItineraryItem).filter(ItineraryItem.trip_id == trip_id).all()
        visited_count = len(itinerary_items)

        distance_km, matched_place_count, total_place_count = _compute_trip_distance(
            itinerary_items, trip.destination
        )

        insights = _build_report_insights(
            budget=trip.budget,
            total_spent=total_spent,
            visited_count=visited_count,
            distance_km=distance_km,
            category_breakdown=category_breakdown,
        )

        return TripReportResponse(
            ready=True,
            total_spent=total_spent,
            budget=trip.budget,
            budget_diff_pct=budget_diff_pct,
            category_breakdown=category_breakdown,
            visited_count=visited_count,
            distance_km=distance_km,
            matched_place_count=matched_place_count,
            total_place_count=total_place_count,
            insights=insights,
            satisfaction_rating=trip.satisfaction_rating,
            retrospective_note=trip.retrospective_note,
        )

    def generate_trip_pdf(self, *, db: Session, trip_id: int) -> bytes:
        """A4 itinerary + budget PDF, built from whatever's actually saved
        right now - unlike get_trip_report(), this isn't gated on the trip
        having ended, since a printable plan is just as useful beforehand."""
        trip = self.get_trip_or_404(db=db, trip_id=trip_id)

        expenses = db.query(Expense).filter(Expense.trip_id == trip_id).all()
        total_spent = sum(e.amount_krw for e in expenses)
        category_breakdown = _compute_category_breakdown(expenses)

        itinerary_items = (
            db.query(ItineraryItem)
            .filter(ItineraryItem.trip_id == trip_id)
            .order_by(ItineraryItem.day_number.asc(), ItineraryItem.id.asc())
            .all()
        )

        return _build_trip_pdf_bytes(
            trip=trip,
            itinerary_items=itinerary_items,
            total_spent=total_spent,
            category_breakdown=category_breakdown,
        )


trip_service = TripService()
