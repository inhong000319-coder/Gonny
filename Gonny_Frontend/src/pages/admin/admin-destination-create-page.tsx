import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AppShell } from "../../app/layouts/app-shell";
import { apiClient } from "../../shared/api/client";
import {
  defaultDayPresetOptions,
  DESTINATION_DEFAULT_DAYS_MAX,
  DESTINATION_DEFAULT_DAYS_MIN,
  DestinationEditorState,
  DestinationSummary,
  emptyDestinationEditorState,
  getApiErrorMessage,
  parseCommaList,
  toPositiveInteger,
  validateDestinationEditor,
} from "./admin-data-shared";

export function AdminDestinationCreatePage() {
  const navigate = useNavigate();
  const [editor, setEditor] = useState<DestinationEditorState>(emptyDestinationEditorState());
  const [existingCities, setExistingCities] = useState<string[]>([]);
  const [statusText, setStatusText] = useState(
    "먼저 여행지를 만들면 그 아래에 장소를 바로 추가할 수 있습니다.",
  );
  const [loaded, setLoaded] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    async function loadDestinations() {
      try {
        const response = await apiClient.get<{ destinations: DestinationSummary[] }>("/admin/destinations");
        setExistingCities((response.data.destinations ?? []).map((item) => item.city.toLowerCase()));
      } catch (error) {
        setStatusText(getApiErrorMessage(error, "여행지 목록을 불러오지 못했습니다."));
      } finally {
        setLoaded(true);
      }
    }

    void loadDestinations();
  }, []);

  const errors = useMemo(() => validateDestinationEditor(editor, existingCities), [editor, existingCities]);

  function updateEditor<K extends keyof DestinationEditorState>(key: K, value: DestinationEditorState[K]) {
    setEditor((current) => ({ ...current, [key]: value }));
  }

  async function saveDestination() {
    if (errors.length) {
      setStatusText(errors[0]);
      return;
    }

    const defaultDays = toPositiveInteger(editor.default_days, 0);
    if (defaultDays < DESTINATION_DEFAULT_DAYS_MIN || defaultDays > DESTINATION_DEFAULT_DAYS_MAX) {
      setStatusText(
        `기본 여행 일수는 ${DESTINATION_DEFAULT_DAYS_MIN}일부터 ${DESTINATION_DEFAULT_DAYS_MAX}일 사이의 정수여야 합니다.`,
      );
      return;
    }

    const payload = {
      continent: editor.continent.trim().toLowerCase(),
      continent_label: editor.continent_label.trim(),
      country: editor.country.trim().toLowerCase(),
      country_label: editor.country_label.trim(),
      city: editor.city.trim().toLowerCase(),
      city_label: editor.city_label.trim(),
      aliases: parseCommaList(editor.aliases),
      default_days: defaultDays,
    };

    setIsSaving(true);
    setStatusText("여행지를 저장하는 중입니다...");

    try {
      await apiClient.post("/admin/destinations", payload);
      navigate(
        `/admin/data?continent=${payload.continent}&country=${payload.country}&city=${payload.city}`,
        { replace: true },
      );
    } catch (error) {
      setStatusText(getApiErrorMessage(error, "여행지를 생성하지 못했습니다."));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <AppShell>
      <section className="admin-page">
        <div className="admin-header">
          <div>
            <p className="planner-kicker">데이터 관리</p>
            <h1 className="planner-title">여행지 추가</h1>
            <p className="planner-description">
              영문 이름은 내부 매칭용으로 사용되고, 화면 이름은 실제 화면에 보이는 이름입니다.
            </p>
          </div>
          <p className="admin-status">{loaded ? statusText : "현재 여행지 목록을 불러오는 중입니다..."}</p>
        </div>

        <div className="admin-breadcrumb">
          <Link className="admin-secondary-link" to="/admin/data">
            목록으로 돌아가기
          </Link>
        </div>

        <section className="admin-panel admin-editor-panel">
          <div className="admin-panel-head">
            <h2>여행지 정보</h2>
            <button
              className="admin-primary-button"
              disabled={errors.length > 0 || isSaving}
              onClick={() => void saveDestination()}
              type="button"
            >
              저장
            </button>
          </div>

          <div className="admin-form">
            {errors.length ? (
              <section className="admin-alert-card">
                <strong>아래 항목을 먼저 확인해주세요.</strong>
                <ul>
                  {errors.map((error) => (
                    <li key={error}>{error}</li>
                  ))}
                </ul>
              </section>
            ) : null}

            <section className="admin-section-shell">
              <div className="admin-section-body">
                <div className="admin-form-grid">
                  <label>
                    <span className="admin-label-row">
                      <span>대륙 영문 이름</span>
                      <strong className="admin-required-badge">필수</strong>
                    </span>
                    <input
                      placeholder="예: asia"
                      value={editor.continent}
                      onChange={(event) => updateEditor("continent", event.target.value)}
                    />
                    <small>내부 매칭용 값입니다. 화면에 직접 보이는 이름은 아닙니다.</small>
                  </label>
                  <label>
                    <span className="admin-label-row">
                      <span>대륙 표시 이름</span>
                      <strong className="admin-required-badge">필수</strong>
                    </span>
                    <input
                      placeholder="예: 아시아"
                      value={editor.continent_label}
                      onChange={(event) => updateEditor("continent_label", event.target.value)}
                    />
                  </label>
                </div>

                <div className="admin-form-grid">
                  <label>
                    <span className="admin-label-row">
                      <span>국가 영문 이름</span>
                      <strong className="admin-required-badge">필수</strong>
                    </span>
                    <input
                      placeholder="예: japan"
                      value={editor.country}
                      onChange={(event) => updateEditor("country", event.target.value)}
                    />
                  </label>
                  <label>
                    <span className="admin-label-row">
                      <span>국가 표시 이름</span>
                      <strong className="admin-required-badge">필수</strong>
                    </span>
                    <input
                      placeholder="예: 일본"
                      value={editor.country_label}
                      onChange={(event) => updateEditor("country_label", event.target.value)}
                    />
                  </label>
                </div>

                <div className="admin-form-grid">
                  <label>
                    <span className="admin-label-row">
                      <span>도시 영문 이름</span>
                      <strong className="admin-required-badge">필수</strong>
                    </span>
                    <input
                      placeholder="예: tokyo"
                      value={editor.city}
                      onChange={(event) => updateEditor("city", event.target.value)}
                    />
                    <small>JSON 파일명과 내부 매칭 키로 사용됩니다.</small>
                  </label>
                  <label>
                    <span className="admin-label-row">
                      <span>도시 표시 이름</span>
                      <strong className="admin-required-badge">필수</strong>
                    </span>
                    <input
                      placeholder="예: 도쿄"
                      value={editor.city_label}
                      onChange={(event) => updateEditor("city_label", event.target.value)}
                    />
                  </label>
                </div>

                <div className="admin-form-grid">
                  <label>
                    <span>검색용 별칭</span>
                    <input
                      placeholder="예: tokyo, tokio, japan-capital"
                      value={editor.aliases}
                      onChange={(event) => updateEditor("aliases", event.target.value)}
                    />
                    <small>쉼표로 구분해서 입력하면 이 여행지로 함께 인식됩니다.</small>
                  </label>
                  <label>
                    <span className="admin-label-row">
                      <span>기본 여행 일수</span>
                      <strong className="admin-required-badge">필수</strong>
                    </span>
                    <input
                      placeholder="예: 3"
                      value={editor.default_days}
                      onChange={(event) => updateEditor("default_days", event.target.value)}
                    />
                    <small>아직 여행 기간이 정해지지 않았을 때 기본 추천값으로 사용됩니다. 아래 토글을 누르거나 직접 입력할 수 있습니다.</small>
                    <div className="admin-chip-row selection">
                      {defaultDayPresetOptions.map((preset) => (
                        <button
                          key={preset.value}
                          className={editor.default_days === preset.value ? "admin-chip active" : "admin-chip"}
                          onClick={() => updateEditor("default_days", preset.value)}
                          type="button"
                        >
                          {preset.label}
                        </button>
                      ))}
                    </div>
                  </label>
                </div>
              </div>
            </section>
          </div>
        </section>
      </section>
    </AppShell>
  );
}
