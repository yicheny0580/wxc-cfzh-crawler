import { CrawlControls } from "./CrawlControls";
import { PublicRefreshButton } from "./PublicRefreshButton";
import { ErrorBanner, SummaryStrip } from "./Summary";
import type { CrawlStatusResponse, HealthResponse, SummaryResponse } from "./types";

export function InspectorHeader({
  health,
  summary,
  bootLoading,
  publicMode,
  refreshingAfterCrawl,
  crawlStatus,
  crawlError,
  crawlActionLoading,
  error,
  onRefresh,
  onStartCrawl,
  onStopCrawl
}: {
  health: HealthResponse | null;
  summary: SummaryResponse | null;
  bootLoading: boolean;
  publicMode: boolean;
  refreshingAfterCrawl: boolean;
  crawlStatus: CrawlStatusResponse | null;
  crawlError: string | null;
  crawlActionLoading: boolean;
  error: string | null;
  onRefresh: () => void;
  onStartCrawl: (pages: number, allPages: boolean) => void;
  onStopCrawl: () => void;
}) {
  return (
    <header className="shrink-0 border-b border-stone-300 bg-[#fbfaf7]">
      <div className="mx-auto flex max-w-[1800px] flex-col gap-2 px-3 py-3 sm:px-4 lg:px-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
              <h1 className="text-xl font-semibold text-stone-950">CFZH Inspector</h1>
              <SummaryStrip summary={summary} loading={bootLoading} />
            </div>
            <p className="mt-1 max-w-full truncate text-sm text-stone-600">
              {health?.db_path || summary?.db_path || "SQLite database"}
            </p>
          </div>
          {health ? (
            publicMode ? (
              <PublicRefreshButton loading={refreshingAfterCrawl} onRefresh={onRefresh} />
            ) : (
              <CrawlControls
                status={crawlStatus}
                error={crawlError}
                actionLoading={crawlActionLoading}
                onStart={onStartCrawl}
                onStop={onStopCrawl}
              />
            )
          ) : null}
        </div>
        {error ? <ErrorBanner message={error} /> : null}
      </div>
    </header>
  );
}
