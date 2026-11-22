import { useEffect, useMemo, useRef, useState } from "react";
import { MAX_NIGHTS, addDays, diffNights, isSameLocalDate, parseLocalISODate, startOfLocalToday, toLocalISODate } from "../utils/trip-duration";

type DateRangeCalendarProps = {
  // 확정된 값(부모 폼 상태) - 선택 진행 중(한쪽만 찍은 상태)에는 바뀌지
  // 않는다. 두 번째 클릭에서만 onChange로 확정된 새 값을 올려보낸다.
  startDate: string;
  nights: number;
  onChange: (startDate: string, nights: number) => void;
};

const WEEKDAY_LABELS = ["일", "월", "화", "수", "목", "금", "토"];

function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function addMonths(date: Date, months: number): Date {
  return new Date(date.getFullYear(), date.getMonth() + months, 1);
}

function buildMonthGrid(monthStart: Date): Array<Date | null> {
  const firstWeekday = monthStart.getDay();
  const daysInMonth = new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 0).getDate();
  const cells: Array<Date | null> = [];
  for (let i = 0; i < firstWeekday; i += 1) {
    cells.push(null);
  }
  for (let day = 1; day <= daysInMonth; day += 1) {
    cells.push(new Date(monthStart.getFullYear(), monthStart.getMonth(), day));
  }
  return cells;
}

