const REGION_LABELS: Record<string, string> = {
  bangkok: "방콕",
  barcelona: "바르셀로나",
  busan: "부산",
  chiangmai: "치앙마이",
  fukuoka: "후쿠오카",
  gangneung: "강릉",
  gyeongju: "경주",
  jeju: "제주",
  jeonju: "전주",
  kyoto: "교토",
  osaka: "오사카",
  paris: "파리",
  rome: "로마",
  seoul: "서울",
  singapore: "싱가포르",
  sokcho: "속초",
  taipei: "타이베이",
  tokyo: "도쿄",
  vladivostok: "블라디보스토크",
  yeosu: "여수",
};

export function formatRegionLabel(value: string | null | undefined) {
  if (!value) {
    return "";
  }

  return REGION_LABELS[value] ?? value;
}
