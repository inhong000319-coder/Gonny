from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.itinerary import ItineraryItem
from app.models.trip import Trip
from app.schemas.generator import ItineraryGenerationRequest
from app.schemas.itinerary import ItineraryItemCreate, ItineraryItemResponse, ItineraryItemUpdate
from app.schemas.trip import TripDetailResponse
from app.services.itinerary_generator import generate_itinerary as generate_itinerary_service


router = APIRouter(prefix="/trips/{trip_id}", tags=["itinerary-items"])


def get_trip_or_404(trip_id: int, db: Session) -> Trip:
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return trip


@router.post("/itinerary-items", response_model=ItineraryItemResponse)
def create_itinerary_item(
    trip_id: int,
    itinerary_item: ItineraryItemCreate,
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)

    db_item = ItineraryItem(
        trip_id=trip_id,
        day_number=itinerary_item.day_number,
        time_slot=itinerary_item.time_slot,
        place_name=itinerary_item.place_name,
        category=itinerary_item.category,
        notes=itinerary_item.notes,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.patch("/itinerary-items/{item_id}", response_model=ItineraryItemResponse)
def update_itinerary_item(
    trip_id: int,
    item_id: int,
    itinerary_item: ItineraryItemUpdate,
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)
    db_item = db.query(ItineraryItem).filter(ItineraryItem.trip_id == trip_id, ItineraryItem.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary item not found")

    if itinerary_item.day_number is not None:
        db_item.day_number = itinerary_item.day_number
    if itinerary_item.time_slot is not None:
        db_item.time_slot = itinerary_item.time_slot
    if itinerary_item.place_name is not None:
        db_item.place_name = itinerary_item.place_name
    if itinerary_item.category is not None:
        db_item.category = itinerary_item.category
    if itinerary_item.notes is not None:
        db_item.notes = itinerary_item.notes

    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/itinerary-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_itinerary_item(
    trip_id: int,
    item_id: int,
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)
    db_item = db.query(ItineraryItem).filter(ItineraryItem.trip_id == trip_id, ItineraryItem.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary item not found")

    db.delete(db_item)
    db.commit()


@router.get("/itinerary-items", response_model=list[ItineraryItemResponse])
def list_itinerary_items(trip_id: int, db: Session = Depends(get_db)):
    get_trip_or_404(trip_id, db)

    itinerary_items = (
        db.query(ItineraryItem)
        .filter(ItineraryItem.trip_id == trip_id)
        .order_by(ItineraryItem.day_number.asc(), ItineraryItem.id.asc())
        .all()
    )
    return itinerary_items


@router.post("/generate-itinerary", response_model=TripDetailResponse)
def generate_itinerary(trip_id: int, db: Session = Depends(get_db)):
    trip = get_trip_or_404(trip_id, db)

    request_data = ItineraryGenerationRequest(
        destination=trip.destination,
        start_date=trip.start_date,
        end_date=trip.end_date,
        budget=trip.budget,
        travel_style=trip.travel_style,
        companion_type=trip.companion_type,
    )

    generated_result = generate_itinerary_service(request_data)

    db.query(ItineraryItem).filter(ItineraryItem.trip_id == trip_id).delete()

    for day in generated_result.days:
        for item in day.items:
            db.add(
                ItineraryItem(
                    trip_id=trip_id,
                    day_number=day.day_number,
                    time_slot=item.time_slot,
                    place_name=item.place_name,
                    category=item.category,
                    notes=item.notes,
                )
            )

    db.commit()
    db.refresh(trip)
    return trip
