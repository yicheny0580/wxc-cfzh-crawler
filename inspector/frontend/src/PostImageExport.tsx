import { Clipboard, Download, Loader2 } from "lucide-react";
import { forwardRef, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { toBlob } from "html-to-image";
import { toDataURL as qrCodeToDataURL } from "qrcode";

import { displayTitle, formatDate, formatNumber } from "./format";
import { sanitizePostBodyHtmlForImageExport } from "./postImageExportHtml";
import type { PostDetail } from "./types";

const EXPORT_WIDTH = 760;
const IMAGE_LOAD_TIMEOUT_MS = 15000;
const QR_CODE_SIZE = 92;

type ExportAction = "copy" | "download";

function exportFileName(post: PostDetail): string {
  return `cfzh-post-${post.post_id}.png`;
}

function metadataItems(post: PostDetail): string[] {
  return [
    post.author || "Unknown author",
    formatDate(post.published_at),
    `${formatNumber(post.read_count)} reads`,
    `${formatNumber(post.actual_reply_count)} replies`,
    `#${post.post_id}`
  ];
}

function waitForImage(image: HTMLImageElement): Promise<void> {
  if (image.complete && image.naturalWidth > 0) {
    return Promise.resolve();
  }

  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      cleanup();
      reject(new Error("Timed out while loading an inline post image."));
    }, IMAGE_LOAD_TIMEOUT_MS);

    const cleanup = () => {
      window.clearTimeout(timeout);
      image.removeEventListener("load", handleLoad);
      image.removeEventListener("error", handleError);
    };

    const handleLoad = () => {
      cleanup();
      if (image.naturalWidth > 0) {
        resolve();
      } else {
        reject(new Error("An inline post image could not be loaded."));
      }
    };

    const handleError = () => {
      cleanup();
      reject(new Error("An inline post image could not be loaded."));
    };

    image.addEventListener("load", handleLoad, { once: true });
    image.addEventListener("error", handleError, { once: true });
  });
}

async function waitForExportAssets(element: HTMLElement) {
  if (document.fonts) {
    await document.fonts.ready;
  }

  const images = Array.from(element.querySelectorAll("img"));
  await Promise.all(images.map(waitForImage));
}

async function renderPostBlob(element: HTMLElement): Promise<Blob> {
  await waitForExportAssets(element);
  const blob = await toBlob(element, {
    backgroundColor: "#fbfaf7",
    cacheBust: true,
    height: element.scrollHeight,
    includeQueryParams: true,
    pixelRatio: 2,
    skipFonts: true,
    style: {
      bottom: "auto",
      left: "0px",
      margin: "0",
      position: "static",
      right: "auto",
      top: "0px"
    },
    width: EXPORT_WIDTH
  });

  if (!blob) {
    throw new Error("Post image export failed.");
  }
  return blob;
}

