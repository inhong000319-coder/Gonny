import { RouterProvider } from "react-router-dom";
import { router } from "../router";

export function AppRouterProvider() {
  return <RouterProvider router={router} />;
}
