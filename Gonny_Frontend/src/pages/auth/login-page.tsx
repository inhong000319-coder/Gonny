import { AuthLayout } from "../../app/layouts/auth-layout";
import { LoginPanel } from "../../features/auth/components/login-panel";
import { useDocumentTitle } from "../../shared/hooks/use-document-title";

export function LoginPage() {
  useDocumentTitle("로그인");

  return (
    <AuthLayout>
      <LoginPanel />
    </AuthLayout>
  );
}