function downloadBlob(blob: Blob, filename: string) {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

async function copyBlob(blob: Blob) {
  if (!navigator.clipboard?.write || typeof ClipboardItem === "undefined") {
    throw new Error("Image copy is not supported by this browser.");
  }
  await navigator.clipboard.write([new ClipboardItem({ [blob.type]: blob })]);
}

function nextAnimationFrame(): Promise<void> {
  return new Promise((resolve) => window.requestAnimationFrame(() => resolve()));
}

function generateSourceQrCode(url: string): Promise<string> {
  return qrCodeToDataURL(url, {
    color: {
      dark: "#1c1917",
      light: "#ffffff"
    },
    errorCorrectionLevel: "M",
    margin: 1,
    type: "image/png",
    width: QR_CODE_SIZE
  });
}

export function PostImageExport({ post }: { post: PostDetail }) {
  const cardRef = useRef<HTMLDivElement | null>(null);
  const [activeAction, setActiveAction] = useState<ExportAction | null>(null);
  const [renderCard, setRenderCard] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [sourceQrCodeDataUrl, setSourceQrCodeDataUrl] = useState<string | null>(null);
  const exportHtml = useMemo(
    () => sanitizePostBodyHtmlForImageExport(post.post_id, post.body_html),
    [post.body_html, post.post_id]
  );
  const busy = activeAction !== null;

  useEffect(() => {
    setSourceQrCodeDataUrl(null);
  }, [post.url]);

  const runExport = async (action: ExportAction) => {
    if (busy) {
      return;
    }

    setActiveAction(action);
    setMessage(null);
    try {
      const qrCodeDataUrl = sourceQrCodeDataUrl ?? (await generateSourceQrCode(post.url));
      setSourceQrCodeDataUrl(qrCodeDataUrl);
      setRenderCard(true);
      await nextAnimationFrame();
      const card = cardRef.current;
      if (!card) {
        throw new Error("Post image export failed.");
      }
      const blob = await renderPostBlob(card);
      if (action === "download") {
        downloadBlob(blob, exportFileName(post));
        setMessage("Downloaded.");
      } else {
        await copyBlob(blob);
        setMessage("Copied.");
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Post image export failed.");
    } finally {
      setActiveAction(null);
      setRenderCard(false);
    }
  };

  return (
    <div className="flex flex-col items-start gap-1 sm:items-end">
      <div className="flex items-center gap-2">
        <ExportButton
          action="download"
          activeAction={activeAction}
          icon={<Download className="h-4 w-4" />}
          label="Download post image"
          onClick={runExport}
        />
        <ExportButton
          action="copy"
          activeAction={activeAction}
          icon={<Clipboard className="h-4 w-4" />}
          label="Copy post image"
          onClick={runExport}
        />
      </div>
      {message ? <div className="max-w-64 text-xs text-stone-600">{message}</div> : null}
      {renderCard && sourceQrCodeDataUrl ? (
        <PostExportCard
          post={post}
          exportHtml={exportHtml}
          qrCodeDataUrl={sourceQrCodeDataUrl}
          ref={cardRef}
        />
      ) : null}
    </div>
  );
}

function ExportButton({
  action,
  activeAction,
  icon,
  label,
  onClick
}: {
  action: ExportAction;
  activeAction: ExportAction | null;
  icon: ReactNode;
  label: string;
  onClick: (action: ExportAction) => void;
}) {
  const busy = activeAction !== null;
  const isActive = activeAction === action;
  return (
    <button
      type="button"
      onClick={() => onClick(action)}
      disabled={busy}
      className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-stone-300 bg-[#fffdf8] text-stone-800 transition hover:bg-stone-50 focus:outline-none focus:ring-2 focus:ring-emerald-600 disabled:cursor-wait disabled:opacity-70"
      title={label}
      aria-label={label}
    >
      {isActive ? <Loader2 className="h-4 w-4 animate-spin" /> : icon}
    </button>
  );
}

const PostExportCard = forwardRef<
  HTMLDivElement,
  {
    post: PostDetail;
    exportHtml: string;
    qrCodeDataUrl: string;
  }
>(({ post, exportHtml, qrCodeDataUrl }, ref) => (
  <div
    ref={ref}
    aria-hidden="true"
    className="post-export-card fixed left-[-10000px] top-0 w-[760px] bg-[#fbfaf7] p-8 text-stone-900"
  >
    <div className="border-b border-stone-300 pb-5">
      <div className="mb-2 text-xs font-semibold uppercase text-emerald-800">
        {post.forum.toUpperCase()}
      </div>
      <h1 className="text-3xl font-semibold leading-10 text-stone-950">{displayTitle(post)}</h1>
      <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-sm text-stone-600">
        {metadataItems(post).map((item) => (
          <span key={item}>{item}</span>
        ))}
      </div>
      <div className="mt-4 flex items-center gap-4 rounded-md border border-stone-200 bg-white p-3">
        <img
          src={qrCodeDataUrl}
          alt=""
          width={QR_CODE_SIZE}
          height={QR_CODE_SIZE}
          className="h-[92px] w-[92px] shrink-0"
        />
        <div className="min-w-0 text-sm leading-6 text-stone-700">
          <div className="font-medium text-emerald-800">Source</div>
          <div className="break-all text-stone-600">{post.url}</div>
          <div className="mt-1 text-xs uppercase tracking-wide text-stone-500">
            Scan to open original post
          </div>
        </div>
      </div>
    </div>
    <div className="py-6">
      {exportHtml ? (
        <div
          className="reader-body reader-body-html text-[17px] leading-8 text-stone-900"
          dangerouslySetInnerHTML={{ __html: exportHtml }}
        />
      ) : post.body_text ? (
        <div className="reader-body whitespace-pre-wrap text-[17px] leading-8 text-stone-900">
          {post.body_text}
        </div>
      ) : (
        <div className="text-sm text-stone-500">No body text.</div>
      )}
    </div>
  </div>
));

PostExportCard.displayName = "PostExportCard";
