import { apiClient } from "../../../shared/api/client";

export type ExpiresIn = "1d" | "7d" | "unlimited";

export type CreateShareLinkPayload = {
  expires_in: ExpiresIn;
};

export type ShareLinkResult = {
  share_url: string;
  token: string;
  expires_at: string | null;
};

export async function createShareLink(tripId: string, payload: CreateShareLinkPayload): Promise<ShareLinkResult> {
  const response = await apiClient.post<ShareLinkResult>(`/trips/${tripId}/share`, payload);
  return response.data;
}
