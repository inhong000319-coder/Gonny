import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "../../../shared/components/ui/button";
import { formatAccommodationPriceLabel } from "../../../shared/pricing";
import { queryKeys } from "../../../shared/api/query-keys";
import { useTripAccommodationOptionsQuery } from "../hooks/use-trip-accommodation-options-query";
import { useUpdateTripAccommodationMutation } from "../hooks/use-update-trip-accommodation-mutation";

type AccommodationChangePanelProps = {
  tripId: string;
  // 현재 저장된 숙소 - 둘 다 없으면(undefined) "저장된 숙소 없음".
  currentAccommodationId?: string;
  currentAccommodationLabel?: string;
};

const TYPE_FILTER_ALL = "전체";

export function AccommodationChangePanel({
  tripId,
  currentAccommodationId,
  currentAccommodationLabel,
}: AccommodationChangePanelProps) {
  const queryClient = useQueryClient();
  const [isOpen, setIsOpen] = useState(false);
  const [typeFilter, setTypeFilter] = useState(TYPE_FILTER_ALL);
  const [keyword, setKeyword] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [actionError, setActionError] = useState("");
  const [actionMessage, setActionMessage] = useState("");

  const optionsQuery = useTripAccommodationOptionsQuery(tripId, isOpen);
  const mutation = useUpdateTripAccommodationMutation(tripId);

  const types = useMemo(() => {
    const unique = Array.from(new Set((optionsQuery.data ?? []).map((option) => option.accommodation_type)));
    return [TYPE_FILTER_ALL, ...unique];
  }, [optionsQuery.data]);

  const filteredOptions = useMemo(() => {
    const normalizedKeyword = keyword.trim().toLocaleLowerCase();
    return (optionsQuery.data ?? []).filter((option) => {
      const matchesType = typeFilter === TYPE_FILTER_ALL || option.accommodation_type === typeFilter;
      const matchesKeyword = !normalizedKeyword || option.name.toLocaleLowerCase().includes(normalizedKeyword);
      return matchesType && matchesKeyword;
    });
  }, [optionsQuery.data, typeFilter, keyword]);

  const handleToggleOpen = () => {
    setIsOpen((previous) => !previous);
    setActionError("");
    setActionMessage("");
  };

  const invalidateAfterChange = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.trip(tripId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.trips }),
    ]);
  };

  const handleSave = async () => {
    if (!selectedId) {
      return;
    }
    setActionError("");
    setActionMessage("");
    try {
      await mutation.mutateAsync(selectedId);
      await invalidateAfterChange();
      setActionMessage("숙소를 바꿨어요.");
      setIsOpen(false);
      setSelectedId(null);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "숙소 변경에 실패했어요.");
    }
  };

  const handleUnset = async () => {
    if (!window.confirm("숙소를 해제할까요? 일정과 비용은 바뀌지 않아요.")) {
      return;
    }
    setActionError("");
    setActionMessage("");
    try {
      await mutation.mutateAsync(null);
      await invalidateAfterChange();
      setActionMessage("숙소를 해제했어요.");
      setIsOpen(false);
      setSelectedId(null);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "숙소 해제에 실패했어요.");
    }
  };

  return (
    <div className="card">
      <h2 className="section-title">숙소</h2>
      <p className="section-subtitle" style={{ marginBottom: 12 }}>
        {currentAccommodationLabel ? `현재 숙소: ${currentAccommodationLabel}` : "저장된 숙소 없음"}
      </p>

      {actionMessage ? <p className="planner-feedback success">{actionMessage}</p> : null}

      <Button onClick={handleToggleOpen} type="button" variant="secondary">
        {isOpen ? "숙소 변경 닫기" : "숙소 변경"}
      </Button>

      {isOpen ? (
        <div className="stack" style={{ marginTop: 16 }}>
          <p className="section-subtitle" style={{ margin: 0 }}>
            일정과 비용은 바뀌지 않아요.
          </p>

          {optionsQuery.isLoading ? (
            <p className="section-subtitle" style={{ margin: 0 }}>
              숙소 후보를 불러오는 중이에요.
            </p>
          ) : optionsQuery.isError ? (
            <div>
              <p className="planner-feedback error">
                {optionsQuery.error instanceof Error ? optionsQuery.error.message : "숙소 후보를 불러오지 못했어요."}
              </p>
              <Button onClick={() => optionsQuery.refetch()} type="button" variant="secondary">
                다시 시도
              </Button>
            </div>
          ) : (optionsQuery.data ?? []).length === 0 ? (
            <p className="section-subtitle" style={{ margin: 0 }}>
              선택할 수 있는 숙소 정보가 없어요.
            </p>
          ) : (
            <>
              <div className="chip-list">
                {types.map((type) => (
                  <button
                    className={`chip ${typeFilter === type ? "active" : ""}`}
                    key={type}
                    onClick={() => setTypeFilter(type)}
                    type="button"
                  >
                    {type}
                  </button>
                ))}
              </div>

              <label className="field">
                <span>이름 검색</span>
                <input
                  onChange={(event) => setKeyword(event.target.value)}
                  placeholder="숙소 이름으로 검색"
                  value={keyword}
                />
              </label>

              {filteredOptions.length === 0 ? (
                <p className="section-subtitle" style={{ margin: 0 }}>
                  조건에 맞는 숙소가 없어요.
                </p>
              ) : (
                <div className="stack" style={{ gap: 8, maxHeight: 320, overflowY: "auto" }}>
                  {filteredOptions.map((option) => {
                    const isCurrent = option.id === currentAccommodationId;
                    const isSelected = option.id === selectedId;
                    return (
                      <button
                        className="timeline-item"
                        key={option.id}
                        onClick={() => setSelectedId(option.id)}
                        style={{
                          textAlign: "left",
                          cursor: "pointer",
                          borderColor: isSelected ? "var(--primary)" : undefined,
                          background: isSelected ? "var(--primary-soft)" : undefined,
                        }}
                        type="button"
                      >
                        <div className="row" style={{ justifyContent: "space-between" }}>
                          <strong>{option.name}</strong>
                          {isCurrent ? <span className="badge">현재 숙소</span> : null}
                        </div>
                        <p className="section-subtitle" style={{ margin: "4px 0 0" }}>
                          {option.accommodation_type} · {option.area} ·{" "}
                          {formatAccommodationPriceLabel(option.average_price_krw)}
                        </p>
                      </button>
                    );
                  })}
                </div>
              )}

              <div className="row">
                <Button disabled={!selectedId || mutation.isPending} onClick={handleSave} type="button">
                  {mutation.isPending ? "저장 중..." : "저장"}
                </Button>
              </div>
            </>
          )}

          {/* 해제는 후보 목록 로딩/오류/빈 상태와 무관하게 항상 쓸 수
              있어야 한다 - 목록이 비어 있거나 조회에 실패해도 이미
              저장된 숙소를 떼어내는 것 자체는 그 목록이 필요 없다. */}
          {currentAccommodationId ? (
            <div className="row">
              <Button disabled={mutation.isPending} onClick={handleUnset} type="button" variant="ghost">
                숙소 해제
              </Button>
            </div>
          ) : null}

          {actionError ? <p className="planner-feedback error">{actionError}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
