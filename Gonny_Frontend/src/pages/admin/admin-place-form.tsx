import { useState } from "react";
import {
  applySlotBiasPreset,
  budgetOptions,
  categoryOptions,
  companionOptions,
  durationPresetOptions,
  labelBudgetBand,
  mobilityOptions,
  paceOptions,
  PlaceEditorState,
  priorityPresetOptions,
  slotBiasPresetOptions,
  slotWeightOptions,
  timeOptions,
  toggleSelection,
  visibilityLevelOptions,
} from "./admin-data-shared";

type Props = {
  editor: PlaceEditorState;
  isCreating: boolean;
  errors: string[];
  isDirty: boolean;
  isSaving?: boolean;
  onChange: <K extends keyof PlaceEditorState>(key: K, value: PlaceEditorState[K]) => void;
  onAutoFillId: () => void;
  onSave: () => void;
};

function RequiredLabel({ children }: { children: string }) {
  return (
    <span className="admin-label-row">
      <span>{children}</span>
      <strong className="admin-required-badge">필수</strong>
    </span>
  );
}

export function AdminPlaceForm({
  editor,
  isCreating,
  errors,
  isDirty,
  isSaving = false,
  onChange,
  onAutoFillId,
  onSave,
}: Props) {
  const [openSections, setOpenSections] = useState({
    basic: true,
    recommendation: true,
    notes: true,
    preview: true,
  });

  function toggleSection(key: keyof typeof openSections) {
    setOpenSections((current) => ({ ...current, [key]: !current[key] }));
  }

  function applyDuration(value: string) {
    onChange("duration_hours", value);
  }

  function applyPriority(value: string) {
    onChange("priority", value);
  }

  function applySlotPreset(preset: { morning: number; afternoon: number; evening: number }) {
    const nextEditor = applySlotBiasPreset(editor, preset);
    onChange("slot_bias_morning", nextEditor.slot_bias_morning);
    onChange("slot_bias_afternoon", nextEditor.slot_bias_afternoon);
    onChange("slot_bias_evening", nextEditor.slot_bias_evening);
  }

  function applySlotValue(key: "slot_bias_morning" | "slot_bias_afternoon" | "slot_bias_evening", value: string) {
    onChange(key, value);
  }

  return (
    <section className="admin-panel admin-editor-panel">
      <div className="admin-panel-head">
        <h2>{isCreating ? "장소 추가" : "장소 수정"}</h2>
        <div className="admin-editor-actions">
          <span className={isDirty ? "admin-save-hint dirty" : "admin-save-hint"}>
            {isDirty ? "저장하지 않은 변경사항이 있습니다." : "모든 변경사항이 저장되었습니다."}
          </span>
          <button
            className="admin-primary-button"
            disabled={errors.length > 0 || !isDirty || isSaving}
            onClick={onSave}
            type="button"
          >
            저장
          </button>
        </div>
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
          <button className="admin-section-toggle" onClick={() => toggleSection("basic")} type="button">
            <strong>기본 정보</strong>
            <span>{openSections.basic ? "접기" : "펼치기"}</span>
          </button>
          {openSections.basic ? (
            <div className="admin-section-body">
              <div className="admin-form-grid">
                <label>
                  <RequiredLabel>내부 식별용 영문 이름</RequiredLabel>
                  <div className="admin-inline-field">
                    <input
                      placeholder="예: seoul-forest"
                      value={editor.id}
                      onChange={(event) => onChange("id", event.target.value)}
                    />
                    <button className="admin-secondary-button" onClick={onAutoFillId} type="button">
                      자동 생성
                    </button>
                  </div>
                  <small>내부 매칭과 파일 저장에 사용하는 영문 키입니다.</small>
                </label>
                <label>
                  <RequiredLabel>장소 이름</RequiredLabel>
                  <input
                    placeholder="예: 서울숲"
                    value={editor.name}
                    onChange={(event) => onChange("name", event.target.value)}
                  />
                  <small>사용자 화면에 보여지는 이름입니다.</small>
                </label>
              </div>

              <div className="admin-form-grid">
                <label>
                  <RequiredLabel>지역 이름</RequiredLabel>
                  <input
                    placeholder="예: 성수"
                    value={editor.area}
                    onChange={(event) => onChange("area", event.target.value)}
                  />
                  <small>장소를 묶어 보여줄 지역 또는 동네 이름입니다.</small>
                </label>
                <label>
                  <RequiredLabel>예상 소요 시간</RequiredLabel>
                  <input
                    value={editor.duration_hours}
                    onChange={(event) => onChange("duration_hours", event.target.value)}
                  />
                  <small>시간 단위의 정수로 입력해주세요. 아래 버튼으로 빠르게 채울 수 있습니다.</small>
                  <div className="admin-chip-row selection">
                    {durationPresetOptions.map((preset) => (
                      <button
                        key={preset.value}
                        className={editor.duration_hours === preset.value ? "admin-chip active" : "admin-chip"}
                        onClick={() => applyDuration(preset.value)}
                        type="button"
                      >
                        {preset.label}
                      </button>
                    ))}
                  </div>
                </label>
              </div>

              <small>원하는 값이 없으면 입력칸에 직접 숫자를 적을 수 있습니다.</small>

              <label>
                  <RequiredLabel>짧은 소개</RequiredLabel>
                <textarea
                  rows={3}
                  value={editor.summary}
                  onChange={(event) => onChange("summary", event.target.value)}
                />
                <small>왜 이 장소를 일정에 넣을 만한지 1~2문장으로 적어주세요.</small>
              </label>

              <div className="admin-form-grid">
                <label>
                  <span>공식 링크</span>
                  <input
                    placeholder="선택 입력: 웹사이트 또는 지도 링크"
                    value={editor.official_url}
                    onChange={(event) => onChange("official_url", event.target.value)}
                  />
                </label>
                <label>
                  <span>예약 안내</span>
                  <input
                    placeholder="예: 주말에는 예약 권장"
                    value={editor.booking_hint}
                    onChange={(event) => onChange("booking_hint", event.target.value)}
                  />
                </label>
              </div>
            </div>
          ) : null}
        </section>

        <section className="admin-section-shell">
          <button className="admin-section-toggle" onClick={() => toggleSection("recommendation")} type="button">
            <strong>추천 설정</strong>
            <span>{openSections.recommendation ? "접기" : "펼치기"}</span>
          </button>
          {openSections.recommendation ? (
            <div className="admin-section-body">
              <label>
                <RequiredLabel>카테고리</RequiredLabel>
                <div className="admin-chip-row selection">
                  {categoryOptions.map((option) => (
                    <button
                      key={option.value}
                      className={editor.category.includes(option.value) ? "admin-chip active" : "admin-chip"}
                      onClick={() => onChange("category", toggleSelection(editor.category, option.value))}
                      type="button"
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </label>

              <label>
                <RequiredLabel>추천 시간대</RequiredLabel>
                <div className="admin-chip-row selection">
                  {timeOptions.map((option) => (
                    <button
                      key={option.value}
                      className={editor.time_fit.includes(option.value) ? "admin-chip active" : "admin-chip"}
                      onClick={() => onChange("time_fit", toggleSelection(editor.time_fit, option.value))}
                      type="button"
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </label>

              <label>
                <RequiredLabel>예산 구간</RequiredLabel>
                <div className="admin-chip-row selection">
                  {budgetOptions.map((option) => (
                    <button
                      key={option.value}
                      className={editor.budget_level.includes(option.value) ? "admin-chip active" : "admin-chip"}
                      onClick={() => onChange("budget_level", toggleSelection(editor.budget_level, option.value))}
                      type="button"
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </label>

              <label>
                <RequiredLabel>어울리는 여행 유형</RequiredLabel>
                <div className="admin-chip-row selection">
                  {companionOptions.map((option) => (
                    <button
                      key={option.value}
                      className={editor.suitable_for.includes(option.value) ? "admin-chip active" : "admin-chip"}
                      onClick={() => onChange("suitable_for", toggleSelection(editor.suitable_for, option.value))}
                      type="button"
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </label>

              <label>
                <span>일정 템포</span>
                <div className="admin-chip-row selection">
                  {paceOptions.map((option) => (
                    <button
                      key={option.value}
                      className={editor.pace.includes(option.value) ? "admin-chip active" : "admin-chip"}
                      onClick={() => onChange("pace", toggleSelection(editor.pace, option.value))}
                      type="button"
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </label>

              <label>
                <span>이동 방식</span>
                <div className="admin-chip-row selection">
                  {mobilityOptions.map((option) => (
                    <button
                      key={option.value}
                      className={editor.mobility.includes(option.value) ? "admin-chip active" : "admin-chip"}
                      onClick={() => onChange("mobility", toggleSelection(editor.mobility, option.value))}
                      type="button"
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </label>

              <div className="admin-form-grid">
                <label>
                  <RequiredLabel>추천 우선순위</RequiredLabel>
                  <input value={editor.priority} onChange={(event) => onChange("priority", event.target.value)} />
                  <small>값이 높을수록 일정에 더 자주 추천됩니다.</small>
                </label>
                <label>
                  <span>노출 수준</span>
                  <select value={editor.mvp_tier} onChange={(event) => onChange("mvp_tier", event.target.value)}>
                    {visibilityLevelOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <small>
                    {visibilityLevelOptions.find((option) => option.value === editor.mvp_tier)?.description ?? ""}
                  </small>
                </label>
              </div>

              <div className="admin-chip-row selection">
                {priorityPresetOptions.map((preset) => (
                  <button
                    key={preset.value}
                    className={editor.priority === preset.value ? "admin-chip active" : "admin-chip"}
                    onClick={() => applyPriority(preset.value)}
                    type="button"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>

              <div className="admin-inline-checks">
                <label className="admin-checkbox">
                  <input
                    checked={editor.is_active}
                    onChange={(event) => onChange("is_active", event.target.checked)}
                    type="checkbox"
                  />
                  <span>일정 생성에 사용</span>
                </label>
                <label className="admin-checkbox">
                  <input
                    checked={editor.full_day_recommended}
                    onChange={(event) => onChange("full_day_recommended", event.target.checked)}
                    type="checkbox"
                  />
                  <span>하루 코스로 활용 가능</span>
                </label>
              </div>

              <div className="admin-form-grid">
                <label>
                  <span>분위기 키워드</span>
                  <input
                    placeholder="예: 잔잔함, 풍경, 트렌디"
                    value={editor.mood_keywords}
                    onChange={(event) => onChange("mood_keywords", event.target.value)}
                  />
                </label>
                <label>
                  <span>강조 태그</span>
                  <input
                    placeholder="예: 강변, 데이트, 노을"
                    value={editor.highlight_tags}
                    onChange={(event) => onChange("highlight_tags", event.target.value)}
                  />
                </label>
              </div>

              <label>
                <span>추천 문구 메모</span>
                <input
                  placeholder="선택 입력: 설명 문구에 참고할 짧은 메모"
                  value={editor.note_templates}
                  onChange={(event) => onChange("note_templates", event.target.value)}
                />
              </label>
            </div>
          ) : null}
        </section>

        <section className="admin-section-shell">
          <button className="admin-section-toggle" onClick={() => toggleSection("notes")} type="button">
            <strong>시간대 및 메모 힌트</strong>
            <span>{openSections.notes ? "접기" : "펼치기"}</span>
          </button>
          {openSections.notes ? (
            <div className="admin-section-body">
              <div className="admin-form-section">
                <div className="admin-section-title">
                  <strong>시간대 가중치</strong>
                  <span>특정 시간대에 더 잘 맞는 장소라면 아래 버튼으로 바로 적용할 수 있습니다.</span>
                </div>

                <div className="admin-chip-row selection">
                  {slotBiasPresetOptions.map((preset) => (
                    <button
                      key={preset.label}
                      className="admin-chip"
                      onClick={() => applySlotPreset(preset)}
                      type="button"
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>

                <div className="admin-form-grid">
                  <label>
                    <span>오전 가중치</span>
                    <input
                      value={editor.slot_bias_morning}
                      onChange={(event) => onChange("slot_bias_morning", event.target.value)}
                    />
                    <div className="admin-chip-row selection">
                      {slotWeightOptions.map((option) => (
                        <button
                          key={`morning-${option.value}`}
                          className={editor.slot_bias_morning === option.value ? "admin-chip active" : "admin-chip"}
                          onClick={() => applySlotValue("slot_bias_morning", option.value)}
                          type="button"
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                  </label>
                  <label>
                    <span>오후 가중치</span>
                    <input
                      value={editor.slot_bias_afternoon}
                      onChange={(event) => onChange("slot_bias_afternoon", event.target.value)}
                    />
                    <div className="admin-chip-row selection">
                      {slotWeightOptions.map((option) => (
                        <button
                          key={`afternoon-${option.value}`}
                          className={editor.slot_bias_afternoon === option.value ? "admin-chip active" : "admin-chip"}
                          onClick={() => applySlotValue("slot_bias_afternoon", option.value)}
                          type="button"
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                  </label>
                  <label>
                    <span>저녁 가중치</span>
                    <input
                      value={editor.slot_bias_evening}
                      onChange={(event) => onChange("slot_bias_evening", event.target.value)}
                    />
                    <div className="admin-chip-row selection">
                      {slotWeightOptions.map((option) => (
                        <button
                          key={`evening-${option.value}`}
                          className={editor.slot_bias_evening === option.value ? "admin-chip active" : "admin-chip"}
                          onClick={() => applySlotValue("slot_bias_evening", option.value)}
                          type="button"
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                  </label>
                </div>
              </div>

              <div className="admin-form-section">
                <div className="admin-section-title">
                  <strong>하루 코스 메모</strong>
                  <span>오래 머무를 수 있는 장소라면 오전, 오후, 저녁 메모 예시를 적어둘 수 있습니다.</span>
                </div>
                <div className="admin-form-grid">
                  <label>
                    <span>오전 메모 예시</span>
                    <textarea
                      rows={5}
                      placeholder="한 줄에 하나씩 입력"
                      value={editor.full_day_notes_morning}
                      onChange={(event) => onChange("full_day_notes_morning", event.target.value)}
                    />
                  </label>
                  <label>
                    <span>오후 메모 예시</span>
                    <textarea
                      rows={5}
                      placeholder="한 줄에 하나씩 입력"
                      value={editor.full_day_notes_afternoon}
                      onChange={(event) => onChange("full_day_notes_afternoon", event.target.value)}
                    />
                  </label>
                  <label>
                    <span>저녁 메모 예시</span>
                    <textarea
                      rows={5}
                      placeholder="한 줄에 하나씩 입력"
                      value={editor.full_day_notes_evening}
                      onChange={(event) => onChange("full_day_notes_evening", event.target.value)}
                    />
                  </label>
                </div>
              </div>
            </div>
          ) : null}
        </section>

        <section className="admin-section-shell">
          <button className="admin-section-toggle" onClick={() => toggleSection("preview")} type="button">
            <strong>미리보기</strong>
            <span>{openSections.preview ? "접기" : "펼치기"}</span>
          </button>
          {openSections.preview ? (
            <div className="admin-preview-card">
              <p className="admin-preview-title">{editor.name || "장소 이름을 입력하면 카드 미리보기에 표시됩니다."}</p>
              <p className="admin-preview-summary">{editor.summary || "짧은 소개를 입력하면 사용자에게 보일 설명을 미리 확인할 수 있습니다."}</p>
              <div className="admin-chip-row">
                {editor.category.map((value) => (
                  <span key={value} className="admin-preview-chip">
                    {categoryOptions.find((option) => option.value === value)?.label ?? value}
                  </span>
                ))}
              </div>
              <div className="admin-preview-lines">
                <p>추천 예산: {editor.budget_level.map(labelBudgetBand).join(", ") || "아직 없음"}</p>
                <p>오전 메모: {editor.full_day_notes_morning.split("\n").filter(Boolean)[0] || "아직 없음"}</p>
                <p>오후 메모: {editor.full_day_notes_afternoon.split("\n").filter(Boolean)[0] || "아직 없음"}</p>
                <p>저녁 메모: {editor.full_day_notes_evening.split("\n").filter(Boolean)[0] || "아직 없음"}</p>
              </div>
              <div className="admin-preview-meta">
                <span>우선순위 {editor.priority || "미입력"}</span>
                <span>
                  {visibilityLevelOptions.find((option) => option.value === editor.mvp_tier)?.label ?? editor.mvp_tier}
                </span>
                <span>{editor.is_active ? "활성" : "비활성"}</span>
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </section>
  );
}
