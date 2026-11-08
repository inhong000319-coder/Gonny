// Accommodation nightly rates and the total estimated-cost range are
// individually-checked reference values from third-party sources (price
// comparison sites, official pages), not live prices - see site-footer.tsx
// for the same caveat shown to users. Update this when prices are re-checked.
export const PRICE_REFERENCE_PERIOD = "2026년 10월";

const MANWON_KRW = 10000;

// Exact amount under 1만 원, else rounded to the nearest 만 원 - a precise
// "109,254원" reads as more certain than a web-sourced reference price
// actually is, so anything at or above 1만 원 is shown as "11만 원" instead.
export function formatApproxManwon(value: number): string {
  if (value < MANWON_KRW) {
    return `${value.toLocaleString("ko-KR")}원`;
  }
  const manwon = Math.round(value / MANWON_KRW);
  return `${manwon.toLocaleString("ko-KR")}만 원`;
}

// 숙소 1박 가격 라벨 - 가격 미확인(null/undefined)을 "가격 정보 없음"으로
// 표시한다. 원래 features/trip-create/utils/accommodation-swap.ts에
// 있었으나(일정 생성 결과 화면의 "다른 숙소" 교체 패널용), 저장된 여행의
// 숙소 변경 패널(features/trips)도 같은 포맷이 필요해 공용 위치로
// 옮겼다 - accommodation-swap.ts는 이 함수를 그대로 재export한다.
export function formatAccommodationPriceLabel(averagePriceKrw: number | null | undefined): string {
  if (averagePriceKrw == null) {
    return "가격 정보 없음";
  }
  return `1박 약 ${formatApproxManwon(averagePriceKrw)}`;
}

export function formatApproxManwonRange(min: number, max: number): string {
  // min === 0 means "some priced places are free" - "약 0원 ~ 약 X" reads as
  // if even the free part were an estimate, so the confirmed 0 stays exact
  // and only the upper end gets the "약" treatment.
  if (min === 0) {
    return max === 0 ? "0원" : `0원 ~ 약 ${formatApproxManwon(max)}`;
  }
  const minLabel = formatApproxManwon(min);
  const maxLabel = formatApproxManwon(max);
  return minLabel === maxLabel ? `약 ${minLabel}` : `약 ${minLabel} ~ ${maxLabel}`;
}
