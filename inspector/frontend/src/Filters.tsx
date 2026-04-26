import { Check, Search, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { authorLabel, formatNumber } from "./format";
import type { AuthorSummary } from "./types";

export function AuthorFilter({
  authors,
  value,
  onChange
}: {
  authors: AuthorSummary[];
  value: string;
  onChange: (value: string) => void;
}) {
  const [filter, setFilter] = useState("");
  const [open, setOpen] = useState(false);
  const closeTimerRef = useRef<number | null>(null);

  const filteredAuthors = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    const matches = needle
      ? authors.filter((item) => item.name.toLowerCase().includes(needle))
      : authors;
    return matches.slice(0, 80);
  }, [authors, filter]);

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

  const selectAuthor = (nextAuthor: string) => {
    onChange(nextAuthor);
    setFilter("");
    setOpen(false);
  };

  const closeSoon = () => {
    clearCloseTimer();
    closeTimerRef.current = window.setTimeout(() => setOpen(false), 120);
  };

  const clearInput = () => {
    if (filter) {
      setFilter("");
      setOpen(true);
      return;
    }
    selectAuthor("");
  };

  return (
    <div className="relative min-w-0">
      <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-500" />
      <input
        value={filter}
        onBlur={closeSoon}
        onChange={(event) => {
          setFilter(event.target.value);
          setOpen(true);
        }}
        onFocus={() => {
          clearCloseTimer();
          setOpen(true);
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setOpen(false);
          }
          if (event.key === "Enter" && filteredAuthors.length > 0) {
            event.preventDefault();
            selectAuthor(filteredAuthors[0].name);
          }
        }}
        placeholder={value ? `Author: ${value}` : "Filter authors"}
        className={`h-9 w-full rounded-md border border-stone-300 bg-white pl-8 pr-8 text-sm text-stone-900 outline-none transition placeholder:text-stone-500 focus:border-emerald-600 focus:ring-2 focus:ring-emerald-200 ${
          value && !filter ? "placeholder:text-stone-900" : ""
        }`}
        aria-label="Filter authors"
      />
      {filter || value ? (
        <button
          type="button"
          onMouseDown={(event) => event.preventDefault()}
          onClick={clearInput}
          className="absolute right-2 top-1/2 inline-flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md text-stone-500 hover:bg-stone-100 hover:text-stone-900"
          title={filter ? "Clear author search" : "Clear author filter"}
        >
          <X className="h-4 w-4" />
        </button>
      ) : null}
      {open ? (
        <div
          className="scrollbar-stable absolute left-0 right-0 top-full z-30 mt-1 max-h-72 overflow-y-auto rounded-md border border-stone-300 bg-white py-1 shadow-lg"
          onMouseDown={(event) => event.preventDefault()}
        >
          <button
            type="button"
            onClick={() => selectAuthor("")}
            className={`flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm transition hover:bg-stone-50 ${
              value ? "text-stone-700" : "bg-emerald-50 font-medium text-stone-950"
            }`}
          >
            <span>All authors</span>
            <span className="text-xs text-stone-500">{formatNumber(authors.length)}</span>
          </button>
          {filteredAuthors.length > 0 ? (
            filteredAuthors.map((item) => (
              <button
                key={item.name}
                type="button"
                onClick={() => selectAuthor(item.name)}
                className={`flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm transition hover:bg-stone-50 ${
                  value === item.name ? "bg-emerald-50 font-medium text-stone-950" : "text-stone-700"
                }`}
                title={authorLabel(item)}
              >
                <span className="min-w-0 truncate">{item.name}</span>
                <span className="shrink-0 text-xs text-stone-500">
                  {formatNumber(item.total)}
                </span>
              </button>
            ))
          ) : (
            <div className="px-3 py-3 text-sm text-stone-500">No matching authors.</div>
          )}
        </div>
      ) : null}
    </div>
  );
}

export function TypeFilter({
  includePosts,
  includeReplies,
  showLabel = true,
  onIncludePostsChange,
  onIncludeRepliesChange
}: {
  includePosts: boolean;
  includeReplies: boolean;
  showLabel?: boolean;
  onIncludePostsChange: (checked: boolean) => void;
  onIncludeRepliesChange: (checked: boolean) => void;
}) {
  return (
    <fieldset className="inline-flex h-9 items-center gap-1 rounded-md border border-stone-300 bg-white p-1">
      <legend className="sr-only">Result type</legend>
      {showLabel ? (
        <span className="ml-1 mr-1 text-xs font-medium uppercase text-stone-500">Type</span>
      ) : null}
      <TypeFilterOption label="Posts" checked={includePosts} onChange={onIncludePostsChange} />
      <TypeFilterOption
        label="Replies"
        checked={includeReplies}
        onChange={onIncludeRepliesChange}
      />
    </fieldset>
  );
}

function TypeFilterOption({
  label,
  checked,
  onChange
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label
      className={`flex h-7 cursor-pointer items-center gap-1.5 rounded px-2 text-sm transition ${
        checked ? "bg-emerald-700 text-white" : "text-stone-700 hover:bg-stone-100"
      }`}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="sr-only"
      />
      <span
        className={`inline-flex h-3.5 w-3.5 items-center justify-center rounded-sm border ${
          checked ? "border-white bg-white text-emerald-700" : "border-stone-400 bg-white"
        }`}
      >
        {checked ? <Check className="h-3 w-3" /> : null}
      </span>
      <span>{label}</span>
    </label>
  );
}
