import { ButtonHTMLAttributes, PropsWithChildren } from "react";

type ButtonProps = PropsWithChildren<
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "primary" | "secondary" | "ghost";
  }
>;

export function Button({ children, className = "", variant = "primary", ...props }: ButtonProps) {
  return (
    <button {...props} className={`button ${variant} ${className}`.trim()}>
      {children}
    </button>
  );
}
