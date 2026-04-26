import { RotateCcw, SlidersHorizontal, X } from "lucide-react";
import { useMemo } from "react";

import { AuthorFilter, TypeFilter } from "./Filters";
import {
  DEFAULT_RESULT_TYPE_FILTER,
  resultTypeFiltersMatch,
  type ResultTypeFilterPreference
} from "./resultTypePreference";
import {
  EMPTY_PUBLISHED_TIME_FILTER,
  TIME_PRESET_OPTIONS,
  hasInvalidPublishedTimeRange,
  publishedTimeFilterLabel,
  type PublishedTimeFilter,
  type TimePreset
} from "./timeFilter";
import type { AuthorSummary } from "./types";

interface FilterPanelProps {
  authors: AuthorSummary[];
  author: string;
  onAuthorChange: (value: string) => void;
  resultTypeFilter: ResultTypeFilterPreference;
  onResultTypeFilterChange: (value: ResultTypeFilterPreference) => void;
  publishedTimeFilter: PublishedTimeFilter;
  onPublishedTimeFilterChange: (value: PublishedTimeFilter) => void;
  onClearFilters: () => void;
}

interface FilterChip {
  key: string;
  label: string;
  onRemove: () => void;
}

export function FilterPanel({
  authors,
  author,
  onAuthorChange,
  resultTypeFilter,
  onResultTypeFilterChange,
  publishedTimeFilter,
  onPublishedTimeFilterChange,
  onClearFilters
}: FilterPanelProps) {
  const invalidTimeRange = hasInvalidPublishedTimeRange(publishedTimeFilter);
  const chips = useMemo<FilterChip[]>(() => {
    const nextChips: FilterChip[] = [];
    const timeLabel = publishedTimeFilterLabel(publishedTimeFilter);

    if (author) {
      nextChips.push({
        key: "author",
        label: `Author: ${author}`,
        onRemove: () => onAuthorChange("")
      });
    }

    if (!resultTypeFiltersMatch(resultTypeFilter, DEFAULT_RESULT_TYPE_FILTER)) {
      nextChips.push({
        key: "type",
        label: resultTypeLabel(resultTypeFilter),
        onRemove: () => onResultTypeFilterChange(DEFAULT_RESULT_TYPE_FILTER)
      });
    }

    if (timeLabel) {
      nextChips.push({
        key: "time",
        label: `Published: ${timeLabel}`,
        onRemove: () => onPublishedTimeFilterChange(EMPTY_PUBLISHED_TIME_FILTER)
      });
    }

    return nextChips;
  }, [
    author,
    onAuthorChange,
    onPublishedTimeFilterChange,
    onResultTypeFilterChange,
    publishedTimeFilter,
    resultTypeFilter
  ]);

  const updateResultType = (nextFilter: ResultTypeFilterPreference) => {
    if (!nextFilter.includePosts && !nextFilter.includeReplies) {
      return;
    }
    onResultTypeFilterChange(nextFilter);
  };

  return (
    <section className="shrink-0 border-b border-stone-300 bg-[#fbfaf7]" aria-label="Result filters">
      <div className="mx-auto max-w-[1800px] px-3 py-2 sm:px-4 lg:px-6">
        <div className="flex flex-col gap-2 xl:flex-row xl:items-center">
          <div className="grid min-w-0 flex-1 gap-2 md:grid-cols-[minmax(220px,320px)_auto_minmax(0,1fr)] md:items-center">
            <AuthorFilter authors={authors} value={author} onChange={onAuthorChange} />
            <TypeFilter
              includePosts={resultTypeFilter.includePosts}
              includeReplies={resultTypeFilter.includeReplies}
              showLabel={false}
              onIncludePostsChange={(checked) =>
                updateResultType({ ...resultTypeFilter, includePosts: checked })
              }
              onIncludeRepliesChange={(checked) =>
                updateResultType({ ...resultTypeFilter, includeReplies: checked })
              }
            />
            <PublishedTimeControl
              value={publishedTimeFilter}
              invalid={invalidTimeRange}
              onChange={onPublishedTimeFilterChange}
            />
          </div>

          {chips.length > 0 ? (
            <button
              type="button"
              onClick={onClearFilters}
              className="inline-flex h-9 shrink-0 items-center justify-center gap-2 self-start rounded-md border border-stone-300 bg-white px-3 text-sm font-medium text-stone-700 transition hover:border-stone-400 hover:bg-stone-50 hover:text-stone-950 xl:self-auto"
              title="Clear filters"
            >
              <RotateCcw className="h-4 w-4" />
              <span>Clear</span>
            </button>
          ) : null}
        </div>

        {chips.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-1.5 border-t border-stone-200 pt-2">
            {chips.map((chip) => (
              <button
                key={chip.key}
                type="button"
                onClick={chip.onRemove}
                className="inline-flex max-w-full items-center gap-1 rounded-sm border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-950 transition hover:bg-emerald-100 sm:max-w-[28rem]"
                title={`Remove ${chip.label}`}
              >
                <span className="min-w-0 truncate">{chip.label}</span>
                <X className="h-3 w-3 shrink-0" />
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}

function PublishedTimeControl({
  value,
  invalid,
  onChange
}: {
  value: PublishedTimeFilter;
  invalid: boolean;
  onChange: (value: PublishedTimeFilter) => void;
}) {
  const selectPreset = (preset: TimePreset) => {
    if (preset === "custom") {
      onChange({ ...value, preset });
      return;
    }
    onChange({ ...EMPTY_PUBLISHED_TIME_FILTER, preset });
  };
  const showCustomDates =
    value.preset === "custom" || Boolean(value.publishedFrom || value.publishedTo);

  return (
    <div className="min-w-0">
      <div
        className={`flex min-w-0 flex-col gap-2 ${showCustomDates ? "lg:flex-row lg:items-start" : ""}`}
      >
        <div className="inline-flex max-w-full flex-wrap items-center gap-1 self-start rounded-md border border-stone-300 bg-white p-1 lg:flex-nowrap">
          <span className="hidden shrink-0 px-2 text-xs font-medium uppercase text-stone-500 2xl:inline">
            Published
          </span>
          {TIME_PRESET_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => selectPreset(option.value)}
              className={`h-7 rounded px-2.5 text-sm transition focus:outline-none focus:ring-2 focus:ring-emerald-600 ${
                value.preset === option.value
                  ? "bg-emerald-700 font-medium text-white"
                  : "text-stone-700 hover:bg-stone-100 hover:text-stone-950"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
        {showCustomDates ? (
          <div className="grid min-w-0 grid-cols-2 gap-2 lg:w-[320px] lg:shrink-0">
            <DateInput
              label="From"
              value={value.publishedFrom}
              onChange={(publishedFrom) => onChange({ ...value, preset: "custom", publishedFrom })}
            />
            <DateInput
              label="To"
              value={value.publishedTo}
              onChange={(publishedTo) => onChange({ ...value, preset: "custom", publishedTo })}
            />
          </div>
        ) : null}
      </div>
      {invalid ? (
        <p className="mt-1 text-xs text-red-700" role="alert">
          Start date must be on or before end date.
        </p>
      ) : null}
    </div>
  );
}

function DateInput({
  label,
  value,
  onChange
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="flex h-9 min-w-0 items-center rounded-md border border-stone-300 bg-white px-2 text-xs font-medium uppercase text-stone-500 transition focus-within:border-emerald-600 focus-within:ring-2 focus-within:ring-emerald-200">
      <span className="shrink-0">{label}</span>
      <input
        type="date"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="min-w-0 flex-1 border-0 bg-transparent pl-2 text-sm normal-case text-stone-900 outline-none"
      />
    </label>
  );
}

function resultTypeLabel(filter: ResultTypeFilterPreference): string {
  if (filter.includePosts && filter.includeReplies) {
    return "Posts + replies";
  }
  if (filter.includePosts) {
    return "Posts only";
  }
  return "Replies only";
}
