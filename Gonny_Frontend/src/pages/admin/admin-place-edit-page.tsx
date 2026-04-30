import { MouseEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { AppShell } from "../../app/layouts/app-shell";
import { apiClient } from "../../shared/api/client";
import { AdminPlaceForm } from "./admin-place-form";
import {
  CityCatalog,
  emptyEditorState,
  getApiErrorMessage,
  labelCity,
  PLACE_DURATION_MAX_HOURS,
  PLACE_DURATION_MIN_HOURS,
  PlaceEditorState,
  PlaceData,
  PLACE_PRIORITY_MAX,
  PLACE_PRIORITY_MIN,
  suggestPlaceId,
  toEditorState,
  toPayload,
  toPositiveInteger,
  validatePlaceEditor,
} from "./admin-data-shared";

export function AdminPlaceEditPage() {
  const navigate = useNavigate();
  const { city = "", placeId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const [catalog, setCatalog] = useState<CityCatalog | null>(null);
  const [editor, setEditor] = useState<PlaceEditorState | null>(null);
  const [savedSnapshot, setSavedSnapshot] = useState("");
  const [statusText, setStatusText] = useState("항목을 입력하고 저장하면 여행지 장소 목록에 반영됩니다.");
  const [isSaving, setIsSaving] = useState(false);

  const isCreating = !placeId;
  const backUrl = `/admin/data${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;

  useEffect(() => {
    async function loadCatalog() {
      if (!city) return;

      try {
        const response = await apiClient.get<CityCatalog>(`/admin/destinations/${city}`);
        setCatalog(response.data);

        if (isCreating) {
          const nextEditor = emptyEditorState(response.data.places[0]?.area ?? "");
          setEditor(nextEditor);
          setSavedSnapshot(JSON.stringify(nextEditor));
          return;
        }

        const targetPlace = response.data.places.find((place) => place.id === placeId);
        if (!targetPlace) {
          setStatusText("해당 장소를 찾을 수 없습니다.");
          return;
        }

        const nextEditor = toEditorState(targetPlace);
        setEditor(nextEditor);
        setSavedSnapshot(JSON.stringify(nextEditor));
      } catch (error) {
        setStatusText(getApiErrorMessage(error, "여행지 데이터를 불러오지 못했습니다."));
      }
    }

    void loadCatalog();
  }, [city, isCreating, placeId]);

  useEffect(() => {
    function handleBeforeUnload(event: BeforeUnloadEvent) {
      if (!editor) return;
      if (JSON.stringify(editor) === savedSnapshot) return;
      event.preventDefault();
      event.returnValue = "";
    }

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [editor, savedSnapshot]);

  const isDirty = editor ? JSON.stringify(editor) !== savedSnapshot : false;
  const errors = useMemo(
    () => (editor ? validatePlaceEditor(editor, catalog, isCreating, isCreating ? "" : placeId) : []),
    [catalog, editor, isCreating, placeId],
  );

  function updateEditor<K extends keyof PlaceEditorState>(key: K, value: PlaceEditorState[K]) {
    if (!editor) return;
    setEditor({ ...editor, [key]: value });
  }

  function autoFillId() {
    if (!editor || !city) return;
    const nextId = suggestPlaceId(
      city,
      editor.name,
      (catalog?.places ?? []).map((place) => place.id.toLowerCase()),
    );
    setEditor({ ...editor, id: nextId });
    setStatusText("현재 도시와 장소 이름을 기준으로 내부 식별용 영문 이름을 자동 생성했습니다.");
  }

  async function savePlace() {
    if (!editor || !city || isSaving) return;

    if (errors.length) {
      setStatusText(errors[0]);
      return;
    }

    const payload: PlaceData = toPayload(editor);
    const priority = toPositiveInteger(editor.priority, 0);
    const durationHours = toPositiveInteger(editor.duration_hours, 0);

    if (
      priority < PLACE_PRIORITY_MIN ||
      priority > PLACE_PRIORITY_MAX ||
      durationHours < PLACE_DURATION_MIN_HOURS ||
      durationHours > PLACE_DURATION_MAX_HOURS
    ) {
      setStatusText(
        `추천 우선순위는 ${PLACE_PRIORITY_MIN}-${PLACE_PRIORITY_MAX}, 예상 소요 시간은 ${PLACE_DURATION_MIN_HOURS}-${PLACE_DURATION_MAX_HOURS}시간 사이여야 합니다.`,
      );
      return;
    }

    setIsSaving(true);
    setStatusText("변경사항을 저장하는 중입니다...");

    try {
      if (isCreating) {
        const response = await apiClient.post<CityCatalog>(`/admin/destinations/${city}/places`, payload);
        const savedPlace = response.data.places.find((place) => place.id === payload.id) ?? payload;
        const nextEditor = toEditorState(savedPlace);
        setEditor(nextEditor);
        setSavedSnapshot(JSON.stringify(nextEditor));
        setStatusText(`${payload.name} 장소를 추가했습니다.`);
        navigate(`/admin/data/${city}/${payload.id}/edit${searchParams.toString() ? `?${searchParams.toString()}` : ""}`, {
          replace: true,
        });
        return;
      }

      const response = await apiClient.put<CityCatalog>(`/admin/destinations/${city}/places/${placeId}`, payload);
      const savedPlace = response.data.places.find((place) => place.id === payload.id) ?? payload;
      const nextEditor = toEditorState(savedPlace);
      setEditor(nextEditor);
      setSavedSnapshot(JSON.stringify(nextEditor));
      setStatusText(`${payload.name} 장소를 수정했습니다.`);
    } catch (error) {
      setStatusText(getApiErrorMessage(error, "장소를 저장하지 못했습니다."));
    } finally {
      setIsSaving(false);
    }
  }

  function handleBackClick(event: MouseEvent<HTMLAnchorElement>) {
    if (!isDirty) return;
    const shouldLeave = window.confirm("저장하지 않은 변경사항이 있습니다. 정말 이 페이지를 나가시겠습니까?");
    if (!shouldLeave) {
      event.preventDefault();
    }
  }

  return (
    <AppShell>
      <section className="admin-page">
        <div className="admin-header">
          <div>
            <p className="planner-kicker">데이터 관리</p>
            <h1 className="planner-title">
              {isCreating ? "장소 추가" : `${catalog ? catalog.city_label?.trim() || labelCity(catalog.city) : ""} 장소 수정`}
            </h1>
            <p className="planner-description">
              한 번에 한 장소씩 정리하면 일정 생성에 쓰이는 데이터 품질을 안정적으로 유지할 수 있습니다.
            </p>
          </div>
          <p className="admin-status">{statusText}</p>
        </div>

        <div className="admin-breadcrumb">
          <Link className="admin-secondary-link" onClick={handleBackClick} to={backUrl}>
            목록으로 돌아가기
          </Link>
        </div>

        {isCreating ? (
          <section className="admin-tip-card">
            <strong>{catalog ? `${labelCity(catalog.city)} 장소 추가` : "장소 추가"}</strong>
            <p>장소 이름과 카테고리부터 입력한 뒤, 지역, 추천 시간대, 소개, 추천 설정을 채워보세요.</p>
          </section>
        ) : null}

        {editor ? (
          <AdminPlaceForm
            editor={editor}
            errors={errors}
            isDirty={isDirty && !isSaving}
            isCreating={isCreating}
            isSaving={isSaving}
            onChange={updateEditor}
            onAutoFillId={autoFillId}
            onSave={() => void savePlace()}
          />
        ) : null}
      </section>
    </AppShell>
  );
}
