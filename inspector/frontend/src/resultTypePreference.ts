export interface ResultTypeFilterPreference {
  includePosts: boolean;
  includeReplies: boolean;
}

const RESULT_TYPE_FILTER_STORAGE_KEY = "cfzh-inspector.result-type-filter.v1";

const DEFAULT_RESULT_TYPE_FILTER: ResultTypeFilterPreference = {
  includePosts: true,
  includeReplies: false
};

function normalizeResultTypeFilterPreference(value: unknown): ResultTypeFilterPreference | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const candidate = value as Partial<ResultTypeFilterPreference>;
  if (
    typeof candidate.includePosts !== "boolean" ||
    typeof candidate.includeReplies !== "boolean" ||
    (!candidate.includePosts && !candidate.includeReplies)
  ) {
    return null;
  }

  return {
    includePosts: candidate.includePosts,
    includeReplies: candidate.includeReplies
  };
}

export function readResultTypeFilterPreference(): ResultTypeFilterPreference {
  if (typeof window === "undefined") {
    return DEFAULT_RESULT_TYPE_FILTER;
  }

  try {
    const storedPreference = window.localStorage.getItem(RESULT_TYPE_FILTER_STORAGE_KEY);
    if (!storedPreference) {
      return DEFAULT_RESULT_TYPE_FILTER;
    }
    const parsedPreference = normalizeResultTypeFilterPreference(JSON.parse(storedPreference));
    return parsedPreference ?? DEFAULT_RESULT_TYPE_FILTER;
  } catch {
    return DEFAULT_RESULT_TYPE_FILTER;
  }
}

export function writeResultTypeFilterPreference(preference: ResultTypeFilterPreference) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(RESULT_TYPE_FILTER_STORAGE_KEY, JSON.stringify(preference));
  } catch {
    return;
  }
}
