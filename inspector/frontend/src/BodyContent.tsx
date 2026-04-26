import { useMemo, type KeyboardEvent, type MouseEvent } from "react";

import { sanitizeBodyHtml } from "./bodyHtml";

export interface ReaderImage {
  src: string;
  alt: string;
}

function readerImageFromTarget(target: EventTarget | null, container: HTMLElement): ReaderImage | null {
  if (!(target instanceof HTMLElement)) {
    return null;
  }

  const image = target.closest<HTMLImageElement>("img[data-reader-image]");
  if (!image || !container.contains(image)) {
    return null;
  }

  const src = image.currentSrc || image.src;
  if (!src) {
    return null;
  }

  return {
    src,
    alt: image.getAttribute("alt") || image.getAttribute("title") || ""
  };
}

export function BodyContent({
  html,
  text,
  className = "",
  onImageOpen
}: {
  html: string | null;
  text: string | null;
  className?: string;
  onImageOpen?: (image: ReaderImage) => void;
}) {
  const sanitizedHtml = useMemo(() => sanitizeBodyHtml(html), [html]);
  const classes = `reader-body ${className}`.trim();

  const openImageFromEvent = (
    event: MouseEvent<HTMLDivElement> | KeyboardEvent<HTMLDivElement>
  ) => {
    if (!onImageOpen) {
      return;
    }

    const image = readerImageFromTarget(event.target, event.currentTarget);
    if (!image) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    onImageOpen(image);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    openImageFromEvent(event);
  };

  if (sanitizedHtml) {
    return (
      <div
        className={`reader-body-html ${classes}`}
        onClick={openImageFromEvent}
        onKeyDown={handleKeyDown}
        dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
      />
    );
  }

  if (text) {
    return <div className={`whitespace-pre-wrap ${classes}`}>{text}</div>;
  }

  return <div className="text-sm text-stone-500">No body text.</div>;
}
