import { FormEvent, useState } from "react";
import { Button } from "../../../shared/components/ui/button";
import { useCreateExpenseMutation } from "../hooks/use-create-expense-mutation";

type AddExpenseFormProps = {
  tripId: string;
};

const expenseCategoryOptions = ["식비", "교통", "숙박", "쇼핑", "입장료", "기타"];

function buildInitialFormState() {
  return {
    category: "",
    amount: "",
    note: "",
    spent_at: new Date().toISOString().slice(0, 10),
  };
}

export function AddExpenseForm({ tripId }: AddExpenseFormProps) {
  const [form, setForm] = useState(buildInitialFormState);
  const createExpenseMutation = useCreateExpenseMutation(tripId);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.category.trim() || !form.amount) {
      return;
    }

    try {
      await createExpenseMutation.mutateAsync({
        category: form.category.trim(),
        amount: Number(form.amount),
        currency: "KRW",
        note: form.note.trim(),
        spent_at: form.spent_at,
      });
      setForm(buildInitialFormState());
    } catch {
      // createExpenseMutation.isError below already surfaces this to the user.
    }
  };

  return (
    <div className="card stack">
      <div>
        <h2 className="section-title">지출 추가</h2>
        <p className="section-subtitle" style={{ marginBottom: 0 }}>
          이번 여행에서 쓴 비용을 기록하면 예산 요약과 최근 지출에 바로 반영돼요.
        </p>
      </div>

      <form className="stack" onSubmit={handleSubmit}>
        <div className="community-inline-grid">
          <label className="field">
            <span>카테고리</span>
            <input
              list="expense-category-options"
              onChange={(event) => setForm((prev) => ({ ...prev, category: event.target.value }))}
              placeholder="예: 식비"
              value={form.category}
            />
          </label>
          <label className="field">
            <span>금액 (KRW)</span>
            <input
              min="0"
              onChange={(event) => setForm((prev) => ({ ...prev, amount: event.target.value }))}
              type="number"
              value={form.amount}
            />
          </label>
        </div>

        <div className="community-inline-grid">
          <label className="field">
            <span>날짜</span>
            <input
              onChange={(event) => setForm((prev) => ({ ...prev, spent_at: event.target.value }))}
              type="date"
              value={form.spent_at}
            />
          </label>
          <label className="field">
            <span>메모</span>
            <input
              onChange={(event) => setForm((prev) => ({ ...prev, note: event.target.value }))}
              placeholder="예: 흑돼지 점심"
              value={form.note}
            />
          </label>
        </div>

        <datalist id="expense-category-options">
          {expenseCategoryOptions.map((option) => (
            <option key={option} value={option} />
          ))}
        </datalist>

        {createExpenseMutation.isError ? (
          <p className="planner-feedback error">지출을 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.</p>
        ) : null}

        <Button disabled={createExpenseMutation.isPending || !form.category.trim() || !form.amount} type="submit">
          {createExpenseMutation.isPending ? "저장 중..." : "지출 추가"}
        </Button>
      </form>
    </div>
  );
}
