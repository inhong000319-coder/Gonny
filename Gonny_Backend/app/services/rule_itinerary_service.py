import re
from collections import defaultdict

from app.providers.place_catalog.local_json_catalog import LocalJsonPlaceCatalogProvider
from app.schemas.place_catalog import CityPlaceCatalog, PlaceData
from app.schemas.rule_itinerary import (
    CatalogCityOption,
    NormalizedRuleRequest,
    RuleItineraryItem,
    RuleItineraryRequest,
    RuleItineraryResponse,
)


TIME_SLOTS = ["morning", "afternoon", "evening"]
DEFAULT_CONCEPTS = ["sightseeing"]
DEFAULT_STYLE = "easy"
DEFAULT_COMPANION = "friend"
DEFAULT_CITY_BY_COUNTRY = {
    "korea": "seoul",
    "south korea": "seoul",
    "japan": "tokyo",
    "russia": "vladivostok",
    "france": "paris",
    "thailand": "bangkok",
}
SLOT_CATEGORY_PREFERENCE = {
    "morning": {"relax", "nature", "cafe", "sightseeing", "culture"},
    "afternoon": {"sightseeing", "shopping", "culture", "activity", "nature"},
    "evening": {"food", "shopping", "relax", "photo", "nightlife"},
}
PLACE_NAME_KO = {
    "gyeongbokgung": "경복궁",
    "bukchon": "북촌한옥마을",
    "insadong": "인사동 거리",
    "myeongdong": "명동",
    "namsan-tower": "N서울타워",
    "hongdae": "홍대",
    "yeouido-hangang": "여의도 한강공원",
    "gangnam": "강남역 일대",
    "coex": "코엑스몰과 별마당도서관",
    "asakusa-sensoji": "센소지와 나카미세 거리",
    "ueno-park": "우에노 공원",
    "ameyoko": "아메요코 시장거리",
    "shibuya": "시부야 스크램블 교차로와 센터가이",
    "meiji-jingu": "메이지 신궁",
    "harajuku": "다케시타 거리와 하라주쿠",
    "tsukiji": "츠키지 장외시장",
    "ginza": "긴자",
    "odaiba": "오다이바 해변 지구",
    "dotonbori": "도톤보리",
    "kuromon-market": "구로몬 시장",
    "osaka-castle": "오사카성",
    "shinsaibashi": "신사이바시 쇼핑 아케이드",
    "tsutenkaku": "쓰텐카쿠와 신세카이",
    "umeda-sky": "우메다 스카이 빌딩",
    "nakazakicho": "나카자키초 카페 거리",
    "tennoji-park": "덴노지 공원",
    "sumiyoshi-taisha": "스미요시 타이샤",
    "grand-palace": "방콕 왕궁",
    "wat-pho": "왓 포",
    "wat-arun": "왓 아룬",
    "yaowarat": "야오와랏 로드",
    "chatuchak": "짜뚜짝 시장",
    "iconsiam": "아이콘시암",
    "lumpini": "룸피니 공원",
    "siam": "시암 스퀘어",
    "asiatique": "아시아티크 리버프론트",
    "arbat-street": "아르바트 거리",
    "sportivnaya-embankment": "스포르티브나야 해안 산책로",
    "tokarevsky-lighthouse": "토카레브스키 등대",
    "revolution-square": "혁명광장",
    "railway-station": "블라디보스토크 기차역",
    "svetlanskaya-street": "스베틀란스카야 거리",
    "eagle-nest": "이글스 네스트 전망대",
    "millionka": "밀리온카 지구",
    "cafe-tour-center": "도심 카페 코스",
    "eiffel-tower": "에펠탑",
    "louvre": "루브르 박물관",
    "montmartre": "몽마르트르",
    "seine-river": "센강 산책로",
    "le-marais": "르 마레",
    "orsay": "오르세 미술관",
    "luxembourg": "뤽상부르 공원",
    "saint-germain": "생제르맹",
}
AREA_LABEL_KO = {
    "jongno": "종로",
    "myeongdong": "명동",
    "namsan": "남산",
    "hongdae": "홍대",
    "yeouido": "여의도",
    "gangnam": "강남",
    "seongsu": "성수",
    "itaewon": "이태원",
    "jamsil": "잠실",
    "dongdaemun": "동대문",
    "euljiro": "을지로",
    "asakusa": "아사쿠사",
    "ueno": "우에노",
    "yanaka": "야나카",
    "shibuya": "시부야",
    "harajuku": "하라주쿠",
    "ginza": "긴자",
    "odaiba": "오다이바",
    "roppongi": "롯폰기",
    "akihabara": "아키하바라",
    "kiyosumi": "기요스미",
    "kichijoji": "기치조지",
    "ebisu": "에비스",
    "namba": "난바",
    "castle-area": "오사카성 일대",
    "shinsekai": "신세카이",
    "umeda": "우메다",
    "tennoji": "덴노지",
    "sumiyoshi": "스미요시",
    "bay-area": "베이 에어리어",
    "nakanoshima": "나카노시마",
    "fukushima": "후쿠시마",
    "old-city": "올드타운",
    "riverside": "리버사이드",
    "chinatown": "차이나타운",
    "chatuchak": "짜뚜짝",
    "silom": "실롬",
    "siam": "시암",
    "green-zone": "그린존",
    "ari": "아리",
    "asok": "아속",
    "city-center": "도심",
    "seaside": "해안가",
    "tokarevsky": "토카레브스키",
    "russky-island": "루스키섬",
    "viewpoint": "전망대 일대",
    "suburb": "외곽",
    "canal": "운하 주변",
    "bercy": "베르시",
}
CONCEPT_LABEL_KO = {
    "food": "식사",
    "shopping": "쇼핑",
    "relax": "휴양",
    "sightseeing": "관광",
    "culture": "문화",
    "nature": "자연",
}
COMPANION_REASON_KO = {
    "solo": "혼자서도 부담 없이 움직이기 좋습니다.",
    "couple": "둘이서 분위기 있게 시간을 보내기 좋습니다.",
    "friend": "친구와 함께 즐기기 좋은 활기 있는 동선입니다.",
    "family": "가족과 함께 무리 없이 둘러보기 좋습니다.",
}
TIME_SLOT_REASON_KO = {
    "morning": "오전에 가볍게 시작하기 좋고",
    "afternoon": "하루의 핵심 일정으로 넣기 좋고",
    "evening": "저녁 시간에 여유롭게 마무리하기 좋고",
}
BUDGET_REASON_KO = {
    "low": "가성비를 살리기 좋으며",
    "medium": "비용과 만족도의 균형이 잘 맞고",
    "high": "조금 더 편안하고 완성도 있는 여행 예산과 잘 맞으며",
}


