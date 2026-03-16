# ✈️ AI 여행 일정 생성 & 실시간 조율 에이전트
> **서비스명 미정** | AI-Powered Travel Planner for Korean Travelers

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black"/>
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white"/>
  <img src="https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white"/>
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-In%20Development-yellow?style=flat-square"/>
  <img src="https://img.shields.io/badge/Version-v1.0.0-blue?style=flat-square"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square"/>
</p>

---

## 📌 프로젝트 소개

> **"카테고리를 선택하고 원하는 조건을 입력하면, AI가 날씨·동행자·예산·숙박·이동수단을 모두 반영한 여행 일정을 자동으로 생성해드립니다."**

한국인 AI 여행 활용률이 2년 만에 **3배(15% → 45%)** 급증했지만, 기존 서비스들은 날씨 반영, 동행자 취향 조율, PDF 저장, 여행 후 회고 기능이 모두 빠져 있었습니다.
이 프로젝트는 그 **4가지 공백을 모두 채운** 국내 특화 AI 여행 플래너입니다.

### 🎯 핵심 차별점

| 기능 | 트리플 | 마이로 | 트립지니 | **우리 서비스** |
|---|:---:|:---:|:---:|:---:|
| 자연어 + 카테고리 하이브리드 입력 | △ | ✕ | ✓ | **✓** |
| 날씨 기반 일정 재추천 | ✕ | ✕ | ✕ | **✓** |
| 동행자 취향 통합 조율 | ✕ | ✕ | ✕ | **✓** |
| 장소 단위 핀포인트 수정 | ✕ | ✕ | ✕ | **✓** |
| 일정 PDF 내보내기 | ✕ | ✕ | ✕ | **✓** |
| 여행 후 AI 회고 리포트 | ✕ | ✕ | ✕ | **✓** |
| 계절별 여행지 추천 | ✕ | ✕ | ✕ | **✓** |
| 한국 공공 API 특화 | △ | △ | ✕ | **✓** |

---

## 🗂️ 목차

