from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from openai import OpenAI

from app.core.settings import settings
from app.schemas.place_catalog import PlaceData
from app.schemas.rule_itinerary import NormalizedRuleRequest


logger = logging.getLogger(__name__)

TIME_SLOT_OPENING = {
    "morning": "{place_name}, 오전 일정의 시작으로 넣기 좋아요!",
    "afternoon": "{place_name}, 오후 일정에 자연스럽게 넣기 좋아요!",
    "evening": "{place_name}, 저녁 일정으로 마무리하기 좋아요!",
}

TIME_SLOT_REASON = {
    "morning": [
        "오전에 가면 조금 더 차분한 분위기에서 여유 있게 둘러볼 수 있어요.",
        "사람이 아주 몰리기 전 시간대라 첫 코스로 시작하기에 부담이 적어요.",
        "하루를 천천히 열고 싶을 때 넣어두면 전체 흐름이 한결 편안해져요.",
    ],
    "afternoon": [
        "오후에 들르면 하루 중간 흐름을 자연스럽게 이어가기 좋아요.",
        "점심 이후에 가볍게 둘러보기 좋고, 다음 코스로 넘어가기도 수월해요.",
        "한창 움직이던 시간대에 리듬을 크게 끊지 않고 이어가기 좋아요.",
    ],
    "evening": [
        "저녁에 가면 하루 분위기를 조금 더 편하게 정리하기 좋아요.",
        "해가 기울기 시작하는 시간대와 잘 어울려서 마무리 코스로 넣기 좋아요.",
        "동선이 어느 정도 정리된 뒤 가볍게 들르기 좋은 시간대예요.",
    ],
}

STYLE_REASON = {
    "tight": "짧은 일정에서도 핵심만 빠르게 담기 좋은 편이에요.",
    "easy": "무리하게 서두르지 않아도 흐름을 만들기 좋아요.",
    "near-stay": "숙소 근처 위주로 움직이는 일정에도 붙이기 편해요.",
    "mobility-first": "이동 부담을 크게 늘리지 않으면서 넣기 좋은 코스예요.",
}

COMPANION_REASON = {
    "solo": "혼자 움직일 때도 속도를 스스로 조절하기 편해요.",
    "couple": "둘이 함께 분위기를 즐기기 좋은 장면이 자연스럽게 생겨요.",
    "friend": "같이 가볍게 이야기 나누며 둘러보기 좋은 장소예요.",
    "family": "가족과 함께 움직일 때도 무리 없이 넣기 좋아요.",
}

BUDGET_REASON = {
    "low": "비교적 가볍게 일정에 넣기 좋은 편이에요.",
    "medium": "너무 과하지 않게 만족도를 챙기기 좋아요.",
    "high": "조금 더 여유 있는 일정에도 자연스럽게 어울려요.",
}

CATEGORY_REASON = {
    "sightseeing": "도시의 대표적인 분위기를 가장 먼저 느끼기 좋은 장소예요.",
    "culture": "그 지역만의 결이나 분위기를 조금 더 또렷하게 느낄 수 있어요.",
    "food": "식사나 간식 자체가 일정의 재미가 되기 좋은 코스예요.",
    "shopping": "구경하는 재미가 있어서 일정 분위기를 바꿔주기 좋아요.",
    "relax": "너무 바쁘게만 움직이지 않도록 하루 흐름에 여유를 더해줘요.",
    "nature": "도시적인 장면 사이에서 풍경으로 숨을 돌리기 좋아요.",
    "photo": "사진으로 남겼을 때 만족도가 높은 장소예요.",
    "activity": "직접 체험하는 재미가 있어서 일정에 생동감을 더해줘요.",
    "nightlife": "저녁 이후 분위기를 살리기에 잘 맞는 편이에요.",
    "family": "연령대가 달라도 함께 둘러보기 편한 코스예요.",
}


@dataclass(frozen=True)
class RuleNoteContext:
    place: PlaceData
    request: NormalizedRuleRequest
    time_slot: str
    day_number: int
    localized_place_name: str
    localized_area_name: str
    day_area_name: str | None = None
    previous_place_name: str | None = None
    previous_area_name: str | None = None


class BaseRuleNoteGenerator:
    def generate(self, context: RuleNoteContext) -> str:
        raise NotImplementedError


