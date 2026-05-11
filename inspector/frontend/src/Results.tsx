import { ChevronLeft, ChevronRight } from "lucide-react";

import { StateBlock } from "./StateBlock";
import { displayResultTitle, formatDate, formatNumber, resultKey } from "./format";
import type { ResultItem, ResultListResponse } from "./types";

export const PAGE_SIZE = 25;

export function ResultList({
  results,
  loading,
  refreshing = false,
  selectedResultKey,
  notInterestedPostIds,
  onNotInterestedChange,
  onSelect
}: {
  results: ResultItem[];
  loading: boolean;
  refreshing?: boolean;
  selectedResultKey: string | null;
  notInterestedPostIds: Set<string>;
  onNotInterestedChange: (postId: string, hidden: boolean) => void;
  onSelect: (result: ResultItem) => void;
}) {
  if (loading) {
    return <StateBlock text="Loading results..." />;
  }

  if (results.length === 0) {
    return <StateBlock text="No results found." />;
  }

  return (
    <div className="scrollbar-stable min-h-0 flex-1 overflow-y-auto" aria-busy={refreshing}>
      {results.map((result) => {
        const selected = resultKey(result) === selectedResultKey;
        const isReply = result.record_type === "reply";
        const markedNotInterested = notInterestedPostIds.has(result.root_post_id);
        return (
          <div
            key={resultKey(result)}
            className={`group relative border-b border-stone-200 transition ${
              selected
                ? "bg-emerald-50"
                : markedNotInterested
                  ? "bg-stone-100 hover:bg-stone-200/60"
                  : "bg-white hover:bg-stone-50"
            }`}
          >
            <button
              type="button"
              onClick={() => onSelect(result)}
              className="block w-full px-3 py-3 text-left focus:outline-none focus:ring-2 focus:ring-inset focus:ring-emerald-600"
            >
              <div className="flex items-start justify-between gap-3">
                <h2 className="min-w-0 flex-1 text-sm font-semibold leading-5 text-stone-950">
                  {displayResultTitle(result)}
                </h2>
                <span
                  className={`shrink-0 rounded-sm px-1.5 py-0.5 text-xs font-medium ${
                    isReply ? "bg-sky-100 text-sky-900" : "bg-amber-100 text-amber-900"
                  }`}
                >
                  {isReply ? "Reply" : formatNumber(result.actual_reply_count)}
                </span>
              </div>
              <div className="mt-1 flex flex-wrap gap-x-2 gap-y-1 text-xs text-stone-600">
                <span>{result.author || "Unknown"}</span>
                <span>{formatDate(result.published_at)}</span>
                <span>#{isReply ? result.reply_id : result.post_id}</span>
                {result.read_count !== null ? (
                  <span>{formatNumber(result.read_count)} reads</span>
                ) : null}
                {markedNotInterested ? (
                  <span className="font-medium text-red-700">Not interested</span>
                ) : null}
              </div>
              {isReply ? (
                <div className="mt-2 text-xs text-stone-600">
                  Original: {result.root_title?.trim() || `Post ${result.root_post_id}`}
                </div>
              ) : null}
              {result.excerpt ? (
                <p className="mt-2 max-h-10 overflow-hidden text-sm leading-5 text-stone-700">
                  {result.excerpt}
                </p>
              ) : null}
            </button>
            <button
              type="button"
              aria-label={markedNotInterested ? "Undo hide" : "Hide"}
              aria-pressed={markedNotInterested}
              onClick={() => onNotInterestedChange(result.root_post_id, !markedNotInterested)}
              className={`absolute right-2 top-2 z-10 hidden h-7 items-center justify-center rounded-md border px-2 text-xs font-medium shadow-sm transition focus:outline-none focus:ring-2 focus:ring-emerald-600 sm:inline-flex sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100 ${
                markedNotInterested
                  ? "border-red-200 bg-white/95 text-red-700 hover:bg-red-50"
                  : "border-stone-300 bg-white/95 text-stone-600 hover:bg-stone-50 hover:text-stone-950"
              }`}
              title={markedNotInterested ? "Undo hide" : "Hide"}
            >
              {markedNotInterested ? "Undo" : "Hide"}
            </button>
          </div>
        );
      })}
    </div>
  );
}

export function Pagination({
  results,
  canGoBack,
  canGoForward,
  onPrevious,
  onNext
}: {
  results: ResultListResponse | null;
  canGoBack: boolean;
  canGoForward: boolean;
  onPrevious: () => void;
  onNext: () => void;
}) {
  const start = results && results.total > 0 ? results.offset + 1 : 0;
  const end = results ? Math.min(results.offset + results.limit, results.total) : 0;

  return (
    <div className="flex shrink-0 items-center justify-between border-t border-stone-300 bg-[#fbfaf7] px-3 py-2">
      <div className="text-sm text-stone-600">
        {formatNumber(start)}-{formatNumber(end)} of {formatNumber(results?.total ?? 0)}
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onPrevious}
          disabled={!canGoBack}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-stone-300 bg-white text-stone-700 transition hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-40"
          title="Previous page"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={!canGoForward}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-stone-300 bg-white text-stone-700 transition hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-40"
          title="Next page"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
