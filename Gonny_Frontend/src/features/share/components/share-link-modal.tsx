import { Button } from "../../../shared/components/ui/button";

export function ShareLinkModal() {
  return (
    <div className="card">
      <h2 className="section-title">공유 링크 만들기</h2>
      <div className="stack">
        <label className="field">
          <span>권한</span>
          <select defaultValue="read">
            <option value="read">읽기 전용</option>
            <option value="edit">편집 가능</option>
          </select>
        </label>
        <label className="field">
          <span>만료 기간</span>
          <select defaultValue="7d">
            <option value="1d">1일</option>
            <option value="7d">7일</option>
            <option value="never">무제한</option>
          </select>
        </label>
        <div className="row">
          <Button>링크 생성</Button>
          <Button variant="secondary">URL 복사</Button>
        </div>
      </div>
    </div>
  );
}
