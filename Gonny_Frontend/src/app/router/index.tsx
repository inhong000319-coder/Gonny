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
import { ProfilePage } from "../../pages/profile/profile-page";
import { InspirationPage } from "../../pages/inspiration/inspiration-page";
import { SharedTripPage } from "../../pages/shared/shared-trip-page";
import { AdminDataPage } from "../../pages/admin/admin-data-page";
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
      { path: "/profile", element: <ProfilePage /> },
      { path: "/admin/data", element: <AdminDataPage /> },
      { path: "/admin/data/:city/new", element: <AdminPlaceEditPage /> },
      { path: "/admin/data/:city/:placeId/edit", element: <AdminPlaceEditPage /> },
    ],
  },
]);
