import { useState } from "react";
import { Button } from "../../../shared/components/ui/button";

const travelStyles = ["미식", "자연", "휴양", "쇼핑", "문화", "액티비티"];
const transportOptions = ["대중교통", "렌터카", "도보 위주", "혼합"];
const accommodationOptions = ["호텔", "펜션", "게스트하우스", "에어비앤비"];

export function TripCreateForm() {
  const [selectedStyles, setSelectedStyles] = useState<string[]>(["미식", "자연"]);

  const toggleStyle = (value: string) => {
    setSelectedStyles((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value],
    );
  };

  return (
    <div className="page-grid grid-two">
      <div className="card stack">
        <div>
          <h2 className="section-title">새 여행 만들기</h2>
          <p className="section-subtitle">
            요구사항 문서 기준의 카테고리 중심 입력 흐름을 먼저 화면으로 옮겨둔 상태입니다.
          </p>
        </div>

        <label className="field">
          <span>여행지</span>
          <input defaultValue="제주도" placeholder="예: 제주도, 부산, 강릉" />
        </label>

        <div className="row">
          <label className="field" style={{ flex: 1 }}>
            <span>출발일</span>
            <input defaultValue="2026-05-01" type="date" />
          </label>
          <label className="field" style={{ flex: 1 }}>
            <span>도착일</span>
            <input defaultValue="2026-05-03" type="date" />
          </label>
        </div>

        <div className="field">
          <span>여행 스타일</span>
          <div className="chip-list">
            {travelStyles.map((style) => (
              <button
                key={style}
                className={selectedStyles.includes(style) ? "chip active" : "chip"}
                onClick={() => toggleStyle(style)}
                type="button"
              >
                {style}
              </button>
            ))}
          </div>
        </div>

        <div className="row">
          <label className="field" style={{ flex: 1 }}>
            <span>예산</span>
            <input defaultValue="500000" type="number" />
          </label>
          <label className="field" style={{ flex: 1 }}>
            <span>이동 수단</span>
            <select defaultValue={transportOptions[1]}>
              {transportOptions.map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </label>
        </div>

        <label className="field">
          <span>숙박 유형</span>
          <select defaultValue={accommodationOptions[1]}>
            {accommodationOptions.map((option) => (
              <option key={option}>{option}</option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>추가 요청</span>
          <textarea defaultValue="조용한 곳 위주로 보고 싶고, 붐비는 핫플은 제외해줘." rows={5} />
        </label>

        <div className="row">
          <Button>AI 일정 생성하기</Button>
          <Button variant="secondary">초기화</Button>
        </div>
      </div>

      <div className="card stack">
        <div>
          <h2 className="section-title">미리보기</h2>
          <p className="section-subtitle">
            생성 진행 상태, 스트리밍 결과, 요약 카드가 들어갈 영역입니다.
          </p>
        </div>

        <div className="metric">
          <strong>현재 선택</strong>
          <p style={{ marginBottom: 0 }}>제주도 / 2박 3일 / 렌터카 / 펜션 / 미식 + 자연</p>
        </div>

        <div className="metric">
          <strong>예상 결과</strong>
          <p style={{ marginBottom: 0 }}>
            일자별 일정, 날씨 경고, 장소 교체, 예산 추적, 숙소 추천 흐름으로 이어집니다.
          </p>
        </div>

        <div className="metric">
          <strong>생성 진행 상태</strong>
          <div className="progress-bar" style={{ marginTop: 12 }}>
            <div className="progress-fill" style={{ width: "45%" }} />
          </div>
          <p className="section-subtitle" style={{ margin: "10px 0 0" }}>
            여행 조건 정리 완료 → 장소 검증 중 → 일정 조합 중
          </p>
        </div>
      </div>
    </div>
  );
}
