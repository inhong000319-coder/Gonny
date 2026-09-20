import { useMutation } from "@tanstack/react-query";
import { createShareLink, CreateShareLinkPayload } from "../api/create-share-link";

export function useCreateShareLinkMutation(tripId: string) {
  return useMutation({
    mutationFn: (payload: CreateShareLinkPayload) => createShareLink(tripId, payload),
  });
}
