import type {
  AuthorSummary,
  CrawlStatusResponse,
  HealthResponse,
  PostDetail,
  PostListResponse,
  ResultListResponse,
  SummaryResponse
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { Accept: "application/json" },
    ...init
  });

  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") {
        message = payload.detail;
      }
    } catch {
      // Keep the HTTP status text when the response is not JSON.
    }
    throw new Error(message);
  }

  return (await response.json()) as T;
}

function browserTimezone(): string | undefined {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || undefined;
  } catch {
    return undefined;
  }
}

function addPublishedFilterParams(
  params: URLSearchParams,
  query: { publishedFrom?: string; publishedTo?: string }
) {
  const publishedFrom = query.publishedFrom?.trim();
  const publishedTo = query.publishedTo?.trim();
  if (publishedFrom) {
    params.set("published_from", publishedFrom);
  }
  if (publishedTo) {
    params.set("published_to", publishedTo);
  }
  if (publishedFrom || publishedTo) {
    const timezone = browserTimezone();
    if (timezone) {
      params.set("published_timezone", timezone);
    }
  }
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export function getCrawlStatus(): Promise<CrawlStatusResponse> {
  return request<CrawlStatusResponse>("/api/crawl/status");
}

export function startCrawl(pages: number): Promise<CrawlStatusResponse> {
  return request<CrawlStatusResponse>("/api/crawl", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ pages })
  });
}

export function stopCrawl(): Promise<CrawlStatusResponse> {
  return request<CrawlStatusResponse>("/api/crawl/stop", {
    method: "POST",
    headers: { Accept: "application/json" }
  });
}

export function crawlWebSocketUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/api/crawl/ws`;
}

export function getSummary(): Promise<SummaryResponse> {
  return request<SummaryResponse>("/api/summary");
}

export function getAuthors(): Promise<AuthorSummary[]> {
  return request<AuthorSummary[]>("/api/authors");
}

export interface PostQuery {
  search?: string;
  author?: string;
  publishedFrom?: string;
  publishedTo?: string;
  limit: number;
  offset: number;
}

export function getPosts(query: PostQuery): Promise<PostListResponse> {
  const params = new URLSearchParams();
  if (query.search?.trim()) {
    params.set("search", query.search.trim());
  }
  if (query.author?.trim()) {
    params.set("author", query.author.trim());
  }
  addPublishedFilterParams(params, query);
  params.set("limit", String(query.limit));
  params.set("offset", String(query.offset));
  return request<PostListResponse>(`/api/posts?${params.toString()}`);
}

export interface ResultQuery {
  search?: string;
  author?: string;
  publishedFrom?: string;
  publishedTo?: string;
  includePosts: boolean;
  includeReplies: boolean;
  limit: number;
  offset: number;
}

export function getResults(query: ResultQuery): Promise<ResultListResponse> {
  const params = new URLSearchParams();
  if (query.search?.trim()) {
    params.set("search", query.search.trim());
  }
  if (query.author?.trim()) {
    params.set("author", query.author.trim());
  }
  addPublishedFilterParams(params, query);
  params.set("include_posts", String(query.includePosts));
  params.set("include_replies", String(query.includeReplies));
  params.set("limit", String(query.limit));
  params.set("offset", String(query.offset));
  return request<ResultListResponse>(`/api/results?${params.toString()}`);
}

export function getPost(postId: string): Promise<PostDetail> {
  return request<PostDetail>(`/api/posts/${encodeURIComponent(postId)}`);
}
