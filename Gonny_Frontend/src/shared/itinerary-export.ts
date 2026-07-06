type ExportLabels = {
  cityLabel: string;
  countryLabel: string;
  continentLabel: string;
  budgetLabel: string;
  styleLabel: string;
  companionLabel: string;
  conceptLabels: string[];
  timeSlotLabel: (value: string) => string;
};

type ItineraryItem = {
  day_number: number;
  time_slot: string;
  place_name: string;
  category: string;
  area: string;
  notes: string;
};

type ItineraryResult = {
  city: string;
  country: string;
  continent: string;
  travelers: number;
  nights: number;
  days: number;
  items: ItineraryItem[];
};

function buildSafeFilename(value: string) {
  return value.replace(/[<>:"/\\|?*\x00-\x1F]/g, "-").trim() || "gonny-itinerary";
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function groupItemsByDay(items: ItineraryItem[]) {
  return items.reduce<Map<number, ItineraryItem[]>>((groups, item) => {
    const current = groups.get(item.day_number) ?? [];
    current.push(item);
    groups.set(item.day_number, current);
    return groups;
  }, new Map());
}

function buildSummaryLines(result: ItineraryResult, labels: ExportLabels) {
  return [
    `${labels.cityLabel} 여행 일정`,
    `${labels.countryLabel} · ${labels.continentLabel}`,
    `${result.nights}박 ${result.days}일 · ${result.travelers}명`,
    `예산: ${labels.budgetLabel}`,
    `스타일: ${labels.styleLabel}`,
    `동행: ${labels.companionLabel}`,
    `컨셉: ${labels.conceptLabels.join(", ")}`,
  ];
}

function buildHtmlDocument(result: ItineraryResult, labels: ExportLabels) {
  const days = Array.from(groupItemsByDay(result.items).entries()).sort((left, right) => left[0] - right[0]);

  const dayMarkup = days
    .map(
      ([day, items]) => `
        <section class="day">
          <h2>DAY ${day}</h2>
          ${items
            .map(
              (item) => `
                <article class="item">
                  <div class="item-head">
                    <strong>${escapeHtml(labels.timeSlotLabel(item.time_slot))}</strong>
                    <span>${escapeHtml(item.place_name)}</span>
                  </div>
                  <p class="meta">${escapeHtml(item.area)} · ${escapeHtml(item.category)}</p>
                  <p class="notes">${escapeHtml(item.notes)}</p>
                </article>
              `,
            )
            .join("")}
        </section>
      `,
    )
    .join("");

  return `
    <!doctype html>
    <html lang="ko">
      <head>
        <meta charset="utf-8" />
        <title>${escapeHtml(labels.cityLabel)} 여행 일정</title>
        <style>
          body { font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; color: #111827; }
          h1, h2 { margin: 0 0 12px; }
          .summary { margin: 16px 0 24px; padding: 16px; background: #f3f4f6; border-radius: 12px; }
          .summary p { margin: 4px 0; }
          .day { margin-top: 24px; padding-top: 8px; border-top: 1px solid #e5e7eb; }
          .item { margin: 14px 0; padding: 14px; border: 1px solid #e5e7eb; border-radius: 12px; }
          .item-head { display: flex; gap: 12px; align-items: baseline; }
          .meta { color: #6b7280; margin: 6px 0; }
          .notes { white-space: pre-wrap; margin: 0; }
        </style>
      </head>
      <body>
        <h1>${escapeHtml(labels.cityLabel)} 여행 일정</h1>
        <div class="summary">
          ${buildSummaryLines(result, labels)
            .map((line) => `<p>${escapeHtml(line)}</p>`)
            .join("")}
        </div>
        ${dayMarkup}
      </body>
    </html>
  `;
}

function createObjectUrl(content: string, type: string) {
  return URL.createObjectURL(new Blob([content], { type }));
}

export function createItineraryDocDownload(result: ItineraryResult, labels: ExportLabels) {
  const filename = `${buildSafeFilename(labels.cityLabel || result.city)}-itinerary.doc`;
  const href = createObjectUrl(buildHtmlDocument(result, labels), "application/msword;charset=utf-8");
  return { href, filename };
}

export function createItineraryPrintPreview(result: ItineraryResult, labels: ExportLabels) {
  const filename = `${buildSafeFilename(labels.cityLabel || result.city)}-itinerary-print.html`;
  const href = createObjectUrl(buildHtmlDocument(result, labels), "text/html;charset=utf-8");
  return { href, filename };
}

export function revokeItineraryExportUrl(href?: string | null) {
  if (!href) {
    return;
  }

  URL.revokeObjectURL(href);
}
