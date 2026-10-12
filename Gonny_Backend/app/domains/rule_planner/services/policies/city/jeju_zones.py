from __future__ import annotations

from app.domains.destination_catalog.schemas import PlaceData

from ...travel_estimate import haversine_distance_km

# 이 모듈은 현재 jeju.py의 하루-구역 선택(preferred_area_order/
# same_area_continuity_bonus/neighbor_area_bonus)에는 연결되어 있지 않다 -
# 실측 비교 결과 연결 시 day_car_total/cross-day 이동거리/장소 커버리지가
# 모두 오히려 나빠졌다(원인: Jeju 카탈로그 밀도가 8개 세부 구역으로 쪼개기엔
# 아직 부족해 "같은/인접 구역에 머문다"는 신호보다 "매일 새 구역을 쓴다"는
# 기존 다양화 로직이 더 세분화된 구역 사이에서 더 먼 거리로 이어졌고, 슬롯
# 전환 보너스는 이미 거리 기반 coordinate_area_transition_bonus가 선점해
# 구역 레이블 보너스를 거의 무력화했다 - PR 설명 참고). 대신 구역별 장소
# 부족 현황 진단(이 작업의 4번 항목)이 이 모듈의 ZONE_CENTERS/resolve_zone을
# 사용한다. 장소 데이터가 더 채워지면 하루-구역 묶기 재시도의 기반이 된다.
#
# 가정값 (2026-10 destinations/jeju.json 65곳 좌표 분석 기반).
#
# 기존 area(east-jeju/west-jeju/seogwipo-west/seongsan) 4분류 중 east-jeju는
# 제주시 동문시장 인근 군집(12곳, 경도 약 126.52~126.53)과 구좌·월정리 북동
# 군집(14곳, 경도 약 126.66~126.86)으로 뚜렷하게 양분된다 - 두 군집 사이
# ~12km 구간에는 장소가 전혀 없다. 하나의 area로 묶인 채로는 숙소/하루 일정이
# 그 구간을 가로질러 흩어질 수 있으므로, east-jeju를 jeju-city/dongbu 두
# 구역으로 쪼갠다. west-jeju(15곳)/seogwipo-west(11곳)/seongsan(12곳)은 내부
# 최대 분산이 13~16km로 비교적 조밀해 추가로 쪼개지 않는다
# (west-jeju->bukseo, seogwipo-west->jungmun-andeok로 이름만 재부여).
#
# namdong(남동/표선·남원)·seogwipo-si(서귀포시내)·daejeong(대정)은 현재
# destinations/jeju.json·accommodations/jeju.json 어디에도 장소가 없어
# 실측 중심점을 낼 수 없다 - 좌표를 비워 두면 nearest_zone()이 이 구역을
# 영원히 고르지 못해(항상 거리 0인 실측 구역이 더 가깝게 측정됨) 구역 부족
# 진단(이 작업의 4번 항목)에 드러나지도 않으므로, 제주 행정 중심지(읍/동
# 사무소) 좌표로 근사해 둔다. 장소 데이터가 채워지면 실측 중심점으로
# 교체해야 한다.
ZONE_CENTERS: dict[str, tuple[float, float]] = {
    "jeju-city": (33.511545, 126.526385),  # 실측 중심점 (12곳)
    "dongbu": (33.524966, 126.785864),  # 실측 중심점 (14곳)
    "seongsan": (33.445751, 126.915765),  # 실측 중심점 (12곳)
    "namdong": (33.302100, 126.777600),  # 근사치: 표선면·남원읍사무소 중간점
    "seogwipo-si": (33.254100, 126.560000),  # 근사치: 서귀포시청 인근
    "jungmun-andeok": (33.261064, 126.397893),  # 실측 중심점 (11곳)
    "daejeong": (33.213600, 126.250600),  # 근사치: 대정읍사무소(모슬포) 인근
    "bukseo": (33.418381, 126.302778),  # 실측 중심점 (15곳)
}

# 가정값: 제주 해안 일주도로(1132번) 순서를 따르는 고리형 인접관계.
# 시계방향으로 jeju-city -> dongbu -> seongsan -> namdong -> seogwipo-si ->
# jungmun-andeok -> daejeong -> bukseo -> jeju-city. 섬을 가로지르는 대각선
# 인접(예: jeju-city <-> seogwipo-si)은 실제 이동시간이 해안 경로보다 길어
# "인접"으로 보지 않는다 - 각 구역은 고리 위 양 옆 구역 2개와만 인접.
ZONE_RING_ORDER = [
    "jeju-city",
    "dongbu",
    "seongsan",
    "namdong",
    "seogwipo-si",
    "jungmun-andeok",
    "daejeong",
    "bukseo",
]


def _build_ring_adjacency(order: list[str]) -> dict[str, set[str]]:
    zone_count = len(order)
    return {
        zone: {order[(index - 1) % zone_count], order[(index + 1) % zone_count]}
        for index, zone in enumerate(order)
    }


ZONE_ADJACENCY: dict[str, set[str]] = _build_ring_adjacency(ZONE_RING_ORDER)

# 가정값: 좌표가 없는 장소(현재 제주 카탈로그엔 없지만 방어적으로 둔다)는
# 기존 area 4분류 중 그 area의 좌표가 실제로 더 많이 모인 구역으로 근사한다.
# 좌표 기반으로 재계산할 수 없다고 구역 자체를 비워 두면(None) 그 장소가
# 하루-구역 묶기 로직에서 완전히 누락되어 오히려 더 나쁜 결과(구역 불문하고
# 아무 데나 배치)를 낳을 수 있으므로, 근사치를 쓰는 쪽을 선택했다.
FALLBACK_ZONE_BY_AREA: dict[str, str] = {
    "east-jeju": "jeju-city",
    "west-jeju": "bukseo",
    "seogwipo-west": "jungmun-andeok",
    "seongsan": "seongsan",
}


def nearest_zone(latitude: float, longitude: float) -> str:
    return min(
        ZONE_CENTERS,
        key=lambda zone: haversine_distance_km(latitude, longitude, *ZONE_CENTERS[zone]),
    )


def resolve_zone(place: PlaceData) -> str | None:
    if place.latitude is not None and place.longitude is not None:
        return nearest_zone(place.latitude, place.longitude)
    return FALLBACK_ZONE_BY_AREA.get(place.area)


def zone_distance_km(zone_a: str, zone_b: str) -> float | None:
    if zone_a not in ZONE_CENTERS or zone_b not in ZONE_CENTERS:
        return None
    return round(haversine_distance_km(*ZONE_CENTERS[zone_a], *ZONE_CENTERS[zone_b]), 2)


def are_adjacent_zones(zone_a: str, zone_b: str) -> bool:
    return zone_b in ZONE_ADJACENCY.get(zone_a, set())
