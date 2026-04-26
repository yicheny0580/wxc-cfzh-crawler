import type {
  AuthorSummary,
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

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
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
  params.set("limit", String(query.limit));
  params.set("offset", String(query.offset));
  return request<PostListResponse>(`/api/posts?${params.toString()}`);
}

export interface ResultQuery {
  search?: string;
  author?: string;
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
  params.set("include_posts", String(query.includePosts));
  params.set("include_replies", String(query.includeReplies));
  params.set("limit", String(query.limit));
  params.set("offset", String(query.offset));
  return request<ResultListResponse>(`/api/results?${params.toString()}`);
}

export function getPost(postId: string): Promise<PostDetail> {
  return request<PostDetail>(`/api/posts/${encodeURIComponent(postId)}`);
}
