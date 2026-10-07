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

export function formatApproxManwonRange(min: number, max: number): string {
  const minLabel = formatApproxManwon(min);
  const maxLabel = formatApproxManwon(max);
  return minLabel === maxLabel ? `약 ${minLabel}` : `약 ${minLabel} ~ ${maxLabel}`;
}
