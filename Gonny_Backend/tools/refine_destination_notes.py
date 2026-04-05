from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESTINATIONS_DIR = ROOT / "app" / "data" / "destinations"

CITY_LABELS = {
    "bangkok": "방콕",
    "barcelona": "바르셀로나",
    "busan": "부산",
    "chiangmai": "치앙마이",
    "fukuoka": "후쿠오카",
    "gangneung": "강릉",
    "gyeongju": "경주",
    "jeju": "제주",
    "jeonju": "전주",
    "kyoto": "교토",
    "osaka": "오사카",
    "paris": "파리",
    "rome": "로마",
    "seoul": "서울",
    "singapore": "싱가포르",
    "sokcho": "속초",
    "taipei": "타이베이",
    "tokyo": "도쿄",
    "vladivostok": "블라디보스토크",
    "yeosu": "여수",
}

CATEGORY_TEMPLATE = {
    "sightseeing": "{place_name}은(는) {city_label}에서 대표적인 장면을 가장 안정적으로 담기 좋은 장소예요.",
    "culture": "{place_name}은(는) {city_label}의 분위기와 결을 조금 더 깊게 느끼고 싶을 때 잘 맞아요.",
    "food": "{place_name}은(는) {area} 동선에서 먹거리와 분위기를 함께 즐기고 싶을 때 잘 어울려요.",
    "shopping": "{place_name}은(는) {area} 쪽에서 구경과 쇼핑을 함께 묶고 싶을 때 자연스럽게 들어가요.",
    "relax": "{place_name}은(는) 일정을 너무 빽빽하게 채우지 않고 조금 더 여유 있게 풀고 싶을 때 좋아요.",
    "nature": "{place_name}은(는) {city_label} 일정에 자연 풍경을 부드럽게 섞고 싶을 때 잘 맞아요.",
    "photo": "{place_name}은(는) 사진으로 남기기 좋은 장면을 일정에 더하고 싶을 때 만족도가 높아요.",
    "activity": "{place_name}은(는) 구경만 하는 일정 대신 체험 요소를 하나 넣고 싶을 때 잘 어울려요.",
    "nightlife": "{place_name}은(는) 저녁 이후 분위기를 조금 더 살아 있게 만들고 싶을 때 좋아요.",
    "family": "{place_name}은(는) 여러 연령대가 함께 움직이는 일정에도 비교적 부담 없이 넣기 좋아요.",
}

CATEGORY_MOODS = {
    "sightseeing": ["상징적인", "안정적인", "만족도 높은"],
    "culture": ["차분한", "정돈된", "깊이 있는"],
    "food": ["맛있게 즐기기 좋은", "로컬한", "활기 있는"],
    "shopping": ["가볍게 구경하기 좋은", "활기 있는", "실속 있는"],
    "relax": ["여유로운", "편안한", "부드러운"],
    "nature": ["시원한", "상쾌한", "자연적인"],
    "photo": ["사진이 잘 나오는", "감성적인", "기억에 남는"],
    "activity": ["경쾌한", "재미 있는", "체험 중심의"],
    "nightlife": ["저녁이 어울리는", "활기 있는", "분위기 있는"],
    "family": ["가족 친화적인", "편안한", "무난한"],
}

CATEGORY_TAGS = {
    "sightseeing": ["대표 명소", "도시다운 풍경", "핵심 관광 포인트"],
    "culture": ["문화 포인트", "분위기 있는 동선", "차분한 관람"],
    "food": ["먹거리 동선", "식사 포인트", "현지 분위기"],
    "shopping": ["구경하는 재미", "쇼핑 동선", "가벼운 변화"],
    "relax": ["여유로운 흐름", "쉬어 가는 코스", "부드러운 템포"],
    "nature": ["자연 풍경", "산책 포인트", "시원한 장면"],
    "photo": ["사진 포인트", "기억 남는 장면", "시각적인 재미"],
    "activity": ["체험 요소", "일정의 변화", "경쾌한 포인트"],
    "nightlife": ["저녁 분위기", "밤 산책", "야간 포인트"],
    "family": ["가족 일정", "무난한 선택", "편안한 코스"],
}


def pick_primary_category(place: dict) -> str:
    categories = place.get("category", [])
    for category in categories:
        if category in CATEGORY_TEMPLATE:
            return category
    return "sightseeing"


def ensure_summary_yo_style(summary: str, city_label: str) -> str:
    text = (summary or "").strip().rstrip(".")
    if not text:
        return f"{city_label} 일정에 자연스럽게 넣기 좋은 코스예요."
    if text.endswith("요"):
        return text + "."
    return text + "요."


def build_template(place: dict, city_label: str) -> str:
    primary = pick_primary_category(place)
    template = CATEGORY_TEMPLATE[primary]
    return template.format(
        place_name="{place_name}",
        area="{area}",
        city_label=city_label,
    )


def build_moods(place: dict) -> list[str]:
    primary = pick_primary_category(place)
    return CATEGORY_MOODS[primary]


def build_tags(place: dict, city_label: str) -> list[str]:
    primary = pick_primary_category(place)
    tags = list(CATEGORY_TAGS[primary])
    if city_label not in "".join(tags):
        tags[1] = f"{city_label}다운 분위기"
    return tags


def refine_file(path: Path) -> None:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    city_key = str(payload.get("city", "")).strip().lower()
    city_label = CITY_LABELS.get(city_key, payload.get("city", "이 도시"))

    for place in payload.get("places", []):
        place["summary"] = ensure_summary_yo_style(place.get("summary", ""), city_label)
        place["mood_keywords"] = build_moods(place)
        place["highlight_tags"] = build_tags(place, city_label)
        place["note_templates"] = [build_template(place, city_label)]

    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main() -> None:
    for path in sorted(DESTINATIONS_DIR.glob("*.json")):
        refine_file(path)
        print(f"refined: {path.name}")


if __name__ == "__main__":
    main()
