import { sanitizeBodyHtml } from "./bodyHtml";

export function postImageProxyPath(postId: string, src: string): string {
  const url = new URL(`/api/posts/${encodeURIComponent(postId)}/image`, window.location.origin);
  url.searchParams.set("src", src);
  return `${url.pathname}${url.search}`;
}

export function sanitizePostBodyHtmlForImageExport(
  postId: string,
  html: string | null
): string {
  const sanitizedHtml = sanitizeBodyHtml(html);
  if (!sanitizedHtml) {
    return "";
  }

  const template = document.createElement("template");
  template.innerHTML = sanitizedHtml;

  for (const image of Array.from(template.content.querySelectorAll("img"))) {
    const src = image.getAttribute("src");
    if (!src) {
      continue;
    }
    image.setAttribute("src", postImageProxyPath(postId, src));
    image.setAttribute("loading", "eager");
    image.removeAttribute("data-reader-image");
    image.removeAttribute("role");
    image.removeAttribute("tabindex");
    image.removeAttribute("aria-label");
  }

  return template.innerHTML.trim();
}
