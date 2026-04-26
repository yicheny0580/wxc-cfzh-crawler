import {
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  RefreshCcw,
  Search,
  X
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { getAuthors, getHealth, getPost, getPosts, getSummary } from "./api";
import { sanitizeBodyHtml } from "./bodyHtml";
import type {
  AuthorSummary,
  HealthResponse,
  PostDetail,
  PostListItem,
  PostListResponse,
  ReplyDetail,
  SummaryResponse
} from "./types";

const PAGE_SIZE = 25;

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "-";
  }
  return new Intl.NumberFormat().format(value);
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function displayTitle(post: Pick<PostListItem | PostDetail, "post_id" | "title">): string {
  return post.title?.trim() || `Post ${post.post_id}`;
}

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [authors, setAuthors] = useState<AuthorSummary[]>([]);
  const [posts, setPosts] = useState<PostListResponse | null>(null);
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);
  const [selectedPost, setSelectedPost] = useState<PostDetail | null>(null);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [author, setAuthor] = useState("");
  const [offset, setOffset] = useState(0);
  const [bootLoading, setBootLoading] = useState(true);
  const [postsLoading, setPostsLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  const rootAuthors = useMemo(() => authors.filter((item) => item.posts > 0), [authors]);
  const canGoBack = offset > 0;
  const canGoForward = posts ? offset + posts.limit < posts.total : false;

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
  }, [author]);

  useEffect(() => {
    let active = true;
    setPostsLoading(true);
    setError(null);

    getPosts({
      search: debouncedQuery,
      author,
      limit: PAGE_SIZE,
      offset
    })
      .then((payload) => {
        if (active) {
          setPosts(payload);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load posts.");
          setPosts(null);
        }
      })
      .finally(() => {
        if (active) {
          setPostsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [author, debouncedQuery, offset]);

  useEffect(() => {
    if (!posts) {
      return;
    }

    if (posts.items.length === 0) {
      setSelectedPostId(null);
      setSelectedPost(null);
      return;
    }

    if (!selectedPostId || !posts.items.some((post) => post.post_id === selectedPostId)) {
      setSelectedPostId(posts.items[0].post_id);
    }
  }, [posts, selectedPostId]);

  useEffect(() => {
    if (!selectedPostId) {
      return;
    }

    let active = true;
    setDetailLoading(true);
    setDetailError(null);
    getPost(selectedPostId)
      .then((payload) => {
        if (active) {
          setSelectedPost(payload);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setDetailError(err instanceof Error ? err.message : "Failed to load post.");
          setSelectedPost(null);
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
  }, [selectedPostId]);

  const reloadAll = () => {
    setBootLoading(true);
    refreshOverview()
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to refresh inspector data.");
      })
      .finally(() => setBootLoading(false));
    setOffset(0);
  };

  return (
    <div className="min-h-screen bg-[#f6f3ed] text-stone-900">
      <header className="border-b border-stone-300 bg-[#fbfaf7]">
        <div className="mx-auto flex max-w-[1600px] flex-col gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-stone-950">CFZH Inspector</h1>
              <p className="mt-1 max-w-full truncate text-sm text-stone-600">
                {health?.db_path || summary?.db_path || "SQLite database"}
              </p>
            </div>
            <button
              type="button"
              onClick={reloadAll}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-stone-300 bg-white px-3 text-sm font-medium text-stone-800 shadow-sm transition hover:bg-stone-50 focus:outline-none focus:ring-2 focus:ring-emerald-600"
              title="Refresh"
            >
              <RefreshCcw className="h-4 w-4" />
              Refresh
            </button>
          </div>
          <SummaryStrip summary={summary} loading={bootLoading} />
          {error ? <ErrorBanner message={error} /> : null}
        </div>
      </header>

      <main className="mx-auto grid max-w-[1600px] gap-4 px-4 py-4 sm:px-6 lg:grid-cols-[390px_minmax(0,1fr)] lg:px-8">
        <aside className="min-h-[calc(100vh-220px)] border border-stone-300 bg-[#fbfaf7]">
          <div className="border-b border-stone-300 p-3">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-500" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search posts"
                className="h-10 w-full rounded-md border border-stone-300 bg-white pl-9 pr-9 text-sm text-stone-900 outline-none transition placeholder:text-stone-500 focus:border-emerald-600 focus:ring-2 focus:ring-emerald-200"
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
            <select
              value={author}
              onChange={(event) => setAuthor(event.target.value)}
              className="mt-3 h-10 w-full rounded-md border border-stone-300 bg-white px-3 text-sm text-stone-900 outline-none transition focus:border-emerald-600 focus:ring-2 focus:ring-emerald-200"
            >
              <option value="">All authors</option>
              {rootAuthors.map((item) => (
                <option key={item.name} value={item.name}>
                  {item.name} ({item.posts})
                </option>
              ))}
            </select>
          </div>
          <PostList
            posts={posts?.items ?? []}
            loading={postsLoading}
            selectedPostId={selectedPostId}
            onSelect={setSelectedPostId}
          />
          <Pagination
            posts={posts}
            canGoBack={canGoBack}
            canGoForward={canGoForward}
            onPrevious={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            onNext={() => setOffset(offset + PAGE_SIZE)}
          />
        </aside>

        <section className="min-h-[calc(100vh-220px)] border border-stone-300 bg-[#fbfaf7]">
          <ReaderPane
            post={selectedPost}
            loading={detailLoading}
            error={detailError}
            empty={!selectedPostId && !postsLoading}
          />
        </section>
      </main>
    </div>
  );
}

function SummaryStrip({
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
    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
      {items.map(([label, value]) => (
        <div key={label} className="border border-stone-300 bg-white px-3 py-2">
          <div className="text-xs font-medium uppercase text-stone-500">{label}</div>
          <div className="mt-1 text-lg font-semibold text-stone-950">
            {loading && value === "-" ? "..." : value}
          </div>
        </div>
      ))}
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-900">
      {message}
    </div>
  );
}

function PostList({
  posts,
  loading,
  selectedPostId,
  onSelect
}: {
  posts: PostListItem[];
  loading: boolean;
  selectedPostId: string | null;
  onSelect: (postId: string) => void;
}) {
  if (loading) {
    return <StateBlock text="Loading posts..." />;
  }

  if (posts.length === 0) {
    return <StateBlock text="No posts found." />;
  }

  return (
    <div className="scrollbar-stable max-h-[calc(100vh-384px)] overflow-y-auto">
      {posts.map((post) => {
        const selected = post.post_id === selectedPostId;
        return (
          <button
            key={post.post_id}
            type="button"
            onClick={() => onSelect(post.post_id)}
            className={`block w-full border-b border-stone-200 px-3 py-3 text-left transition focus:outline-none focus:ring-2 focus:ring-inset focus:ring-emerald-600 ${
              selected ? "bg-emerald-50" : "bg-white hover:bg-stone-50"
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <h2 className="min-w-0 flex-1 text-sm font-semibold leading-5 text-stone-950">
                {displayTitle(post)}
              </h2>
              <span className="shrink-0 rounded-sm bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-900">
                {formatNumber(post.actual_reply_count)}
              </span>
            </div>
            <div className="mt-1 flex flex-wrap gap-x-2 gap-y-1 text-xs text-stone-600">
              <span>{post.author || "Unknown"}</span>
              <span>{formatDate(post.published_at)}</span>
              <span>{formatNumber(post.read_count)} reads</span>
            </div>
            {post.excerpt ? (
              <p className="mt-2 max-h-10 overflow-hidden text-sm leading-5 text-stone-700">
                {post.excerpt}
              </p>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

function Pagination({
  posts,
  canGoBack,
  canGoForward,
  onPrevious,
  onNext
}: {
  posts: PostListResponse | null;
  canGoBack: boolean;
  canGoForward: boolean;
  onPrevious: () => void;
  onNext: () => void;
}) {
  const start = posts && posts.total > 0 ? posts.offset + 1 : 0;
  const end = posts ? Math.min(posts.offset + posts.limit, posts.total) : 0;

  return (
    <div className="flex items-center justify-between border-t border-stone-300 bg-[#fbfaf7] px-3 py-3">
      <div className="text-sm text-stone-600">
        {formatNumber(start)}-{formatNumber(end)} of {formatNumber(posts?.total ?? 0)}
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

function ReaderPane({
  post,
  loading,
  error,
  empty
}: {
  post: PostDetail | null;
  loading: boolean;
  error: string | null;
  empty: boolean;
}) {
  if (loading) {
    return <StateBlock text="Loading post..." />;
  }

  if (error) {
    return <StateBlock text={error} />;
  }

  if (empty || !post) {
    return <StateBlock text="Select a post." />;
  }

  return (
    <article className="scrollbar-stable max-h-[calc(100vh-220px)] overflow-y-auto">
      <div className="border-b border-stone-300 bg-white px-4 py-4 sm:px-6">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <h2 className="text-xl font-semibold leading-7 text-stone-950 sm:text-2xl">
              {displayTitle(post)}
            </h2>
            <MetaLine post={post} />
          </div>
          <a
            href={post.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex h-9 shrink-0 items-center justify-center gap-2 rounded-md border border-stone-300 bg-[#fffdf8] px-3 text-sm font-medium text-stone-800 transition hover:bg-stone-50 focus:outline-none focus:ring-2 focus:ring-emerald-600"
          >
            <ExternalLink className="h-4 w-4" />
            Open
          </a>
        </div>
      </div>

      <div className="px-4 py-5 sm:px-6">
        <BodyContent
          html={post.body_html}
          text={post.body_text}
          className="text-base leading-7 text-stone-900"
        />
      </div>

      <div className="border-t border-stone-300 px-4 py-4 sm:px-6">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h3 className="text-base font-semibold text-stone-950">Replies</h3>
          <span className="rounded-sm bg-amber-100 px-2 py-1 text-xs font-medium text-amber-900">
            {formatNumber(post.actual_reply_count)}
          </span>
        </div>
        {post.replies.length > 0 ? (
          <div className="space-y-3">
            {post.replies.map((reply) => (
              <ReplyNode key={reply.reply_id} reply={reply} />
            ))}
          </div>
        ) : (
          <div className="border border-stone-300 bg-white px-3 py-6 text-center text-sm text-stone-600">
            No replies.
          </div>
        )}
      </div>
    </article>
  );
}

function MetaLine({ post }: { post: PostDetail | PostListItem }) {
  return (
    <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-sm text-stone-600">
      <span>{post.author || "Unknown author"}</span>
      <span>{formatDate(post.published_at)}</span>
      <span>{formatNumber(post.read_count)} reads</span>
      <span>{formatNumber(post.actual_reply_count)} replies</span>
      <span>#{post.post_id}</span>
    </div>
  );
}

function ReplyNode({ reply }: { reply: ReplyDetail }) {
  return (
    <div className="border-l-2 border-emerald-700 bg-white pl-3">
      <div className="border border-stone-200 px-3 py-3">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
            <span className="font-semibold text-stone-950">{reply.author || "Unknown"}</span>
            <span className="text-stone-500">{formatDate(reply.published_at)}</span>
            <span className="text-stone-500">#{reply.reply_id}</span>
          </div>
          <a
            href={reply.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex h-7 w-7 items-center justify-center rounded-md text-stone-500 hover:bg-stone-100 hover:text-stone-900"
            title="Open reply"
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        </div>
        {reply.title ? (
          <div className="mt-2 text-sm font-medium text-stone-800">{reply.title}</div>
        ) : null}
        {reply.body_html || reply.body_text ? (
          <BodyContent
            html={reply.body_html}
            text={reply.body_text}
            className="mt-2 text-sm leading-6 text-stone-800"
          />
        ) : !reply.title ? (
          <div className="mt-2 text-sm text-stone-500">No body text.</div>
        ) : null}
      </div>
      {reply.replies.length > 0 ? (
        <div className="mt-3 space-y-3 pl-3">
          {reply.replies.map((child) => (
            <ReplyNode key={child.reply_id} reply={child} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function BodyContent({
  html,
  text,
  className = ""
}: {
  html: string | null;
  text: string | null;
  className?: string;
}) {
  const sanitizedHtml = useMemo(() => sanitizeBodyHtml(html), [html]);
  const classes = `reader-body ${className}`.trim();

  if (sanitizedHtml) {
    return (
      <div
        className={`reader-body-html ${classes}`}
        dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
      />
    );
  }

  if (text) {
    return <div className={`whitespace-pre-wrap ${classes}`}>{text}</div>;
  }

  return <div className="text-sm text-stone-500">No body text.</div>;
}

function StateBlock({ text }: { text: string }) {
  return (
    <div className="flex min-h-52 items-center justify-center px-4 text-center text-sm text-stone-600">
      {text}
    </div>
  );
}

export default App;