export function DateRangeCalendar({ startDate, nights, onChange }: DateRangeCalendarProps) {
  const today = useMemo(() => startOfLocalToday(), []);
  const confirmedStart = useMemo(() => parseLocalISODate(startDate), [startDate]);
  const confirmedEnd = useMemo(() => addDays(confirmedStart, nights), [confirmedStart, nights]);

  const [pendingStart, setPendingStart] = useState<Date | null>(null);
  const [viewMonth, setViewMonth] = useState<Date>(() => startOfMonth(confirmedStart));
  const [focusedDate, setFocusedDate] = useState<Date>(confirmedStart);
  const buttonRefs = useRef(new Map<string, HTMLButtonElement>());
  const pendingFocusRef = useRef(false);

  useEffect(() => {
    if (!pendingFocusRef.current) {
      return;
    }
    pendingFocusRef.current = false;
    const key = toLocalISODate(focusedDate);
    buttonRefs.current.get(key)?.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewMonth, focusedDate]);

  // 빠른 선택 칩처럼 달력 바깥에서 startDate/nights가 바뀌면(onChange를
  // 거쳐 부모 폼 상태가 바뀐 경우) 보여주는 달도 그 값으로 맞춘다 - 단,
  // 선택이 진행 중(pendingStart)일 때는 그 진행을 덮어쓰지 않는다.
  useEffect(() => {
    if (pendingStart) {
      return;
    }
    const nextStart = parseLocalISODate(startDate);
    setViewMonth((current) =>
      current.getFullYear() === nextStart.getFullYear() && current.getMonth() === nextStart.getMonth()
        ? current
        : startOfMonth(nextStart),
    );
    setFocusedDate(nextStart);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startDate, nights]);

  const isDisabled = (date: Date): boolean => {
    if (date.getTime() < today.getTime()) {
      return true;
    }
    if (pendingStart) {
      const maxEnd = addDays(pendingStart, MAX_NIGHTS);
      return date.getTime() > maxEnd.getTime();
    }
    return false;
  };

  const isOverMaxNightsNotice = useMemo(() => {
    if (!pendingStart) {
      return false;
    }
    // 현재 보고 있는 달에 "최대 30박" 상한에 걸려 비활성화된 날짜가 실제로
    // 있을 때만 안내를 보여준다(상한과 무관한 달에서까지 보일 필요는 없다).
    const maxEnd = addDays(pendingStart, MAX_NIGHTS);
    const monthEnd = new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1, 0);
    return monthEnd.getTime() > maxEnd.getTime();
  }, [pendingStart, viewMonth]);

  const moveFocus = (deltaDays: number) => {
    const next = addDays(focusedDate, deltaDays);
    if (next.getMonth() !== viewMonth.getMonth() || next.getFullYear() !== viewMonth.getFullYear()) {
      setViewMonth(startOfMonth(next));
    }
    pendingFocusRef.current = true;
    setFocusedDate(next);
  };

  const commitSelection = (clicked: Date) => {
    if (!pendingStart) {
      setPendingStart(clicked);
      setFocusedDate(clicked);
      return;
    }

    if (isSameLocalDate(clicked, pendingStart)) {
      onChange(toLocalISODate(pendingStart), 0);
      setPendingStart(null);
      return;
    }

    if (clicked.getTime() < pendingStart.getTime()) {
      // 종료일이 시작일보다 앞 - 그 날짜를 새 시작일로 다시 본다(아직 미확정).
      setPendingStart(clicked);
      setFocusedDate(clicked);
      return;
    }

    const selectedNights = diffNights(toLocalISODate(pendingStart), toLocalISODate(clicked));
    onChange(toLocalISODate(pendingStart), Math.min(selectedNights, MAX_NIGHTS));
    setPendingStart(null);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    switch (event.key) {
      case "ArrowLeft":
        event.preventDefault();
        moveFocus(-1);
        break;
      case "ArrowRight":
        event.preventDefault();
        moveFocus(1);
        break;
      case "ArrowUp":
        event.preventDefault();
        moveFocus(-7);
        break;
      case "ArrowDown":
        event.preventDefault();
        moveFocus(7);
        break;
      case "Enter":
      case " ":
        event.preventDefault();
        if (!isDisabled(focusedDate)) {
          commitSelection(focusedDate);
        }
        break;
      default:
        break;
    }
  };

  const rangeStart = pendingStart ?? confirmedStart;
  const rangeEnd = pendingStart ?? confirmedEnd;

  const cells = useMemo(() => buildMonthGrid(viewMonth), [viewMonth]);
  // 오늘이 속한 달보다 더 과거로는 갈 수 없다 - 그 이전 달은 전부 지난
  // 날짜뿐이라 보여줘도 고를 게 없다.
  const isAtCurrentMonth =
    viewMonth.getFullYear() === today.getFullYear() && viewMonth.getMonth() === today.getMonth();

  return (
    <div className="tc-calendar">
      <div className="tc-calendar-head">
        <button
          aria-disabled={isAtCurrentMonth}
          aria-label="이전 달"
          className="tc-calendar-nav"
          disabled={isAtCurrentMonth}
          onClick={() => setViewMonth((month) => addMonths(month, -1))}
          type="button"
        >
          ‹
        </button>
        <strong className="tc-calendar-title">
          {viewMonth.getFullYear()}년 {viewMonth.getMonth() + 1}월
        </strong>
        <button
          aria-label="다음 달"
          className="tc-calendar-nav"
          onClick={() => setViewMonth((month) => addMonths(month, 1))}
          type="button"
        >
          ›
        </button>
      </div>

      <div className="tc-calendar-weekdays" aria-hidden="true">
        {WEEKDAY_LABELS.map((label) => (
          <span key={label}>{label}</span>
        ))}
      </div>

      <div className="tc-calendar-grid" onKeyDown={handleKeyDown} role="grid">
        {cells.map((date, index) => {
          if (!date) {
            return <span aria-hidden="true" className="tc-calendar-cell tc-calendar-cell-blank" key={`blank-${index}`} />;
          }

          const dateKey = toLocalISODate(date);
          const disabled = isDisabled(date);
          const isRangeStart = isSameLocalDate(date, rangeStart);
          const isRangeEnd = isSameLocalDate(date, rangeEnd);
          const inRange = date.getTime() >= rangeStart.getTime() && date.getTime() <= rangeEnd.getTime();
          const isToday = isSameLocalDate(date, today);
          const isFocusable = isSameLocalDate(date, focusedDate);

          const classNames = ["tc-calendar-day"];
          if (inRange) classNames.push("is-in-range");
          if (isRangeStart || isRangeEnd) classNames.push("is-range-edge");
          if (isToday) classNames.push("is-today");

          return (
            <button
              aria-label={`${date.getFullYear()}년 ${date.getMonth() + 1}월 ${date.getDate()}일`}
              aria-pressed={isRangeStart || isRangeEnd}
              className={classNames.join(" ")}
              disabled={disabled}
              key={dateKey}
              onClick={() => commitSelection(date)}
              onFocus={() => setFocusedDate(date)}
              ref={(element) => {
                if (element) {
                  buttonRefs.current.set(dateKey, element);
                } else {
                  buttonRefs.current.delete(dateKey);
                }
              }}
              tabIndex={isFocusable ? 0 : -1}
              type="button"
            >
              {date.getDate()}
            </button>
          );
        })}
      </div>

      <p className="tc-note" role="status">
        {pendingStart
          ? isOverMaxNightsNotice
            ? "종료일을 선택해 주세요(같은 날을 다시 누르면 당일치기). 최대 30박까지 선택할 수 있어요."
            : "종료일을 선택해 주세요(같은 날을 다시 누르면 당일치기)."
          : "시작일을 선택해 주세요."}
      </p>
    </div>
  );
}
