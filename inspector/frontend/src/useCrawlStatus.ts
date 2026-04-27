import { useEffect, useRef, useState } from "react";

import { crawlWebSocketUrl, getCrawlStatus, startCrawl, stopCrawl } from "./api";
import type { CrawlState, CrawlStatusResponse } from "./types";

const FINAL_CRAWL_STATES: CrawlState[] = ["succeeded", "failed", "stopped"];

export function useCrawlStatus(onTerminal: () => void, enabled: boolean) {
  const [status, setStatus] = useState<CrawlStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const lastState = useRef<CrawlState | null>(null);
  const onTerminalRef = useRef(onTerminal);

  useEffect(() => {
    onTerminalRef.current = onTerminal;
  }, [onTerminal]);

  function applyStatus(payload: CrawlStatusResponse) {
    setStatus(payload);
    if (payload.state === "running" || payload.state === "stopping") {
      setError(null);
    }
  }

  useEffect(() => {
    if (!enabled) {
      setStatus(null);
      setError(null);
      setActionLoading(false);
      lastState.current = null;
      return;
    }

    let active = true;
    let socket: WebSocket | null = null;
    let reconnectHandle: number | null = null;

    getCrawlStatus()
      .then((payload) => {
        if (active) {
          applyStatus(payload);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load crawl status.");
        }
      });

    const connect = () => {
      socket = new WebSocket(crawlWebSocketUrl());
      socket.onmessage = (event) => {
        try {
          applyStatus(JSON.parse(event.data) as CrawlStatusResponse);
        } catch {
          setError("Received invalid crawl status.");
        }
      };
      socket.onerror = () => {
        setError("Crawl status connection failed.");
      };
      socket.onclose = () => {
        if (!active) {
          return;
        }
        reconnectHandle = window.setTimeout(connect, 2000);
      };
    };

    connect();

    return () => {
      active = false;
      if (reconnectHandle !== null) {
        window.clearTimeout(reconnectHandle);
      }
      socket?.close();
    };
  }, [enabled]);

  useEffect(() => {
    const previous = lastState.current;
    const current = status?.state ?? null;
    lastState.current = current;

    if (
      previous &&
      (previous === "running" || previous === "stopping") &&
      current &&
      FINAL_CRAWL_STATES.includes(current)
    ) {
      onTerminalRef.current();
    }
  }, [status?.state]);

  const start = (pages: number) => {
    setActionLoading(true);
    setError(null);
    if (!enabled) {
      setActionLoading(false);
      return;
    }
    startCrawl(pages)
      .then(applyStatus)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to start crawl.");
      })
      .finally(() => setActionLoading(false));
  };

  const stop = () => {
    setActionLoading(true);
    setError(null);
    if (!enabled) {
      setActionLoading(false);
      return;
    }
    stopCrawl()
      .then(applyStatus)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to stop crawl.");
      })
      .finally(() => setActionLoading(false));
  };

  return { actionLoading, error, start, status, stop };
}
