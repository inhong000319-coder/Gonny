import { FormEvent, useMemo, useState } from "react";
import { AppShell } from "../../app/layouts/app-shell";
import { CommunityJournalModal } from "../../features/community/components/community-journal-modal";
import { useCommunityJournalsQuery } from "../../features/community/hooks/use-community-journals-query";
import { formatRegionLabel } from "../../features/community/lib/region-label";
import { Button } from "../../shared/components/ui/button";

function formatDate(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(parsed);
}

function buildPageNumbers(page: number, totalPages: number) {
  const start = Math.max(1, page - 2);
  const end = Math.min(totalPages, start + 4);
  const pages: number[] = [];
  for (let current = start; current <= end; current += 1) {
    pages.push(current);
  }
  return pages;
}

export function CommunityJournalsPage() {
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<"views" | "recommendations">("views");
  const [searchInput, setSearchInput] = useState("");
  const [keyword, setKeyword] = useState("");
  const [selectedJournalId, setSelectedJournalId] = useState<number | null>(null);

  const { data, isLoading } = useCommunityJournalsQuery({
    page,
    pageSize: 9,
    sort,
    keyword,
  });

  const totalPages = useMemo(() => {
    if (!data) {
      return 1;
    }
    return Math.max(1, Math.ceil(data.total / data.page_size));
  }, [data]);

  const pages = buildPageNumbers(page, totalPages);

  const handleSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPage(1);
    setKeyword(searchInput);
  };

  return (
    <AppShell>
      <section className="page-hero panel panel-gradient">
        <div className="stack">
          <span className="section-kicker">COMMUNITY JOURNALS</span>
          <h1 className="section-title" style={{ fontSize: "2.1rem", margin: 0 }}>
            여행 다이어리 전체 보기
          </h1>
          <p className="section-subtitle" style={{ marginBottom: 0 }}>
            조회수, 추천수, 제목 키워드 기준으로 원하는 다이어리를 찾아볼 수 있어요.
          </p>
        </div>
      </section>

      <section className="card stack">
        <form className="row" onSubmit={handleSearchSubmit} style={{ alignItems: "end", gap: "12px", flexWrap: "wrap" }}>
          <label className="field" style={{ flex: 1, minWidth: "220px" }}>
            <span>글 제목 검색</span>
            <input value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="예: 제주, 브런치, 야경" />
          </label>
          <label className="field" style={{ minWidth: "200px" }}>
            <span>정렬 기준</span>
            <select value={sort} onChange={(event) => setSort(event.target.value as "views" | "recommendations")}>
              <option value="views">조회수순</option>
              <option value="recommendations">추천순</option>
            </select>
          </label>
          <Button type="submit">검색하기</Button>
        </form>
      </section>

      <section className="card stack">
        {isLoading ? <p className="section-subtitle">다이어리를 불러오고 있어요.</p> : null}

        <div className="stack">
          {data?.items.map((journal) => (
            <article key={journal.id} className="timeline-item community-entry-card">
              <div className="memory-list-head">
                <div>
                  <strong>{journal.title}</strong>
                  <p className="community-meta-line">
                    {journal.trip_title} · {formatRegionLabel(journal.destination)} · {formatDate(journal.created_at)}
                  </p>
                </div>
                <button className="button secondary" onClick={() => setSelectedJournalId(journal.id)} type="button">
                  글 보기
                </button>
              </div>
              <p className="community-entry-copy">{journal.diary_text}</p>
              <div className="chip-list">
                <span className="chip">조회수 {journal.view_count}</span>
                <span className="chip">추천 {journal.recommendation_count}</span>
              </div>
            </article>
          ))}
        </div>

        <div className="row" style={{ justifyContent: "center", gap: "8px", flexWrap: "wrap" }}>
          <button className="button secondary" disabled={page <= 1} onClick={() => setPage((prev) => prev - 1)} type="button">
            {"<"}
          </button>
          {pages.map((pageNumber) => (
            <button
              key={pageNumber}
              className={pageNumber === page ? "button" : "button secondary"}
              onClick={() => setPage(pageNumber)}
              type="button"
            >
              {pageNumber}
            </button>
          ))}
          <button
            className="button secondary"
            disabled={page >= totalPages}
            onClick={() => setPage((prev) => prev + 1)}
            type="button"
          >
            {">"}
          </button>
        </div>
      </section>

      {selectedJournalId !== null ? <CommunityJournalModal journalId={selectedJournalId} onClose={() => setSelectedJournalId(null)} /> : null}
    </AppShell>
  );
}
