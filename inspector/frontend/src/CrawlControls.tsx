import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Loader2,
  RefreshCcw,
  Square
} from "lucide-react";
import {
  type FocusEvent,
  type FormEvent,
  type KeyboardEvent,
  useEffect,
  useRef,
  useState
} from "react";

import { formatNumber } from "./format";
import type { CrawlState, CrawlStatusResponse } from "./types";

const MIN_PAGES = 1;
const MAX_PAGES = 600;

const STATE_LABELS: Record<CrawlState, string> = {
  idle: "Idle",
  running: "Crawling",
  stopping: "Stopping",
  succeeded: "Complete",
  failed: "Failed",
  stopped: "Stopped"
};

function count(status: CrawlStatusResponse | null, recordType: string, state: string): number {
  return status?.progress?.frontier[recordType]?.[state] ?? 0;
}

function activeCount(status: CrawlStatusResponse | null): number {
  return count(status, "post", "in_progress") + count(status, "reply", "in_progress");
}

function pendingCount(status: CrawlStatusResponse | null): number {
  return count(status, "post", "pending") + count(status, "reply", "pending");
}

function failedCount(status: CrawlStatusResponse | null): number {
  return count(status, "post", "failed") + count(status, "reply", "failed");
}

function suppressedCount(status: CrawlStatusResponse | null): number {
  return count(status, "post", "suppressed") + count(status, "reply", "suppressed");
}

