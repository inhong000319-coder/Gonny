import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AppShell } from "../../app/layouts/app-shell";
import { apiClient } from "../../shared/api/client";
import {
  CityCatalog,
  DestinationSummary,
  displayCity,
  displayContinent,
  displayCountry,
  getApiErrorMessage,
  labelCategory,
  labelVisibilityLevel,
} from "./admin-data-shared";

type PlaceListItem = CityCatalog["places"][number] & {
  city: string;
  cityLabel: string;
};

export function AdminDataPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [destinations, setDestinations] = useState<DestinationSummary[]>([]);
  const [catalogs, setCatalogs] = useState<CityCatalog[]>([]);
  const [statusText, setStatusText] = useState(
    "여행지를 고르거나 장소를 검색해서 바로 수정 화면으로 이동해보세요.",
  );

  const selectedContinent = searchParams.get("continent") ?? "";
  const selectedCountry = searchParams.get("country") ?? "";
  const selectedCity = searchParams.get("city") ?? "";
  const searchKeyword = searchParams.get("q") ?? "";
  const selectedView = searchParams.get("view") ?? "all";

  useEffect(() => {
    async function loadDestinations() {
      try {
        const response = await apiClient.get<{ destinations: DestinationSummary[] }>("/admin/destinations");
        setDestinations(response.data.destinations ?? []);
      } catch (error) {
        setStatusText(getApiErrorMessage(error, "여행지 목록을 불러오지 못했습니다."));
      }
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
        displayContinent(destination),
        displayCountry(destination),
        displayCity(destination),
      ]
        .join(" ")
        .toLowerCase();
      return keyword ? searchTarget.includes(keyword) : true;
    });
  }, [destinations, searchKeyword]);

  const continentOptions = useMemo(
    () => Array.from(new Set(filteredDestinations.map((destination) => destination.continent))),
    [filteredDestinations],
  );

  const countryOptions = useMemo(() => {
    if (!selectedContinent) {
      return Array.from(new Set(filteredDestinations.map((destination) => destination.country)));
    }
    return Array.from(
      new Set(
        filteredDestinations
          .filter((destination) => destination.continent === selectedContinent)
          .map((destination) => destination.country),
      ),
    );
  }, [filteredDestinations, selectedContinent]);

  const cityOptions = useMemo(() => {
    return filteredDestinations.filter((destination) => {
      if (selectedContinent && destination.continent !== selectedContinent) return false;
      if (selectedCountry && destination.country !== selectedCountry) return false;
      return true;
    });
  }, [filteredDestinations, selectedContinent, selectedCountry]);

  useEffect(() => {
    async function loadCatalogs() {
      const targetCities = cityOptions
        .filter((destination) => !selectedCity || destination.city === selectedCity)
        .map((destination) => destination.city);

      if (!targetCities.length) {
        setCatalogs([]);
        return;
      }

      try {
        const responses = await Promise.all(
          targetCities.map((city) => apiClient.get<CityCatalog>(`/admin/destinations/${city}`)),
        );
        setCatalogs(responses.map((response) => response.data));
      } catch (error) {
        setStatusText(getApiErrorMessage(error, "장소 목록을 불러오지 못했습니다."));
      }
    }

    void loadCatalogs();
  }, [cityOptions, selectedCity]);

  const activeCatalog = useMemo(() => {
    if (!selectedCity) return null;
    return catalogs.find((catalog) => catalog.city === selectedCity) ?? null;
  }, [catalogs, selectedCity]);

  const placeList = useMemo(() => {
    if (!catalogs.length) return [];
    const keyword = searchKeyword.trim().toLowerCase();
    return catalogs
      .flatMap((catalog) =>
        catalog.places.map((place) => ({
          ...place,
          city: catalog.city,
          cityLabel: catalog.city_label?.trim() || displayCity(catalog),
        })),
      )
      .filter((place) => {
        const searchTarget = [place.name, place.id, place.area, place.summary, place.cityLabel, ...place.category]
          .join(" ")
          .toLowerCase();
        if (keyword && !searchTarget.includes(keyword)) {
          return false;
        }

        if (selectedView === "active") return (place.is_active ?? true) === true;
        if (selectedView === "inactive") return (place.is_active ?? true) === false;
        if (selectedView === "activity") {
          return place.category.some((category) => ["activity", "theme_park", "local_experience"].includes(category));
        }
        if (selectedView === "core") return (place.mvp_tier ?? "standard") === "core";
        return true;
      })
      .sort((left, right) => {
        const activeGap = Number(right.is_active ?? true) - Number(left.is_active ?? true);
        if (activeGap !== 0) return activeGap;
        return right.priority - left.priority;
      });
  }, [catalogs, searchKeyword, selectedView]);

  function updateParam(key: string, value: string) {
    const nextParams = new URLSearchParams(searchParams);
    const currentValue = searchParams.get(key) ?? "";

    if (!value || currentValue === value) {
      nextParams.delete(key);
      if (key === "continent") {
        nextParams.delete("country");
        nextParams.delete("city");
      }
      if (key === "country") {
        nextParams.delete("city");
      }
    } else {
      nextParams.set(key, value);
      if (key === "continent") {
        nextParams.delete("country");
        nextParams.delete("city");
      }
      if (key === "country") {
        nextParams.delete("city");
      }
    }
    setSearchParams(nextParams);
  }

  async function toggleActive(placeId: string, nextActive: boolean, placeName: string) {
    const targetPlace = placeList.find((place) => place.id === placeId);
    if (!targetPlace) return;

    try {
      await apiClient.patch(`/admin/destinations/${targetPlace.city}/places/${placeId}/active`, {
        is_active: nextActive,
      });
      const responses = await Promise.all(
        catalogs.map((catalog) => apiClient.get<CityCatalog>(`/admin/destinations/${catalog.city}`)),
      );
      setCatalogs(responses.map((response) => response.data));
      setStatusText(`${placeName} 장소를 ${nextActive ? "활성" : "비활성"} 상태로 변경했습니다.`);
    } catch (error) {
      setStatusText(getApiErrorMessage(error, "장소 상태를 변경하지 못했습니다."));
    }
  }

  const selectedQuery = `?${new URLSearchParams(
    Object.fromEntries(
      Object.entries({
        continent: selectedContinent,
        country: selectedCountry,
        city: selectedCity,
        q: searchKeyword,
        view: selectedView,
      }).filter(([, value]) => value),
    ),
  ).toString()}`;

  return (
    <AppShell>
      <section className="admin-page">
        <div className="admin-header">
          <div>
            <p className="planner-kicker">데이터 관리</p>
            <h1 className="planner-title">여행지 및 장소 관리</h1>
            <p className="planner-description">
              지역별로 빠르게 찾고, 필요한 여행지나 장소를 바로 수정할 수 있습니다.
            </p>
          </div>
          <p className="admin-status">{statusText}</p>
        </div>

        <section className="admin-filter-shell">
          <label className="admin-search">
            <span>검색</span>
            <input
              placeholder="도시, 장소명, 지역, 카테고리로 검색"
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
                  {displayContinent(
                    filteredDestinations.find((destination) => destination.continent === continent) ?? {
                      continent,
                      continent_label: null,
                    },
                  )}
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
                  {displayCountry(
                    filteredDestinations.find(
                      (destination) => destination.continent === selectedContinent && destination.country === country,
                    ) ?? { country, country_label: null },
                  )}
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
                  {displayCity(destination)}
                </button>
              ))}
            </div>
          </div>
        </section>

        <div className="admin-summary-bar">
          <div className="admin-summary-card">
            <strong>{selectedCity && activeCatalog ? activeCatalog.city_label?.trim() || displayCity(activeCatalog) : "전체 도시"}</strong>
            <span>{placeList.length}개 장소</span>
          </div>
          <div className="admin-summary-card">
            <strong>활성 장소</strong>
            <span>{placeList.filter((place) => place.is_active ?? true).length}</span>
          </div>
          <div className="admin-summary-card">
            <strong>액티비티 중심 장소</strong>
            <span>
              {placeList.filter((place) =>
                place.category.some((category) => ["activity", "theme_park", "local_experience"].includes(category)),
              ).length}
            </span>
          </div>
        </div>

        <section className="admin-panel admin-list-panel">
          <div className="admin-panel-head">
            <h2>장소 목록</h2>
            <div className="admin-editor-actions">
              <Link className="admin-secondary-link" to="/admin/data/new-destination">
                여행지 추가
              </Link>
              <Link
                className={selectedCity ? "admin-primary-link" : "admin-primary-link disabled"}
                to={selectedCity ? `/admin/data/${selectedCity}/new${selectedQuery}` : "/admin/data"}
              >
                {selectedCity
                  ? `${displayCity(
                      cityOptions.find((destination) => destination.city === selectedCity) ?? {
                        city: selectedCity,
                        city_label: null,
                      },
                    )}에 장소 추가`
                  : "먼저 도시를 선택해주세요"}
              </Link>
            </div>
          </div>

          <div className="admin-sub-filter-row">
            {[
              { value: "all", label: "전체" },
              { value: "active", label: "활성만" },
              { value: "inactive", label: "비활성만" },
              { value: "activity", label: "액티비티만" },
              { value: "core", label: "대표 장소만" },
            ].map((filter) => (
              <button
                key={filter.value}
                className={selectedView === filter.value ? "admin-chip active" : "admin-chip"}
                onClick={() => updateParam("view", filter.value)}
                type="button"
              >
                {filter.label}
              </button>
            ))}
          </div>

          <div className="admin-place-list admin-place-list-scroll compact">
            {placeList.length ? (
              placeList.map((place) => (
                <article key={place.id} className="admin-place-card">
                  <div className="admin-place-main">
                    <strong>{place.name}</strong>
                    <span className="admin-place-city">{place.cityLabel}</span>
                    <span>{place.category.map(labelCategory).join(", ")}</span>
                    <span>
                      우선순위 {place.priority} - {labelVisibilityLevel(place.mvp_tier ?? "standard")} -{" "}
                      {(place.is_active ?? true) ? "활성" : "비활성"}
                    </span>
                  </div>
                  <div className="admin-card-actions">
                    <Link className="admin-secondary-link" to={`/admin/data/${place.city}/${place.id}/edit${selectedQuery}`}>
                      수정
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
              ))
            ) : (
              <article className="admin-empty-card">
                <strong>현재 조건에 맞는 장소가 없습니다.</strong>
                <p>검색어나 필터를 바꾸거나, 선택한 도시에 새 장소를 추가해보세요.</p>
              </article>
            )}
          </div>
        </section>
      </section>
    </AppShell>
  );
}
