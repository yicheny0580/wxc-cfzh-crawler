import type { ReplyDetail } from "./types";

const REPLY_COLLAPSE_STORAGE_KEY_PREFIX = "cfzh-inspector.reply-collapse-state.v1.";

export function allReplyIds(replies: ReplyDetail[]): string[] {
  return replies.flatMap((reply) => [reply.reply_id, ...allReplyIds(reply.replies)]);
}

export function readReplyCollapseState(postId: string, replies: ReplyDetail[]): Set<string> {
  if (typeof window === "undefined") {
    return new Set();
  }

  try {
    const storedState = window.localStorage.getItem(storageKeyForPost(postId));
    if (!storedState) {
      return new Set();
    }

    const parsedState: unknown = JSON.parse(storedState);
    if (!Array.isArray(parsedState)) {
      return new Set();
    }

    const availableReplyIds = new Set(allReplyIds(replies));
    return new Set(
      parsedState.filter(
        (replyId): replyId is string =>
          typeof replyId === "string" && availableReplyIds.has(replyId)
      )
    );
  } catch {
    return new Set();
  }
}

export function writeReplyCollapseState(
  postId: string,
  collapsedReplyIds: Set<string>,
  replies: ReplyDetail[]
) {
  if (typeof window === "undefined") {
    return;
  }

  const currentCollapsedReplyIds = allReplyIds(replies).filter((replyId) =>
    collapsedReplyIds.has(replyId)
  );

  try {
    if (currentCollapsedReplyIds.length === 0) {
      window.localStorage.removeItem(storageKeyForPost(postId));
      return;
    }

    window.localStorage.setItem(storageKeyForPost(postId), JSON.stringify(currentCollapsedReplyIds));
  } catch {
    return;
  }
}

function storageKeyForPost(postId: string): string {
  return `${REPLY_COLLAPSE_STORAGE_KEY_PREFIX}${postId}`;
}
