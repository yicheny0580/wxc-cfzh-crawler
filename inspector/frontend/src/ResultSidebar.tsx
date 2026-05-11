import { Search, X } from "lucide-react";

import { PAGE_SIZE, Pagination, ResultList } from "./Results";
import type { ResultItem, ResultListResponse } from "./types";

export function ResultSidebar({
  query,
  results,
  loading,
  refreshing,
  selectedResultKey,
  canGoBack,
  canGoForward,
  notInterestedPostIds,
  onQueryChange,
  onSelect,
  onToggleNotInterested,
  onPrevious,
  onNext
}: {
  query: string;
  results: ResultListResponse | null;
  loading: boolean;
  refreshing: boolean;
  selectedResultKey: string | null;
  canGoBack: boolean;
  canGoForward: boolean;
  notInterestedPostIds: Set<string>;
  onQueryChange: (query: string) => void;
  onSelect: (result: ResultItem) => void;
  onToggleNotInterested: (postId: string) => void;
  onPrevious: () => void;
  onNext: () => void;
}) {
  return (
    <aside className="flex min-h-[360px] flex-col overflow-hidden border border-stone-300 bg-[#fbfaf7] lg:sticky lg:top-3 lg:h-[calc(100vh-1.5rem)] lg:min-h-0">
      <div className="shrink-0 border-b border-stone-300 p-2">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-500" />
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Search posts and replies"
            className="h-9 w-full rounded-md border border-stone-300 bg-white pl-9 pr-9 text-sm text-stone-900 outline-none transition placeholder:text-stone-500 focus:border-emerald-600 focus:ring-2 focus:ring-emerald-200"
          />
          {query ? (
            <button
              type="button"
              onClick={() => onQueryChange("")}
              className="absolute right-2 top-1/2 inline-flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md text-stone-500 hover:bg-stone-100 hover:text-stone-900"
              title="Clear search"
            >
              <X className="h-4 w-4" />
            </button>
          ) : null}
        </div>
      </div>
      <ResultList
        results={results?.items ?? []}
        loading={loading}
        refreshing={refreshing}
        selectedResultKey={selectedResultKey}
        notInterestedPostIds={notInterestedPostIds}
        onSelect={onSelect}
        onToggleNotInterested={onToggleNotInterested}
      />
      <Pagination
        results={results}
        canGoBack={canGoBack}
        canGoForward={canGoForward}
        onPrevious={onPrevious}
        onNext={onNext}
      />
    </aside>
  );
}

export { PAGE_SIZE };
