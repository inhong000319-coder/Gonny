# Rule Planner Phase 1 Candidate Places

이 문서는 `Phase 1` 우선 권역에 대해 **다음으로 추가 검토할 후보 장소 리스트 초안**을 정리한 문서다.  
목표는 바로 JSON에 넣는 것이 아니라, **후보 풀을 먼저 좁히고 데이터 입력 기준을 맞추는 것**이다.

함께 보면 좋은 문서:

- `docs/rule_planner_data_priority.md`
- `docs/rule_planner_city_policies.md`
- `docs/rule_planner_city_place_map.md`

## 이번 Phase 1 대상

- `seoul/euljiro`
- `seoul/seongsu`
- `seoul/myeongdong`
- `busan/songdo`

## 사용 원칙

후보를 실제 데이터로 넣기 전 아래 항목을 확인한다.

1. 현재 운영 중인지
2. 여행자 관점에서 장소성이 충분한지
3. 권역 슬러그와 실제 동선이 어긋나지 않는지
4. 기존 장소와 카테고리가 과도하게 중복되지 않는지
5. 우천/가족/저녁 시간대 대체 카드로 의미가 있는지

## Seoul / Euljiro

현재 `euljiro`는 `을지로 노포 골목` 1곳에 크게 의존하고 있다.  
그래서 식도락/야간 감성을 유지하면서도 `culture`, `photo`, `shopping` 쪽 후보를 함께 보강하는 것이 좋다.

| 후보 장소 | 추천 slug 초안 | 추천 카테고리 | 보강 이유 | 검증 메모 |
| --- | --- | --- | --- | --- |
| 세운상가 | `sewoon-plaza` | `culture`, `photo`, `shopping` | 을지로 특유의 공업/레트로 감성과 도시 풍경을 담기 좋다. | 실제 권역을 `euljiro`로 둘지 최종 확인 |
| 청계천박물관 | `cheonggyecheon-museum` | `culture`, `sightseeing`, `photo` | 실내 대안 카드이면서 을지로·청계천 맥락과도 잘 맞는다. | 우천 대체 카드로 가치가 높음 |
| 방산시장 | `bangsan-market` | `shopping`, `culture`, `food` | 시장형/재료형 공간이라 기존 노포 골목과 다른 결의 로컬 경험을 만든다. | 관광 체감이 충분한지 검토 필요 |
| 을지로 조명거리 | `euljiro-lighting-street` | `shopping`, `photo`, `local_experience` | 야간/골목 상권 감성을 확장할 수 있다. | 장소 단위로 넣을지 거리형 스팟으로 넣을지 판단 필요 |

### 우선 추가 추천

1. `sewoon-plaza`
2. `cheonggyecheon-museum`
3. `bangsan-market`

## Seoul / Seongsu

현재 `seongsu`는 `성수동 카페거리` 1곳뿐이라, 정책상 중요도에 비해 데이터 밀도가 매우 낮다.  
그래서 `trend + relax + culture` 조합을 만들 수 있는 대표 스팟을 먼저 채우는 것이 좋다.

| 후보 장소 | 추천 slug 초안 | 추천 카테고리 | 보강 이유 | 검증 메모 |
| --- | --- | --- | --- | --- |
| 서울숲 | `seoul-forest` | `relax`, `nature`, `photo` | 성수 권역에 자연/산책 축을 넣어 시간대 편성이 훨씬 유연해진다. | 대표성 높음, 우선순위 최상 |
| S-Factory | `s-factory` | `culture`, `photo`, `shopping` | 전시/팝업/브랜드 이벤트형 공간으로 성수의 트렌드 감성을 잘 반영한다. | 운영 형태 변동 여부 확인 필요 |
| 아모레 성수 | `amore-seongsu` | `shopping`, `local_experience`, `photo` | 체험형/브랜드형 공간이라 기존 카페거리와 다른 경험값을 준다. | 브랜드 공간이라 장기 운영 여부 확인 |
| 서울숲길 편집숍 거리 | `seoul-forest-shop-street` | `shopping`, `food`, `photo` | 성수동 카페거리 외에 쇼핑/트렌드 축을 분리해줄 수 있다. | 거리형 데이터 입력 여부 검토 |

