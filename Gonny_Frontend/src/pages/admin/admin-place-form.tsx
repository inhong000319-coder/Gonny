import { useState } from "react";
import {
  budgetOptions,
  categoryOptions,
  companionOptions,
  mobilityOptions,
  paceOptions,
  PlaceEditorState,
  timeOptions,
  toggleSelection,
} from "./admin-data-shared";

type Props = {
  editor: PlaceEditorState;
  isCreating: boolean;
  errors: string[];
  onChange: <K extends keyof PlaceEditorState>(key: K, value: PlaceEditorState[K]) => void;
  onAutoFillId: () => void;
  onSave: () => void;
};

export function AdminPlaceForm({ editor, isCreating, errors, onChange, onAutoFillId, onSave }: Props) {
  const [openSections, setOpenSections] = useState({
    basic: true,
    recommendation: true,
    notes: true,
    preview: true,
  });

  function toggleSection(key: keyof typeof openSections) {
    setOpenSections((current) => ({ ...current, [key]: !current[key] }));
  }

  return (
    <section className="admin-panel admin-editor-panel">
      <div className="admin-panel-head">
        <h2>{isCreating ? "장소 추가" : "장소 수정"}</h2>
        <button className="admin-primary-button" onClick={onSave} type="button">
          저장
        </button>
      </div>

      <div className="admin-form">
        {errors.length ? (
          <section className="admin-alert-card">
            <strong>저장 전에 확인해 주세요.</strong>
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
                  <span>장소 아이디</span>
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
                  <small>영문 소문자, 숫자, 하이픈만 사용할 수 있어요.</small>
                </label>
                <label>
                  <span>장소명</span>
                  <input value={editor.name} onChange={(event) => onChange("name", event.target.value)} />
                  <small>실제로 서비스에 보이는 이름이에요.</small>
                </label>
              </div>

              <div className="admin-form-grid">
                <label>
                  <span>지역 코드</span>
                  <input value={editor.area} onChange={(event) => onChange("area", event.target.value)} />
                  <small>예: 종로, 해운대, 시부야처럼 묶음 기준이 되는 지역이에요.</small>
                </label>
                <label>
                  <span>예상 소요 시간</span>
                  <input value={editor.duration_hours} onChange={(event) => onChange("duration_hours", event.target.value)} />
                  <small>숫자로 입력해 주세요. 예: 2, 3.5</small>
                </label>
              </div>

              <label>
                <span>소개 문장</span>
                <textarea rows={3} value={editor.summary} onChange={(event) => onChange("summary", event.target.value)} />
              </label>

              <div className="admin-form-grid">
                <label>
                  <span>공식 링크</span>
                  <input value={editor.official_url} onChange={(event) => onChange("official_url", event.target.value)} />
                </label>
                <label>
                  <span>예약 힌트</span>
                  <input value={editor.booking_hint} onChange={(event) => onChange("booking_hint", event.target.value)} />
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
                <span>카테고리</span>
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
                <span>시간대</span>
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
                <span>예산대</span>
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
                <span>동행 유형</span>
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
                <span>여행 밀도</span>
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
                  <span>추천 우선순위</span>
                  <input value={editor.priority} onChange={(event) => onChange("priority", event.target.value)} />
                  <small>숫자가 높을수록 더 자주 추천돼요.</small>
                </label>
                <label>
                  <span>MVP 단계</span>
                  <select value={editor.mvp_tier} onChange={(event) => onChange("mvp_tier", event.target.value)}>
                    <option value="core">핵심</option>
                    <option value="standard">기본</option>
                    <option value="hidden">후순위 후보</option>
                  </select>
                </label>
              </div>

              <div className="admin-inline-checks">
                <label className="admin-checkbox">
                  <input
                    checked={editor.is_active}
                    onChange={(event) => onChange("is_active", event.target.checked)}
                    type="checkbox"
                  />
                  <span>활성 상태</span>
                </label>
                <label className="admin-checkbox">
                  <input
                    checked={editor.full_day_recommended}
                    onChange={(event) => onChange("full_day_recommended", event.target.checked)}
                    type="checkbox"
                  />
                  <span>하루형 액티비티</span>
                </label>
              </div>

              <div className="admin-form-grid">
                <label>
                  <span>분위기 키워드</span>
                  <input
                    placeholder="쉼표로 구분해서 입력해 주세요."
                    value={editor.mood_keywords}
                    onChange={(event) => onChange("mood_keywords", event.target.value)}
                  />
                </label>
                <label>
                  <span>강조 태그</span>
                  <input
                    placeholder="쉼표로 구분해서 입력해 주세요."
                    value={editor.highlight_tags}
                    onChange={(event) => onChange("highlight_tags", event.target.value)}
                  />
                </label>
              </div>

              <label>
                <span>노트 템플릿</span>
                <input
                  placeholder="쉼표로 구분해서 여러 개 입력할 수 있어요."
                  value={editor.note_templates}
                  onChange={(event) => onChange("note_templates", event.target.value)}
                />
              </label>
            </div>
          ) : null}
        </section>

        <section className="admin-section-shell">
          <button className="admin-section-toggle" onClick={() => toggleSection("notes")} type="button">
            <strong>운영 메모</strong>
            <span>{openSections.notes ? "접기" : "펼치기"}</span>
          </button>
          {openSections.notes ? (
            <div className="admin-section-body">
              <div className="admin-form-section">
                <div className="admin-section-title">
                  <strong>시간대 가중치</strong>
                  <span>숫자가 높을수록 해당 시간대에 더 잘 추천돼요.</span>
                </div>
                <div className="admin-form-grid">
                  <label>
                    <span>오전 가중치</span>
                    <input value={editor.slot_bias_morning} onChange={(event) => onChange("slot_bias_morning", event.target.value)} />
                  </label>
                  <label>
                    <span>오후 가중치</span>
                    <input value={editor.slot_bias_afternoon} onChange={(event) => onChange("slot_bias_afternoon", event.target.value)} />
                  </label>
                  <label>
                    <span>저녁 가중치</span>
                    <input value={editor.slot_bias_evening} onChange={(event) => onChange("slot_bias_evening", event.target.value)} />
                  </label>
                </div>
              </div>

              <div className="admin-form-section">
                <div className="admin-section-title">
                  <strong>하루 운영 메모</strong>
                  <span>각 줄마다 한 문장씩 입력하면 일정 생성에 활용돼요.</span>
                </div>
                <div className="admin-form-grid">
                  <label>
                    <span>오전 메모</span>
                    <textarea
                      rows={5}
                      placeholder="한 줄에 한 문장씩 입력해 주세요."
                      value={editor.full_day_notes_morning}
                      onChange={(event) => onChange("full_day_notes_morning", event.target.value)}
                    />
                  </label>
                  <label>
                    <span>오후 메모</span>
                    <textarea
                      rows={5}
                      placeholder="한 줄에 한 문장씩 입력해 주세요."
                      value={editor.full_day_notes_afternoon}
                      onChange={(event) => onChange("full_day_notes_afternoon", event.target.value)}
                    />
                  </label>
                  <label>
                    <span>저녁 메모</span>
                    <textarea
                      rows={5}
                      placeholder="한 줄에 한 문장씩 입력해 주세요."
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
              <p className="admin-preview-title">{editor.name || "장소명을 입력하면 여기서 바로 확인할 수 있어요."}</p>
              <p className="admin-preview-summary">{editor.summary || "소개 문장을 입력하면 추천 문구의 톤을 미리 보기 쉽게 보여드려요."}</p>
              <div className="admin-chip-row">
                {editor.category.map((value) => (
                  <span key={value} className="admin-preview-chip">
                    {categoryOptions.find((option) => option.value === value)?.label ?? value}
                  </span>
                ))}
              </div>
              <div className="admin-preview-lines">
                <p>오전 메모: {editor.full_day_notes_morning.split("\n").filter(Boolean)[0] || "입력 전"}</p>
                <p>오후 메모: {editor.full_day_notes_afternoon.split("\n").filter(Boolean)[0] || "입력 전"}</p>
                <p>저녁 메모: {editor.full_day_notes_evening.split("\n").filter(Boolean)[0] || "입력 전"}</p>
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </section>
  );
}
