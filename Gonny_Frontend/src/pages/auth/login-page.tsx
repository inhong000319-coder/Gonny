import { AuthLayout } from "../../app/layouts/auth-layout";
import { LoginPanel } from "../../features/auth/components/login-panel";

export function LoginPage() {
  return (
    <AuthLayout>
      <LoginPanel />
    </AuthLayout>
  );
}
