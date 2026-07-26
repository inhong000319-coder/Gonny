# Rule Planner City Policies

현재 `Rule Planner`는 공통 점수 로직 위에 도시별 정책을 얇게 덧씌우는 구조다.  
목표는 추천 결과를 완전히 하드코딩하는 것이 아니라, 같은 점수대 후보가 있을 때 도시별 동선과 분위기에 더 맞는 권역이 먼저 선택되도록 보정하는 것이다.

시각 자료는 `docs/rule_planner_city_diagrams.md`에서 함께 볼 수 있다.  
권역별 현재 장소 매핑은 `docs/rule_planner_city_place_map.md`에서 함께 관리한다.

## 현재 적용 범위

- 공개 노출 도시: `seoul`, `busan`, `jeju`
- 정책 등록 위치: `app/domains/rule_planner/services/policies/city/__init__.py`
- 공통 슬롯 점수 로직: `app/domains/rule_planner/services/slot_scoring.py`
- 도시별 정책 파일:
  - `app/domains/rule_planner/services/policies/city/seoul.py`
  - `app/domains/rule_planner/services/policies/city/busan.py`
  - `app/domains/rule_planner/services/policies/city/jeju.py`

## 정책이 하는 일

도시 정책은 아래 5가지만 조정한다.

1. `preferred_area_order`
   - 권역별 누적 점수를 바탕으로 하루 대표 권역 우선순위를 정한다.
2. `preferred_area_match_bonus`
   - 해당 일차의 대표 권역과 같은 권역이면 가산점을 준다.
3. `same_area_continuity_bonus`
   - 직전 장소와 같은 권역이면 연속 동선으로 보고 가산점을 준다.
4. `neighbor_area_bonus`
   - 직전 권역과 인접한 권역이면 이동 피로가 덜한 흐름으로 보고 가산점을 준다.
5. `evening_food_bonus`
   - 저녁 슬롯에서 음식/야간 분위기가 강한 장소를 조금 더 밀어준다.

즉, “어느 도시든 같은 공식으로 계산하되, 마지막 정렬 단계에서 도시별 감각을 살짝 반영한다”가 핵심이다.

## Seoul

### 권역 의도

- `jongno`
  - 서울 전통/문화 중심축
  - `culture`, `food`, `relax`에 강함
- `euljiro`
  - 힙한 식음/야간 감성 축
  - `culture`, `food`, 친구 여행에 강함
- `myeongdong`
  - 쇼핑과 접근성이 강한 중심 권역
- `dongdaemun`
  - 문화/쇼핑 연결 권역
- `seongsu`
  - 트렌디한 쇼핑/카페/가벼운 휴식 축
- `hongdae`
  - 친구 여행, 식음, 저녁 분위기 축
- `yeouido`
  - 휴식형 산책 축
- `gangnam`
  - 쇼핑/도심형 이동 거점
- `jamsil`
  - 휴식형 + 가족/대형 스팟 수용 축
- `itaewon`
  - 저녁 식음과 분위기 전환 축

### 권역 순서

기본 동선 보정 순서:

`jongno → euljiro → myeongdong → dongdaemun → seongsu → hongdae → yeouido → gangnam → jamsil → itaewon`

### 인접 권역 의도

- 종로/을지로/명동/동대문은 중심권 도보·단거리 이동 축으로 묶는다.
- 성수/잠실/강남은 동남권 이동 축으로 본다.
- 홍대/여의도는 서남권 흐름으로 본다.
- 이태원/남산은 도심 전환 구간으로 본다.

### 추천 성향

- 문화 여행이면 `jongno`, `euljiro`, `dongdaemun`
- 식도락이면 `euljiro`, `hongdae`, `seongsu`, `itaewon`, `jongno`
- 휴식이면 `yeouido`, `jamsil`, `seongsu`, `jongno`
- 쇼핑이면 `seongsu`, `gangnam`, `myeongdong`, `hongdae`
- 친구 여행이면 `euljiro`, `hongdae`, `seongsu`, `itaewon`

## Busan

### 권역 의도

- `nampo`
  - 부산 원도심 기반 식음/쇼핑/시장 감성 축
  - 짧은 체류 일정이나 저녁 동선에 유리