class TemplateRuleNoteGenerator(BaseRuleNoteGenerator):
    def generate(self, context: RuleNoteContext) -> str:
        full_day_note = self._build_full_day_note(context)
        if full_day_note:
            return full_day_note

        opening = self._build_opening(context)
        details = [
            self._build_time_sentence(context),
            self._build_summary_sentence(context),
            self._build_route_sentence(context),
        ]
        polished_lines = [self._polish_sentence(sentence) for sentence in details if sentence]
        return "\n".join([opening, *polished_lines])

    def _build_full_day_note(self, context: RuleNoteContext) -> str:
        if not context.place.full_day_recommended:
            return ""

        custom_lines = context.place.full_day_notes.get(context.time_slot, [])
        if not custom_lines:
            return ""

        polished = [self._polish_sentence(line) for line in custom_lines[:4] if line]
        if len(polished) < 4:
            return ""

        return "\n".join(polished)

    def _build_opening(self, context: RuleNoteContext) -> str:
        template = TIME_SLOT_OPENING.get(context.time_slot, "{place_name}, 이번 일정에 넣기 좋아요!")
        return template.format(place_name=context.localized_place_name)

    def _build_time_sentence(self, context: RuleNoteContext) -> str:
        main_reason = self._pick(TIME_SLOT_REASON.get(context.time_slot, []), context, offset=1)
        supporting_reason = self._pick_non_empty(
            [
                STYLE_REASON.get(context.request.style, ""),
                COMPANION_REASON.get(context.request.companion_type, ""),
                BUDGET_REASON.get(context.request.budget_band, ""),
            ],
            context,
            offset=2,
        )
        return " ".join(part for part in [main_reason, supporting_reason] if part).strip()

    def _build_summary_sentence(self, context: RuleNoteContext) -> str:
        templates = context.place.note_templates or []
        if templates:
            template = self._pick(templates, context, offset=0)
            return template.format(
                place_name=context.localized_place_name,
                area=context.localized_area_name,
                day_number=context.day_number,
                time_slot=context.time_slot,
            )

        summary = self._normalize_summary(context.place.summary)
        if summary:
            return summary

        category_reason = self._build_category_sentence(context)
        if category_reason:
            return category_reason

        return f"{context.localized_area_name} 쪽 동선에 넣었을 때 전체 흐름을 안정적으로 잡아주기 좋아요."

    def _build_route_sentence(self, context: RuleNoteContext) -> str:
        if context.previous_place_name and context.previous_area_name == context.localized_area_name:
            return (
                f"둘러본 뒤에도 {context.previous_place_name}과 같은 권역에서 이어서 움직일 수 있어서 "
                "하루 동선이 깔끔하게 이어져요."
            )

        if "walkable" in context.place.mobility and context.day_area_name:
            return f"둘러본 뒤에도 {context.day_area_name} 쪽으로 자연스럽게 이어가기 좋아서 다음 코스 연결이 편해요."

        if "nearby" in context.place.mobility and context.day_area_name:
            return f"같은 날에는 {context.day_area_name} 주변 코스와 묶기 좋아서 일정이 산만해지지 않아요."

        tags = [self._polish_fragment(tag) for tag in context.place.highlight_tags or [] if tag]
        if tags:
            picked_tag = self._pick(tags, context, offset=4)
            return f"하루 코스에 {picked_tag} 같은 포인트를 더해줘서 일정이 단조롭게 느껴지지 않아요."

        moods = [self._polish_fragment(tag) for tag in context.place.mood_keywords or [] if tag]
        if moods:
            picked_mood = self._pick(moods, context, offset=5)
            return f"하루 분위기를 {picked_mood} 쪽으로 정리해주기에도 잘 맞아요."

        return f"{context.localized_area_name} 일대 흐름을 자연스럽게 이어주기 좋아서 앞뒤 코스와도 잘 연결돼요."

    def _build_category_sentence(self, context: RuleNoteContext) -> str:
        for category in context.place.category:
            if category in CATEGORY_REASON:
                return CATEGORY_REASON[category]
        return ""

    def _normalize_summary(self, summary: str) -> str:
        cleaned = summary.strip().rstrip(".!")
        if not cleaned:
            return ""
        if self._looks_korean(cleaned):
            return self._polish_sentence(cleaned)
        return ""

    def _polish_sentence(self, text: str) -> str:
        sentence = text.strip()
        if not sentence:
            return ""

        sentence = self._resolve_particles(sentence)
        sentence = sentence.replace("  ", " ")
        sentence = re.sub(r"[.]{2,}", ".", sentence)
        sentence = re.sub(r"[!]{2,}", "!", sentence)
        sentence = sentence.rstrip()

        if sentence.endswith(("요", "요.", "요!", "니다.", "니다!")):
            if sentence.endswith("요"):
                return sentence + "."
            return sentence

        if sentence.endswith(("다", "다.", "다!")):
            base = sentence[:-1] if sentence.endswith(("다.", "다!")) else sentence[:-1]
            return base + "요."

        if sentence.endswith((".", "!")):
            sentence = sentence[:-1]

        return sentence + "요."

    def _polish_fragment(self, text: str) -> str:
        fragment = self._resolve_particles(text.strip().rstrip(".!"))
        fragment = fragment.replace("  ", " ")
        return fragment

    def _resolve_particles(self, text: str) -> str:
        patterns = {
            "은(는)": self._topic_particle,
            "이(가)": self._subject_particle,
            "을(를)": self._object_particle,
            "와(과)": self._and_particle,
        }
        resolved = text
        for token, chooser in patterns.items():
            pattern = re.compile(rf"([가-힣A-Za-z0-9]+){re.escape(token)}")
            resolved = pattern.sub(lambda match: f"{match.group(1)}{chooser(match.group(1))}", resolved)
        return resolved

    def _topic_particle(self, word: str) -> str:
        return "은" if self._has_final_consonant(word) else "는"

    def _subject_particle(self, word: str) -> str:
        return "이" if self._has_final_consonant(word) else "가"

    def _object_particle(self, word: str) -> str:
        return "을" if self._has_final_consonant(word) else "를"

    def _and_particle(self, word: str) -> str:
        return "과" if self._has_final_consonant(word) else "와"

    def _has_final_consonant(self, word: str) -> bool:
        if not word:
            return False
        last_char = word[-1]
        if "가" <= last_char <= "힣":
            return (ord(last_char) - ord("가")) % 28 != 0
        return False

    def _pick(self, options: list[str], context: RuleNoteContext, *, offset: int) -> str:
        if not options:
            return ""
        index = self._seed(context, offset) % len(options)
        return options[index]

    def _pick_non_empty(self, options: list[str], context: RuleNoteContext, *, offset: int) -> str:
        filtered = [option for option in options if option]
        if not filtered:
            return ""
        return self._pick(filtered, context, offset=offset)

    def _seed(self, context: RuleNoteContext, offset: int) -> int:
        return sum(ord(char) for char in context.place.id) + context.day_number + offset

    def _looks_korean(self, text: str) -> bool:
        korean_count = sum(1 for char in text if "가" <= char <= "힣")
        ascii_letter_count = sum(1 for char in text if char.isascii() and char.isalpha())
        return korean_count >= ascii_letter_count and korean_count > 0


