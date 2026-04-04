import { PublicLayout } from "../../app/layouts/public-layout";
import { TripCreateForm } from "../../features/trip-create/components/trip-create-form";

export function PlannerPage() {
  return (
    <PublicLayout>
      <TripCreateForm />
    </PublicLayout>
  );
}
