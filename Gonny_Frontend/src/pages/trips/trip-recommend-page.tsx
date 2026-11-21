import { AppShell } from "../../app/layouts/app-shell";
import { TripCreateForm } from "../../features/trip-create/components/trip-create-form";
import { useDocumentTitle } from "../../shared/hooks/use-document-title";

export function TripRecommendPage() {
  useDocumentTitle("일정 만들기");

  return (
    <AppShell>
      <TripCreateForm />
    </AppShell>
  );
}
