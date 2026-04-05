import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { AppShell } from "../../app/layouts/app-shell";
import { apiClient } from "../../shared/api/client";
import { AdminPlaceForm } from "./admin-place-form";
import {
  CityCatalog,
  emptyEditorState,
  labelCity,
  PlaceEditorState,
  PlaceData,
  suggestPlaceId,
  toEditorState,
  toPayload,
  validatePlaceEditor,
} from "./admin-data-shared";

export function AdminPlaceEditPage() {
  const navigate = useNavigate();
  const { city = "", placeId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const [catalog, setCatalog] = useState<CityCatalog | null>(null);
  const [editor, setEditor] = useState<PlaceEditorState | null>(null);
  const [statusText, setStatusText] = useState("입력한 내용은 저장 버튼을 누르면 바로 데이터에 반영돼요.");

  const isCreating = placeId === "new";
  const backUrl = `/admin/data${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;

  useEffect(() => {
    async function loadCatalog() {
      if (!city) return;
      const response = await apiClient.get<CityCatalog>(`/admin/destinations/${city}`);
      setCatalog(response.data);

      if (isCreating) {
        setEditor(emptyEditorState(response.data.places[0]?.area ?? ""));
        return;
      }

      const targetPlace = response.data.places.find((place) => place.id === placeId);
      if (targetPlace) {
        setEditor(toEditorState(targetPlace));
      }
    }

    void loadCatalog();
  }, [city, isCreating, placeId]);

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
    setStatusText("장소 아이디를 자동으로 넣어드렸어요.");
  }

  async function savePlace() {
    if (!editor || !city) return;

    const errors = validatePlaceEditor(editor, catalog, isCreating, isCreating ? "" : placeId);
    if (errors.length) {
      setStatusText(errors[0]);
      return;
    }

    const payload: PlaceData = toPayload(editor);

    if (isCreating) {
      await apiClient.post(`/admin/destinations/${city}/places`, payload);
      navigate(`/admin/data/${city}/${payload.id}/edit${searchParams.toString() ? `?${searchParams.toString()}` : ""}`, {
        replace: true,
      });
      setStatusText(`${payload.name} 장소를 새로 추가했어요.`);
      return;
    }

    await apiClient.put(`/admin/destinations/${city}/places/${placeId}`, payload);
    setStatusText(`${payload.name} 내용을 저장했어요.`);
  }

  return (
    <AppShell>
      <section className="admin-page">
        <div className="admin-header">
          <div>
            <p className="planner-kicker">데이터 운영</p>
            <h1 className="planner-title">{isCreating ? "새 장소 추가" : `${catalog ? labelCity(catalog.city) : ""} 장소 수정`}</h1>
            <p className="planner-description">
              길게 펼쳐진 목록 대신, 수정이 필요한 장소만 따로 열어서 집중해서 편집할 수 있는 화면이에요.
            </p>
          </div>
          <p className="admin-status">{statusText}</p>
        </div>

        <div className="admin-breadcrumb">
          <Link className="admin-secondary-link" to={backUrl}>
            목록으로 돌아가기
          </Link>
        </div>

        {isCreating ? (
          <section className="admin-tip-card">
            <strong>{catalog ? `${labelCity(catalog.city)}에 새 장소를 추가하고 있어요.` : "새 장소를 추가하고 있어요."}</strong>
            <p>먼저 장소명과 카테고리를 고르고, 그 다음 추천 시간대와 소개 문장을 넣으면 훨씬 수월하게 입력할 수 있어요.</p>
          </section>
        ) : null}

        {editor ? (
          <AdminPlaceForm
            editor={editor}
            errors={validatePlaceEditor(editor, catalog, isCreating, isCreating ? "" : placeId)}
            isCreating={isCreating}
            onChange={updateEditor}
            onAutoFillId={autoFillId}
            onSave={() => void savePlace()}
          />
        ) : null}
      </section>
    </AppShell>
  );
}
