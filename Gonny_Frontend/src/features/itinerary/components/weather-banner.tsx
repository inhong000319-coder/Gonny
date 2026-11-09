import { useState } from "react";
import { Button } from "../../../shared/components/ui/button";

// Structurally mirrors the backend's RuleSlotAlternative (see
// trip-create-form.tsx's own local copy) - kept local for the same reason
// as RuleWeatherAlert below.
type WeatherSwapCandidate = {
  place_id: string;
  place_name: string;
  category: string;
  area: string;
  notes: string;
  average_cost_krw?: number | null;
};

type WeatherTimeSlot = "morning" | "afternoon" | "evening";

// Structurally mirrors the backend's RuleWeatherAffectedItem (PR #115) -
// one entry per (alert.day_number, time_slot) that the alert's affected
// place occupies.
type WeatherAffectedItem = {
  time_slot: WeatherTimeSlot;
  place_id: string;
  place_name: string;
  swap_candidates: WeatherSwapCandidate[];
};

// Structurally mirrors the backend's RuleWeatherAlert
// (day_number/condition/precipitation_mm/affected_place_names/
// suggested_alternatives/affected_items) - kept local rather than imported from
// trip-create-form.tsx, same pattern as shared/itinerary-export.ts's
// own local ItineraryItem/ExportLabels types.
type RuleWeatherAlert = {
  day_number: number;
  condition: "rain" | "snow";
  precipitation_mm: number;
  affected_place_names: string[];
  suggested_alternatives: string[];
  // 구버전 응답(캐시 등)에는 없을 수 있어 옵셔널 - 없거나 비어 있으면
  // suggested_alternatives 배지 표시로 폴백한다.
  affected_items?: WeatherAffectedItem[];
};

type WeatherBannerProps = {
  alert: RuleWeatherAlert;
  // 이 affected item이 현재 어떤 후보로 교체돼 있는지(없으면 null) - 부모의
  // slotSwaps를 직접 넘기지 않고 조회 결과만 받는다(이 컴포넌트는
  // slotSwaps/result.items를 모른다).
  getActiveSwapPlaceId: (item: WeatherAffectedItem) => string | null;
  // candidateName이 이 affected item이 아닌 다른 슬롯에서 이미 쓰이고
  // 있는지 - 역시 판정 결과만 받는다.
  isSwapNameUsedElsewhere: (item: WeatherAffectedItem, candidateName: string) => boolean;
  onSelectSwap: (item: WeatherAffectedItem, candidate: WeatherSwapCandidate) => void;
  onRevertSwap: (item: WeatherAffectedItem) => void;
};

