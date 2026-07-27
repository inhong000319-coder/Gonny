from __future__ import annotations

import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
DATA_DIR = PROJECT_ROOT / "app" / "data" / "destinations"
TARGET_CITIES = ("seoul", "busan", "jeju")


def is_polluted_summary(summary: str) -> bool:
    if summary.endswith("다요."):
        return True
    return summary.endswith("요.") and any(char.isascii() and char.isalpha() for char in summary)


def repair_summary(summary: str) -> str:
    if summary.endswith("다요."):
        return summary[:-2] + "."
    if summary.endswith("요.") and any(char.isascii() and char.isalpha() for char in summary):
        return summary[:-2] + "."
    return summary


def load_history_commits(path: Path) -> list[str]:
    return subprocess.check_output(
        ["git", "log", "--format=%H", "--reverse", "--", str(path)],
        text=True,
        encoding="utf-8",
    ).splitlines()


def load_catalog_at_commit(commit: str, path: Path) -> dict:
    relative_path = path.relative_to(REPO_ROOT).as_posix()
    return json.loads(
        subprocess.check_output(
            ["git", "show", f"{commit}:{relative_path}"],
            text=True,
            encoding="utf-8",
        )
    )


def collect_clean_history(path: Path) -> dict[str, str]:
    clean_history: dict[str, str] = {}
    for commit in load_history_commits(path):
        catalog = load_catalog_at_commit(commit, path)
        for place in catalog["places"]:
            summary = place["summary"]
            if not is_polluted_summary(summary):
                clean_history[place["id"]] = summary
    return clean_history


def repair_city(path: Path) -> dict[str, int]:
    clean_history = collect_clean_history(path)
    catalog = json.loads(path.read_text(encoding="utf-8"))

    repaired_from_history = 0
    repaired_with_fallback = 0
    unchanged = 0

    for place in catalog["places"]:
        summary = place["summary"]
        if not is_polluted_summary(summary):
            unchanged += 1
            continue

        historical_summary = clean_history.get(place["id"])
        if historical_summary and not is_polluted_summary(historical_summary):
            place["summary"] = historical_summary
            repaired_from_history += 1
            continue

        repaired_summary = repair_summary(summary)
        if repaired_summary != summary:
            place["summary"] = repaired_summary
            repaired_with_fallback += 1

    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "repaired_from_history": repaired_from_history,
        "repaired_with_fallback": repaired_with_fallback,
        "unchanged": unchanged,
    }


def verify() -> dict[str, int]:
    polluted_count = 0
    total_count = 0

    for city in TARGET_CITIES:
        catalog = json.loads((DATA_DIR / f"{city}.json").read_text(encoding="utf-8"))
        for place in catalog["places"]:
            total_count += 1
            if is_polluted_summary(place["summary"]):
                polluted_count += 1

    if polluted_count:
        raise SystemExit(f"Found {polluted_count} polluted summaries in visible city data.")

    return {"total_places": total_count, "polluted_summaries": polluted_count}


def main() -> None:
    for city in TARGET_CITIES:
        result = repair_city(DATA_DIR / f"{city}.json")
        print(city, result)
    print(verify())


if __name__ == "__main__":
    main()
