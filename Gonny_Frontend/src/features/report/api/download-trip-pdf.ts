import { apiClient } from "../../../shared/api/client";

// GET /trips/{tripId}/pdf returns a raw application/pdf binary (not the
// {success, data, message} envelope the expense endpoints use), so this
// reads the response as a blob and triggers a normal browser download
// rather than going through react-query like the other report data.
export async function downloadTripPdf(tripId: string): Promise<void> {
  const response = await apiClient.get(`/trips/${tripId}/pdf`, { responseType: "blob" });
  const blobUrl = URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));

  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = `trip_${tripId}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(blobUrl);
}
