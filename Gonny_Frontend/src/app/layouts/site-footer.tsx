export function SiteFooter() {
  return (
    <footer className="site-footer">
      <p>
        여행 정보 출처:{" "}
        <a href="https://www.data.go.kr" rel="noopener noreferrer" target="_blank">
          한국관광공사 TourAPI
        </a>{" "}
        (공공데이터포털)
      </p>
      <p>숙소 유형 일부와 예산 등급은 서비스에서 보정·추정한 값으로 원본과 다를 수 있습니다.</p>
      <p>입장료·숙소 요금은 확인 시점의 참고 정보이며 실제 요금과 다를 수 있습니다.</p>
    </footer>
  );
}