class RuleItineraryService:
    def __init__(self, catalog_provider: LocalJsonPlaceCatalogProvider | None = None):
        self.catalog_provider = catalog_provider or LocalJsonPlaceCatalogProvider()

    def list_catalog_options(self) -> list[CatalogCityOption]:
        return self.catalog_provider.list_city_options()

    def generate(self, request: RuleItineraryRequest) -> RuleItineraryResponse:
        normalized = self._normalize_request(request)
        city_catalog = self.catalog_provider.get_city_catalog(
            continent=normalized.continent,
            country=normalized.country,
            city=normalized.city,
        )
        items = self._build_items(normalized, city_catalog)

        return RuleItineraryResponse(
            continent=city_catalog.continent,
            country=city_catalog.country,
            city=city_catalog.city,
            travelers=normalized.travelers,
            nights=normalized.nights,
            days=normalized.days,
            budget_band=normalized.budget_band,
            concepts=normalized.concepts,
            style=normalized.style,
            companion_type=normalized.companion_type,
            items=items,
        )

    def _normalize_request(self, request: RuleItineraryRequest) -> NormalizedRuleRequest:
        nights, days = self._normalize_duration(
            nights=request.nights,
            days=request.days,
            duration_label=request.duration_label,
        )
        concepts = request.concepts or DEFAULT_CONCEPTS
        style = request.style or DEFAULT_STYLE
        companion_type = request.companion_type or DEFAULT_COMPANION
        budget_band = self._normalize_budget(request.budget_value, request.budget_band)

        continent = (request.continent or "asia").strip().lower()
        country = (request.country or "").strip().lower()
        city = (request.city or "").strip().lower()

        if not city and country:
            city = DEFAULT_CITY_BY_COUNTRY.get(country, "")
        if not city:
            city = "seoul"
        if not country:
            country = next(
                (country_name for country_name, mapped_city in DEFAULT_CITY_BY_COUNTRY.items() if mapped_city == city),
                "korea",
            )

        return NormalizedRuleRequest(
            continent=continent,
            country=country,
            city=city,
            travelers=request.travelers or 2,
            nights=nights,
            days=days,
            budget_band=budget_band,
            concepts=concepts,
            style=style,
            companion_type=companion_type,
        )

    def _normalize_duration(
        self,
        *,
        nights: int | None,
        days: int | None,
        duration_label: str | None,
    ) -> tuple[int, int]:
        if duration_label:
            match = re.search(r"(\d+)\s*박\s*(\d+)\s*일", duration_label)
            if match:
                return int(match.group(1)), int(match.group(2))

        if nights and days:
            return nights, days
        if nights and not days:
            return nights, nights + 1
        if days and not nights:
            return max(days - 1, 1), days
        return 2, 3

    def _normalize_budget(self, budget_value: int | None, budget_band: str | None) -> str:
        if budget_band:
            return budget_band
        if budget_value is None:
            return "medium"
        if budget_value < 100:
            return "low"
        if budget_value < 300:
            return "medium"
        return "high"

    def _build_items(
        self,
        request: NormalizedRuleRequest,
        city_catalog: CityPlaceCatalog,
    ) -> list[RuleItineraryItem]:
        scored_places = sorted(
            city_catalog.places,
            key=lambda place: self._base_score(place, request),
            reverse=True,
        )

        area_scores = self._group_area_scores(scored_places, request)
        preferred_areas = [area for area, _ in sorted(area_scores.items(), key=lambda item: item[1], reverse=True)]
        used_ids: set[str] = set()
        items: list[RuleItineraryItem] = []

        for day_number in range(1, request.days + 1):
            day_area = self._pick_day_area(preferred_areas, scored_places, used_ids, day_number)

            for slot in TIME_SLOTS:
                chosen = self._pick_place_for_slot(
                    scored_places=scored_places,
                    request=request,
                    time_slot=slot,
                    used_ids=used_ids,
                    preferred_area=day_area,
                )
                if chosen is None:
                    continue

                used_ids.add(chosen.id)
                main_category = chosen.category[0] if chosen.category else "sightseeing"
                items.append(
                    RuleItineraryItem(
                        day_number=day_number,
                        time_slot=slot,
                        place_name=self._localize_place_name(chosen),
                        category=main_category,
                        area=self._localize_area(chosen.area),
                        notes=self._build_note(
                            place=chosen,
                            request=request,
                            time_slot=slot,
                            day_number=day_number,
                        ),
                    )
                )

        return items

    def _group_area_scores(self, places: list[PlaceData], request: NormalizedRuleRequest) -> dict[str, int]:
        area_scores: dict[str, int] = defaultdict(int)
        for place in places:
            area_scores[place.area] += self._base_score(place, request)
        return area_scores

    def _pick_day_area(
        self,
        preferred_areas: list[str],
        places: list[PlaceData],
        used_ids: set[str],
        day_number: int,
    ) -> str | None:
        if preferred_areas:
            for offset in range(len(preferred_areas)):
                candidate_area = preferred_areas[(day_number - 1 + offset) % len(preferred_areas)]
                if any(place.area == candidate_area and place.id not in used_ids for place in places):
                    return candidate_area
        return None

    def _pick_place_for_slot(
        self,
        *,
        scored_places: list[PlaceData],
        request: NormalizedRuleRequest,
        time_slot: str,
        used_ids: set[str],
        preferred_area: str | None,
    ) -> PlaceData | None:
        available_places = [place for place in scored_places if place.id not in used_ids]
        slot_fitting_places = [place for place in available_places if time_slot in place.time_fit]
        candidate_pool = slot_fitting_places or available_places

        ranked_candidates = sorted(
            candidate_pool,
            key=lambda place: self._slot_score(
                place=place,
                request=request,
                time_slot=time_slot,
                preferred_area=preferred_area,
            ),
            reverse=True,
        )
        return ranked_candidates[0] if ranked_candidates else None

    def _localize_place_name(self, place: PlaceData) -> str:
        return PLACE_NAME_KO.get(place.id, place.name)

    def _localize_area(self, area: str) -> str:
        return AREA_LABEL_KO.get(area, area)

    def _base_score(self, place: PlaceData, request: NormalizedRuleRequest) -> int:
        score = place.priority * 10
        score += len(set(place.category) & set(request.concepts)) * 8

        if request.budget_band in place.budget_level:
            score += 6
        if request.companion_type in place.suitable_for:
            score += 5
        if request.style == "easy" and "easy" in place.pace:
            score += 4
        if request.style == "tight" and "tight" in place.pace:
            score += 4
        if request.style in {"near-stay", "mobility-first"} and (
            "walkable" in place.mobility or "nearby" in place.mobility
        ):
            score += 4

        return score

    def _slot_score(
        self,
        *,
        place: PlaceData,
        request: NormalizedRuleRequest,
        time_slot: str,
        preferred_area: str | None,
    ) -> int:
        score = self._base_score(place, request)

        if time_slot in place.time_fit:
            score += 12
        if preferred_area and place.area == preferred_area:
            score += 9
        if set(place.category) & SLOT_CATEGORY_PREFERENCE[time_slot]:
            score += 5
        if time_slot == "evening" and "food" in place.category:
            score += 4
        if time_slot == "morning" and ("relax" in place.category or "cafe" in place.category):
            score += 3
        if request.style == "near-stay" and place.area == preferred_area:
            score += 3

        return score

    def _build_note(
        self,
        *,
        place: PlaceData,
        request: NormalizedRuleRequest,
        time_slot: str,
        day_number: int,
    ) -> str:
        _ = day_number
        place_name = self._localize_place_name(place)
        area_name = self._localize_area(place.area)
        concept_text = ", ".join(CONCEPT_LABEL_KO.get(concept, concept) for concept in request.concepts)
        slot_reason = TIME_SLOT_REASON_KO[time_slot]
        budget_reason = BUDGET_REASON_KO[request.budget_band]
        companion_reason = COMPANION_REASON_KO[request.companion_type]

        return (
            f"{place_name}은(는) {slot_reason} {concept_text} 중심 여행의 분위기와 잘 맞습니다. "
            f"{area_name} 주변으로 동선을 묶기 좋아 이동이 단순하고, {budget_reason} "
            f"{companion_reason}"
        )


rule_itinerary_service = RuleItineraryService()
