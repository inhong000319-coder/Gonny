# Gonny 프론트엔드 폴더 구조

## 1. 기준 스택

- React
- Vite
- TypeScript
- Tailwind CSS
- React Router
- TanStack Query
- Axios
- Zustand 또는 Context 최소 사용

## 2. 추천 디렉터리 구조

```txt
src/
  app/
    providers/
      query-provider.tsx
      router-provider.tsx
      auth-provider.tsx
    router/
      index.tsx
      protected-route.tsx
    layouts/
      app-shell.tsx
      auth-layout.tsx
      public-layout.tsx
    styles/
      globals.css
      tokens.css
    main.tsx

  pages/
    landing/
      landing-page.tsx
    auth/
      login-page.tsx
      onboarding-page.tsx
    trips/
      trips-page.tsx
      trip-create-page.tsx
      trip-detail-page.tsx
      trip-share-page.tsx
    profile/
      profile-page.tsx
    inspiration/
      inspiration-page.tsx
    shared/
      shared-trip-page.tsx

  features/
    auth/
      api/
        login-kakao.ts
        login-google.ts
        refresh-token.ts
        logout.ts
      components/
        social-login-button.tsx
        login-panel.tsx
      hooks/
        use-auth.ts
        use-token-refresh.ts
      store/
        auth-store.ts
      types/
        auth.ts

    profile/
      api/
        get-me.ts
        update-me.ts
        delete-me.ts
      components/
        profile-form.tsx
        travel-history-list.tsx
      types/
        profile.ts

    trip-create/
      api/
        create-trip.ts
      components/
        trip-create-form.tsx
        destination-section.tsx
        schedule-section.tsx
        style-section.tsx
        budget-section.tsx
        transport-section.tsx
        accommodation-section.tsx
        meal-section.tsx
        companions-section.tsx
        extra-request-section.tsx
        generation-progress.tsx
      hooks/
        use-trip-create-form.ts
      types/
        trip-create.ts

    trips/
      api/
        get-trips.ts
        get-trip-detail.ts
        update-trip.ts
        delete-trip.ts
      components/
        trip-card.tsx
        trip-list.tsx
        trip-header.tsx
        trip-summary.tsx
      types/
        trip.ts

    itinerary/
      api/
        replace-trip-item.ts
        get-alternatives.ts
        checkin-trip-item.ts
        get-weather.ts
        get-weather-recommendation.ts
      components/
        day-tabs.tsx
        day-timeline.tsx
        itinerary-item-card.tsx
        item-actions.tsx
        weather-banner.tsx
        weather-badge.tsx
        checkin-button.tsx
        alternative-list.tsx
        replace-item-modal.tsx
        weather-recommend-modal.tsx
      types/
        itinerary.ts

    accommodations/
      api/
        get-accommodations.ts
        select-accommodation.ts
      components/
        accommodation-filter.tsx
        accommodation-card.tsx
        accommodation-map.tsx
      types/
        accommodation.ts

    companions/
      api/
        create-companions.ts
        get-companions.ts
        delete-companion.ts
      components/
        companion-form.tsx
        companion-card.tsx
        companion-tag-selector.tsx
        companion-summary.tsx
      types/
        companion.ts

    budget/
      api/
        create-expense.ts
        get-expenses.ts
        delete-expense.ts
        get-expense-summary.ts
      components/
        budget-summary-card.tsx
        budget-gauge.tsx
        expense-form-modal.tsx
        expense-list.tsx
        expense-category-chart.tsx
      types/
        budget.ts

    share/
      api/
        create-share-link.ts
        get-shared-trip.ts
      components/
        share-link-modal.tsx
        share-permission-selector.tsx
        share-link-result.tsx
      types/
        share.ts

    report/
      api/
        get-trip-report.ts
        download-report-pdf.ts
      components/
        report-summary.tsx
        report-insights.tsx
        report-chart.tsx
      types/
        report.ts

    inspiration/
      api/
        get-season-recommendations.ts
        get-festivals.ts
        get-exchange-rate.ts
      components/
        season-feed.tsx
        festival-calendar.tsx
        exchange-rate-card.tsx
      types/
        inspiration.ts

  shared/
    api/
      client.ts
      interceptors.ts
      error-handler.ts
      query-keys.ts
    components/
      ui/
        button.tsx
        input.tsx
        textarea.tsx
        select.tsx
        chip.tsx
        badge.tsx
        modal.tsx
        sheet.tsx
        tabs.tsx
        toast.tsx
        spinner.tsx
        skeleton.tsx
        progress.tsx
      feedback/
        empty-state.tsx
        error-state.tsx
        loading-state.tsx
      map/
        trip-map.tsx
        map-marker.tsx
      chart/
        pie-chart.tsx
        gauge-chart.tsx
    hooks/
      use-modal.ts
      use-toast.ts
      use-geolocation.ts
      use-copy.ts
      use-debounce.ts
    lib/
      date.ts
      currency.ts
      storage.ts
      token.ts
      validators.ts
      constants.ts
    types/
      api.ts
      common.ts
    assets/
      icons/
      images/
```

