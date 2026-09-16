import { Button } from "./button";

type LoadErrorCardProps = {
  title: string;
  description?: string;
  onRetry: () => void;
};

// 실제로 존재하고 정상 작동하는 엔드포인트가 "아직 준비되지 않음"이
// 아니라 일시적으로 실패했을 때 쓰는 카드. "준비 중" 계열 문구를 쓰는
// 미구현 기능(예: BudgetSummaryCard, ExpenseList)과는 의도적으로
// 다른 어조를 쓴다 - 여기는 다시 시도하면 될 수 있다는 걸 알려준다.
export function LoadErrorCard({ title, description, onRetry }: LoadErrorCardProps) {
  return (
    <div className="card">
      <h2 className="section-title">{title}</h2>
      {description ? (
        <p className="section-subtitle" style={{ marginBottom: 12 }}>
          {description}
        </p>
      ) : null}
      <Button onClick={onRetry} type="button">
        다시 시도
      </Button>
    </div>
  );
}
