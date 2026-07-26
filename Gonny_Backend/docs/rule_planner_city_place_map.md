# Rule Planner City Place Map

이 문서는 현재 `Rule Planner`가 사용하는 도시별 권역-장소 매핑표다.  
정책 문서가 “왜 이 권역을 우선하는가”를 설명한다면, 이 문서는 “각 권역에 지금 어떤 장소가 들어가 있는가”를 빠르게 확인하기 위한 운영 문서다.  
보강 우선순위는 `docs/rule_planner_data_priority.md`에서 함께 관리한다.

## 기준

- 소스 오브 트루스:
  - `app/data/destinations/seoul.json`
  - `app/data/destinations/busan.json`
  - `app/data/destinations/jeju.json`
- 권역 키는 영문 슬러그 기준으로 관리한다.
- 사용자 노출 라벨은 `AREA_LABEL_KO` 기준으로 해석한다.
- 아래 표는 현재 데이터 파일에 들어 있는 장소 기준이며, 권역 재편 시 함께 갱신해야 한다.

## Seoul

| `slug` | 노출 라벨 | 현재 포함 장소 | 주요 카테고리 | 운영 포인트 |
| --- | --- | --- | --- | --- |
| `jongno` | 종로 | Gyeongbokgung Palace, Bukchon Hanok Village, Insadong Street, 창덕궁과 후원, 익선동 한옥거리 | `sightseeing`, `culture`, `food`, `photo`, `relax` | 서울 전통/문화 중심축. 문화·식도락·가벼운 산책을 한 권역에서 묶기 좋다. |
| `euljiro` | 을지로 | 을지로 노포 골목, 세운상가, 청계천박물관, 을지로 노가리골목, 대림상가 | `food`, `culture`, `nightlife`, `photo`, `shopping`, `sightseeing` | 식도락/야간 축에 저녁형 로컬 골목과 상가 산책 카드가 더해져 을지로의 시간대 개성이 한층 또렷해졌다. |
| `myeongdong` | 명동 | Myeongdong, 명동성당, 한국은행 화폐박물관 | `shopping`, `food`, `sightseeing`, `culture`, `photo` | 쇼핑 허브에 랜드마크와 실내 문화 카드가 붙어 도착·출발일 활용성이 좋아졌다. |
| `dongdaemun` | 동대문 | 동대문디자인플라자, 흥인지문, 동대문 쇼핑타운 | `culture`, `photo`, `shopping`, `sightseeing` | 문화·야간 사진·쇼핑 흐름이 한 권역 안에서 이어지도록 보강된 중심 보조 권역. |
| `seongsu` | 성수 | 성수동 카페거리, 서울숲, S-Factory | `shopping`, `food`, `photo`, `relax`, `nature`, `culture` | 카페/쇼핑 축에 산책형 공원과 전시형 공간이 붙어 시간대 편성이 훨씬 유연해졌다. |
| `hongdae` | 홍대 | Hongdae, 망원시장, 연남동 경의선숲길, KT&G 상상마당 홍대, 트릭아이미술관, 롤링홀, AK플라자 홍대 | `shopping`, `food`, `nightlife`, `culture`, `relax`, `photo`, `activity` | 친구 여행·저녁 분위기 축에 라이브 공연장과 실내 쇼핑 카드가 더해져 홍대의 야간 개성과 우천 대응력이 더 선명해졌다. |
| `yeouido` | 여의도 | Yeouido Hangang Park, Eland Hangang Cruise, 더현대 서울, 63 Square, KBS홀, 세마벙커 | `relax`, `nature`, `photo`, `activity`, `local_experience`, `shopping`, `food`, `sightseeing`, `culture`, `nightlife` | 한강 휴식 축에 공연장과 전시형 실내 문화 카드가 더해져 여의도 일정의 우천 대응과 저녁 문화 선택지가 좋아졌다. |
| `gangnam` | 강남 | Gangnam Station Area, COEX Mall and Starfield Library, 압구정 로데오 거리, 봉은사, 선정릉, 현대 모터스튜디오 서울, K현대미술관 | `shopping`, `food`, `culture`, `photo`, `nightlife`, `relax`, `nature` | 도심형 쇼핑 축에 전시형 문화 공간이 더해져 강남 일정의 실내 문화 밀도와 우천 대응력이 좋아졌다. |
| `jamsil` | 잠실 | 석촌호수 산책로, Lotte World Adventure, Seoul Sky, 롯데월드몰, 롯데월드 아쿠아리움, 한성백제박물관 | `relax`, `photo`, `nature`, `activity`, `theme_park`, `family`, `shopping`, `food`, `sightseeing`, `culture` | 가족·액티비티 축에 실내 가족 체험과 역사 박물관 카드가 더해져 잠실 일정의 우천 대응과 문화 결이 훨씬 좋아졌다. |
| `itaewon` | 이태원 | 이태원 경리단길, 전쟁기념관, 이태원 앤틱가구거리 | `food`, `culture`, `nightlife`, `photo`, `sightseeing` | 저녁 식음 축에 낮 시간 문화·산책 카드가 붙어 전환 권역으로 쓰기 쉬워졌다. |
| `namsan` | 남산 | N Seoul Tower, 남산 케이블카, 남산공원 산책로 | `sightseeing`, `photo`, `relax`, `activity`, `nature` | 전망형 랜드마크에 이동 체험과 산책 동선이 추가돼 연속 코스 운영이 가능해졌다. |

