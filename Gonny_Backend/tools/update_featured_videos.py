from __future__ import annotations

import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "app" / "data" / "destinations"

VIDEO_MAP = {
    "seoul": {
        "video_id": "sr3O7ArQTYY",
        "title": "SEOUL VACATION TRAVEL GUIDE | Expedia",
        "channel": "Expedia",
        "view_count_text": "조회수 3,516,149회",
        "published": "8년 전",
    },
    "jeju": {
        "video_id": "OWaQI-3pefA",
        "title": "Ultimate Guide to JEJU Island (72HRS)",
        "channel": "Doobydobap",
        "view_count_text": "조회수 1,127,731회",
        "published": "1년 전",
    },
    "busan": {
        "video_id": "Qh3wrmSUqaI",
        "title": "Busan Vacation Travel Guide | Expedia",
        "channel": "Expedia",
        "view_count_text": "조회수 1,440,681회",
        "published": "7년 전",
    },
    "gangneung": {
        "video_id": "pQwnc-50uMg",
        "title": "Recommended travel destinations in Korea✨Gangneung Travel Guide‼️Korea Travel Vlog🇰🇷",
        "channel": "유일랜드 Uiland",
        "view_count_text": "조회수 497,858회",
        "published": "4년 전",
    },
    "gyeongju": {
        "video_id": "ziuTjx4ioo8",
        "title": "Recommended travel destinations in Korea✨Gyeongju Travel Guide‼️Korea Travel Vlog🇰🇷",
        "channel": "유일랜드 Uiland",
        "view_count_text": "조회수 506,248회",
        "published": "4년 전",
    },
    "jeonju": {
        "video_id": "btjvJ4MCmtg",
        "title": "Recommend a must-visit destination in Korea ✨Jeonju Travel Guide ‼️ Korea Travel Vlog 🇰🇷",
        "channel": "유일랜드 Uiland",
        "view_count_text": "조회수 329,837회",
        "published": "4년 전",
    },
    "sokcho": {
        "video_id": "5UwwZo4_t08",
        "title": "속초여행 BEST 8곳 속초맛집 추천 5곳/ Sokcho Travel Course in Gangwon-do,South Korea",
        "channel": "GoGoMong 고고몽",
        "view_count_text": "조회수 205,794회",
        "published": "3년 전",
    },
    "yeosu": {
        "video_id": "upWyMSQDJJk",
        "title": "Recommend a must-see destination in Korea✨Yeosu Travel Guide‼️Korea Travel Vlog🇰🇷",
        "channel": "유일랜드 Uiland",
        "view_count_text": "조회수 666,424회",
        "published": "4년 전",
    },
    "tokyo": {
        "video_id": "HYSMJ-lM2t0",
        "title": "100 Things to do in TOKYO, JAPAN | Japan Travel Guide",
        "channel": "kimdao",
        "view_count_text": "조회수 6,280,060회",
        "published": "8년 전",
    },
    "osaka": {
        "video_id": "TJke9-CUJ9Q",
        "title": "Top 15 things to do in Osaka Japan | Osaka Travel Guide",
        "channel": "Allan Su",
        "view_count_text": "조회수 1,378,692회",
        "published": "6년 전",
    },
    "kyoto": {
        "video_id": "2G0Hh8f9Cc8",
        "title": "Top 5 Things to do in Kyoto",
        "channel": "Japan Guide",
        "view_count_text": "조회수 2,150,580회",
        "published": "8년 전",
    },
    "fukuoka": {
        "video_id": "MNHYBTnUeJI",
        "title": "Ultimate Fukuoka Travel Guide: Top City Spots & Nearby Attractions!",
        "channel": "히제이 HEEJ",
        "view_count_text": "조회수 1,755,452회",
        "published": "1년 전",
    },
    "bangkok": {
        "video_id": "KyC_mKy7Zf8",
        "title": "BANGKOK, THAILAND | 10 BEST Things To Do In & Around Bangkok (+ Travel Tips!)",
        "channel": "World Wild Hearts",
        "view_count_text": "조회수 1,423,195회",
        "published": "3년 전",
    },
    "chiangmai": {
        "video_id": "tH3Y-0i5jR8",
        "title": "CHIANG MAI, THAILAND | 10 BEST Things To Do In & Around Chiang Mai",
        "channel": "World Wild Hearts",
        "view_count_text": "조회수 531,099회",
        "published": "3년 전",
    },
    "taipei": {
        "video_id": "r_nCj1X_Hhw",
        "title": "Best Things to do in Taipei - Overnight City Guide",
        "channel": "FEATR",
        "view_count_text": "조회수 892,799회",
        "published": "10년 전",
    },
    "singapore": {
        "video_id": "P_q3BdrFsLI",
        "title": "Singapore Vacation Travel Guide | Expedia",
        "channel": "Expedia",
        "view_count_text": "조회수 3,923,935회",
        "published": "12년 전",
    },
    "paris": {
        "video_id": "AQ6GmpMu5L8",
        "title": "Paris Vacation Travel Guide | Expedia",
        "channel": "Expedia",
        "view_count_text": "조회수 4,965,047회",
        "published": "13년 전",
    },
    "rome": {
        "video_id": "DEJx0CYrDHk",
        "title": "Rome Vacation Travel Guide | Expedia",
        "channel": "Expedia",
        "view_count_text": "조회수 2,240,503회",
        "published": "12년 전",
    },
    "barcelona": {
        "video_id": "Y9qZf_imVTs",
        "title": "BARCELONA TRAVEL GUIDE 🏖️ Top 25 Things to Do, See, Eat, Drink & Experience in Barcelona, Spain 🇪🇸✨",
        "channel": "Samuel and Audrey - Travel and Food Videos",
        "view_count_text": "조회수 1,593,195회",
        "published": "10년 전",
    },
    "vladivostok": {
        "video_id": "bB6DGkrIVZk",
        "title": "4K Walking Tour with City Sounds - Trip to Vladivostok, Russia",
        "channel": "4K Urban Life",
        "view_count_text": "조회수 128,143회",
        "published": "5년 전",
    },
}


def enrich(video: dict[str, str]) -> dict[str, str]:
    video_id = video["video_id"]
    return {
        **video,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "embed_url": f"https://www.youtube.com/embed/{video_id}",
        "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
    }


def main() -> None:
    for path in sorted(DATA_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        city = data.get("city")
        if city not in VIDEO_MAP:
            continue

        data["featured_video"] = enrich(VIDEO_MAP[city])

        with path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

        print(f"updated featured video: {city}")


if __name__ == "__main__":
    main()
