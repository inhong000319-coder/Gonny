import { AuthLayout } from "../../app/layouts/auth-layout";
import { Button } from "../../shared/components/ui/button";

export function OnboardingPage() {
  return (
    <AuthLayout>
      <div className="stack">
        <h1 className="section-title">기본 여행 취향 설정</h1>
        <label className="field">
          <span>닉네임</span>
          <input defaultValue="고니" />
        </label>
        <label className="field">
          <span>기본 동행자</span>
          <select defaultValue="커플">
            <option>혼자</option>
            <option>커플</option>
            <option>친구</option>
            <option>가족</option>
          </select>
        </label>
        <Button>저장하고 시작하기</Button>
      </div>
    </AuthLayout>
  );
}
