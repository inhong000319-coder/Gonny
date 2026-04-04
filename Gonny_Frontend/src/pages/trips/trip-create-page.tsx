import { AppShell } from "../../app/layouts/app-shell";
import { TripCreateForm } from "../../features/trip-create/components/trip-create-form";

export function TripCreatePage() {
  return (
    <AppShell>
      <TripCreateForm />
    </AppShell>
  );
}
