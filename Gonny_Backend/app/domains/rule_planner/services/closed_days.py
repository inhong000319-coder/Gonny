"""Best-effort weekly-closure detection from destination_catalog's raw
closed_days prose.

closed_days is free-form text scraped from TourAPI (e.g. "매주 화요일 ※ 단,
정기휴일이 공휴일과 겹칠 경우에는 개방하며...", "매달 첫째 주 월요일", "점포별로
상이함"), not a structured schedule - see PlaceData.closed_days. Reliably
parsing arbitrary prose across venue types is out of scope, so this module
deliberately only recognizes the clearest, most common patterns:

- "연중무휴" / "휴무일 없음" style phrasing -> open every day.
- "매주 <요일>[,<요일>...]요일 ..." -> closed on those weekdays, every week.

Anything else - ambiguous phrasing, seasonal/conditional closures, biweekly
("격주"), or month-based patterns ("매달 첫째 주 월요일", "매월 첫째, 셋째
화요일") - is reported as "unknown" rather than guessed at. Per this
feature's scope: a wrong "closed" guess blocks a valid placement, which is
worse than simply not knowing, so we only ever exclude on high-confidence
matches.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class ClosureCertainty(str, Enum):
    OPEN_EVERY_DAY = "open_every_day"
    CLOSED_ON_WEEKDAYS = "closed_on_weekdays"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ClosureInfo:
    certainty: ClosureCertainty
    # 0=Monday ... 6=Sunday, matching datetime.date.weekday().
    closed_weekdays: frozenset[int] = field(default_factory=frozenset)


WEEKDAY_LABEL_KO = {
    0: "월요일",
    1: "화요일",
    2: "수요일",
    3: "목요일",
    4: "금요일",
    5: "토요일",
    6: "일요일",
}

_WEEKDAY_CHAR_TO_INDEX = {
    "월": 0,
    "화": 1,
    "수": 2,
    "목": 3,
    "금": 4,
    "토": 5,
    "일": 6,
}

_NO_CLOSURE_MARKERS = (
    "연중무휴",
    "연중 무휴",
    "휴무일 없음",
    "휴무 없음",
    "휴관일 없음",
)

# Presence of any of these means the text describes something more
# complex than a flat, every-week closure (seasonal variation, biweekly,
# nth-week-of-month, per-venue/per-program variation, ad-hoc closures,
# etc.) - bail out to "unknown" even if a "매주 ..." fragment is also
# present, rather than risk a confidently-wrong exclusion.
_COMPLEX_PATTERN_MARKERS = (
    "계절",
    "시즌",
    "동절기",
    "하절기",
    "격주",
    "홀수",
    "짝수",
    "부정기",
    "매월",
    "매달",
    "임시",
    "변경",
    "별도",
    "상이",
    "협의",
    "탄력",
    "단,",
    "공휴일",
)

# Matches "매주" followed by one or more weekday characters (optionally
# separated by punctuation) and the "요일" suffix, e.g. "매주 화요일",
# "매주 월,수요일", "[사무실]매주 월요일".
_WEEKLY_CLOSURE_RE = re.compile(r"매주\s*([월화수목금토일](?:\s*[,·、/및]\s*[월화수목금토일])*)\s*요일")


def parse_closed_days(closed_days_text: str | None) -> ClosureInfo:
    if not closed_days_text:
        return ClosureInfo(certainty=ClosureCertainty.UNKNOWN)

    text = closed_days_text.strip()
    if not text:
        return ClosureInfo(certainty=ClosureCertainty.UNKNOWN)

    if any(marker in text for marker in _COMPLEX_PATTERN_MARKERS):
        return ClosureInfo(certainty=ClosureCertainty.UNKNOWN)

    if any(marker in text for marker in _NO_CLOSURE_MARKERS):
        return ClosureInfo(certainty=ClosureCertainty.OPEN_EVERY_DAY)

    match = _WEEKLY_CLOSURE_RE.search(text)
    if not match:
        return ClosureInfo(certainty=ClosureCertainty.UNKNOWN)

    closed_weekdays = {
        _WEEKDAY_CHAR_TO_INDEX[char] for char in match.group(1) if char in _WEEKDAY_CHAR_TO_INDEX
    }
    if not closed_weekdays:
        return ClosureInfo(certainty=ClosureCertainty.UNKNOWN)

    return ClosureInfo(certainty=ClosureCertainty.CLOSED_ON_WEEKDAYS, closed_weekdays=frozenset(closed_weekdays))


def is_confirmed_closed_on(closed_days_text: str | None, weekday: int) -> bool:
    """True only when closed_days_text unambiguously says this place is
    closed every week on the given weekday (0=Monday ... 6=Sunday).
    Ambiguous or unrecognized text returns False - see module docstring."""
    info = parse_closed_days(closed_days_text)
    return info.certainty == ClosureCertainty.CLOSED_ON_WEEKDAYS and weekday in info.closed_weekdays
