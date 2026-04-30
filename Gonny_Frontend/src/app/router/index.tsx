import { createBrowserRouter } from "react-router-dom";
import { ProtectedRoute } from "./protected-route";
import { LandingPage } from "../../pages/landing/landing-page";
import { LoginPage } from "../../pages/auth/login-page";
import { OnboardingPage } from "../../pages/auth/onboarding-page";
import { PlannerPage } from "../../pages/planner/planner-page";
import { TripsPage } from "../../pages/trips/trips-page";
import { TripCreatePage } from "../../pages/trips/trip-create-page";
import { TripRecommendPage } from "../../pages/trips/trip-recommend-page";
import { TripDetailPage } from "../../pages/trips/trip-detail-page";
import { TripMemoryPage } from "../../pages/trips/trip-memory-page";
import { TripMemoryDiaryPage } from "../../pages/trips/trip-memory-diary-page";
import { TripMemoryTodoPage } from "../../pages/trips/trip-memory-todo-page";
import { TripMemoryReviewsPage } from "../../pages/trips/trip-memory-reviews-page";
import { ProfilePage } from "../../pages/profile/profile-page";
import { CommunityPage } from "../../pages/community/community-page";
import { CommunityJournalsPage } from "../../pages/community/community-journals-page";
import { CommunityPlacesPage } from "../../pages/community/community-places-page";
import { InspirationPage } from "../../pages/inspiration/inspiration-page";
import { SharedTripPage } from "../../pages/shared/shared-trip-page";
import { AdminDataPage } from "../../pages/admin/admin-data-page";
import { AdminDestinationCreatePage } from "../../pages/admin/admin-destination-create-page";
import { AdminPlaceEditPage } from "../../pages/admin/admin-place-edit-page";

export const router = createBrowserRouter([
  { path: "/", element: <LandingPage /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/onboarding", element: <OnboardingPage /> },
  { path: "/inspiration", element: <InspirationPage /> },
  { path: "/planner", element: <PlannerPage /> },
  { path: "/share/:token", element: <SharedTripPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      { path: "/trips", element: <TripsPage /> },
      { path: "/trips/new", element: <TripCreatePage /> },
      { path: "/trips/recommend", element: <TripRecommendPage /> },
      { path: "/trips/:tripId", element: <TripDetailPage /> },
      { path: "/trips/:tripId/memory", element: <TripMemoryPage /> },
      { path: "/trips/:tripId/memory/diary", element: <TripMemoryDiaryPage /> },
      { path: "/trips/:tripId/memory/todos", element: <TripMemoryTodoPage /> },
      { path: "/trips/:tripId/memory/reviews", element: <TripMemoryReviewsPage /> },
      { path: "/community", element: <CommunityPage /> },
      { path: "/community/journals", element: <CommunityJournalsPage /> },
      { path: "/community/places", element: <CommunityPlacesPage /> },
      { path: "/profile", element: <ProfilePage /> },
      { path: "/admin/data", element: <AdminDataPage /> },
      { path: "/admin/data/new-destination", element: <AdminDestinationCreatePage /> },
      { path: "/admin/data/:city/new", element: <AdminPlaceEditPage /> },
      { path: "/admin/data/:city/:placeId/edit", element: <AdminPlaceEditPage /> },
    ],
  },
]);
