import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "../../../shared/components/ui/button";
import { queryKeys } from "../../../shared/api/query-keys";
import { TripStayOverview } from "../../../shared/types/domain";
import { useTripAccommodationOptionsQuery } from "../hooks/use-trip-accommodation-options-query";
import { useUpdateTripAccommodationMutation } from "../hooks/use-update-trip-accommodation-mutation";
import { formatAccommodationLabel, formatStayNightRange } from "../utils/format-accommodation-label";
import { getAdjacentAccommodationIds } from "../utils/trip-stay-adjacency";
import { TripAccommodationOptionDto } from "../types/trips";

type AccommodationChangePanelProps = {
  tripId: string;
  // #135 - 항상 전달됨(TripOverview.stays, 숙소 없으면 []). 길이 1
  // 이하면 기존 단일 숙소 UI/동작을 한 글자도 바꾸지 않고 그대로 쓴다
  // (stays[0]가 그 "현재 숙소"다) - 과제 constraint.
  stays: TripStayOverview[];
};

const TYPE_FILTER_ALL = "전체";

// 후보 목록(유형 필터 + 검색 + 선택)만 다루는 조각 - 단일 숙소 패널과
// stay별 변경 행이 똑같은 후보 선택 UI를 쓰므로 하나로 모았다.
// excludedAccommodationIds(인접 stay가 이미 쓰는 숙소, #135)에 해당하는
// 후보는 고를 수 없게 비활성화한다 - 서버도 422로 막지만, 애초에 고를 수
// 없게 해서 그 에러를 거의 안 보게 하려는 보조 장치일 뿐이다.
function AccommodationOptionPicker({
  tripId,
  currentAccommodationId,
  excludedAccommodationIds = [],
  isSaving,
  onSave,
}: {
  tripId: string;
  currentAccommodationId?: string;
  excludedAccommodationIds?: string[];
  isSaving: boolean;
  onSave: (accommodationId: string) => void;
}) {
  const [typeFilter, setTypeFilter] = useState(TYPE_FILTER_ALL);
  const [keyword, setKeyword] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const optionsQuery = useTripAccommodationOptionsQuery(tripId, true);

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

  if (optionsQuery.isLoading) {
    return (
      <p className="section-subtitle" style={{ margin: 0 }}>
        숙소 후보를 불러오는 중이에요.
      </p>
    );
  }

  if (optionsQuery.isError) {
    return (
      <div>
        <p className="planner-feedback error">
          {optionsQuery.error instanceof Error ? optionsQuery.error.message : "숙소 후보를 불러오지 못했어요."}
        </p>
        <Button onClick={() => optionsQuery.refetch()} type="button" variant="secondary">
          다시 시도
        </Button>
      </div>
    );
  }

  if ((optionsQuery.data ?? []).length === 0) {
    return (
      <p className="section-subtitle" style={{ margin: 0 }}>
        선택할 수 있는 숙소 정보가 없어요.
      </p>
    );
  }

  return (
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
        <input onChange={(event) => setKeyword(event.target.value)} placeholder="숙소 이름으로 검색" value={keyword} />
      </label>

      {filteredOptions.length === 0 ? (
        <p className="section-subtitle" style={{ margin: 0 }}>
          조건에 맞는 숙소가 없어요.
        </p>
      ) : (
        <div className="stack" style={{ gap: 8, maxHeight: 320, overflowY: "auto" }}>
          {filteredOptions.map((option: TripAccommodationOptionDto) => {
            const isCurrent = option.id === currentAccommodationId;
            const isSelected = option.id === selectedId;
            const isExcluded = excludedAccommodationIds.includes(option.id) && !isCurrent;
            return (
              <button
                className="timeline-item"
                disabled={isExcluded}
                key={option.id}
                onClick={() => setSelectedId(option.id)}
                style={{
                  textAlign: "left",
                  cursor: isExcluded ? "not-allowed" : "pointer",
                  opacity: isExcluded ? 0.5 : 1,
                  borderColor: isSelected ? "var(--primary)" : undefined,
                  background: isSelected ? "var(--primary-soft)" : undefined,
                }}
                type="button"
              >
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <strong>{option.name}</strong>
                  {isCurrent ? <span className="badge">현재 숙소</span> : isExcluded ? <span className="badge">인접 숙소와 중복</span> : null}
                </div>
                <p className="section-subtitle" style={{ margin: "4px 0 0" }}>
                  {option.accommodation_type} · {option.area}
                </p>
              </button>
            );
          })}
        </div>
      )}

      <div className="row">
        <Button disabled={!selectedId || isSaving} onClick={() => selectedId && onSave(selectedId)} type="button">
          {isSaving ? "저장 중..." : "저장"}
        </Button>
      </div>
    </>
  );
}