function elapsedLabel(seconds: number | null): string {
  if (seconds === null) {
    return "-";
  }
  if (seconds < 60) {
    return `${Math.floor(seconds)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.floor(seconds % 60);
  return `${minutes}m ${remainder}s`;
}

function stateClass(state: CrawlState): string {
  if (state === "running") {
    return "border-emerald-300 bg-emerald-50 text-emerald-900";
  }
  if (state === "stopping") {
    return "border-amber-300 bg-amber-50 text-amber-950";
  }
  if (state === "failed") {
    return "border-red-300 bg-red-50 text-red-900";
  }
  if (state === "succeeded") {
    return "border-emerald-200 bg-white text-emerald-900";
  }
  return "border-stone-300 bg-white text-stone-800";
}

function pillDetail(
  status: CrawlStatusResponse | null,
  pages: string,
  allPages: boolean
): string {
  const state = status?.state ?? "idle";
  if (state === "idle") {
    if (allPages) {
      return "All pages";
    }
    return `${pages || "5"} pages`;
  }
  if (state === "running") {
    return `${elapsedLabel(status?.elapsed_seconds ?? null)} · ${formatNumber(
      status?.progress?.saved_posts ?? 0
    )} posts`;
  }
  if (state === "stopping") {
    return "waiting for exit";
  }
  if (state === "failed") {
    return "details available";
  }
  return elapsedLabel(status?.elapsed_seconds ?? null);
}

function StatusIcon({ state }: { state: CrawlState }) {
  if (state === "running" || state === "stopping") {
    return <Loader2 className="h-4 w-4 animate-spin" />;
  }
  if (state === "succeeded") {
    return <CheckCircle2 className="h-4 w-4" />;
  }
  if (state === "failed") {
    return <AlertCircle className="h-4 w-4" />;
  }
  if (state === "stopped") {
    return <Clock3 className="h-4 w-4" />;
  }
  return <RefreshCcw className="h-4 w-4" />;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-medium uppercase text-stone-500">{label}</dt>
      <dd className="mt-0.5 truncate text-sm font-semibold text-stone-950">{value}</dd>
    </div>
  );
}

export function CrawlControls({
  status,
  error,
  actionLoading,
  onStart,
  onStop
}: {
  status: CrawlStatusResponse | null;
  error: string | null;
  actionLoading: boolean;
  onStart: (pages: number, allPages: boolean) => void;
  onStop: () => void;
}) {
  const [pages, setPages] = useState("5");
  const [allPages, setAllPages] = useState(false);
  const [open, setOpen] = useState(false);
  const [hoverOpen, setHoverOpen] = useState(false);
  const [focusOpen, setFocusOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const closeTimerRef = useRef<number | null>(null);
  const parsedPages = Number.parseInt(pages, 10);
  const pagesValid =
    Number.isInteger(parsedPages) && parsedPages >= MIN_PAGES && parsedPages <= MAX_PAGES;
  const state = status?.state ?? "idle";
  const active = state === "running" || state === "stopping";
  const hasError = Boolean(error) || state === "failed";
  const displayState: CrawlState = hasError && state === "idle" ? "failed" : state;
  const requestedPages = status?.pages ?? (pagesValid ? parsedPages : 5);
  const statusAllPages = status && status.state !== "idle" ? status.all_pages : null;
  const requestedAllPages = statusAllPages ?? allPages;
  const popoverOpen = open || hoverOpen || focusOpen;

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if ((!allPages && !pagesValid) || active || actionLoading) {
      return;
    }
    onStart(pagesValid ? parsedPages : 5, allPages);
  };

  useEffect(() => {
    const closeOnOutsidePointer = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
        setHoverOpen(false);
        setFocusOpen(false);
      }
    };
    document.addEventListener("pointerdown", closeOnOutsidePointer);
    return () => document.removeEventListener("pointerdown", closeOnOutsidePointer);
  }, []);

  useEffect(() => {
    return () => {
      if (closeTimerRef.current !== null) {
        window.clearTimeout(closeTimerRef.current);
      }
    };
  }, []);

  const clearCloseTimer = () => {
    if (closeTimerRef.current !== null) {
      window.clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  };

  const openFromPointer = () => {
    clearCloseTimer();
    setHoverOpen(true);
  };

  const closeFromPointer = () => {
    clearCloseTimer();
    closeTimerRef.current = window.setTimeout(() => {
      setHoverOpen(false);
      closeTimerRef.current = null;
    }, 120);
  };

  const updateFocusOpen = (event: FocusEvent<HTMLDivElement>) => {
    if (!rootRef.current?.contains(event.relatedTarget as Node | null)) {
      setFocusOpen(false);
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Escape") {
      return;
    }
    setOpen(false);
    setHoverOpen(false);
    setFocusOpen(false);
  };

  return (
    <div
      ref={rootRef}
      className="relative z-30 flex justify-start lg:justify-end"
      onBlur={updateFocusOpen}
      onFocus={() => setFocusOpen(true)}
      onKeyDown={handleKeyDown}
      onPointerEnter={openFromPointer}
      onPointerLeave={closeFromPointer}
    >
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className={`inline-flex h-10 min-w-[178px] items-center justify-between gap-3 rounded-md border px-3 text-left shadow-sm transition hover:bg-stone-50 focus:outline-none focus:ring-2 focus:ring-emerald-600 ${stateClass(
          displayState
        )}`}
        aria-expanded={popoverOpen}
        aria-haspopup="dialog"
        title="Crawl refresh"
      >
        <span className="flex min-w-0 items-center gap-2">
          <StatusIcon state={displayState} />
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold">
              {STATE_LABELS[displayState]}
            </span>
            <span className="block truncate text-xs opacity-75">
              {pillDetail(status, pages, requestedAllPages)}
            </span>
          </span>
        </span>
        <ChevronDown className="h-4 w-4 shrink-0 opacity-60" />
      </button>

      <div
        className={`absolute right-0 top-full w-[calc(100vw-2rem)] max-w-[390px] pt-2 ${
          popoverOpen ? "block" : "hidden"
        }`}
      >
        <div
          role="dialog"
          className="border border-stone-300 bg-[#fbfaf7] p-3 text-stone-900 shadow-lg"
        >
          <form className="flex flex-col gap-2" onSubmit={submit}>
            <label className="flex min-h-9 items-center gap-2 text-sm font-medium text-stone-800">
              <input
                type="checkbox"
                checked={allPages}
                disabled={active || actionLoading}
                onChange={(event) => setAllPages(event.target.checked)}
                className="h-4 w-4 rounded border-stone-300 text-emerald-700 focus:ring-emerald-600 disabled:cursor-not-allowed disabled:opacity-60"
              />
              <span>All pages</span>
            </label>
            <div className="flex items-end gap-2">
              <label className="min-w-0 flex-1 text-xs font-medium uppercase text-stone-500">
                <span className="mb-1 block">Pages</span>
                <input
                  type="number"
                  min={MIN_PAGES}
                  max={MAX_PAGES}
                  value={pages}
                  disabled={allPages || active || actionLoading}
                  onChange={(event) => setPages(event.target.value)}
                  className="h-9 w-full rounded-md border border-stone-300 bg-white px-2 text-sm font-normal text-stone-900 outline-none transition focus:border-emerald-600 focus:ring-2 focus:ring-emerald-200 disabled:cursor-not-allowed disabled:opacity-60"
                />
              </label>
              <button
                type="submit"
                disabled={(!allPages && !pagesValid) || active || actionLoading}
                className="inline-flex h-9 shrink-0 items-center justify-center gap-2 rounded-md border border-stone-300 bg-white px-3 text-sm font-medium text-stone-800 transition hover:bg-stone-50 focus:outline-none focus:ring-2 focus:ring-emerald-600 disabled:cursor-not-allowed disabled:opacity-50"
                title="Start crawl refresh"
              >
                <RefreshCcw className="h-4 w-4" />
                Refresh
              </button>
            </div>
          </form>

          {(state === "running" || state === "stopping") && (
            <button
              type="button"
              onClick={onStop}
              disabled={state !== "running" || actionLoading}
              className="mt-2 inline-flex h-9 w-full items-center justify-center gap-2 rounded-md border border-red-300 bg-white px-3 text-sm font-medium text-red-800 transition hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:cursor-not-allowed disabled:opacity-50"
              title="Stop crawl"
            >
              <Square className="h-4 w-4" />
              {state === "stopping" ? "Stopping" : "Stop"}
            </button>
          )}

          <dl className="mt-3 grid grid-cols-2 gap-x-5 gap-y-2 border-t border-stone-200 pt-3">
            <Metric label="Status" value={STATE_LABELS[state]} />
            <Metric
              label="Requested"
              value={requestedAllPages ? "All pages" : formatNumber(requestedPages)}
            />
            <Metric label="Elapsed" value={elapsedLabel(status?.elapsed_seconds ?? null)} />
            <Metric
              label="Saved"
              value={`${formatNumber(status?.progress?.saved_posts ?? 0)} posts`}
            />
            <Metric
              label="Replies"
              value={formatNumber(status?.progress?.saved_replies ?? 0)}
            />
            <Metric label="Pending" value={formatNumber(pendingCount(status))} />
            <Metric label="Active" value={formatNumber(activeCount(status))} />
            <Metric label="Failed" value={formatNumber(failedCount(status))} />
            <Metric label="Suppressed" value={formatNumber(suppressedCount(status))} />
          </dl>

          {error ? (
            <div className="mt-3 border-t border-red-200 pt-2 text-sm text-red-800">{error}</div>
          ) : null}
          {status?.error ? (
            <div className="mt-3 border-t border-red-200 pt-2 text-sm text-red-800">
              {status.error}
            </div>
          ) : null}
          {status?.stderr_tail && state === "failed" ? (
            <pre className="mt-2 max-h-28 overflow-auto whitespace-pre-wrap bg-stone-100 p-2 text-[11px] leading-4 text-stone-700">
              {status.stderr_tail}
            </pre>
          ) : null}
        </div>
      </div>
    </div>
  );
}
