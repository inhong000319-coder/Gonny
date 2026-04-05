from __future__ import annotations

import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "app" / "data" / "destinations"


ACTIVITY_PLACE_MAP: dict[str, list[dict[str, object]]] = {
    "busan": [
        {
            "id": "skyline-luge-busan",
            "name": "Skyline Luge Busan",
            "category": ["activity", "local_experience", "photo"],
            "budget_level": ["medium"],
            "suitable_for": ["couple", "friend", "family"],
            "time_fit": ["afternoon", "evening"],
            "area": "osiria",
            "duration_hours": 3,
            "priority": 8,
            "pace": ["easy"],
            "mobility": ["taxi-needed"],
            "summary": "부산 바다 분위기를 보면서 속도감 있는 체험을 즐기기 좋은 액티비티예요.",
            "official_url": "https://busan.skylineluge.kr/en/",
            "booking_hint": "해 질 무렵까지 머물면 바다 풍경과 야간 분위기를 함께 챙기기 좋아요.",
            "slot_bias": {"afternoon": 9, "evening": 6, "morning": -4},
            "mood_keywords": ["신나는", "속도감 있는", "친구와 가기 좋은"],
            "highlight_tags": ["부산 체험형 코스", "오시리아 액티비티", "바다 전망"],
            "note_templates": [
                "{place_name}은(는) 부산에서 풍경만 보는 일정보다 몸으로 즐기는 시간을 넣고 싶을 때 잘 맞아요."
            ],
        }
    ],
    "gangneung": [
        {
            "id": "haslla-art-world",
            "name": "Haslla Art World",
            "category": ["activity", "local_experience", "photo", "culture"],
            "budget_level": ["medium"],
            "suitable_for": ["solo", "couple", "friend", "family"],
            "time_fit": ["morning", "afternoon"],
            "area": "gangdong",
            "duration_hours": 3,
            "priority": 8,
            "pace": ["easy"],
            "mobility": ["taxi-needed"],
            "summary": "강릉 바다 풍경과 예술 공간을 함께 즐기기 좋은 체험형 미술공원이에요.",
            "official_url": "https://www.haslla.kr/web2018/sub3/3_sub1.php",
            "booking_hint": "실내 전시와 야외 조각공원을 같이 보려면 오전이나 낮 시간대로 여유 있게 잡는 편이 좋아요.",
            "slot_bias": {"morning": 7, "afternoon": 8, "evening": -8},
            "mood_keywords": ["감각적인", "사진 남기기 좋은", "강릉다운"],
            "highlight_tags": ["바다와 예술", "강릉 체험 코스", "포토 스폿"],
            "note_templates": [
                "{place_name}은(는) 강릉에서 바다와 전시를 한 번에 즐기고 싶을 때 만족도가 높은 편이에요."
            ],
        }
    ],
    "gyeongju": [
        {
            "id": "gyeongju-expo-grand-park",
            "name": "Gyeongju Expo Grand Park",
            "category": ["activity", "local_experience", "culture", "photo"],
            "budget_level": ["medium"],
            "suitable_for": ["solo", "couple", "friend", "family"],
            "time_fit": ["afternoon", "evening"],
            "area": "bomun",
            "duration_hours": 3,
            "priority": 8,
            "pace": ["easy"],
            "mobility": ["taxi-needed"],
            "summary": "경주 역사 분위기를 미디어아트와 전시, 야간 콘텐츠로 풀어낸 복합 체험 공간이에요.",
            "official_url": "https://english.visitkorea.or.kr/svc/whereToGo/locIntrdn/rgnContentsView.do?vcontsId=93384",
            "booking_hint": "보문단지 동선과 같이 묶으면 낮부터 밤까지 자연스럽게 이어가기 좋아요.",
            "slot_bias": {"afternoon": 8, "evening": 9, "morning": -4},
            "mood_keywords": ["입체적인", "야간에도 좋은", "경주다운"],
            "highlight_tags": ["경주 체험형 공원", "미디어아트", "보문단지 코스"],
            "note_templates": [
                "{place_name}은(는) 경주에서 유적 관람만으로는 아쉬울 때 체험형 콘텐츠를 더하기 좋아요."
            ],
        }
    ],
    "seoul": [
        {
            "id": "lotte-world-adventure",
            "name": "Lotte World Adventure",
            "category": ["activity", "theme_park", "family"],
            "budget_level": ["medium", "high"],
            "suitable_for": ["couple", "friend", "family"],
            "time_fit": ["morning", "afternoon", "evening"],
            "area": "jamsil",
            "duration_hours": 4,
            "priority": 8,
            "pace": ["easy", "tight"],
            "mobility": ["subway-friendly"],
            "summary": "서울에서 하루를 통째로 써도 아깝지 않은 대표 실내 놀이공원이에요.",
            "official_url": "https://adventure.lotteworld.com/eng/main/index.do",
            "booking_hint": "주말이나 성수기에는 입장권과 매직패스를 미리 확인해두는 편이 좋아요.",
            "full_day_recommended": True,
            "full_day_notes": {
                "morning": [
                    "롯데월드 어드벤처, 오전부터 대표 어트랙션을 중심으로 시작하기 좋아요!",
                    "입장 직후에는 대기 시간이 길어지기 전에 인기 놀이기구를 먼저 타두면 하루 흐름이 훨씬 편해져요.",
                    "실내 동선이 잘 잡혀 있어서 날씨 영향을 덜 받고 신나는 분위기로 텐션을 올리기 좋아요.",
                    "점심은 파크 안에서 간단하게 해결해두면 오후 어트랙션과 퍼레이드 동선을 끊기지 않게 이어가기 좋아요.",
                ],
                "afternoon": [
                    "롯데월드 어드벤처, 오후에는 공연과 어트랙션을 같이 묶어서 즐기기 좋아요!",
                    "한창 활기가 올라오는 시간대라 사진 포인트나 시즌 퍼레이드까지 함께 챙기면 만족도가 높아요.",
                    "오전에 강한 놀이기구를 탔다면 오후에는 실내 포토존이나 비교적 가벼운 어트랙션으로 리듬을 조절하기 좋아요.",
                    "중간에 디저트나 간식을 한 번 넣어두면 저녁까지 지치지 않고 오래 즐기기 편해요.",
                ],
                "evening": [
                    "롯데월드 어드벤처, 저녁에는 야간 분위기까지 보고 마무리하기 좋아요!",
                    "조명이 켜진 뒤에는 같은 공간도 분위기가 달라져서 낮과는 또 다른 재미가 살아나요.",
                    "마지막에는 아쉬웠던 어트랙션을 한두 개 더 타거나 기념품 구경까지 묶어서 천천히 정리하면 좋아요.",
                    "저녁 식사도 파크 안이나 바로 주변에서 해결할 수 있어서 하루를 한 장소에서 안정감 있게 마무리하기 좋아요.",
                ],
            },
            "mood_keywords": ["활기찬", "신나는", "함께 즐기기 좋은"],
            "highlight_tags": ["대표 놀이공원", "실내 액티비티", "가족·친구 코스"],
            "note_templates": [
                "{place_name}은(는) 서울 일정에 확실한 체험 요소를 넣고 싶을 때 만족도가 높은 장소예요."
            ],
        },
        {
            "id": "e-land-hangang-cruise",
            "name": "Eland Hangang Cruise",
            "category": ["activity", "local_experience", "photo"],
            "budget_level": ["medium", "high"],
            "suitable_for": ["solo", "couple", "friend", "family"],
            "time_fit": ["afternoon", "evening"],
            "area": "yeouido",
            "duration_hours": 2,
            "priority": 7,
            "pace": ["easy"],
            "mobility": ["subway-friendly"],
            "summary": "한강 위에서 서울 스카이라인을 다른 각도로 볼 수 있는 체험이에요.",
            "official_url": "https://elandcruise.com/",
            "booking_hint": "석양 시간대나 야경 시간대를 노리면 분위기가 더 좋아요.",
            "slot_bias": {"afternoon": 4, "evening": 10},
            "mood_keywords": ["여유로운", "야경이 어울리는", "기억에 남는"],
            "highlight_tags": ["한강 체험", "서울 야경", "기분 전환 코스"],
            "note_templates": [
                "{place_name}은(는) 서울 풍경을 걷는 대신 물 위에서 한 번 더 느껴보고 싶을 때 잘 어울려요."
            ],
        },
    ],
    "tokyo": [
        {
            "id": "tokyo-disneysea",
            "name": "Tokyo DisneySea",
            "category": ["activity", "theme_park", "photo"],
            "budget_level": ["high"],
            "suitable_for": ["couple", "friend", "family"],
            "time_fit": ["morning", "afternoon", "evening"],
            "area": "bay-area",
            "duration_hours": 8,
            "priority": 9,
            "pace": ["easy", "tight"],
            "mobility": ["train-friendly"],
            "summary": "도쿄에서만 경험할 수 있는 대표 테마파크라 하루를 통째로 써도 아깝지 않아요.",
            "official_url": "https://www.tokyodisneyresort.jp/en/tds/",
            "booking_hint": "입장권과 인기 어트랙션 우선 이용 방법을 미리 확인해두면 훨씬 수월해요.",
            "full_day_recommended": True,
            "full_day_notes": {
                "morning": [
                    "도쿄 디즈니씨, 오전부터 인기 어트랙션 중심으로 시작하기 좋아요!",
                    "입장 직후에는 대기 줄이 길어지기 전에 대표 놀이기구를 먼저 공략해두면 하루 흐름이 훨씬 편해져요.",
                    "파크 자체 분위기가 특별해서 처음 들어가는 순간부터 도쿄에서만 가능한 하루를 시작하는 느낌이 분명해요.",
                    "점심은 이동 동선 안에서 가볍게 해결해두면 오후 쇼나 어트랙션으로 자연스럽게 이어가기 좋아요.",
                ],
                "afternoon": [
                    "도쿄 디즈니씨, 오후에는 구역별 분위기를 넓게 즐기기 좋아요!",
                    "놀이기구만 몰아서 타기보다 쇼, 산책, 포토 스폿을 함께 섞으면 디즈니씨만의 매력이 훨씬 잘 살아나요.",
                    "친구끼리나 커플 일정이라면 중간중간 사진 남기기 좋은 구역을 여유 있게 보는 편이 만족도가 높아요.",
                    "오후 간식까지 파크 안에서 챙기면 이동 없이 리듬을 유지하면서 저녁 시간대로 넘어가기 편해요.",
                ],
                "evening": [
                    "도쿄 디즈니씨, 저녁에는 야경과 퍼포먼스까지 보고 마무리하기 좋아요!",
                    "조명이 켜진 뒤 분위기가 한층 더 살아나서 낮보다 더 기억에 남는 장면이 많아져요.",
                    "마지막에는 아쉬운 어트랙션을 한두 개 더 타거나 기념품 구경까지 천천히 묶어두면 하루가 깔끔하게 정리돼요.",
                    "저녁 식사도 파크 안에서 해결하면 늦은 시간까지 도쿄 디즈니씨의 흐름을 끊기지 않게 즐길 수 있어요.",
                ],
            },
            "mood_keywords": ["특별한", "하루를 크게 쓰는", "설레는"],
            "highlight_tags": ["도쿄 대표 테마파크", "현지 인기 체험", "하루 코스"],
            "note_templates": [
                "{place_name}은(는) 도쿄에서만 가능한 체험을 일정에 넣고 싶을 때 가장 강한 선택지 중 하나예요."
            ],
        },
    ],
    "taipei": [
        {
            "id": "maokong-gondola",
            "name": "Maokong Gondola",
            "category": ["activity", "local_experience", "photo"],
            "budget_level": ["low", "medium"],
            "suitable_for": ["solo", "couple", "friend", "family"],
            "time_fit": ["afternoon", "evening"],
            "area": "wenshan",
            "duration_hours": 2,
            "priority": 8,
            "pace": ["easy"],
            "mobility": ["subway-friendly"],
            "summary": "타이베이에서 산쪽 풍경과 차 문화를 함께 느끼기 좋은 대표 체험이에요.",
            "official_url": "https://english.gondola.taipei/",
            "booking_hint": "날씨 영향을 받을 수 있어서 비 예보가 있으면 먼저 운행 여부를 확인하는 편이 좋아요.",
            "slot_bias": {"afternoon": 10, "evening": 6, "morning": -4},
            "mood_keywords": ["여유로운", "풍경이 살아나는", "타이베이다운"],
            "highlight_tags": ["마오콩 곤돌라", "타이베이 전망", "차 문화 코스"],
            "note_templates": [
                "{place_name}은(는) 도심 관광만으로는 아쉬울 때 타이베이의 다른 결을 느끼기 좋아요."
            ],
        },
        {
            "id": "taipei-childrens-amusement-park",
            "name": "Taipei Children's Amusement Park",
            "category": ["activity", "theme_park", "family"],
            "budget_level": ["low", "medium"],
            "suitable_for": ["couple", "friend", "family"],
            "time_fit": ["morning", "afternoon", "evening"],
            "area": "shilin",
            "duration_hours": 3,
            "priority": 7,
            "pace": ["easy"],
            "mobility": ["subway-friendly"],
            "summary": "타이베이에서 가볍게 놀이공원 분위기를 즐기기 좋은 가족형 테마파크예요.",
            "official_url": "https://travel.taipei/en/attraction/details/671",
            "booking_hint": "스린 야시장이나 과학관 동선과 함께 묶으면 반나절 코스로 쓰기 좋아요.",
            "slot_bias": {"morning": 7, "afternoon": 5, "evening": -2},
            "mood_keywords": ["경쾌한", "가볍게 즐기는", "가족과 가기 좋은"],
            "highlight_tags": ["타이베이 놀이공원", "스린 코스", "반나절 액티비티"],
            "note_templates": [
                "{place_name}은(는) 타이베이 일정에 부담 없이 넣을 수 있는 밝은 분위기의 체험 코스예요."
            ],
        },
    ],
    "osaka": [
        {
            "id": "universal-studios-japan",
            "name": "Universal Studios Japan",
            "category": ["activity", "theme_park", "photo"],
            "budget_level": ["high"],
            "suitable_for": ["couple", "friend", "family"],
            "time_fit": ["morning", "afternoon", "evening"],
            "area": "bay-area",
            "duration_hours": 8,
            "priority": 9,
            "pace": ["easy", "tight"],
            "mobility": ["train-friendly"],
            "summary": "오사카에서 하루를 통째로 써서 즐기기 좋은 대표 테마파크예요.",
            "official_url": "https://www.usj.co.jp/e/",
            "booking_hint": "입장권과 익스프레스 패스 여부를 먼저 정하면 동선이 훨씬 편해져요.",
            "full_day_recommended": True,
            "full_day_notes": {
                "morning": [
                    "유니버설 스튜디오 재팬, 오전부터 인기 존을 먼저 공략하기 좋아요!",
                    "입장 직후에는 가장 붐비는 어트랙션 쪽으로 먼저 움직여두면 하루 만족도가 확실히 올라가요.",
                    "오사카 일정에 강한 액티비티 하루를 만들고 싶을 때 시작점부터 기대감을 끌어올리기 좋아요.",
                    "점심은 파크 안에서 빠르게 해결해두면 오후 퍼레이드나 인기 존 동선을 끊지 않고 이어가기 편해요.",
                ],
                "afternoon": [
                    "유니버설 스튜디오 재팬, 오후에는 구역별 분위기와 굿즈 구경까지 함께 즐기기 좋아요!",
                    "오전에 강한 어트랙션을 중심으로 돌았다면 오후에는 사진 포인트와 테마 존을 넓게 보는 편이 균형이 좋아요.",
                    "친구나 커플 일정이라면 캐릭터 구역과 시즌 이벤트를 같이 챙기면 훨씬 기억에 남아요.",
                    "중간에 간식이나 시그니처 메뉴를 한 번 넣어두면 저녁까지 체력 관리가 훨씬 편해요.",
                ],
                "evening": [
                    "유니버설 스튜디오 재팬, 저녁에는 야간 분위기까지 즐기며 마무리하기 좋아요!",
                    "해가 지면 파크 분위기가 달라져서 같은 공간도 낮과는 전혀 다른 느낌으로 남아요.",
                    "마지막에는 아쉬웠던 어트랙션을 다시 보거나 기념품을 정리하면서 천천히 하루를 닫아주면 좋아요.",
                    "저녁 식사까지 파크 안이나 바로 주변에서 해결하면 하루 코스가 흔들리지 않고 깔끔하게 끝나요.",
                ],
            },
            "mood_keywords": ["화려한", "신나는", "하루형 체험"],
            "highlight_tags": ["오사카 대표 테마파크", "하루 코스", "강한 액티비티"],
            "note_templates": [
                "{place_name}은(는) 오사카 일정에 확실한 체험 하루를 넣고 싶을 때 가장 먼저 검토할 만한 장소예요."
            ],
        },
    ],
    "fukuoka": [
        {
            "id": "marine-world-uminonakamichi",
            "name": "Marine World Uminonakamichi",
            "category": ["activity", "local_experience", "family"],
            "budget_level": ["medium"],
            "suitable_for": ["solo", "couple", "friend", "family"],
            "time_fit": ["morning", "afternoon"],
            "area": "seaside",
            "duration_hours": 3,
            "priority": 8,
            "pace": ["easy"],
            "mobility": ["train-friendly"],
            "summary": "규슈 바다를 테마로 꾸민 후쿠오카 대표 아쿠아리움이에요.",
            "official_url": "https://marine-world.jp/",
            "booking_hint": "도심에서 조금 떨어져 있어서 해변 공원 동선과 함께 묶는 편이 좋아요.",
            "slot_bias": {"morning": 9, "afternoon": 3, "evening": -6},
            "mood_keywords": ["시원한", "가족과 가기 좋은", "후쿠오카다운"],
            "highlight_tags": ["규슈 바다 테마", "아쿠아리움", "반나절 체험"],
            "note_templates": [
                "{place_name}은(는) 후쿠오카에서 실내형 체험 코스를 하나 넣고 싶을 때 만족도가 높은 편이에요."
            ],
        },
        {
            "id": "fukuoka-open-top-bus",
            "name": "Fukuoka Open Top Bus",
            "category": ["activity", "local_experience", "photo"],
            "budget_level": ["medium"],
            "suitable_for": ["solo", "couple", "friend", "family"],
            "time_fit": ["afternoon", "evening"],
            "area": "city-center",
            "duration_hours": 2,
            "priority": 7,
            "pace": ["easy"],
            "mobility": ["walkable"],
            "summary": "후쿠오카 시내 주요 풍경을 바람 맞으며 한 번에 둘러보기 좋은 체험이에요.",
            "official_url": "https://fukuokaopentopbus.jp/en/",
            "booking_hint": "예약형 코스라 시간이 맞는 날에 미리 좌석을 잡아두는 편이 좋아요.",
            "slot_bias": {"afternoon": 8, "evening": 7, "morning": -3},
            "mood_keywords": ["가볍게 즐기는", "도시 풍경이 살아나는", "이동이 편한"],
            "highlight_tags": ["오픈톱버스", "후쿠오카 시내 코스", "짧은 체험"],
            "note_templates": [
                "{place_name}은(는) 많이 걷지 않으면서 후쿠오카 시내 분위기를 넓게 보고 싶을 때 잘 맞아요."
            ],
        },
    ],
    "bangkok": [
        {
            "id": "mahanakhon-skywalk",
            "name": "Mahanakhon SkyWalk",
            "category": ["activity", "local_experience", "photo"],
            "budget_level": ["high"],
            "suitable_for": ["solo", "couple", "friend", "family"],
            "time_fit": ["afternoon", "evening"],
            "area": "silom",
            "duration_hours": 2,
            "priority": 8,
            "pace": ["easy"],
            "mobility": ["subway-friendly"],
            "summary": "방콕 스카이라인을 가장 강하게 체감할 수 있는 전망형 액티비티예요.",
            "official_url": "https://kingpowermahanakhon.co.th/about/",
            "booking_hint": "노을 직전이나 야경 시간대로 맞추면 만족도가 훨씬 높아요.",
            "slot_bias": {"afternoon": 8, "evening": 11, "morning": -10},
            "mood_keywords": ["화려한", "도시 야경이 살아나는", "기억에 남는"],
            "highlight_tags": ["방콕 전망 명소", "스카이워크", "야경 코스"],
            "note_templates": [
                "{place_name}은(는) 방콕의 높은 에너지를 한 번에 느끼고 싶을 때 잘 어울리는 체험이에요."
            ],
        }
    ],
    "chiangmai": [
        {
            "id": "chiang-mai-night-safari",
            "name": "Chiang Mai Night Safari",
            "category": ["activity", "local_experience", "family"],
            "budget_level": ["medium"],
            "suitable_for": ["couple", "friend", "family"],
            "time_fit": ["afternoon", "evening"],
            "area": "suburb",
            "duration_hours": 3,
            "priority": 8,
            "pace": ["easy"],
            "mobility": ["taxi-needed"],
            "summary": "치앙마이에서 낮과 밤 사파리 트램을 즐길 수 있는 대표 체험형 공원이에요.",
            "official_url": "https://chiangmainightsafari.com/en/",
            "booking_hint": "영어 트램 시간과 야간 프로그램 시간을 미리 보고 가면 훨씬 알차게 즐길 수 있어요.",
            "slot_bias": {"afternoon": 4, "evening": 12, "morning": -10},
            "mood_keywords": ["이색적인", "저녁이 살아나는", "가족과 가기 좋은"],
            "highlight_tags": ["나이트 사파리", "트램 체험", "치앙마이 이색 코스"],
            "note_templates": [
                "{place_name}은(는) 치앙마이에서 평범한 야시장 대신 색다른 저녁 체험을 넣고 싶을 때 좋아요."
            ],
        },
        {
            "id": "chiang-mai-celadon-workshop",
            "name": "Chiang Mai Celadon Workshop",
            "category": ["activity", "local_experience", "culture"],
            "budget_level": ["medium"],
            "suitable_for": ["solo", "couple", "friend", "family"],
            "time_fit": ["morning", "afternoon"],
            "area": "suburb",
            "duration_hours": 2,
            "priority": 7,
            "pace": ["easy"],
            "mobility": ["taxi-needed"],
            "summary": "란나 지역 공예 분위기를 손으로 직접 느껴볼 수 있는 도자 워크숍 체험이에요.",
            "official_url": "https://tourismproduct.tourismthailand.org/en/2025/09/01/%E0%B9%80%E0%B8%8A%E0%B8%B5%E0%B8%A2%E0%B8%87%E0%B9%83%E0%B8%AB%E0%B8%A1%E0%B9%88-%E0%B9%80%E0%B8%8B%E0%B8%A5%E0%B8%B2%E0%B8%94%E0%B8%AD%E0%B8%99/",
            "booking_hint": "체험 가능 시간과 예약 여부를 먼저 확인하고 넣으면 동선이 훨씬 깔끔해져요.",
            "slot_bias": {"morning": 10, "afternoon": 4, "evening": -8},
            "mood_keywords": ["차분한", "직접 만들어보는", "치앙마이다운"],
            "highlight_tags": ["란나 공예", "워크숍 체험", "지역색 있는 코스"],
            "note_templates": [
                "{place_name}은(는) 치앙마이에서 구경보다 손으로 직접 해보는 체험을 넣고 싶을 때 잘 어울려요."
            ],
        },
    ],
    "singapore": [
        {
            "id": "universal-studios-singapore",
            "name": "Universal Studios Singapore",
            "category": ["activity", "theme_park", "photo"],
            "budget_level": ["high"],
            "suitable_for": ["couple", "friend", "family"],
            "time_fit": ["morning", "afternoon", "evening"],
            "area": "sentosa",
            "duration_hours": 8,
            "priority": 8,
            "pace": ["easy", "tight"],
            "mobility": ["train-friendly"],
            "summary": "싱가포르에서 하루를 꽉 채워 즐기기 좋은 대표 테마파크예요.",
            "official_url": "https://www.rwsentosa.com/en/attractions/universal-studios-singapore",
            "booking_hint": "센토사 일정과 섞기보다 하루를 분리해서 잡는 편이 훨씬 자연스러워요.",
            "full_day_recommended": True,
            "full_day_notes": {
                "morning": [
                    "유니버설 스튜디오 싱가포르, 오전부터 인기 어트랙션 중심으로 시작하기 좋아요!",
                    "입장 초반에는 대기 시간이 짧은 편이라 대표 놀이기구를 먼저 타두면 하루 전체가 훨씬 여유로워져요.",
                    "센토사에서 가장 확실한 액티비티 하루를 만들고 싶을 때 시작부터 분위기를 올리기 좋아요.",
                    "점심은 파크 안에서 해결해두면 더운 시간대에도 이동 부담 없이 다음 존으로 이어가기 편해요.",
                ],
                "afternoon": [
                    "유니버설 스튜디오 싱가포르, 오후에는 존별 분위기를 넓게 즐기기 좋아요!",
                    "한낮에는 실내 어트랙션이나 공연형 콘텐츠를 섞어두면 체력 분배가 훨씬 자연스러워요.",
                    "테마 구역이 또렷해서 사진 포인트와 굿즈 구경을 함께 넣었을 때 만족도가 높아요.",
                    "중간에 시원한 음료나 간식을 챙기면 저녁까지 지치지 않고 오래 즐기기 좋아요.",
                ],
                "evening": [
                    "유니버설 스튜디오 싱가포르, 저녁에는 남은 어트랙션과 기념품 구경으로 마무리하기 좋아요!",
                    "해가 기울면 낮보다 한결 편안하게 돌아볼 수 있어서 마지막 동선을 정리하기 수월해요.",
                    "아쉬웠던 구역을 한 번 더 보거나 사진을 정리하면서 천천히 하루를 닫아주면 만족감이 커요.",
                    "저녁 식사도 센토사 안에서 이어가기 쉬워서 하루 코스를 끊지 않고 마무리하기 좋아요.",
                ],
            },
            "mood_keywords": ["휴양지와 잘 어울리는", "화려한", "하루형 체험"],
            "highlight_tags": ["싱가포르 대표 테마파크", "센토사 하루 코스", "강한 액티비티"],
            "note_templates": [
                "{place_name}은(는) 싱가포르 일정에 하루를 통째로 써서 노는 날을 만들고 싶을 때 잘 맞아요."
            ],
        },
        {
            "id": "night-safari-singapore",
            "name": "Night Safari Singapore",
            "category": ["activity", "local_experience", "family"],
            "budget_level": ["medium", "high"],
            "suitable_for": ["couple", "friend", "family"],
            "time_fit": ["evening"],
            "area": "mandai",
            "duration_hours": 3,
            "priority": 8,
            "pace": ["easy"],
            "mobility": ["taxi-needed"],
            "summary": "싱가포르에서 밤 시간을 가장 특별하게 써볼 수 있는 대표 야간 체험이에요.",
            "official_url": "https://www.mandai.com/en/night-safari.html",
            "booking_hint": "완전히 어두워진 뒤 분위기가 살아나서 저녁 전후 동선으로 붙이는 편이 좋아요.",
            "slot_bias": {"evening": 14, "afternoon": 2, "morning": -14},
            "mood_keywords": ["이색적인", "밤이 살아나는", "가족과 가기 좋은"],
            "highlight_tags": ["싱가포르 야간 체험", "만다이 코스", "트램 체험"],
            "note_templates": [
                "{place_name}은(는) 싱가포르에서 저녁 시간을 뻔하지 않게 보내고 싶을 때 가장 먼저 보기 좋은 코스예요."
            ],
        }
    ],
    "jeju": [
        {
            "id": "aqua-planet-jeju",
            "name": "Aqua Planet Jeju",
            "category": ["activity", "local_experience", "family"],
            "budget_level": ["medium", "high"],
            "suitable_for": ["solo", "couple", "friend", "family"],
            "time_fit": ["morning", "afternoon"],
            "area": "seongsan",
            "duration_hours": 3,
            "priority": 8,
            "pace": ["easy"],
            "mobility": ["taxi-needed"],
            "summary": "제주 바다를 실내에서 깊이 있게 만나볼 수 있는 대표 체험 공간이에요.",
            "official_url": "https://www.aquaplanet.co.kr/jeju/index.do",
            "booking_hint": "공연 시간과 생태설명회 시간을 함께 보면 훨씬 알차게 둘러볼 수 있어요.",
            "slot_bias": {"morning": 8, "afternoon": 4, "evening": -8},
            "mood_keywords": ["시원한", "몰입감 있는", "가족과 가기 좋은"],
            "highlight_tags": ["제주 바다 체험", "실내 코스", "날씨 영향 적은 일정"],
            "note_templates": [
                "{place_name}은(는) 제주 자연을 조금 다른 방식으로 체험하고 싶을 때 넣기 좋아요."
            ],
        },
        {
            "id": "jeju-rail-bike",
            "name": "Jeju Rail Bike",
            "category": ["activity", "local_experience", "nature"],
            "budget_level": ["low", "medium"],
            "suitable_for": ["couple", "friend", "family"],
            "time_fit": ["morning", "afternoon"],
            "area": "gujwa",
            "duration_hours": 2,
            "priority": 7,
            "pace": ["easy"],
            "mobility": ["taxi-needed"],
            "summary": "제주 동쪽 풍경을 바람 맞으며 가볍게 즐기기 좋은 체험형 코스예요.",
            "official_url": "http://www.jejurailpark.com/m/index.php",
            "booking_hint": "동선이 동부권에 있을 때 묶어두면 이동 효율이 좋아요.",
            "slot_bias": {"morning": 8, "afternoon": 5, "evening": -10},
            "mood_keywords": ["경쾌한", "바람이 느껴지는", "가볍게 즐기는"],
            "highlight_tags": ["제주 동부 체험", "레일바이크", "풍경과 체험 동시 만족"],
            "note_templates": [
                "{place_name}은(는) 제주에서 구경만 하지 않고 직접 움직이며 풍경을 즐기고 싶을 때 잘 맞아요."
            ],
        },
    ],
    "jeonju": [
        {
            "id": "jeonju-hanok-hanbok-experience",
            "name": "Jeonju Hanok Hanbok Experience",
            "category": ["activity", "local_experience", "culture", "photo"],
            "budget_level": ["low", "medium"],
            "suitable_for": ["solo", "couple", "friend", "family"],
            "time_fit": ["morning", "afternoon"],
            "area": "hanok-village",
            "duration_hours": 2,
            "priority": 8,
            "pace": ["easy"],
            "mobility": ["walkable"],
            "summary": "전주한옥마을 분위기를 가장 직접적으로 즐길 수 있는 대표 체험이에요.",
            "official_url": "https://hanok.jeonju.go.kr/contents/exp10",
            "booking_hint": "한옥마을 산책 코스와 함께 붙이면 사진 남기기에도 좋아요.",
            "slot_bias": {"morning": 8, "afternoon": 5, "evening": -6},
            "mood_keywords": ["전주다운", "사진 남기기 좋은", "가볍게 즐기는"],
            "highlight_tags": ["한복 체험", "한옥마을 코스", "전주 감성"],
            "note_templates": [
                "{place_name}은(는) 전주 분위기를 눈으로만 보는 대신 직접 입고 걸어보는 재미가 있어요."
            ],
        },
        {
            "id": "hanbyeok-traditional-play",
            "name": "Hanbyeok Traditional Play Experience",
            "category": ["activity", "local_experience", "culture"],
            "budget_level": ["low", "medium"],
            "suitable_for": ["friend", "family"],
            "time_fit": ["afternoon"],
            "area": "jeonjucheon",
            "duration_hours": 2,
            "priority": 7,
            "pace": ["easy"],
            "mobility": ["walkable"],
            "summary": "전통놀이를 직접 해보면서 전주다운 체험 요소를 더하기 좋아요.",
            "official_url": "https://hanok.jeonju.go.kr/contents/exp9",
            "booking_hint": "단체 체험 위주라 운영 조건을 먼저 확인하고 넣는 편이 좋아요.",
            "slot_bias": {"afternoon": 9, "morning": 2, "evening": -10},
            "mood_keywords": ["정겨운", "함께 웃기 좋은", "전통적인"],
            "highlight_tags": ["전통놀이", "전주 체험", "가족·친구 일정"],
            "note_templates": [
                "{place_name}은(는) 전주에서 조금 더 생활감 있는 체험을 하고 싶을 때 만족도가 높아요."
            ],
        },
    ],
    "kyoto": [
        {
            "id": "toei-kyoto-studio-park",
            "name": "Toei Kyoto Studio Park",
            "category": ["activity", "theme_park", "culture", "photo"],
            "budget_level": ["medium", "high"],
            "suitable_for": ["solo", "couple", "friend", "family"],
            "time_fit": ["morning", "afternoon"],
            "area": "uzumasa",
            "duration_hours": 4,
            "priority": 8,
            "pace": ["easy"],
            "mobility": ["subway-friendly"],
            "summary": "에도 시대 세트장을 직접 걷고 즐길 수 있어서 교토 일정에 확실한 변화를 줘요.",
            "official_url": "https://global.toei-eigamura.com/",
            "booking_hint": "쇼 일정이 있는 날이면 체류 시간을 조금 넉넉하게 잡는 편이 좋아요.",
            "mood_keywords": ["색다른", "몰입감 있는", "사진 남기기 좋은"],
            "highlight_tags": ["교토 테마파크", "시대극 세트장", "체험형 코스"],
            "note_templates": [
                "{place_name}은(는) 사찰 위주 일정 사이에 색다른 체험을 넣고 싶을 때 특히 잘 어울려요."
            ],
        },
        {
            "id": "sagano-romantic-train",
            "name": "Sagano Romantic Train",
            "category": ["activity", "local_experience", "nature", "photo"],
            "budget_level": ["medium"],
            "suitable_for": ["solo", "couple", "friend", "family"],
            "time_fit": ["morning", "afternoon"],
            "area": "arashiyama",
            "duration_hours": 2,
            "priority": 8,
            "pace": ["easy"],
            "mobility": ["subway-friendly"],
            "summary": "아라시야마 풍경을 열차 위에서 천천히 즐길 수 있는 교토 대표 체험이에요.",
            "official_url": "https://www.sagano-kanko.co.jp/en/",
            "booking_hint": "단풍철이나 벚꽃철에는 좌석 예약을 먼저 확인하는 편이 좋아요.",
            "mood_keywords": ["차분한", "풍경이 살아나는", "계절감 있는"],
            "highlight_tags": ["아라시야마 체험", "열차 코스", "계절 풍경"],
            "note_templates": [
                "{place_name}은(는) 교토의 풍경을 걷는 것과는 또 다른 방식으로 느끼고 싶을 때 추천하기 좋아요."
            ],
        },
    ],
    "paris": [
        {
            "id": "disneyland-paris",
            "name": "Disneyland Paris",
            "category": ["activity", "theme_park", "family"],
            "budget_level": ["high"],
            "suitable_for": ["couple", "friend", "family"],
            "time_fit": ["morning", "afternoon", "evening"],
            "area": "marne-la-vallee",
            "duration_hours": 6,
            "priority": 8,
            "pace": ["easy", "tight"],
            "mobility": ["train-friendly"],
            "summary": "파리 근교에서 하루를 크게 써서 즐기기 좋은 대표 테마파크예요.",
            "official_url": "https://www.disneylandparis.com/",
            "booking_hint": "도심 일정과 섞기보다 하루를 통째로 비우는 편이 더 자연스러워요.",
            "mood_keywords": ["화려한", "하루를 크게 쓰는", "설레는"],
            "highlight_tags": ["파리 근교 테마파크", "하루 코스", "가족·커플 일정"],
            "note_templates": [
                "{place_name}은(는) 박물관과 거리 산책 중심 일정에서 완전히 다른 리듬을 만들고 싶을 때 좋아요."
            ],
        },
        {
            "id": "vedettes-du-pont-neuf-cruise",
            "name": "Vedettes du Pont Neuf Cruise",
            "category": ["activity", "local_experience", "photo"],
            "budget_level": ["medium", "high"],
            "suitable_for": ["solo", "couple", "friend", "family"],
            "time_fit": ["afternoon", "evening"],
            "area": "ile-de-la-cite",
            "duration_hours": 2,
            "priority": 8,
            "pace": ["easy"],
            "mobility": ["walkable"],
            "summary": "센강 위에서 파리의 대표 풍경을 한 번에 담기 좋은 클래식한 체험이에요.",
            "official_url": "https://www.vedettesdupontneuf.com/cruises/",
            "booking_hint": "노을 무렵이나 야경 시간대로 맞추면 만족도가 더 높아요.",
            "mood_keywords": ["우아한", "파리다운", "야경이 어울리는"],
            "highlight_tags": ["센강 크루즈", "파리 야경", "대표 체험"],
            "note_templates": [
                "{place_name}은(는) 파리 풍경을 걷는 대신 물 위에서 한 번 정리해보고 싶을 때 잘 맞아요."
            ],
        },
    ],
    "rome": [
        {
            "id": "bioparco-di-roma",
            "name": "Bioparco di Roma",
            "category": ["activity", "nature", "family"],
            "budget_level": ["medium"],
            "suitable_for": ["solo", "couple", "friend", "family"],
            "time_fit": ["morning", "afternoon"],
            "area": "villa-borghese",
            "duration_hours": 3,
            "priority": 7,
            "pace": ["easy"],
            "mobility": ["walkable"],
            "summary": "유적 중심 일정 사이에서 한숨 돌리며 즐기기 좋은 로마의 체험형 공원 코스예요.",
            "official_url": "https://www.bioparco.it/",
            "booking_hint": "보르게세 공원 동선과 함께 묶으면 하루 흐름이 훨씬 자연스러워요.",
            "mood_keywords": ["한결 편안한", "가족과 가기 좋은", "초록이 있는"],
            "highlight_tags": ["보르게세 코스", "체험형 공원", "가벼운 변주"],
            "note_templates": [
                "{place_name}은(는) 로마에서 유적만 계속 보는 흐름을 잠깐 환기해주기에 좋아요."
            ],
        },
        {
            "id": "cinecitta-world",
            "name": "Cinecitta World",
            "category": ["activity", "theme_park", "photo"],
            "budget_level": ["medium", "high"],
            "suitable_for": ["couple", "friend", "family"],
            "time_fit": ["morning", "afternoon", "evening"],
            "area": "castel-romano",
            "duration_hours": 5,
            "priority": 7,
            "pace": ["easy"],
            "mobility": ["taxi-needed"],
            "summary": "영화 스튜디오 콘셉트가 살아 있는 로마 근교 테마파크예요.",
            "official_url": "https://www.cinecittaworld.it/en/",
            "booking_hint": "도심 유적 코스와는 거리가 있어서 하루를 분리해서 쓰는 편이 좋아요.",
            "mood_keywords": ["활기찬", "색다른", "하루를 크게 쓰는"],
            "highlight_tags": ["로마 근교 테마파크", "영화 콘셉트", "체험형 하루 코스"],
            "note_templates": [
                "{place_name}은(는) 로마 일정에 예상 밖의 재미를 넣고 싶을 때 꽤 좋은 선택이에요."
            ],
        },
    ],
    "barcelona": [
        {
            "id": "tibidabo-amusement-park",
            "name": "Tibidabo Amusement Park",
            "category": ["activity", "theme_park", "photo"],
            "budget_level": ["medium", "high"],
            "suitable_for": ["couple", "friend", "family"],
            "time_fit": ["afternoon", "evening"],
            "area": "tibidabo",
            "duration_hours": 4,
            "priority": 8,
            "pace": ["easy"],
            "mobility": ["taxi-needed"],
            "summary": "놀이기구와 전망을 함께 즐길 수 있어서 바르셀로나 일정에 재미를 더해줘요.",
            "official_url": "https://tibidabo.cat/en/amusement-park",
            "booking_hint": "시내 관광과 묶기보다 반나절 이상 따로 잡아두는 편이 좋아요.",
            "mood_keywords": ["경쾌한", "전망이 좋은", "사진 남기기 좋은"],
            "highlight_tags": ["언덕 위 놀이공원", "전망 포인트", "반나절 코스"],
            "note_templates": [
                "{place_name}은(는) 바르셀로나에서 풍경과 액티비티를 한 번에 챙기고 싶을 때 잘 맞아요."
            ],
        },
        {
            "id": "montjuic-cable-car",
            "name": "Montjuic Cable Car",
            "category": ["activity", "local_experience", "photo"],
            "budget_level": ["medium"],
            "suitable_for": ["solo", "couple", "friend", "family"],
            "time_fit": ["morning", "afternoon", "evening"],
            "area": "montjuic",
            "duration_hours": 2,
            "priority": 7,
            "pace": ["easy"],
            "mobility": ["subway-friendly"],
            "summary": "몬주익 언덕 풍경을 편하게 올려다보고 내려다볼 수 있는 대표 체험이에요.",
            "official_url": "https://www.telefericdemontjuic.cat/en/",
            "booking_hint": "몬주익 성이나 주변 미술관 동선과 함께 붙이면 효율이 좋아요.",
            "mood_keywords": ["시원한", "가볍게 즐기는", "풍경 중심의"],
            "highlight_tags": ["케이블카 체험", "몬주익 코스", "도시 풍경"],
            "note_templates": [
                "{place_name}은(는) 바르셀로나를 평지에서만 보지 않고 입체적으로 느끼고 싶을 때 좋아요."
            ],
        },
    ],
}


def upsert_places(payload: dict[str, object], additions: list[dict[str, object]]) -> bool:
    places = list(payload.get("places", []))
    if not places:
        return False

    place_index = {place.get("id"): idx for idx, place in enumerate(places)}
    changed = False

    for addition in additions:
        place_id = str(addition["id"])
        if place_id in place_index:
            places[place_index[place_id]] = addition
        else:
            places.append(addition)
        changed = True

    payload["places"] = places
    return changed


def main() -> None:
    for path in sorted(DATA_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        city = str(payload.get("city", "")).strip().lower()
        additions = ACTIVITY_PLACE_MAP.get(city)
        if not additions:
            continue

        if not upsert_places(payload, additions):
            continue

        with path.open("w", encoding="utf-8", newline="\n") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")

        print(f"updated activity places: {city}")


if __name__ == "__main__":
    main()
