import { ChevronDown, ChevronRight, ExternalLink } from "lucide-react";

import { BodyContent, type ReaderImage } from "./BodyContent";
import { countLabel, formatDate } from "./format";
import type { ReplyDetail } from "./types";

function descendantReplyCount(reply: ReplyDetail): number {
  return reply.replies.reduce((total, child) => total + 1 + descendantReplyCount(child), 0);
}

function shouldIgnoreReplyToggle(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return true;
  }
  return Boolean(target.closest("a, button, input, select, textarea, label"));
}

export function ReplyNode({
  reply,
  highlightedReplyId,
  collapsedReplyIds,
  onToggle,
  onImageOpen
}: {
  reply: ReplyDetail;
  highlightedReplyId: string | null;
  collapsedReplyIds: Set<string>;
  onToggle: (replyId: string) => void;
  onImageOpen: (image: ReaderImage) => void;
}) {
  const highlighted = reply.reply_id === highlightedReplyId;
  const collapsed = collapsedReplyIds.has(reply.reply_id);
  const nestedCount = descendantReplyCount(reply);

  return (
    <div className="border-l-2 border-emerald-700 bg-white" data-reply-id={reply.reply_id}>
      <div
        onClick={(event) => {
          if (shouldIgnoreReplyToggle(event.target) || window.getSelection()?.toString()) {
            return;
          }
          onToggle(reply.reply_id);
        }}
        className={`cursor-pointer border px-3 py-3 transition-colors ${
          highlighted
            ? "border-emerald-500 bg-emerald-50 hover:bg-emerald-100"
            : collapsed
              ? "border-stone-300 bg-stone-50 hover:bg-stone-100"
              : "border-stone-200 hover:border-stone-300 hover:bg-stone-50"
        }`}
      >
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-2 text-sm">
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onToggle(reply.reply_id);
              }}
              className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-stone-500 transition hover:bg-stone-100 hover:text-stone-900 focus:outline-none focus:ring-2 focus:ring-emerald-600"
              title={collapsed ? "Expand reply" : "Collapse reply"}
              aria-label={collapsed ? "Expand reply" : "Collapse reply"}
              aria-expanded={!collapsed}
            >
              {collapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>
            <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
              <span className="font-semibold text-stone-950">{reply.author || "Unknown"}</span>
              <span className="text-stone-500">{formatDate(reply.published_at)}</span>
              <span className="text-stone-500">#{reply.reply_id}</span>
              {collapsed && nestedCount > 0 ? (
                <span className="rounded-sm bg-stone-100 px-1.5 py-0.5 text-xs font-medium text-stone-600">
                  {countLabel(nestedCount, "reply")}
                </span>
              ) : null}
            </div>
          </div>
          <a
            href={reply.url}
            target="_blank"
            rel="noreferrer"
            onClick={(event) => event.stopPropagation()}
            className="inline-flex h-7 w-7 items-center justify-center rounded-md text-stone-500 hover:bg-stone-100 hover:text-stone-900"
            title="Open reply"
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        </div>
        {!collapsed ? <ReplyBody reply={reply} onImageOpen={onImageOpen} /> : null}
      </div>
      {!collapsed && reply.replies.length > 0 ? (
        <div className="mt-3 space-y-3 pl-3">
          {reply.replies.map((child) => (
            <ReplyNode
              key={child.reply_id}
              reply={child}
              highlightedReplyId={highlightedReplyId}
              collapsedReplyIds={collapsedReplyIds}
              onToggle={onToggle}
              onImageOpen={onImageOpen}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ReplyBody({
  reply,
  onImageOpen
}: {
  reply: ReplyDetail;
  onImageOpen: (image: ReaderImage) => void;
}) {
  if (reply.title) {
    return (
      <>
        <div className="mt-2 text-sm font-medium text-stone-800">{reply.title}</div>
        {reply.body_html || reply.body_text ? (
          <BodyContent
            html={reply.body_html}
            text={reply.body_text}
            className="mt-2 text-sm leading-6 text-stone-800"
            onImageOpen={onImageOpen}
          />
        ) : null}
      </>
    );
  }

  if (reply.body_html || reply.body_text) {
    return (
      <BodyContent
        html={reply.body_html}
        text={reply.body_text}
        className="mt-2 text-sm leading-6 text-stone-800"
        onImageOpen={onImageOpen}
      />
    );
  }

  return <div className="mt-2 text-sm text-stone-500">No body text.</div>;
}