export function AccommodationChangePanel({ tripId, stays }: AccommodationChangePanelProps) {
  const queryClient = useQueryClient();
  const mutation = useUpdateTripAccommodationMutation(tripId);

  const invalidateAfterChange = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.trip(tripId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.trips }),
    ]);
  };

  if (stays.length < 2) {
    return (
      <SingleAccommodationChangePanel
        currentAccommodationId={stays[0]?.accommodationId}
        currentAccommodationLabel={
          stays[0]
            ? formatAccommodationLabel({
                accommodation_name: stays[0].accommodationName,
                accommodation_type: stays[0].accommodationType,
              })
            : undefined
        }
        invalidateAfterChange={invalidateAfterChange}
        mutation={mutation}
        tripId={tripId}
      />
    );
  }

  return (
    <MultiStayAccommodationChangePanel
      invalidateAfterChange={invalidateAfterChange}
      mutation={mutation}
      stays={stays}
      tripId={tripId}
    />
  );
}

// 숙소가 한 곳(또는 없음)인 여행 - #135 이전과 완전히 같은 UI/동작. PATCH
// 호출에 stayIndex를 안 넘기므로 요청 본문에 stay_index가 들어가지
// 않는다(useUpdateTripAccommodationMutation/updateTripAccommodation 참고).
function SingleAccommodationChangePanel({
  tripId,
  currentAccommodationId,
  currentAccommodationLabel,
  mutation,
  invalidateAfterChange,
}: {
  tripId: string;
  currentAccommodationId?: string;
  currentAccommodationLabel?: string;
  mutation: ReturnType<typeof useUpdateTripAccommodationMutation>;
  invalidateAfterChange: () => Promise<void>;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionMessage, setActionMessage] = useState("");

  const handleToggleOpen = () => {
    setIsOpen((previous) => !previous);
    setActionError("");
    setActionMessage("");
  };

  const handleSave = async (accommodationId: string) => {
    setActionError("");
    setActionMessage("");
    try {
      await mutation.mutateAsync({ accommodationId });
      await invalidateAfterChange();
      setActionMessage("숙소를 바꿨어요.");
      setIsOpen(false);
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
      await mutation.mutateAsync({ accommodationId: null });
      await invalidateAfterChange();
      setActionMessage("숙소를 해제했어요.");
      setIsOpen(false);
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

          <AccommodationOptionPicker
            currentAccommodationId={currentAccommodationId}
            isSaving={mutation.isPending}
            onSave={handleSave}
            tripId={tripId}
          />

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

function formatStayHeading(stay: TripStayOverview): string {
  return `숙소 ${stay.stayIndex + 1} · ${formatStayNightRange(stay.startNight, stay.nights)}`;
}

// 한자어 수사(하나·둘이 아니라 일·이·삼...으로 읽는 숫자) 기준 받침
// 유무로 "을/를"을 고른다 - 마지막 숫자가 1·3·6·7·8·0(일·삼·육·칠·팔·영,
// 받침 있음)이면 "을", 2·4·5·9(이·사·오·구, 받침 없음)이면 "를".
const OBJECT_PARTICLE_NO_BATCHIM_LAST_DIGITS = new Set(["2", "4", "5", "9"]);

function getNumberObjectParticle(value: number): "을" | "를" {
  const lastDigit = Math.abs(value).toString().slice(-1);
  return OBJECT_PARTICLE_NO_BATCHIM_LAST_DIGITS.has(lastDigit) ? "를" : "을";
}

// 숙소가 분할 저장된(2곳 이상) 여행 - stay마다 독립적으로 바꿀 수 있는 행.
function MultiStayAccommodationChangePanel({
  tripId,
  stays,
  mutation,
  invalidateAfterChange,
}: {
  tripId: string;
  stays: TripStayOverview[];
  mutation: ReturnType<typeof useUpdateTripAccommodationMutation>;
  invalidateAfterChange: () => Promise<void>;
}) {
  const [openStayIndex, setOpenStayIndex] = useState<number | null>(null);
  const [actionError, setActionError] = useState("");
  const [actionMessage, setActionMessage] = useState("");

  const handleToggleStay = (stayIndex: number) => {
    setOpenStayIndex((previous) => (previous === stayIndex ? null : stayIndex));
    setActionError("");
    setActionMessage("");
  };

  const handleSaveForStay = async (stayIndex: number, accommodationId: string) => {
    setActionError("");
    setActionMessage("");
    try {
      await mutation.mutateAsync({ accommodationId, stayIndex });
      await invalidateAfterChange();
      const displayIndex = stayIndex + 1;
      setActionMessage(`숙소 ${displayIndex}${getNumberObjectParticle(displayIndex)} 바꿨어요.`);
      setOpenStayIndex(null);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "숙소 변경에 실패했어요.");
    }
  };

  const handleUnsetAll = async () => {
    if (!window.confirm("모든 숙소를 해제할까요? 일정과 비용은 바뀌지 않아요.")) {
      return;
    }
    setActionError("");
    setActionMessage("");
    try {
      await mutation.mutateAsync({ accommodationId: null });
      await invalidateAfterChange();
      setActionMessage("숙소를 모두 해제했어요.");
      setOpenStayIndex(null);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "숙소 해제에 실패했어요.");
    }
  };

  return (
    <div className="card">
      <h2 className="section-title">숙소</h2>
      <p className="section-subtitle" style={{ marginBottom: 12 }}>
        {stays.length}곳으로 나뉜 숙소예요.
      </p>

      {actionMessage ? <p className="planner-feedback success">{actionMessage}</p> : null}

      <div className="stack" style={{ gap: 12 }}>
        {stays.map((stay, index) => (
          <div className="timeline-item" key={stay.stayIndex}>
            <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <strong>{formatStayHeading(stay)}</strong>
                <p className="section-subtitle" style={{ margin: "4px 0 0" }}>
                  {formatAccommodationLabel({
                    accommodation_name: stay.accommodationName,
                    accommodation_type: stay.accommodationType,
                  })}
                </p>
              </div>
              <Button onClick={() => handleToggleStay(index)} type="button" variant="secondary">
                {openStayIndex === index ? "닫기" : "변경"}
              </Button>
            </div>

            {openStayIndex === index ? (
              <div className="stack" style={{ marginTop: 12 }}>
                <AccommodationOptionPicker
                  currentAccommodationId={stay.accommodationId}
                  excludedAccommodationIds={getAdjacentAccommodationIds(stays, index)}
                  isSaving={mutation.isPending}
                  onSave={(accommodationId) => handleSaveForStay(index, accommodationId)}
                  tripId={tripId}
                />
              </div>
            ) : null}
          </div>
        ))}
      </div>

      <div className="row" style={{ marginTop: 16 }}>
        <Button disabled={mutation.isPending} onClick={handleUnsetAll} type="button" variant="ghost">
          숙소 전체 해제
        </Button>
      </div>

      {actionError ? <p className="planner-feedback error">{actionError}</p> : null}
    </div>
  );
}
