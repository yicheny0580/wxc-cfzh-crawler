import { Maximize2, Minimize2, X } from "lucide-react";
import { useEffect, useRef, useState, type MouseEvent } from "react";

import type { ReaderImage } from "./BodyContent";

type ImageDisplayMode = "fit" | "original";

export function ImageOverlay({
  image,
  onClose
}: {
  image: ReaderImage;
  onClose: () => void;
}) {
  const [displayMode, setDisplayMode] = useState<ImageDisplayMode>("fit");
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const imageAlt = image.alt || "Preview image";

  useEffect(() => {
    setDisplayMode("fit");
  }, [image.src]);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialogRef.current?.focus();

    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  const handleBackdropMouseDown = (event: MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      ref={dialogRef}
      role="dialog"
      aria-label={image.alt ? `Image preview: ${image.alt}` : "Image preview"}
      aria-modal="true"
      tabIndex={-1}
      onMouseDown={handleBackdropMouseDown}
      className="fixed inset-0 z-50 flex flex-col bg-stone-950/90 p-3 outline-none sm:p-5"
    >
      <div className="mb-3 flex shrink-0 items-center justify-end gap-2">
        <div className="inline-flex rounded-md border border-white/20 bg-stone-950/75 p-1 shadow-lg">
          <button
            type="button"
            onClick={() => setDisplayMode("fit")}
            aria-pressed={displayMode === "fit"}
            className={`inline-flex h-8 items-center gap-2 rounded px-2 text-xs font-medium transition focus:outline-none focus:ring-2 focus:ring-emerald-300 ${
              displayMode === "fit"
                ? "bg-white text-stone-950"
                : "text-stone-200 hover:bg-white/10 hover:text-white"
            }`}
          >
            <Minimize2 className="h-4 w-4" />
            Fit
          </button>
          <button
            type="button"
            onClick={() => setDisplayMode("original")}
            aria-pressed={displayMode === "original"}
            className={`inline-flex h-8 items-center gap-2 rounded px-2 text-xs font-medium transition focus:outline-none focus:ring-2 focus:ring-emerald-300 ${
              displayMode === "original"
                ? "bg-white text-stone-950"
                : "text-stone-200 hover:bg-white/10 hover:text-white"
            }`}
          >
            <Maximize2 className="h-4 w-4" />
            Original
          </button>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-white/20 bg-stone-950/75 text-stone-100 shadow-lg transition hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-emerald-300"
          title="Close image preview"
          aria-label="Close image preview"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <div
        onMouseDown={handleBackdropMouseDown}
        className={`min-h-0 flex-1 rounded-sm ${
          displayMode === "fit"
            ? "flex items-center justify-center overflow-hidden"
            : "overflow-auto"
        }`}
      >
        <img
          src={image.src}
          alt={imageAlt}
          onMouseDown={(event) => event.stopPropagation()}
          className={
            displayMode === "fit"
              ? "block max-h-full max-w-full select-none object-contain"
              : "block h-auto w-auto max-w-none select-none"
          }
        />
      </div>
    </div>
  );
}
