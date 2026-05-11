import { useEffect, useMemo, useRef, useState } from "react";

import { getAuthors, getHealth, getPost, getResults, getSummary } from "./api";
import { FilterPanel } from "./FilterPanel";
import { HideConfirmationDialog } from "./HideConfirmationDialog";
import { InspectorHeader } from "./InspectorHeader";
import { ResizableInspectorLayout } from "./ResizableInspectorLayout";
import { PAGE_SIZE, ResultSidebar } from "./ResultSidebar";
import { ReaderPane, type FocusRequest } from "./Reader";
import { resultKey } from "./format";
import {
  DEFAULT_INTEREST_FILTER,
  readNotInterestedPostIds,
  resultsVisibleForInterest,
  type InterestFilterPreference,
  writeNotInterestedPostIds
} from "./notInterestedPosts";
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
  const [interestFilter, setInterestFilter] =
    useState<InterestFilterPreference>(DEFAULT_INTEREST_FILTER);
  const [notInterestedPostIds, setNotInterestedPostIds] =
    useState<Set<string>>(readNotInterestedPostIds);
  const [pendingHidePostId, setPendingHidePostId] = useState<string | null>(null);
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
  const publicMode = health?.public_mode ?? false;
  const { publishedFrom, publishedTo } = publishedTimeRange(publishedTimeFilter);
  const notInterestedPostIdList = useMemo(
    () => Array.from(notInterestedPostIds).sort(),
    [notInterestedPostIds]
  );
  const displayResults = useMemo(
    () => resultsVisibleForInterest(results, interestFilter, notInterestedPostIds),
    [interestFilter, notInterestedPostIds, results]
  );
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
  } = useCrawlStatus(refreshAfterCrawl, Boolean(health && !health.public_mode));

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
  }, [author, includePosts, includeReplies, interestFilter, notInterestedPostIdList, publishedFrom, publishedTo]);

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
      excludeRootPostIds: interestFilter === "focus" ? notInterestedPostIdList : undefined,
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
    interestFilter,
    notInterestedPostIdList,
    offset,
    publishedFrom,
    publishedTo,
    reloadToken
  ]);

  useEffect(() => {
    if (!displayResults) {
      return;
    }

    if (displayResults.items.length === 0) {
      setSelectedResultKey(null);
      setSelectedPostId(null);
      setSelectedPost(null);
      return;
    }

    if (
      !selectedResultKey ||
      !displayResults.items.some((item) => resultKey(item) === selectedResultKey)
    ) {
      const first = displayResults.items[0];
      setSelectedResultKey(resultKey(first));
      setSelectedPostId(first.root_post_id);
    }
  }, [displayResults, selectedResultKey]);

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

  const applyNotInterestedPostState = (postId: string, hidden: boolean) => {
    setNotInterestedPostIds((current) => {
      const next = new Set(current);
      if (hidden) {
        next.add(postId);
      } else {
        next.delete(postId);
      }
      if (next.size === current.size && next.has(postId) === current.has(postId)) {
        return current;
      }
      writeNotInterestedPostIds(next);
      return next;
    });
  };

  const requestNotInterestedPostState = (postId: string, hidden: boolean) => {
    if (hidden && !notInterestedPostIds.has(postId)) {
      setPendingHidePostId(postId);
      return;
    }

    applyNotInterestedPostState(postId, hidden);
  };

  const confirmPendingHide = () => {
    if (!pendingHidePostId) {
      return;
    }

    applyNotInterestedPostState(pendingHidePostId, true);
    setPendingHidePostId(null);
  };

  const clearFilters = () => {
    setAuthor("");
    setInterestFilter(DEFAULT_INTEREST_FILTER);
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
      <InspectorHeader
        health={health}
        summary={summary}
        bootLoading={bootLoading}
        publicMode={publicMode}
        refreshingAfterCrawl={refreshingAfterCrawl}
        crawlStatus={crawlStatus}
        crawlError={crawlError}
        crawlActionLoading={crawlActionLoading}
        error={error}
        onRefresh={refreshAfterCrawl}
        onStartCrawl={handleStartCrawl}
        onStopCrawl={handleStopCrawl}
      />

      <FilterPanel
        authors={authors}
        author={author}
        onAuthorChange={setAuthor}
        resultTypeFilter={resultTypeFilter}
        onResultTypeFilterChange={updateResultTypeFilter}
        interestFilter={interestFilter}
        onInterestFilterChange={setInterestFilter}
        publishedTimeFilter={publishedTimeFilter}
        onPublishedTimeFilterChange={setPublishedTimeFilter}
        onClearFilters={clearFilters}
      />

      <ResizableInspectorLayout
        resultsPane={
          <ResultSidebar
            query={query}
            results={displayResults}
            loading={showResultsLoading}
            refreshing={refreshingAfterCrawl && resultsLoading && Boolean(results)}
            selectedResultKey={selectedResultKey}
            canGoBack={canGoBack}
            canGoForward={canGoForward}
            notInterestedPostIds={notInterestedPostIds}
            onQueryChange={setQuery}
            onSelect={selectResult}
            onNotInterestedChange={requestNotInterestedPostState}
            onPrevious={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            onNext={() => setOffset(offset + PAGE_SIZE)}
          />
        }
        readerPane={
          <section className="min-w-0 border border-stone-300 bg-[#fbfaf7]">
            <ReaderPane
              post={selectedPost}
              focusRequest={focusRequest}
              loading={showDetailLoading}
              refreshing={refreshingAfterCrawl && detailLoading && Boolean(selectedPost)}
              error={detailError}
              empty={!selectedPostId && !resultsLoading}
              notInterested={selectedPost ? notInterestedPostIds.has(selectedPost.post_id) : false}
              onNotInterestedChange={requestNotInterestedPostState}
            />
          </section>
        }
      />
      {pendingHidePostId ? (
        <HideConfirmationDialog
          onCancel={() => setPendingHidePostId(null)}
          onConfirm={confirmPendingHide}
        />
      ) : null}
    </div>
  );
}

export default App;
