import { useEffect } from "react";

export function useDocumentTitle(title: string | null | undefined) {
  useEffect(() => {
    if (!title) {
      return;
    }
    document.title = `${title} · Gonny`;
  }, [title]);
}
