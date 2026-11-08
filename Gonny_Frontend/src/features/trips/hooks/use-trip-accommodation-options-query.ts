import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../../../shared/api/query-keys";
import { getTripAccommodationOptions } from "../api/get-trip-accommodation-options";

// enabled: 변경 패널을 펼쳤을 때만 조회한다(페이지 진입 시 자동 조회
// 금지 - 과제 constraint). 패널을 접었다 다시 펼쳐도 React Query의
// 기본 캐시를 그대로 쓴다 - 후보 목록이 트립 저장 중간에 자주 바뀔
// 데이터가 아니라 매번 새로 받아올 필요가 없다고 판단했다.
export function useTripAccommodationOptionsQuery(tripId: string, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.tripAccommodationOptions(tripId),
    queryFn: () => getTripAccommodationOptions(tripId),
    enabled,
  });
}