### 우선 추가 추천

1. `seoul-forest`
2. `s-factory`
3. `amore-seongsu`

## Seoul / Myeongdong

현재 `myeongdong`은 `Myeongdong` 단일 장소 구조라서, 도심 허브 역할에 비해 실제 추천 다양성이 낮다.  
`shopping`에만 치우치지 않게 문화/실내형 대안을 같이 넣는 것이 중요하다.

| 후보 장소 | 추천 slug 초안 | 추천 카테고리 | 보강 이유 | 검증 메모 |
| --- | --- | --- | --- | --- |
| 명동성당 | `myeongdong-cathedral` | `culture`, `sightseeing`, `photo` | 명동 권역의 상징성이 높고 쇼핑 일변도를 완화해준다. | 대표성 높음, 우선순위 최상 |
| 한국은행 화폐박물관 | `bank-of-korea-money-museum` | `culture`, `photo`, `sightseeing` | 실내 대안 카드로 좋고, 도심 역사/건축 포인트도 강하다. | 운영시간 검증 필요 |
| Noon Square | `noon-square` | `shopping`, `food`, `photo` | 기존 명동 메인 거리 데이터와 결이 맞는 상업형 후보. | 장소성이 충분한지 검토 |
| 신세계백화점 본점 | `shinsegae-main-store` | `shopping`, `photo`, `food` | 백화점형 실내 대안 카드로 도착/출발일에 활용 가능하다. | 시즌성 조명/이벤트 편향 주의 |

### 우선 추가 추천

1. `myeongdong-cathedral`
2. `bank-of-korea-money-museum`
3. `shinsegae-main-store`

## Busan / Songdo

현재 `songdo`는 `감천문화마을`, `송도 해상케이블카` 2곳뿐이라, 권역 정체성은 보이지만 코스 볼륨이 작다.  
그래서 바다 전망·산책·체험을 더 붙여 `nampo`와 다른 권역 개성을 확실히 만들어야 한다.

| 후보 장소 | 추천 slug 초안 | 추천 카테고리 | 보강 이유 | 검증 메모 |
| --- | --- | --- | --- | --- |
| 송도해수욕장 | `songdo-beach` | `relax`, `photo`, `sightseeing` | 권역 이름과 직접 연결되는 대표 스팟이라 기본값으로 강하다. | 대표성 최상 |
| 송도용궁구름다리 | `songdo-yonggung-cloud-bridge` | `photo`, `sightseeing`, `activity` | 기존 케이블카와 잘 어울리는 전망/체험형 후보. | 명칭 표기 통일 필요 |
| 암남공원 | `amnam-park` | `nature`, `photo`, `relax` | 자연/산책 축을 보강해 오전 코스 구성에 도움이 된다. | 동선상 `songdo` 편입 적절성 확인 |
| 송도스카이파크 | `songdo-sky-park` | `photo`, `relax`, `sightseeing` | 해안 전망형 권역 성격을 강화한다. | 케이블카와 중복도 검토 |

### 우선 추가 추천

1. `songdo-beach`
2. `songdo-yonggung-cloud-bridge`
3. `amnam-park`

## 바로 입력하지 말고 먼저 할 일

후보를 JSON에 넣기 전에 아래 순서로 점검하는 것을 권장한다.

1. 장소별 공식 페이지 또는 공공 관광 페이지 확인
2. 운영/휴무/폐점 리스크 확인
3. 권역 슬러그 적합성 확인
4. 대표 `category` 3개 이내로 정리
5. `time_fit`, `duration_hours`, `pace`, `mobility` 값 초안 작성
6. 기존 권역 평균 톤과 맞는지 점검

## 다음 작업 추천

이 문서 다음 단계는 아래 둘 중 하나가 가장 자연스럽다.

1. `Phase 1` 후보 12~14곳 중 최종 1차 입력 대상 6~8곳 선택
2. 선택된 후보에 대해 JSON 스키마 기준 초안 데이터 작성
