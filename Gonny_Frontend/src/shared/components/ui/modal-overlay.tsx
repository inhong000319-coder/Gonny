import { PropsWithChildren, useEffect } from "react";

type Props = PropsWithChildren<{
  onClose: () => void;
  className?: string;
}>;

export function ModalOverlay({ onClose, className, children }: Props) {
  useEffect(() => {
    document.body.classList.add("modal-open");
    return () => {
      document.body.classList.remove("modal-open");
    };
  }, []);

  return (
    <div
      className="memory-modal-backdrop"
      onClick={onClose}
      role="presentation"
    >
      <div
        className={className ?? "memory-modal"}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {children}
      </div>
    </div>
  );
}
