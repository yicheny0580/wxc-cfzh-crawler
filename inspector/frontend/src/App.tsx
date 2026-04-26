import { Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { getAuthors, getHealth, getPost, getResults, getSummary } from "./api";
import { CrawlControls } from "./CrawlControls";
import { FilterPanel } from "./FilterPanel";
import { PAGE_SIZE, Pagination, ResultList } from "./Results";
import { ReaderPane, type FocusRequest } from "./Reader";
import { ErrorBanner, SummaryStrip } from "./Summary";
import { resultKey } from "./format";
import {
  DEFAULT_RESULT_TYPE_FILTER,
  readResultTypeFilterPreference,
  type ResultTypeFilterPreference,
  writeResultTypeFilterPreference
} from "./resultTypePreference";
import {
  EMPTY_PUBLISHED_TIME_FILTER,
  publishedTimeRange,
  type PublishedTimeFilter
} from "./timeFilter";
import { useCrawlStatus } from "./useCrawlStatus";
import type {
  AuthorSummary,
  HealthResponse,
  PostDetail,
  ResultItem,
  ResultListResponse,
  SummaryResponse
} from "./types";

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [authors, setAuthors] = useState<AuthorSummary[]>([]);
  const [results, setResults] = useState<ResultListResponse | null>(null);
  const [selectedResultKey, setSelectedResultKey] = useState<string | null>(null);
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);
  const [selectedPost, setSelectedPost] = useState<PostDetail | null>(null);
  const [focusRequest, setFocusRequest] = useState<FocusRequest>({
    id: 0,
    postId: null,
    replyId: null
  });
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [author, setAuthor] = useState("");
  const [resultTypeFilter, setResultTypeFilter] = useState<ResultTypeFilterPreference>(
    readResultTypeFilterPreference
  );
  const [publishedTimeFilter, setPublishedTimeFilter] = useState<PublishedTimeFilter>(
    EMPTY_PUBLISHED_TIME_FILTER
  );
  const [offset, setOffset] = useState(0);
  const [reloadToken, setReloadToken] = useState(0);
  const [bootLoading, setBootLoading] = useState(true);
  const [refreshingAfterCrawl, setRefreshingAfterCrawl] = useState(false);
  const [overviewRefreshingAfterCrawl, setOverviewRefreshingAfterCrawl] = useState(false);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const refreshingAfterCrawlRef = useRef(false);
  const selectedPostRef = useRef<PostDetail | null>(null);
  selectedPostRef.current = selectedPost;

  const { includePosts, includeReplies } = resultTypeFilter;
  const { publishedFrom, publishedTo } = publishedTimeRange(publishedTimeFilter);
  const hasResultScope = includePosts || includeReplies;
  const canGoBack = offset > 0;
  const canGoForward = results ? offset + results.limit < results.total : false;
  const showResultsLoading = resultsLoading && (!results || !refreshingAfterCrawl);
  const showDetailLoading =
    detailLoading &&
    (!selectedPost || !refreshingAfterCrawl || selectedPost.post_id !== selectedPostId);
  const {
    actionLoading: crawlActionLoading,
    error: crawlError,
    start: handleStartCrawl,
    status: crawlStatus,
    stop: handleStopCrawl
  } = useCrawlStatus(refreshAfterCrawl);

  async function refreshOverview() {
    setError(null);
    const [healthPayload, summaryPayload, authorsPayload] = await Promise.all([
      getHealth(),
      getSummary(),
      getAuthors()
    ]);
    setHealth(healthPayload);
    setSummary(summaryPayload);
    setAuthors(authorsPayload);
  }

  useEffect(() => {
    let active = true;
    refreshOverview()
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load inspector data.");
        }
      })
      .finally(() => {
        if (active) {
          setBootLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setOffset(0);
      setDebouncedQuery(query);
    }, 250);
    return () => window.clearTimeout(handle);
  }, [query]);

  useEffect(() => {
    setOffset(0);
  }, [author, includePosts, includeReplies, publishedFrom, publishedTo]);

  useEffect(() => {
    writeResultTypeFilterPreference(resultTypeFilter);
  }, [resultTypeFilter]);

  useEffect(() => {
    let active = true;
    setResultsLoading(true);
    setError(null);
    const preserveCurrentResults = refreshingAfterCrawlRef.current;

    if (!hasResultScope) {
      setResults({ items: [], total: 0, limit: PAGE_SIZE, offset });
      setResultsLoading(false);
      return () => {
        active = false;
      };
    }

    getResults({
      search: debouncedQuery,
      author,
      publishedFrom,
      publishedTo,
      includePosts,
      includeReplies,
      limit: PAGE_SIZE,
      offset
    })
      .then((payload) => {
        if (active) {
          setResults(payload);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load results.");
          if (!preserveCurrentResults) {
            setResults(null);
          }
        }
      })
      .finally(() => {
        if (active) {
          setResultsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [
    author,
    debouncedQuery,
    hasResultScope,
    includePosts,
    includeReplies,
    offset,
    publishedFrom,
    publishedTo,
    reloadToken
  ]);

  useEffect(() => {
    if (!results) {
      return;
    }

    if (results.items.length === 0) {
      setSelectedResultKey(null);
      setSelectedPostId(null);
      setSelectedPost(null);
      return;
    }

    if (!selectedResultKey || !results.items.some((item) => resultKey(item) === selectedResultKey)) {
      const first = results.items[0];
      setSelectedResultKey(resultKey(first));
      setSelectedPostId(first.root_post_id);
    }
  }, [results, selectedResultKey]);

  useEffect(() => {
    if (!selectedPostId) {
      return;
    }

    let active = true;
    setDetailLoading(true);
    setDetailError(null);
    const preserveCurrentPost =
      refreshingAfterCrawlRef.current && selectedPostRef.current?.post_id === selectedPostId;
    getPost(selectedPostId)
      .then((payload) => {
        if (active) {
          setSelectedPost(payload);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setDetailError(err instanceof Error ? err.message : "Failed to load post.");
          if (!preserveCurrentPost) {
            setSelectedPost(null);
          }
        }
      })
      .finally(() => {
        if (active) {
          setDetailLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [selectedPostId, reloadToken]);

  const selectResult = (result: ResultItem) => {
    const replyId = result.record_type === "reply" ? result.reply_id : null;
    setSelectedResultKey(resultKey(result));
    setSelectedPostId(result.root_post_id);
    setFocusRequest((current) => ({
      id: current.id + 1,
      postId: result.root_post_id,
      replyId
    }));
  };

  const updateResultTypeFilter = (nextFilter: ResultTypeFilterPreference) => {
    setResultTypeFilter((current) =>
      nextFilter.includePosts || nextFilter.includeReplies ? nextFilter : current
    );
  };

  const clearFilters = () => {
    setAuthor("");
    setResultTypeFilter(DEFAULT_RESULT_TYPE_FILTER);
    setPublishedTimeFilter(EMPTY_PUBLISHED_TIME_FILTER);
  };

  function refreshAfterCrawl() {
    refreshingAfterCrawlRef.current = true;
    setRefreshingAfterCrawl(true);
    setOverviewRefreshingAfterCrawl(true);
    refreshOverview()
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to refresh inspector data.");
      })
      .finally(() => setOverviewRefreshingAfterCrawl(false));
    setReloadToken((current) => current + 1);
  }

  useEffect(() => {
    if (
      refreshingAfterCrawl &&
      !overviewRefreshingAfterCrawl &&
      !resultsLoading &&
      !detailLoading
    ) {
      refreshingAfterCrawlRef.current = false;
      setRefreshingAfterCrawl(false);
    }
  }, [detailLoading, overviewRefreshingAfterCrawl, refreshingAfterCrawl, resultsLoading]);

  return (
    <div className="min-h-screen bg-[#f6f3ed] text-stone-900">
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
            <CrawlControls
              status={crawlStatus}
              error={crawlError}
              actionLoading={crawlActionLoading}
              onStart={handleStartCrawl}
              onStop={handleStopCrawl}
            />
          </div>
          {error ? <ErrorBanner message={error} /> : null}
        </div>
      </header>

      <FilterPanel
        authors={authors}
        author={author}
        onAuthorChange={setAuthor}
        resultTypeFilter={resultTypeFilter}
        onResultTypeFilterChange={updateResultTypeFilter}
        publishedTimeFilter={publishedTimeFilter}
        onPublishedTimeFilterChange={setPublishedTimeFilter}
        onClearFilters={clearFilters}
      />

      <main className="mx-auto grid w-full max-w-[1800px] gap-3 px-3 py-3 sm:px-4 lg:grid-cols-[360px_minmax(0,1fr)] lg:items-start lg:px-6">
        <aside className="flex min-h-[360px] flex-col overflow-hidden border border-stone-300 bg-[#fbfaf7] lg:sticky lg:top-3 lg:h-[calc(100vh-1.5rem)] lg:min-h-0">
          <div className="shrink-0 border-b border-stone-300 p-2">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-500" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search posts and replies"
                className="h-9 w-full rounded-md border border-stone-300 bg-white pl-9 pr-9 text-sm text-stone-900 outline-none transition placeholder:text-stone-500 focus:border-emerald-600 focus:ring-2 focus:ring-emerald-200"
              />
              {query ? (
                <button
                  type="button"
                  onClick={() => setQuery("")}
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
            loading={showResultsLoading}
            refreshing={refreshingAfterCrawl && resultsLoading && Boolean(results)}
            selectedResultKey={selectedResultKey}
            onSelect={selectResult}
          />
          <Pagination
            results={results}
            canGoBack={canGoBack}
            canGoForward={canGoForward}
            onPrevious={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            onNext={() => setOffset(offset + PAGE_SIZE)}
          />
        </aside>

        <section className="min-w-0 border border-stone-300 bg-[#fbfaf7]">
          <ReaderPane
            post={selectedPost}
            focusRequest={focusRequest}
            loading={showDetailLoading}
            refreshing={refreshingAfterCrawl && detailLoading && Boolean(selectedPost)}
            error={detailError}
            empty={!selectedPostId && !resultsLoading}
          />
        </section>
      </main>
    </div>
  );
}

export default App;
