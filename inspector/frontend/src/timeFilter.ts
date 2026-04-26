export type TimePreset = "all" | "today" | "7d" | "30d" | "90d" | "custom";

export interface PublishedTimeFilter {
  preset: TimePreset;
  publishedFrom: string;
  publishedTo: string;
}

export const EMPTY_PUBLISHED_TIME_FILTER: PublishedTimeFilter = {
  preset: "all",
  publishedFrom: "",
  publishedTo: ""
};

export const TIME_PRESET_OPTIONS: Array<{ value: TimePreset; label: string }> = [
  { value: "all", label: "All" },
  { value: "today", label: "Today" },
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
  { value: "custom", label: "Custom" }
];

function localDateInputValue(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function daysAgo(days: number): Date {
  const today = new Date();
  return new Date(today.getFullYear(), today.getMonth(), today.getDate() - days);
}

function todayInputValue(): string {
  return localDateInputValue(daysAgo(0));
}

function trimDate(value: string): string {
  return value.trim();
}

export function publishedTimeRange(filter: PublishedTimeFilter): {
  publishedFrom?: string;
  publishedTo?: string;
} {
  if (filter.preset === "all") {
    return {};
  }

  if (filter.preset === "custom") {
    const publishedFrom = trimDate(filter.publishedFrom);
    const publishedTo = trimDate(filter.publishedTo);
    return {
      ...(publishedFrom ? { publishedFrom } : {}),
      ...(publishedTo ? { publishedTo } : {})
    };
  }

  const publishedTo = todayInputValue();
  if (filter.preset === "today") {
    return { publishedFrom: publishedTo, publishedTo };
  }

  const days = filter.preset === "7d" ? 6 : filter.preset === "30d" ? 29 : 89;
  return { publishedFrom: localDateInputValue(daysAgo(days)), publishedTo };
}

export function hasPublishedTimeFilter(filter: PublishedTimeFilter): boolean {
  const range = publishedTimeRange(filter);
  return Boolean(range.publishedFrom || range.publishedTo);
}

export function hasInvalidPublishedTimeRange(filter: PublishedTimeFilter): boolean {
  if (filter.preset !== "custom") {
    return false;
  }
  const from = trimDate(filter.publishedFrom);
  const to = trimDate(filter.publishedTo);
  return Boolean(from && to && from > to);
}

function dateLabel(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) {
    return value;
  }

  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric"
  }).format(date);
}

export function publishedTimeFilterLabel(filter: PublishedTimeFilter): string | null {
  if (!hasPublishedTimeFilter(filter)) {
    return null;
  }

  if (filter.preset !== "custom") {
    return TIME_PRESET_OPTIONS.find((option) => option.value === filter.preset)?.label ?? null;
  }

  const from = trimDate(filter.publishedFrom);
  const to = trimDate(filter.publishedTo);
  if (from && to) {
    return `${dateLabel(from)} - ${dateLabel(to)}`;
  }
  if (from) {
    return `From ${dateLabel(from)}`;
  }
  if (to) {
    return `Until ${dateLabel(to)}`;
  }
  return null;
}