- `songdo`
  - 해상뷰와 가벼운 체험을 섞는 보조 권역
  - `nampo`와 한 세트처럼 연결
- `gwangalli`
  - 바다 전망, 야간 분위기, 친구 여행 축
- `haeundae`
  - 대표 해변, 활동성, 사진 스팟, 가족/메인 일정 축

### 권역 순서

기본 동선 보정 순서:

`nampo → songdo → gwangalli → haeundae`

### 인접 권역 의도

- `nampo ↔ songdo`
  - 원도심 + 송도 해안 축
- `gwangalli ↔ haeundae`
  - 동부 해변 축

이 구조는 현재 데이터 수가 적은 부산에서 “가까운 감성끼리 하루 코스를 묶는다”는 목적에 맞춘 단순한 모델이다.

### 추천 성향

- 식도락이면 `nampo`, `gwangalli`, `songdo`
- 쇼핑이면 `nampo`, `haeundae`
- 문화면 `nampo`, `songdo`
- 휴식이면 `haeundae`, `gwangalli`, `songdo`
- 액티비티면 `haeundae`, `songdo`
- 친구 여행이면 `gwangalli`, `nampo`, `haeundae`
- 가족 여행이면 `haeundae`, `songdo`

## Jeju

### 권역 의도

- `east-jeju`
  - 현재 데이터상 가장 범용성이 높은 기본 축
  - 자연, 가벼운 체험, 일부 먹거리/시장 성격을 함께 가짐
- `seongsan`
  - 제주 동부 액티비티/대표 자연 랜드마크 축
  - 활동형 일정에서 가장 먼저 고려
- `seogwipo-west`
  - 서귀포 서부의 풍경형 드라이브/포토 축
- `west-jeju`
  - 카페, 휴식, 가족 친화 해변 축

### 권역 순서

기본 동선 보정 순서:

`east-jeju → seongsan → seogwipo-west → west-jeju`

### 인접 권역 의도

- `east-jeju ↔ seongsan`
  - 동부/성산 축
- `seogwipo-west ↔ west-jeju`
  - 서부/중문 축

현재는 실제 도로 최단거리 기반 모델이 아니라, 데이터 묶음과 여행 감성 기준으로 단순화한 인접 관계다.

### 추천 성향

- 액티비티면 `seongsan`, `east-jeju`
- 자연이면 `east-jeju`, `seogwipo-west`, `west-jeju`, `seongsan`
- 휴식이면 `west-jeju`, `east-jeju`, `seogwipo-west`
- 식도락이면 `east-jeju`, `west-jeju`
- 문화면 `east-jeju`, `seogwipo-west`
- 친구 여행이면 `east-jeju`, `west-jeju`, `seogwipo-west`
- 가족 여행이면 `seongsan`, `west-jeju`, `east-jeju`

## 앞으로 확장할 때 기준

새 도시를 추가할 때는 아래 순서를 권장한다.

1. 데이터 슬러그를 먼저 정리한다.
   - `app/data/destinations/*.json`
   - 권역 키는 영문 슬러그로 고정한다.
2. 한글 노출명은 `AREA_LABEL_KO`에만 둔다.
   - `app/domains/rule_planner/services/constants.py`
3. 도시별 기본 동선 순서와 인접 권역을 상수로 만든다.
4. `policies/city/{city}.py`를 추가한다.
5. `policies/city/__init__.py`에 등록한다.
6. 최소 단위 정책 테스트를 추가한다.
   - 예: 특정 컨셉에서 어떤 권역이 먼저 나와야 하는지
   - 예: 인접 권역 보너스가 어디에만 붙는지

## 운영 메모

- 지금 구조는 “도시별 감성 보정”에는 충분히 가볍고 유연하다.
- 다만 권역 수가 많아지거나 실제 교통 데이터를 붙이기 시작하면, `neighbor_area_bonus`만으로는 한계가 온다.
- 그 단계가 오면 다음 중 하나로 확장하면 된다.
  - 권역 간 이동 비용 매트릭스 도입
  - 도시별 정책을 `dict` 설정 파일 형태로 전환
  - 실제 좌표/소요시간 기반 스코어링 추가