- [주요 기능](#-주요-기능)
- [기술 스택](#-기술-스택)
- [시스템 아키텍처](#-시스템-아키텍처)
- [프로젝트 구조](#-프로젝트-구조)
- [시작하기](#-시작하기)
- [환경 변수 설정](#-환경-변수-설정)
- [API 문서](#-api-문서)
- [팀원 소개](#-팀원-소개)
- [개발 일정](#-개발-일정)
- [향후 계획](#-향후-계획)
- [커밋 컨벤션](#-커밋-컨벤션)

---

## ✨ 주요 기능

### 🗓️ AI 여행 일정 생성
카테고리 선택(여행지·스타일·예산·동행자·이동수단·숙박·식사)만으로 30초 안에 일자별 상세 일정 자동 생성.
원하는 조건이 있다면 자연어로 추가 입력 가능.

### 🌦️ 날씨 기반 일정 재추천
여행 기간 우천·눈 예보 감지 시 AI가 실내 대안 코스를 카드 형태로 제시.
자동 변경이 아닌 **사용자가 직접 선택**하는 방식으로 주도권 보장.

### 👥 동행자 취향 통합 조율
최대 4명의 동행자 취향 태그(미식·자연·문화·쇼핑·힐링·액티비티)를 각자 입력하면
LLM이 가중치를 반영해 모두가 만족하는 통합 일정 생성.

### 📍 장소 단위 핀포인트 수정
마음에 들지 않는 특정 장소만 골라 AI에게 대안을 요청.
날짜 전체 재생성 없이 해당 스팟만 교체 + 되돌리기 지원.

### 🏨 숙박 추천
예산·유형·위치 조건에 맞는 숙소 3~5곳 AI 추천.
야놀자·에어비앤비·Booking.com 예약 링크 바로 연결.

### 🚌 이동수단 안내
대중교통(ODSay API) / 렌터카 / 도보 선택에 따라
장소 간 이동 경로·소요 시간·환승 정보 자동 표시.

### 🍽️ 식당 정보 안내
식사 시간대별 식당 자동 배정. 예약 필요 맛집 뱃지 표시 및
네이버 예약·카카오맵 바로가기 링크 제공.

### ⏱️ 예상 소요 시간 표시
장소 유형별 권장 체류 시간 + 이동 시간 자동 계산.
하루 총 예상 시간 합산 및 과부하(10시간 초과) 경고.

### 🌸 계절별 여행지 추천
봄·여름·가을·겨울 탭 UI + 현재 시즌 자동 감지.
이번 달 전국 축제·행사 캘린더 및 "이번 주말 가기 좋은 곳" 숏폼 추천.

### 💰 예산 관리 & 지출 트래킹
총 예산 설정 → AI 항목별 자동 배분 → 여행 중 지출 입력 → 잔여 예산 실시간 게이지.
해외 여행 시 현지 통화 → 원화 자동 환산.

### 📄 일정 PDF 내보내기
지도 포함 A4 최적화 PDF 자동 생성. 오프라인 여행 중에도 확인 가능.

### 📊 여행 후 AI 회고 리포트
방문 완료 장소·지출 데이터를 AI가 분석해 인사이트 리포트 자동 생성.
예산 초과 분석, 카테고리별 지출 차트 포함.

---

## 🛠️ 기술 스택

### Backend
```
Python 3.11 / FastAPI / SQLAlchemy / PostgreSQL / Redis / Docker
```

### Frontend
```
React 18 / Vite / TailwindCSS / Plotly.js / Chart.js
```

### AI / LLM
```
Claude API (claude-haiku) / OpenAI GPT-4o mini
```

### 외부 API
```
한국관광공사 TourAPI     — 국내 관광지·숙박·음식점·축제 (완전 무료)
한국공항공사 API         — 국내선 실시간 운항 정보 (완전 무료)
OpenWeatherMap           — 날씨 5일 예보 (무료 플랜)
Google Places API        — 장소 평점·운영시간·사진
Google Maps JS API       — 지도·경로 시각화
ODSay API                — 대중교통 경로 안내 (무료 플랜)
ExchangeRate-API         — 실시간 환율 정보 (무료 플랜)
카카오 로그인·공유 API   — OAuth 인증 및 카카오톡 공유
```

### Infra / DevOps
```
Docker Compose / GitHub Actions (CI/CD) / Railway
```

---

## 🏗️ 시스템 아키텍처

```mermaid
graph TB
    subgraph Client["🖥️ Client (React + TailwindCSS)"]
        UI["카테고리 선택 UI\n자연어 입력창\n일정 카드·지도"]
    end

    subgraph Backend["⚙️ FastAPI Backend"]
        Auth["Auth Router\nJWT + OAuth"]
        Trip["Trip Router\n일정 생성·수정"]
        Weather["Weather Router\n날씨 재추천"]
        Season["Season Router\n계절별 추천"]
        Report["Report Router\nPDF + 회고"]

        subgraph LLM["🤖 LLM Agent Layer"]
            Claude["Claude API\nclaude-haiku"]
            GPT["GPT-4o mini"]
        end

        subgraph Storage["💾 Storage"]
            PG["PostgreSQL\n메인 DB"]
            Redis["Redis\n캐시·Rate Limit"]
        end
    end

    subgraph ExternalAPI["🌐 외부 API"]
        TourAPI["한국관광공사\nTourAPI"]
        OWM["OpenWeatherMap\n날씨 예보"]
        GMaps["Google Maps\nPlaces API"]
        ODSay["ODSay\n대중교통"]
        Kakao["카카오\n로그인·공유"]
        Exchange["ExchangeRate\n환율"]
    end

    subgraph Deploy["🚀 배포"]
        Railway["Railway\nDocker 컨테이너"]
        GH["GitHub Actions\nCI/CD"]
    end

    UI -->|HTTPS| Auth
    UI -->|HTTPS| Trip
    UI -->|HTTPS| Weather
    UI -->|HTTPS| Season
    UI -->|HTTPS| Report

    Trip --> LLM
    Report --> LLM
    Weather --> LLM

    Trip --> Storage
    Auth --> Storage
    Report --> Storage

    Trip --> TourAPI
    Trip --> GMaps
    Trip --> ODSay
    Weather --> OWM
    Season --> TourAPI
    Auth --> Kakao
    Report --> Exchange

    GH -->|push to main| Railway
```

---

## 📁 프로젝트 구조

```
project-root/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI 앱 진입점
│   │   ├── core/
│   │   │   ├── config.py         # 환경 변수 설정
│   │   │   ├── database.py       # DB 연결
│   │   │   └── security.py       # JWT 인증
│   │   ├── routers/
│   │   │   ├── auth.py           # 로그인·회원 관리
│   │   │   ├── trips.py          # 일정 생성·수정·조회
│   │   │   ├── weather.py        # 날씨 연동·재추천
│   │   │   ├── places.py         # 장소·숙박·식당 정보
│   │   │   ├── expenses.py       # 예산·지출 트래킹
│   │   │   ├── reports.py        # 회고 리포트·PDF
│   │   │   └── seasons.py        # 계절별 여행지 추천
│   │   ├── services/
│   │   │   ├── llm_service.py    # LLM 호출·프롬프트 관리
│   │   │   ├── tour_api.py       # 한국관광공사 TourAPI
│   │   │   ├── weather_api.py    # OpenWeatherMap
│   │   │   ├── maps_api.py       # Google Maps
│   │   │   └── pdf_service.py    # ReportLab PDF 생성
│   │   └── models/
│   │       ├── user.py
│   │       ├── trip.py
│   │       ├── itinerary.py
│   │       ├── accommodation.py
│   │       ├── expense.py
│   │       └── report.py
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Home.jsx          # 메인·영감 피드
│   │   │   ├── PlanTrip.jsx      # 일정 생성 (카테고리 + 자연어)
│   │   │   ├── Itinerary.jsx     # 일정 상세·수정
│   │   │   ├── SeasonPick.jsx    # 계절별 여행지 추천
│   │   │   ├── Budget.jsx        # 예산 관리
│   │   │   └── Report.jsx        # 회고 리포트
│   │   ├── components/
│   │   │   ├── CategorySelector/ # 카테고리 선택 UI
│   │   │   ├── ItineraryCard/    # 일정 카드
│   │   │   ├── WeatherBanner/    # 날씨 재추천 알림
│   │   │   ├── PlaceCard/        # 장소·숙박·식당 카드
│   │   │   └── BudgetGauge/      # 잔여 예산 게이지
│   │   └── utils/
│   ├── public/
│   ├── Dockerfile
│   └── package.json
│
├── docker-compose.yml
├── docker-compose.dev.yml
├── .github/
│   └── workflows/
│       └── deploy.yml            # CI/CD 파이프라인
└── README.md
```

---

## 🚀 시작하기

### 사전 요구사항
- Docker Desktop 설치
- Git 설치
- 외부 API 키 발급 (아래 [환경 변수 설정](#-환경-변수-설정) 참고)

### 1. 레포지토리 클론

```bash
git clone https://github.com/{your-org}/{repo-name}.git
cd {repo-name}
```

### 2. 환경 변수 파일 생성

```bash
cp .env.example .env
# .env 파일을 열어 API 키 입력
```

### 3. Docker Compose 실행

```bash
docker-compose -f docker-compose.dev.yml up --build
```

### 4. 접속

| 서비스 | URL |
|---|---|
| 프론트엔드 | http://localhost:3000 |
| 백엔드 API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Redis | localhost:6379 |
| PostgreSQL | localhost:5432 |

---

## 🔑 환경 변수 설정

`.env.example` 파일을 복사해 `.env`를 만들고 아래 값을 채워주세요.

```env
# ── LLM ──────────────────────────────
ANTHROPIC_API_KEY=your_claude_api_key
OPENAI_API_KEY=your_openai_api_key       # Claude 사용 시 선택

# ── 인증 ─────────────────────────────
SECRET_KEY=your_jwt_secret_key_here
KAKAO_CLIENT_ID=your_kakao_client_id
KAKAO_REDIRECT_URI=http://localhost:3000/auth/kakao
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# ── 한국 공공 API (무료) ───────────────
TOUR_API_KEY=your_korea_tourism_api_key       # data.go.kr 발급
AIRPORT_API_KEY=your_airport_api_key          # data.go.kr 발급

# ── 외부 API ──────────────────────────
OPENWEATHER_API_KEY=your_openweathermap_key
GOOGLE_MAPS_API_KEY=your_google_maps_key
ODSAY_API_KEY=your_odsay_api_key
EXCHANGE_RATE_API_KEY=your_exchangerate_key

# ── 데이터베이스 ──────────────────────
DATABASE_URL=postgresql://user:password@localhost:5432/travel_db
REDIS_URL=redis://localhost:6379

# ── 앱 설정 ───────────────────────────
ENVIRONMENT=development                        # development / production
ALLOWED_ORIGINS=http://localhost:3000
```

### API 키 발급 링크

| API | 발급 URL | 비용 |
|---|---|---|
| 한국관광공사 TourAPI | [data.go.kr](https://www.data.go.kr) | 무료 |
| 한국공항공사 API | [data.go.kr](https://www.data.go.kr) | 무료 |
| OpenWeatherMap | [openweathermap.org](https://openweathermap.org/api) | 무료 플랜 |
| Google Maps / Places | [console.cloud.google.com](https://console.cloud.google.com) | $200 무료 크레딧/월 |
| ODSay API | [lab.odsay.com](https://lab.odsay.com) | 무료 플랜 |
| 카카오 로그인 | [developers.kakao.com](https://developers.kakao.com) | 무료 |
| Claude API | [console.anthropic.com](https://console.anthropic.com) | 초기 크레딧 제공 |

---

## 📖 API 문서

서버 실행 후 아래 주소에서 Swagger UI 자동 문서를 확인할 수 있습니다.

```
http://localhost:8000/docs       # Swagger UI
http://localhost:8000/redoc      # ReDoc
```

### 주요 엔드포인트

```
POST   /api/v1/auth/kakao                              카카오 OAuth 로그인
POST   /api/v1/auth/google                             구글 OAuth 로그인

POST   /api/v1/trips                                   여행 일정 생성
GET    /api/v1/trips                                   내 여행 목록 조회
GET    /api/v1/trips/{trip_id}                         여행 상세 조회
PATCH  /api/v1/trips/{trip_id}/items/{item_id}         장소 단위 수정
POST   /api/v1/trips/{trip_id}/items/{item_id}/alternatives   대안 장소 추천

GET    /api/v1/weather/{destination}                   여행지 날씨 예보 조회

GET    /api/v1/seasons/recommend                       계절별 여행지 추천
GET    /api/v1/seasons/festivals                       이번 달 축제 캘린더

POST   /api/v1/trips/{trip_id}/expenses                지출 입력
GET    /api/v1/trips/{trip_id}/expenses/summary        예산 요약

GET    /api/v1/trips/{trip_id}/report                  AI 회고 리포트 조회
GET    /api/v1/trips/{trip_id}/pdf                     일정 PDF 다운로드

POST   /api/v1/trips/{trip_id}/share                   공유 링크 생성
```


## 📅 개발 일정

```mermaid
gantt
    title 1개월 개발 스프린트
    dateFormat YYYY-MM-DD
    axisFormat %m/%d

    section 1주차 · 기반 구축
    프로젝트 셋업 (FastAPI + Docker)     :done, w1-1, 2026-04-01, 2d
    OAuth 로그인 + JWT 인증              :done, w1-2, 2026-04-02, 2d
    카테고리 선택 UI                     :done, w1-3, 2026-04-03, 2d
    Claude API + TourAPI 연동           :done, w1-4, 2026-04-05, 2d

    section 2주차 · 핵심 기능
    날씨 API + 일정 재추천               :active, w2-1, 2026-04-08, 2d
    동행자 취향 통합 알고리즘             :active, w2-2, 2026-04-09, 2d
    숙박·이동수단·식당 정보 카드          :active, w2-3, 2026-04-10, 2d
    예상 소요 시간 + 예산 트래킹          :active, w2-4, 2026-04-12, 2d

    section 3주차 · 차별 기능
    장소별 핀포인트 수정·재추천           :w3-1, 2026-04-15, 2d
    수동 체크인 로직                     :w3-2, 2026-04-16, 2d
    PDF 생성 + 카카오 공유              :w3-3, 2026-04-17, 2d
    계절별 여행지 추천 + 환율 연동        :w3-4, 2026-04-19, 2d

    section 4주차 · 통합 & 배포
    AI 회고 리포트                       :w4-1, 2026-04-22, 2d
    Redis 캐싱 최적화                    :w4-2, 2026-04-23, 2d
    통합 테스트 + 버그 수정              :w4-3, 2026-04-24, 3d
    Railway 배포 + CI/CD + README       :w4-4, 2026-04-28, 2d
```

---

## 🗺️ 향후 계획 (글로벌 확장 로드맵)

```mermaid
graph LR
    V1["✅ v1.0\n2026 Q2\n국내 전 지역"]
    V2["🔜 v2.0\n2026 Q4\n아시아\n일본·태국·베트남\n싱가포르·홍콩"]
    V3["📋 v3.0\n2027 Q2\n유럽·아메리카\n오세아니아·중동"]
    APP["📱 모바일 앱\nReact Native\n자동 위치 추적"]
    SOCIAL["👥 소셜 피드\n일정 탐색·복제\n다국어 지원"]

    V1 -->|Google Places 글로벌| V2
    V2 -->|Booking.com API 연동| V3
    V1 -.->|앱 전환| APP
    V3 -.->|커뮤니티 확장| SOCIAL
```

- [ ] 모바일 앱 (React Native) 전환 → 백그라운드 위치 자동 추적
- [ ] 항공권 가격 비교 기능 (Amadeus API 계약 후)
- [ ] 다국어 지원 (영어·일본어·중국어)
- [ ] 소셜 피드 — 다른 사용자 여행 일정 탐색 및 복제

---

## 💬 커밋 컨벤션

### 커밋 메시지 구조

```
<태그>: <제목>

<본문 (선택)>
- 변경 사항 상세 설명
- 관련 이슈 번호 (예: #12)
```

### 태그 목록

| 태그 | 용도 | 예시 |
|---|---|---|
| `feat` | 새 기능 추가 | `feat: 카카오 OAuth 로그인 구현` |
| `fix` | 버그 수정 | `fix: JWT 리프레시 토큰 만료 오류 수정` |
| `refactor` | 기능 변경 없는 코드 개선 | `refactor: llm_service 모듈 분리` |
| `docs` | 문서 수정 | `docs: README API 엔드포인트 목록 업데이트` |
| `chore` | 빌드·설정·패키지 관리 | `chore: FastAPI 버전 0.111로 업그레이드` |
| `test` | 테스트 추가·수정 | `test: 예산 계산기 단위 테스트 추가` |
| `style` | 포매팅·오타 수정 (로직 무관) | `style: black 포매터 전체 적용` |
| `perf` | 성능 개선 | `perf: TourAPI 응답 Redis 캐싱 추가` |

### 스프린트별 커밋 메시지 예시

**1주차 — 기반 구축**
```
feat: 프로젝트 초기 구조 설정 (FastAPI + React + PostgreSQL + Redis)
feat: 카카오 & 구글 OAuth 2.0 로그인 및 JWT 인증 구현
feat: 여행 일정 생성용 카테고리 선택 UI 구현
feat: Claude API 연동 및 AI 일정 생성 기본 기능 구현
feat: 한국관광공사 TourAPI 연동 및 장소 검증 로직 구현
```

**2주차 — 핵심 기능**
```
feat: OpenWeatherMap 연동 및 날씨 기반 일정 재추천 기능 구현
feat: 동행자 취향 통합 조율 알고리즘 구현
feat: 숙박 추천 및 예약 링크 연결 기능 구현
feat: ODSay API 연동 대중교통 경로 안내 기능 구현
feat: 식사 시간대별 식당 자동 배정 기능 구현
feat: 장소별 예상 소요 시간 자동 계산 기능 구현
feat: 예산 트래킹 및 잔여 예산 실시간 게이지 구현
```

**3주차 — 차별 기능**
```
feat: 장소 단위 핀포인트 수정 및 대안 재추천 기능 구현
feat: 수동 체크인 및 GPS 위치 확인 로직 구현
feat: ReportLab 기반 일정 PDF 자동 생성 기능 구현
feat: 카카오톡 일정 공유 카드 연동 구현
feat: ExchangeRate-API 연동 해외 지출 원화 환산 기능 구현
feat: 계절별 여행지 추천 및 축제 캘린더 기능 구현
```

**4주차 — 통합 & 배포**
```
feat: 여행 후 AI 회고 리포트 자동 생성 기능 구현
perf: LLM 응답 Redis 캐싱 최적화 적용
chore: 백엔드·프론트엔드 Railway 배포 환경 Docker 설정
chore: GitHub Actions CI/CD 자동 배포 파이프라인 완성
docs: README 최종 정리 및 데모 영상 링크 추가
```

### 브랜치 전략

```mermaid
gitGraph
    commit id: "초기 설정"
    branch develop
    checkout develop

    branch feat/oauth-login
    commit id: "카카오 로그인 구현"
    commit id: "구글 로그인 구현"
    checkout develop
    merge feat/oauth-login id: "PR 머지"

    branch feat/ai-itinerary
    commit id: "Claude API 연동"
    commit id: "TourAPI 장소 검증"
    checkout develop
    merge feat/ai-itinerary id: "PR 머지 "

    branch feat/weather-recommend
    commit id: "날씨 API 연동"
    commit id: "재추천 알림 로직"
    checkout develop
    merge feat/weather-recommend id: "PR 머지  "

    checkout main
    merge develop id: "🚀 v1.0 배포"
```

```
main         ── 배포용 브랜치 (직접 push 금지, PR만 허용)
develop      ── 개발 통합 브랜치
feat/기능명  ── 기능 개발 브랜치 (예: feat/weather-recommend)
fix/이슈명   ── 버그 수정 브랜치 (예: fix/jwt-refresh-bug)

[흐름]
feat/기능명 → develop (PR + 코드 리뷰) → main (배포)
```

---

## 📄 라이선스

```
MIT License — 자유롭게 사용, 수정, 배포 가능
```

---

## 작업 루틴

```bash
# main 직접 push 금지, 작업은 반드시 브랜치 + PR로 진행

# 1) 시작 전 main 최신화
git checkout main
git pull origin main

# 2) 작업 브랜치 생성
git checkout -b feature/<name>

# 3) 개발 및 커밋
git add .
git commit -m "feat: ..."

# 4) PR 전 main 병합(충돌 사전 확인)
git checkout main
git pull origin main
git checkout feature/<name>
git merge main

# 5) 원격 푸시 및 PR 생성
git push origin feature/<name>
```

## 충돌(Conflict) 발생 시 대응

```bash
# 작업 브랜치에서
git pull origin main

# 충돌 파일 수정 후
git add .
git commit -m "fix: merge conflict resolved"
git push origin feature/<name>
```

## 커밋 메시지 타입

| 타입명 | 기능 |
| --- | --- |
| feat | 새로운 기능 추가 |
| fix | 버그 수정 |
| docs | 문서 변경 |
| style | 포맷팅 등 비기능 변경 |
| refactor | 기능 변화 없는 코드 개선 |
| test | 테스트 추가/수정 |
| chore | 빌드/도구/환경 정리 |
| perf | 성능 개선 |
| build | 빌드 관련 변경 |

## Git 명령어 모음

```bash
git merge main
git pull origin main
git checkout -b feature/<name>
git status
git diff
git add .
git reset HEAD <path>
git commit -m "<type>: <summary>"
git push origin feature/<name>
```
