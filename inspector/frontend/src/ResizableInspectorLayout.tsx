import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode
} from "react";

const RESULTS_PANE_WIDTH_STORAGE_KEY = "cfzh-inspector.results-pane-width.v1";
const DEFAULT_RESULTS_PANE_WIDTH = 360;
const MIN_RESULTS_PANE_WIDTH = 280;
const MAX_RESULTS_PANE_WIDTH = 640;
const MIN_READER_PANE_WIDTH = 420;
const DIVIDER_WIDTH = 20;
const KEYBOARD_RESIZE_STEP = 20;
const DESKTOP_LAYOUT_QUERY = "(min-width: 1024px)";

interface ResizableInspectorLayoutProps {
  resultsPane: ReactNode;
  readerPane: ReactNode;
}

export function ResizableInspectorLayout({
  resultsPane,
  readerPane
}: ResizableInspectorLayoutProps) {
  const containerRef = useRef<HTMLElement | null>(null);
  const dragPointerIdRef = useRef<number | null>(null);
  const isDesktopLayout = useIsDesktopLayout();
  const [resultsPaneWidth, setResultsPaneWidth] = useState(readResultsPaneWidthPreference);
  const [containerWidth, setContainerWidth] = useState(0);
  const [isDragging, setIsDragging] = useState(false);

  const maxResultsPaneWidth = useMemo(
    () => maxResultsPaneWidthFor(containerWidth),
    [containerWidth]
  );

  const layoutStyle = useMemo(
    () =>
      ({
        "--results-pane-width": `${resultsPaneWidth}px`
      }) as CSSProperties,
    [resultsPaneWidth]
  );

  const resizeToClientX = useCallback((clientX: number) => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const metrics = layoutMetricsFor(container);
    setContainerWidth(metrics.width);
    setResultsPaneWidth(clampResultsPaneWidth(clientX - metrics.left, metrics.width));
  }, []);

  const resizeBy = useCallback((delta: number) => {
    const container = containerRef.current;
    const nextContainerWidth = container ? layoutMetricsFor(container).width : 0;
    setContainerWidth(nextContainerWidth);
    setResultsPaneWidth((currentWidth) =>
      clampResultsPaneWidth(currentWidth + delta, nextContainerWidth)
    );
  }, []);

  const resizeTo = useCallback((nextWidth: number) => {
    const container = containerRef.current;
    const nextContainerWidth = container ? layoutMetricsFor(container).width : 0;
    setContainerWidth(nextContainerWidth);
    setResultsPaneWidth(clampResultsPaneWidth(nextWidth, nextContainerWidth));
  }, []);

  useEffect(() => {
    writeResultsPaneWidthPreference(resultsPaneWidth);
  }, [resultsPaneWidth]);

  useEffect(() => {
    if (!isDesktopLayout) {
      return;
    }

    const syncContainerWidth = () => {
      if (!isDesktopViewport()) {
        return;
      }

      const container = containerRef.current;
      if (!container) {
        return;
      }
      const nextContainerWidth = layoutMetricsFor(container).width;
      setContainerWidth(nextContainerWidth);
      setResultsPaneWidth((currentWidth) =>
        clampResultsPaneWidth(currentWidth, nextContainerWidth)
      );
    };

    syncContainerWidth();
    const resizeObserver =
      typeof ResizeObserver !== "undefined" && containerRef.current
        ? new ResizeObserver(syncContainerWidth)
        : null;

    if (containerRef.current) {
      resizeObserver?.observe(containerRef.current);
    }
    window.addEventListener("resize", syncContainerWidth);

    return () => {
      resizeObserver?.disconnect();
      window.removeEventListener("resize", syncContainerWidth);
    };
  }, [isDesktopLayout]);

  useEffect(() => {
    if (!isDragging || typeof document === "undefined") {
      return;
    }

    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    return () => {
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
    };
  }, [isDragging]);

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) {
      return;
    }

    event.preventDefault();
    dragPointerIdRef.current = event.pointerId;
    event.currentTarget.setPointerCapture(event.pointerId);
    setIsDragging(true);
    resizeToClientX(event.clientX);
  };

  const handlePointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (dragPointerIdRef.current !== event.pointerId) {
      return;
    }

    event.preventDefault();
    resizeToClientX(event.clientX);
  };

  const finishDragging = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (dragPointerIdRef.current !== event.pointerId) {
      return;
    }

    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    dragPointerIdRef.current = null;
    setIsDragging(false);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "ArrowLeft" || event.key === "ArrowDown") {
      event.preventDefault();
      resizeBy(-KEYBOARD_RESIZE_STEP);
      return;
    }
    if (event.key === "ArrowRight" || event.key === "ArrowUp") {
      event.preventDefault();
      resizeBy(KEYBOARD_RESIZE_STEP);
      return;
    }
    if (event.key === "Home") {
      event.preventDefault();
      resizeTo(MIN_RESULTS_PANE_WIDTH);
      return;
    }
    if (event.key === "End") {
      event.preventDefault();
      resizeTo(maxResultsPaneWidth);
    }
  };

  const gripDotClass = `h-1 w-1 rounded-full transition ${
    isDragging
      ? "bg-white"
      : "bg-stone-400 group-hover:bg-emerald-700 group-focus-visible:bg-emerald-700"
  }`;

  return (
    <main
      ref={containerRef}
      className="mx-auto grid w-full max-w-[1800px] gap-3 px-3 py-3 sm:px-4 lg:grid-cols-[minmax(280px,var(--results-pane-width))_20px_minmax(0,1fr)] lg:items-start lg:gap-0 lg:px-6"
      style={layoutStyle}
    >
      {resultsPane}
      <div
        role="separator"
        aria-label="Resize results and reader panes"
        aria-orientation="vertical"
        aria-valuemin={MIN_RESULTS_PANE_WIDTH}
        aria-valuemax={maxResultsPaneWidth}
        aria-valuenow={Math.round(resultsPaneWidth)}
        aria-valuetext={`${Math.round(resultsPaneWidth)} pixels`}
        tabIndex={0}
        title="Drag to resize panes"
        className={`group relative hidden cursor-col-resize touch-none select-none items-center justify-center rounded-md outline-none transition-colors lg:sticky lg:top-3 lg:flex lg:h-[calc(100vh-1.5rem)] lg:min-h-[360px] ${
          isDragging
            ? "bg-emerald-100/80"
            : "hover:bg-stone-200/70 focus-visible:bg-emerald-50 focus-visible:ring-2 focus-visible:ring-emerald-600 focus-visible:ring-offset-2 focus-visible:ring-offset-[#f6f3ed]"
        }`}
        onKeyDown={handleKeyDown}
        onPointerCancel={finishDragging}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={finishDragging}
      >
        <span
          aria-hidden="true"
          className={`pointer-events-none absolute inset-y-2 left-1/2 w-px -translate-x-1/2 rounded-full transition-colors ${
            isDragging
              ? "bg-emerald-600"
              : "bg-stone-300 group-hover:bg-emerald-500 group-focus-visible:bg-emerald-500"
          }`}
        />
        <div
          className={`relative flex h-16 w-3 items-center justify-center rounded-full border shadow-sm transition ${
            isDragging
              ? "border-emerald-700 bg-emerald-700 shadow-emerald-900/10"
              : "border-stone-300 bg-[#fbfaf7] shadow-stone-950/5 group-hover:border-emerald-600 group-hover:bg-white group-focus-visible:border-emerald-600 group-focus-visible:bg-white"
          }`}
        >
          <div className="flex flex-col gap-1">
            <span className={gripDotClass} />
            <span className={gripDotClass} />
            <span className={gripDotClass} />
          </div>
        </div>
      </div>
      {readerPane}
    </main>
  );
}

