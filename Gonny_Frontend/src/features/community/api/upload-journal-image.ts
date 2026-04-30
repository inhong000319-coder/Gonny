import { apiClient } from "../../../shared/api/client";
import { JournalImageUploadResponse } from "../types/community";

export async function uploadJournalImage(tripId: string, file: File): Promise<JournalImageUploadResponse> {
  const formData = new FormData();
  formData.append("image", file);
  const response = await apiClient.post<JournalImageUploadResponse>(`/trips/${tripId}/community/journal-images`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}
