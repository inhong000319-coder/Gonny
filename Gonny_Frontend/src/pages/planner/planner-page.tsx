import { PublicLayout } from "../../app/layouts/public-layout";
import { TripCreateForm } from "../../features/trip-create/components/trip-create-form";
import { useDocumentTitle } from "../../shared/hooks/use-document-title";

export function PlannerPage() {
  useDocumentTitle("일정 만들기");

  return (
    <PublicLayout>
      <TripCreateForm />
    </PublicLayout>
  );
}
