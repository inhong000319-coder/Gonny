import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AppShell } from "../../app/layouts/app-shell";
import { apiClient } from "../../shared/api/client";
import {
  CityCatalog,
  DestinationSummary,
  labelCategory,
  labelCity,
  labelContinent,
  labelCountry,
} from "./admin-data-shared";

export function AdminDataPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [destinations, setDestinations] = useState<DestinationSummary[]>([]);
  const [catalog, setCatalog] = useState<CityCatalog | null>(null);
  const [statusText, setStatusText] = useState("도시와 장소를 고른 뒤 수정 페이지로 이동하면 더 편하게 관리할 수 있어요.");

  const selectedContinent = searchParams.get("continent") ?? "";
  const selectedCountry = searchParams.get("country") ?? "";
  const selectedCity = searchParams.get("city") ?? "";
  const searchKeyword = searchParams.get("q") ?? "";

  useEffect(() => {
    async function loadDestinations() {
      const response = await apiClient.get<{ destinations: DestinationSummary[] }>("/admin/destinations");
      setDestinations(response.data.destinations ?? []);
    }

    void loadDestinations();
  }, []);

  const filteredDestinations = useMemo(() => {
    const keyword = searchKeyword.trim().toLowerCase();
    return destinations.filter((destination) => {
      const searchTarget = [
        destination.continent,
        destination.country,
        destination.city,
        labelContinent(destination.continent),
        labelCountry(destination.country),
        labelCity(destination.city),
      ]
        .join(" ")
        .toLowerCase();
      return keyword ? searchTarget.includes(keyword) : true;
    });
  }, [destinations, searchKeyword]);

  const continentOptions = useMemo(() => {
    return Array.from(new Set(filteredDestinations.map((destination) => destination.continent)));
  }, [filteredDestinations]);

  const countryOptions = useMemo(() => {
    if (!selectedContinent) return [];
    return Array.from(
      new Set(
        filteredDestinations
          .filter((destination) => destination.continent === selectedContinent)
          .map((destination) => destination.country),
      ),
    );
  }, [filteredDestinations, selectedContinent]);

  const cityOptions = useMemo(() => {
    if (!selectedContinent || !selectedCountry) return [];
    return filteredDestinations.filter(
      (destination) => destination.continent === selectedContinent && destination.country === selectedCountry,
    );
  }, [filteredDestinations, selectedContinent, selectedCountry]);

  useEffect(() => {
    if (!continentOptions.length) return;

    const nextContinent = continentOptions.includes(selectedContinent) ? selectedContinent : continentOptions[0];
    const nextCountryOptions = Array.from(
      new Set(
        filteredDestinations
          .filter((destination) => destination.continent === nextContinent)
          .map((destination) => destination.country),
      ),
    );
    const nextCountry = nextCountryOptions.includes(selectedCountry) ? selectedCountry : nextCountryOptions[0] ?? "";
    const nextCityOptions = filteredDestinations.filter(
      (destination) => destination.continent === nextContinent && destination.country === nextCountry,
    );
    const nextCity = nextCityOptions.some((destination) => destination.city === selectedCity)
      ? selectedCity
      : nextCityOptions[0]?.city ?? "";

    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("continent", nextContinent);
    if (nextCountry) nextParams.set("country", nextCountry);
    if (nextCity) nextParams.set("city", nextCity);

    if (nextParams.toString() !== searchParams.toString()) {
      setSearchParams(nextParams, { replace: true });
    }
  }, [
    continentOptions,
    filteredDestinations,
    searchParams,
    selectedCity,
    selectedContinent,
    selectedCountry,
    setSearchParams,
  ]);

  useEffect(() => {
    async function loadCatalog() {
      if (!selectedCity) return;
      const response = await apiClient.get<CityCatalog>(`/admin/destinations/${selectedCity}`);
      setCatalog(response.data);
    }

    void loadCatalog();
  }, [selectedCity]);

  const placeList = useMemo(() => {
    if (!catalog) return [];
    const keyword = searchKeyword.trim().toLowerCase();
    return catalog.places.filter((place) => {
      const searchTarget = [place.name, place.id, place.area, place.summary, ...place.category].join(" ").toLowerCase();
      return keyword ? searchTarget.includes(keyword) : true;
    });
  }, [catalog, searchKeyword]);

  function updateParam(key: string, value: string) {
    const nextParams = new URLSearchParams(searchParams);
    if (value) {
      nextParams.set(key, value);
    } else {
      nextParams.delete(key);
    }
    setSearchParams(nextParams);
  }

  async function toggleActive(placeId: string, nextActive: boolean, placeName: string) {
    if (!selectedCity) return;
    await apiClient.patch(`/admin/destinations/${selectedCity}/places/${placeId}/active`, {
      is_active: nextActive,
    });
    const response = await apiClient.get<CityCatalog>(`/admin/destinations/${selectedCity}`);
    setCatalog(response.data);
    setStatusText(`${placeName}의 활성 상태를 변경했어요.`);
  }

  const selectedQuery = `?continent=${selectedContinent}&country=${selectedCountry}&city=${selectedCity}&q=${searchKeyword}`;

  return (
    <AppShell>
      <section className="admin-page">
        <div className="admin-header">
          <div>
            <p className="planner-kicker">데이터 운영</p>
            <h1 className="planner-title">여행 데이터 관리</h1>
            <p className="planner-description">
              목록에서는 빠르게 찾고 고르고, 수정이 필요할 때만 별도 화면으로 들어가도록 나눠서 더 가볍게 운영할 수 있어요.
            </p>
          </div>
          <p className="admin-status">{statusText}</p>
        </div>

        <section className="admin-filter-shell">
          <label className="admin-search">
            <span>검색</span>
            <input
              placeholder="도시명, 장소명, 카테고리로 찾아보세요."
              value={searchKeyword}
              onChange={(event) => updateParam("q", event.target.value)}
            />
          </label>

          <div className="admin-filter-group">
            <span className="admin-filter-label">대륙</span>
            <div className="admin-chip-row">
              {continentOptions.map((continent) => (
                <button
                  key={continent}
                  className={selectedContinent === continent ? "admin-chip active" : "admin-chip"}
                  onClick={() => updateParam("continent", continent)}
                  type="button"
                >
                  {labelContinent(continent)}
                </button>
              ))}
            </div>
          </div>

          <div className="admin-filter-group">
            <span className="admin-filter-label">국가</span>
            <div className="admin-chip-row">
              {countryOptions.map((country) => (
                <button
                  key={country}
                  className={selectedCountry === country ? "admin-chip active" : "admin-chip"}
                  onClick={() => updateParam("country", country)}
                  type="button"
                >
                  {labelCountry(country)}
                </button>
              ))}
            </div>
          </div>

          <div className="admin-filter-group">
            <span className="admin-filter-label">도시</span>
            <div className="admin-chip-row">
              {cityOptions.map((destination) => (
                <button
                  key={destination.city}
                  className={selectedCity === destination.city ? "admin-chip active" : "admin-chip"}
                  onClick={() => updateParam("city", destination.city)}
                  type="button"
                >
                  {labelCity(destination.city)}
                </button>
              ))}
            </div>
          </div>
        </section>

        <div className="admin-summary-bar">
          <div className="admin-summary-card">
            <strong>{catalog ? labelCity(catalog.city) : "-"}</strong>
            <span>전체 장소 {catalog?.places.length ?? 0}개</span>
          </div>
          <div className="admin-summary-card">
            <strong>활성 장소</strong>
            <span>{catalog?.places.filter((place) => place.is_active ?? true).length ?? 0}개</span>
          </div>
          <div className="admin-summary-card">
            <strong>체험 장소</strong>
            <span>
              {catalog?.places.filter((place) =>
                place.category.some((category) => ["activity", "theme_park", "local_experience"].includes(category)),
              ).length ?? 0}
              개
            </span>
          </div>
        </div>

        <section className="admin-panel admin-list-panel">
          <div className="admin-panel-head">
            <h2>장소 목록</h2>
            <Link className="admin-primary-link" to={`/admin/data/${selectedCity}/new${selectedQuery}`}>
              {selectedCity ? `${labelCity(selectedCity)}에 새 장소 추가` : "새 장소 추가"}
            </Link>
          </div>

          <div className="admin-place-list admin-place-list-scroll compact">
            {placeList.map((place) => (
              <article key={place.id} className="admin-place-card">
                <div className="admin-place-main">
                  <strong>{place.name}</strong>
                  <span>{place.category.map(labelCategory).join(", ")}</span>
                  <span>
                    추천 우선순위 {place.priority} · MVP {place.mvp_tier ?? "standard"} ·{" "}
                    {(place.is_active ?? true) ? "활성" : "비활성"}
                  </span>
                </div>
                <div className="admin-card-actions">
                  <Link className="admin-secondary-link" to={`/admin/data/${selectedCity}/${place.id}/edit${selectedQuery}`}>
                    수정하기
                  </Link>
                  <button
                    className="admin-toggle-button"
                    onClick={() => void toggleActive(place.id, !(place.is_active ?? true), place.name)}
                    type="button"
                  >
                    {(place.is_active ?? true) ? "비활성화" : "활성화"}
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </section>
    </AppShell>
  );
}