## Busan

| `slug` | 노출 라벨 | 현재 포함 장소 | 주요 카테고리 | 운영 포인트 |
| --- | --- | --- | --- | --- |
| `nampo` | 남포 | 자갈치시장, 국제시장, BIFF 광장, 태종대, 용두산공원, 보수동 책방골목, 부산타워, 부산근현대역사관 | `food`, `culture`, `shopping`, `nightlife`, `nature`, `sightseeing`, `photo`, `relax`, `family` | 원도심 식도락/시장 축에 전망형 야경과 실내 근대문화 카드가 더해져 남포 권역의 저녁·우천 대응력과 개성이 더 선명해졌다. |
| `songdo` | 송도 | 감천문화마을, 송도 해상케이블카, 송도해수욕장, 암남공원, 송도용궁구름다리, 송도스카이파크, 부산현대미술관, 흰여울문화마을 | `sightseeing`, `culture`, `photo`, `activity`, `relax`, `nature`, `family` | 해변·공원·전망 포인트에 실내 전시와 감성 산책 카드가 더해지면서 송도는 우천·노을 시간대 대응까지 갖춘 바다 보조 축이 됐다. |
| `gwangalli` | 광안리 | 광안리 해변, 민락수변공원, 온천천 카페거리, Millac The Market, F1963 | `relax`, `food`, `photo`, `nightlife`, `shopping`, `culture` | 저녁 바다 분위기 축에 실내 식음·문화 카드가 더해져 우천 대응과 친구 여행 활용 폭이 넓어졌다. |
| `haeundae` | 해운대 | 해운대 해수욕장, 동백섬 산책로, 해운대 블루라인파크, Skyline Luge Busan, SEA LIFE Busan Aquarium, BUSAN X the SKY | `relax`, `photo`, `sightseeing`, `nature`, `activity`, `local_experience`, `culture` | 부산 대표 메인 권역으로 바다·산책·액티비티에 실내 가족형 랜드마크까지 묶을 수 있게 됐다. |

## Jeju

| `slug` | 노출 라벨 | 현재 포함 장소 | 주요 카테고리 | 운영 포인트 |
| --- | --- | --- | --- | --- |
| `east-jeju` | 제주 동부 | 함덕해수욕장, 월정리 해변, 비자림, 동문시장, Jeju Rail Bike, 제주돌문화공원, 해녀박물관, 스누피가든, 델문도 김녕 | `relax`, `photo`, `nature`, `food`, `shopping`, `culture`, `activity`, `local_experience`, `sightseeing`, `family` | 자연·시장·체험 축에 전시형 가족 스팟과 오션뷰 카페 카드가 더해져 동부 권역의 우천 대응력과 휴식 활용도가 더 좋아졌다. |
| `seongsan` | 성산 | 성산일출봉, 섭지코지, Aqua Planet Jeju, 광치기해변, 성읍민속마을 | `sightseeing`, `nature`, `photo`, `relax`, `activity`, `local_experience`, `family`, `culture` | 제주 대표 랜드마크 축에 해안 포인트와 전통 문화 카드가 더해져 일정 폭이 훨씬 넓어졌다. |
| `seogwipo-west` | 서귀포 서부 | 카멜리아힐, 중문색달해변, 오설록 티뮤지엄, 여미지식물원, 제주 테디베어뮤지엄 | `photo`, `nature`, `relax`, `food`, `culture`, `family` | 풍경형 드라이브 축에 실내 정원·가족형 박물관 카드가 붙어 우천 대응력이 좋아졌다. |
| `west-jeju` | 제주 서부 | 애월 카페거리, 한림공원, 협재해수욕장, ARTE Museum Jeju, 제주 유리의성, 9.81 파크 제주, 새별오름 | `food`, `relax`, `photo`, `nature`, `family`, `culture`, `activity` | 카페·해변 중심 휴식 권역에 액티비티와 노을형 마무리 카드가 붙어 서부 일정의 체험 폭과 시간대 대응력이 넓어졌다. |

## 유지보수 체크리스트

권역 데이터 수정 시 아래 항목을 같이 확인한다.

1. `app/data/destinations/*.json`의 `area` 값이 영문 슬러그로 통일되어 있는지
2. `AREA_LABEL_KO`에 노출 라벨이 있는지
3. `docs/rule_planner_city_policies.md`의 권역 설명과 어긋나지 않는지
4. `docs/rule_planner_city_diagrams.md`의 동선/인접 권역 구조와 충돌하지 않는지
5. 특정 권역에 장소가 너무 적어졌다면 정책상 과도한 편향이 생기지 않는지