function useIsDesktopLayout(): boolean {
  const [isDesktopLayout, setIsDesktopLayout] = useState(() => {
    return isDesktopViewport();
  });

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const mediaQuery = window.matchMedia(DESKTOP_LAYOUT_QUERY);
    const syncLayout = () => setIsDesktopLayout(mediaQuery.matches);

    syncLayout();
    mediaQuery.addEventListener("change", syncLayout);
    return () => mediaQuery.removeEventListener("change", syncLayout);
  }, []);

  return isDesktopLayout;
}

function isDesktopViewport(): boolean {
  if (typeof window === "undefined") {
    return true;
  }
  return window.matchMedia(DESKTOP_LAYOUT_QUERY).matches;
}

function layoutMetricsFor(container: HTMLElement): { left: number; width: number } {
  const rect = container.getBoundingClientRect();
  const style = window.getComputedStyle(container);
  const paddingLeft = Number.parseFloat(style.paddingLeft) || 0;
  const paddingRight = Number.parseFloat(style.paddingRight) || 0;

  return {
    left: rect.left + paddingLeft,
    width: Math.max(0, rect.width - paddingLeft - paddingRight)
  };
}

function readResultsPaneWidthPreference(): number {
  if (typeof window === "undefined") {
    return DEFAULT_RESULTS_PANE_WIDTH;
  }

  try {
    const storedWidth = window.localStorage.getItem(RESULTS_PANE_WIDTH_STORAGE_KEY);
    if (!storedWidth) {
      return DEFAULT_RESULTS_PANE_WIDTH;
    }
    return clampResultsPaneWidth(Number(storedWidth), 0);
  } catch {
    return DEFAULT_RESULTS_PANE_WIDTH;
  }
}

function writeResultsPaneWidthPreference(width: number) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(RESULTS_PANE_WIDTH_STORAGE_KEY, String(Math.round(width)));
  } catch {
    return;
  }
}

function clampResultsPaneWidth(width: number, containerWidth: number): number {
  if (!Number.isFinite(width)) {
    return DEFAULT_RESULTS_PANE_WIDTH;
  }

  const maxWidth = maxResultsPaneWidthFor(containerWidth);
  return Math.min(Math.max(Math.round(width), MIN_RESULTS_PANE_WIDTH), maxWidth);
}

function maxResultsPaneWidthFor(containerWidth: number): number {
  if (!Number.isFinite(containerWidth) || containerWidth <= 0) {
    return MAX_RESULTS_PANE_WIDTH;
  }

  const maxWidthWithReadableReader = containerWidth - DIVIDER_WIDTH - MIN_READER_PANE_WIDTH;
  return Math.max(
    MIN_RESULTS_PANE_WIDTH,
    Math.min(MAX_RESULTS_PANE_WIDTH, maxWidthWithReadableReader)
  );
}