function CloudRainIcon() {
  return (
    <svg aria-hidden="true" className="status-icon" fill="none" viewBox="0 0 24 24">
      <path
        d="M8 18h8a4 4 0 0 0 .52-7.97A5.5 5.5 0 0 0 6 11a3.5 3.5 0 0 0 2 7Z"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <path d="M9 18.8 8 21M12 18.8 11 21M15 18.8 14 21" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function conditionLabel(condition: RuleWeatherAlert["condition"]) {
  return condition === "snow" ? "눈" : "비";
}

function timeSlotLabel(slot: WeatherTimeSlot) {
  if (slot === "morning") return "오전";
  if (slot === "afternoon") return "오후";
  return "저녁";
}

export function WeatherBanner({
  alert,
  getActiveSwapPlaceId,
  isSwapNameUsedElsewhere,
  onSelectSwap,
  onRevertSwap,
}: WeatherBannerProps) {
  const [showAlternatives, setShowAlternatives] = useState(false);
  const affectedItems = alert.affected_items ?? [];
  // 구버전 응답이거나(affected_items 없음) 후보가 전부 비어 있으면 고를 수
  // 있는 칩이 하나도 없다 - 그 경우 "골라두면 [재계산]으로…" 안내는
  // 현재 상태와 맞지 않아 PR #116 이전 문구로 되돌린다.
  const hasSelectableCandidates = affectedItems.some((item) => item.swap_candidates.length > 0);
  // 같은 장소명이 여러 슬롯(종일 장소)에 걸쳐 있을 수 있어, 그 중 하나라도
  // 교체 상태면 그 이름의 태그에 "교체됨"을 붙인다. affected_items가 없으면
  // 판정할 방법이 없어 지금처럼(표시 없이) 둔다.
  const swappedPlaceNames = new Set(
    affectedItems.filter((item) => getActiveSwapPlaceId(item) !== null).map((item) => item.place_name),
  );

  return (
    <div className="weather-banner">
      <div className="weather-banner-icon">
        <CloudRainIcon />
      </div>
      <div className="weather-banner-copy">
        <h3 className="section-title" style={{ marginBottom: 6 }}>
          {alert.day_number}일차, {conditionLabel(alert.condition)} 예보가 있어요
        </h3>
        <p className="section-subtitle" style={{ marginBottom: 8 }}>
          {hasSelectableCandidates
            ? `예상 강수량 ${alert.precipitation_mm}mm. 일정은 자동으로 바뀌지 않아요 - 실내 대안을 골라두면 [재계산]으로 이동 시간까지 맞춰드려요.`
            : `예상 강수량 ${alert.precipitation_mm}mm. 일정은 자동으로 바뀌지 않아요 - 실내 대안을 참고해서 직접 정해보세요.`}
        </p>
        {alert.affected_place_names.length > 0 ? (
          <div className="planner-result-tags">
            {alert.affected_place_names.map((placeName) => (
              <span className="badge" key={placeName}>
                {placeName}
                {swappedPlaceNames.has(placeName) ? <span className="tc-alt-chip-area"> · 교체됨</span> : null}
              </span>
            ))}
          </div>
        ) : null}
      </div>
      <div className="weather-banner-actions">
        <Button onClick={() => setShowAlternatives(false)} type="button" variant="secondary">
          이 계획 유지
        </Button>
        <Button onClick={() => setShowAlternatives(true)} type="button">
          실내 대안 보기
        </Button>
      </div>
      {showAlternatives ? (
        affectedItems.length > 0 ? (
          <div className="weather-banner-affected-list">
            {affectedItems.map((item) => {
              const activePlaceId = getActiveSwapPlaceId(item);
              return (
                <div className="weather-banner-affected-row" key={`${item.time_slot}-${item.place_id}`}>
                  <span className="weather-banner-affected-label">
                    {item.place_name} ({timeSlotLabel(item.time_slot)}) → 실내 대안
                  </span>
                  {item.swap_candidates.length > 0 ? (
                    <div className="tc-alt-panel">
                      <div className="tc-chip-row">
                        {item.swap_candidates.map((candidate) => {
                          const isActive = candidate.place_id === activePlaceId;
                          const isDisabled = !isActive && isSwapNameUsedElsewhere(item, candidate.place_name);
                          return (
                            <button
                              aria-pressed={isActive}
                              className={`tc-chip tc-alt-chip ${isActive ? "is-selected" : ""}`}
                              disabled={isDisabled}
                              key={candidate.place_id}
                              onClick={() => onSelectSwap(item, candidate)}
                              title={isDisabled ? "이미 다른 일정에 쓰이고 있어요" : undefined}
                              type="button"
                            >
                              {candidate.place_name}
                              <span className="tc-alt-chip-area"> · {candidate.area}</span>
                            </button>
                          );
                        })}
                        {activePlaceId ? (
                          <button
                            className="tc-btn tc-btn-ghost tc-alt-revert"
                            onClick={() => onRevertSwap(item)}
                            type="button"
                          >
                            원래 장소로 되돌리기
                          </button>
                        ) : null}
                      </div>
                    </div>
                  ) : (
                    <p className="section-subtitle" style={{ marginBottom: 0 }}>
                      바꿀 수 있는 실내 후보가 없어요.
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="weather-banner-alternatives">
            {alert.suggested_alternatives.length > 0 ? (
              alert.suggested_alternatives.map((placeName) => (
                <span className="badge" key={placeName}>
                  {placeName}
                </span>
              ))
            ) : (
              <p className="section-subtitle" style={{ marginBottom: 0 }}>
                추천할 만한 실내 대안을 찾지 못했어요.
              </p>
            )}
          </div>
        )
      ) : null}
    </div>
  );
}
