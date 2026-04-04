import { AppShell } from "../../app/layouts/app-shell";
import { AiTripCreateForm } from "../../features/ai-trip-create/components/ai-trip-create-form";

export function TripCreatePage() {
  return (
    <AppShell>
      <AiTripCreateForm />
    </AppShell>
  );
}
