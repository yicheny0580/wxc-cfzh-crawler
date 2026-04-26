import { formatDate, formatNumber } from "./format";
import type { SummaryResponse } from "./types";

export function SummaryStrip({
  summary,
  loading
}: {
  summary: SummaryResponse | null;
  loading: boolean;
}) {
  const items = [
    ["Posts", summary ? formatNumber(summary.posts) : "-"],
    ["Replies", summary ? formatNumber(summary.replies) : "-"],
    ["Authors", summary ? formatNumber(summary.authors) : "-"],
    ["Latest crawl", summary ? formatDate(summary.latest_crawl_at) : "-"]
  ];

  return (
    <dl className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-stone-600">
      {items.map(([label, value]) => (
        <div
          key={label}
          className="flex items-baseline gap-1.5 border-l border-stone-300 pl-3 first:border-l-0 first:pl-0"
        >
          <dt className="font-medium uppercase text-stone-500">{label}</dt>
          <dd className="font-semibold text-stone-950">
            {loading && value === "-" ? "..." : value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-900">
      {message}
    </div>
  );
}
