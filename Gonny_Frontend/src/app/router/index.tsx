import { createBrowserRouter } from "react-router-dom";
import { ProtectedRoute } from "./protected-route";
import { LandingPage } from "../../pages/landing/landing-page";
import { LoginPage } from "../../pages/auth/login-page";
import { OnboardingPage } from "../../pages/auth/onboarding-page";
import { TripsPage } from "../../pages/trips/trips-page";
import { TripCreatePage } from "../../pages/trips/trip-create-page";
import { TripDetailPage } from "../../pages/trips/trip-detail-page";
import { ProfilePage } from "../../pages/profile/profile-page";
import { InspirationPage } from "../../pages/inspiration/inspiration-page";
import { SharedTripPage } from "../../pages/shared/shared-trip-page";

export const router = createBrowserRouter([
  { path: "/", element: <LandingPage /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/onboarding", element: <OnboardingPage /> },
  { path: "/inspiration", element: <InspirationPage /> },
  { path: "/share/:token", element: <SharedTripPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      { path: "/trips", element: <TripsPage /> },
      { path: "/trips/new", element: <TripCreatePage /> },
      { path: "/trips/:tripId", element: <TripDetailPage /> },
      { path: "/profile", element: <ProfilePage /> },
    ],
  },
]);