class OpenAIRuleNoteGenerator(BaseRuleNoteGenerator):
    def __init__(self, model: str):
        self.model = model
        self.client = OpenAI(api_key=settings.openai_api_key)

    def generate(self, context: RuleNoteContext) -> str:
        prompt = self._build_prompt(context)
        response = self.client.responses.create(model=self.model, input=prompt)
        text = getattr(response, "output_text", "").strip()
        if not text:
            raise ValueError("OpenAI rule note generation returned empty output.")
        return text

    def _build_prompt(self, context: RuleNoteContext) -> str:
        place = context.place
        return (
            "선택된 여행 장소 설명문을 한국어로 작성해주세요.\n"
            "말투는 부드러운 서비스 안내 문구처럼 모두 ~요 체로 작성해주세요.\n"
            "출력 형식은 반드시 아래 구조를 지켜주세요.\n"
            "1. 첫 줄: 추천 한 문장. 예: 경복궁, 오전 일정의 시작으로 넣기 좋아요!\n"
            "2. 그 아래 3문장: 언제 좋은지, 왜 좋은지, 어디와 이어지기 좋은지 설명\n"
            "문장은 짧고 보기 편하게 써주세요.\n"
            "너무 AI처럼 딱딱하거나 과장하지 말고 실제 여행 서비스 문구처럼 자연스럽게 써주세요.\n"
            f"장소명: {context.localized_place_name}\n"
            f"권역: {context.localized_area_name}\n"
            f"시간대: {context.time_slot}\n"
            f"일차: {context.day_number}\n"
            f"요약: {place.summary}\n"
            f"카테고리: {', '.join(place.category)}\n"
            f"예산 구간: {context.request.budget_band}\n"
            f"여행 스타일: {context.request.style}\n"
            f"동행 유형: {context.request.companion_type}\n"
            f"이동 특성: {', '.join(place.mobility)}\n"
            f"분위기 키워드: {', '.join(place.mood_keywords or [])}\n"
            f"강조 태그: {', '.join(place.highlight_tags or [])}\n"
            f"직전 장소: {context.previous_place_name or '없음'}\n"
            f"하루 권역 중심: {context.day_area_name or context.localized_area_name}\n"
        )


class HybridRuleNoteGenerator(BaseRuleNoteGenerator):
    def __init__(self, primary: BaseRuleNoteGenerator | None, fallback: BaseRuleNoteGenerator):
        self.primary = primary
        self.fallback = fallback

    def generate(self, context: RuleNoteContext) -> str:
        if self.primary is None:
            return self.fallback.generate(context)

        try:
            return self.primary.generate(context)
        except Exception as exc:  # pragma: no cover
            logger.warning("Primary rule note generator failed. Falling back to template mode: %s", exc)
            return self.fallback.generate(context)


def build_rule_note_generator() -> BaseRuleNoteGenerator:
    template_generator = TemplateRuleNoteGenerator()
    mode = settings.rule_note_generation_mode.lower()
    model = settings.rule_note_model or settings.openai_model

    if mode == "template":
        return template_generator

    openai_generator = OpenAIRuleNoteGenerator(model=model) if settings.openai_api_key else None

    if mode == "openai":
        return HybridRuleNoteGenerator(primary=openai_generator, fallback=template_generator)

    return HybridRuleNoteGenerator(primary=openai_generator, fallback=template_generator)
