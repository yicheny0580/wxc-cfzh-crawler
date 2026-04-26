export interface HealthResponse {
  ok: boolean;
  db_path: string;
  db_exists: boolean;
  read_only: boolean;
  detail: string | null;
}

export interface SummaryResponse {
  db_path: string;
  posts: number;
  replies: number;
  authors: number;
  latest_crawl_at: string | null;
  latest_post_published_at: string | null;
}

export interface AuthorSummary {
  name: string;
  posts: number;
  replies: number;
  total: number;
}

export interface PostBase {
  post_id: string;
  url: string;
  forum: string;
  title: string | null;
  author: string | null;
  author_profile_url: string | null;
  published_at: string | null;
  edited_at: string | null;
  byte_count: number | null;
  read_count: number | null;
  reply_count: number | null;
  actual_reply_count: number;
  crawled_at: string;
}

export interface PostListItem extends PostBase {
  excerpt: string | null;
}

export interface PostListResponse {
  items: PostListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ReplyDetail {
  reply_id: string;
  root_post_id: string;
  parent_reply_id: string | null;
  url: string;
  forum: string;
  title: string | null;
  author: string | null;
  author_profile_url: string | null;
  published_at: string | null;
  edited_at: string | null;
  body_text: string | null;
  body_html: string | null;
  byte_count: number | null;
  read_count: number | null;
  depth: number;
  forum_order: number | null;
  crawled_at: string;
  replies: ReplyDetail[];
}

export interface PostDetail extends PostBase {
  body_text: string | null;
  body_html: string | null;
  replies: ReplyDetail[];
}
