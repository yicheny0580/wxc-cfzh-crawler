import type { AuthorSummary, PostDetail, PostListItem, ResultItem } from "./types";

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "-";
  }
  return new Intl.NumberFormat().format(value);
}

export function formatDate(value: string | null | undefined): string {
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

export function displayTitle(post: Pick<PostListItem | PostDetail, "post_id" | "title">): string {
  return post.title?.trim() || `Post ${post.post_id}`;
}

export function displayResultTitle(result: ResultItem): string {
  if (result.title?.trim()) {
    return result.title.trim();
  }
  if (result.record_type === "reply" && result.reply_id) {
    return `Reply ${result.reply_id}`;
  }
  return `Post ${result.post_id}`;
}

export function resultKey(result: ResultItem): string {
  return `${result.record_type}:${result.reply_id ?? result.post_id}`;
}

export function countLabel(value: number, singular: string): string {
  return `${formatNumber(value)} ${value === 1 ? singular : `${singular}s`}`;
}

export function authorLabel(author: AuthorSummary): string {
  return `${author.name} (${countLabel(author.posts, "post")}, ${countLabel(
    author.replies,
    "reply"
  )})`;
}