## 3. 폴더 분리 원칙

### `app/`
- 앱 부트스트랩
- 전역 provider
- 라우터
- 레이아웃
- 전역 스타일

### `pages/`
- 라우트 진입 파일만 둔다
- 실제 비즈니스 UI는 `features/`에서 조합한다

### `features/`
- 도메인 단위 분리
- 각 기능은 `api`, `components`, `hooks`, `types`를 기본으로 가진다
- 일정/예산/동행자처럼 API와 UI가 함께 움직이는 단위를 모은다

### `shared/`
- 여러 기능에서 공통으로 쓰는 UI, 훅, 유틸, API 기반 코드를 모은다

## 4. 실제 페이지 조합 예시

### `trip-create-page.tsx`

```txt
TripCreatePage
  AppShell
    TripCreateForm
      DestinationSection
      ScheduleSection
      StyleSection
      BudgetSection
      TransportSection
      AccommodationSection
      MealSection
      CompanionsSection
      ExtraRequestSection
    GenerationProgress
```

### `trip-detail-page.tsx`

```txt
TripDetailPage
  AppShell
    TripHeader
    TripSummary
    Tabs
      ItineraryTab
        WeatherBanner
        DayTabs
        DayTimeline
          ItineraryItemCard
            ItemActions
            CheckinButton
      MapTab
        TripMap
      AccommodationsTab
        AccommodationFilter
        AccommodationCard
        AccommodationMap
      CompanionsTab
        CompanionForm
        CompanionCard
        CompanionSummary
      BudgetTab
        BudgetSummaryCard
        BudgetGauge
        ExpenseList
      ReportTab
        ReportSummary
        ReportChart
        ReportInsights
```

## 5. 라우트 파일 추천 구조

```txt
app/router/index.tsx
pages/landing/landing-page.tsx
pages/auth/login-page.tsx
pages/auth/onboarding-page.tsx
pages/trips/trips-page.tsx
pages/trips/trip-create-page.tsx
pages/trips/trip-detail-page.tsx
pages/profile/profile-page.tsx
pages/inspiration/inspiration-page.tsx
pages/shared/shared-trip-page.tsx
```

예시:

```tsx
const router = createBrowserRouter([
  { path: "/", element: <LandingPage /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/onboarding", element: <OnboardingPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      { path: "/trips", element: <TripsPage /> },
      { path: "/trips/new", element: <TripCreatePage /> },
      { path: "/trips/:tripId", element: <TripDetailPage /> },
      { path: "/profile", element: <ProfilePage /> },
    ],
  },
  { path: "/inspiration", element: <InspirationPage /> },
  { path: "/share/:token", element: <SharedTripPage /> },
]);
```

## 6. 상태 관리 추천

### TanStack Query
- 여행 목록
- 여행 상세
- 날씨
- 숙소
- 동행자
- 지출 목록 / 예산 요약
- 회고 리포트

### 지역 상태
- 모달 열림 여부
- 생성 폼 step 상태
- 공유 링크 복사 상태
- 지도 필터 상태

### 전역 상태
- 로그인 사용자
- 액세스 토큰
- 리프레시 상태

## 7. naming 규칙 추천

- 파일명: `kebab-case`
- 컴포넌트: `PascalCase`
- 훅: `use-*.ts`
- API 함수: 동사 + 대상
- 타입: 도메인 기준 명확하게 분리

예시:
- `get-trip-detail.ts`
- `replace-item-modal.tsx`
- `use-trip-create-form.ts`
- `TripDetail`
- `TripExpenseSummary`

## 8. 먼저 만들 파일 순서

1. `shared/api/client.ts`
2. `app/router/index.tsx`
3. `app/layouts/app-shell.tsx`
4. `features/auth/*`
5. `features/trip-create/*`
6. `features/trips/*`
7. `features/itinerary/*`
8. `features/budget/*`
9. `features/share/*`

## 9. 선택하면 좋은 추가 폴더

디자인 시스템을 조금 더 키울 계획이면 아래도 괜찮다.

```txt
src/
  shared/
    components/
      ui/
      form/
      navigation/
      data-display/
```

테스트를 빨리 붙일 계획이면:

```txt
src/
  test/
    setup.ts
    fixtures/
    mocks/
```

## 10. 한 줄 결론

이 프로젝트는 `pages는 얇게`, `features는 도메인 중심`, `shared는 재사용 중심`으로 가면 가장 안 꼬인다.
