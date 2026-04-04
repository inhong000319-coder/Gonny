import { AppShell } from "../../app/layouts/app-shell";
import { TripCreateForm } from "../../features/trip-create/components/trip-create-form";

export function TripRecommendPage() {
  return (
    <AppShell>
      <TripCreateForm />
    </AppShell>
  );
}
