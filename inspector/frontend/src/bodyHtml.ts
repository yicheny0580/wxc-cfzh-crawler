const WXC_BASE_URL = "https://bbs.wenxuecity.com";

const ALLOWED_TAGS = new Set([
  "a",
  "b",
  "blockquote",
  "br",
  "center",
  "code",
  "del",
  "div",
  "em",
  "font",
  "hr",
  "i",
  "img",
  "ins",
  "li",
  "ol",
  "p",
  "pre",
  "s",
  "section",
  "small",
  "span",
  "strong",
  "sub",
  "sup",
  "table",
  "tbody",
  "td",
  "tfoot",
  "th",
  "thead",
  "tr",
  "u",
  "ul"
]);

const DROP_WITH_CONTENT_TAGS = new Set([
  "base",
  "button",
  "embed",
  "form",
  "iframe",
  "input",
  "link",
  "math",
  "meta",
  "object",
  "option",
  "script",
  "select",
  "style",
  "svg",
  "textarea"
]);

const GLOBAL_ATTRIBUTES = new Set(["title"]);
const LINK_PROTOCOLS = new Set(["http:", "https:", "mailto:", "tel:"]);
const IMAGE_PROTOCOLS = new Set(["http:", "https:"]);
const SAFE_STYLE_PROPERTIES = new Set([
  "-webkit-text-size-adjust",
  "align-self",
  "background-color",
  "border-color",
  "border-radius",
  "border-style",
  "border-width",
  "caret-color",
  "color",
  "display",
  "flex",
  "flex-flow",
  "font-size",
  "font-weight",
  "height",
  "justify-content",
  "letter-spacing",
  "line-height",
  "margin",
  "margin-bottom",
  "margin-left",
  "margin-right",
  "margin-top",
  "max-width",
  "min-width",
  "overflow",
  "overflow-x",
  "overflow-y",
  "padding",
  "text-align",
  "transform",
  "vertical-align",
  "width",
  "z-index"
]);
const SAFE_STYLE_KEYWORDS = new Set([
  "auto",
  "block",
  "bold",
  "center",
  "column",
  "flex",
  "flex-end",
  "flex-start",
  "hidden",
  "inline",
  "inline-block",
  "left",
  "normal",
  "nowrap",
  "right",
  "row",
  "solid",
  "top",
  "transparent",
  "visible",
  "wrap"
]);
const SAFE_STYLE_FUNCTION_NAMES = new Set(["rgb", "rgba", "translate3d"]);
const SAFE_STYLE_VALUE = /^[-#%.,()a-z0-9\s]+$/i;

function absoluteUrl(value: string, allowedProtocols: Set<string>): string | null {
  try {
    const url = new URL(value.trim(), WXC_BASE_URL);
    if (!allowedProtocols.has(url.protocol)) {
      return null;
    }
    return url.href;
  } catch {
    return null;
  }
}

function cleanDimension(value: string): string | null {
  const trimmed = value.trim();
  if (/^\d{1,5}(?:px|%)?$/.test(trimmed)) {
    return trimmed;
  }
  return null;
}

function cleanStyleValue(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed || /(?:url|expression|javascript|behavior|binding|@import)/i.test(trimmed)) {
    return null;
  }

  if (!SAFE_STYLE_VALUE.test(trimmed)) {
    return null;
  }

  for (const match of trimmed.matchAll(/([a-z-]+)\s*\(/gi)) {
    if (!SAFE_STYLE_FUNCTION_NAMES.has(match[1].toLowerCase())) {
      return null;
    }
  }

  const withoutFunctions = trimmed.replace(/[a-z-]+\s*\([^)]*\)/gi, " ");
  const tokens = withoutFunctions.split(/\s+/).filter(Boolean);
  for (const token of tokens) {
    const bareToken = token.replace(/,$/, "").toLowerCase();
    if (SAFE_STYLE_KEYWORDS.has(bareToken)) {
      continue;
    }
    if (/^-?\d+(?:\.\d+)?(?:px|em|rem|%|deg)?$/i.test(bareToken)) {
      continue;
    }
    if (/^#[0-9a-f]{3,8}$/i.test(bareToken)) {
      continue;
    }
    return null;
  }

  return trimmed;
}

function cleanStyle(value: string): string | null {
  const declarations = value
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean);
  const cleanDeclarations: string[] = [];

  for (const declaration of declarations) {
    const separator = declaration.indexOf(":");
    if (separator === -1) {
      continue;
    }

    const property = declaration.slice(0, separator).trim().toLowerCase();
    const propertyValue = cleanStyleValue(declaration.slice(separator + 1));
    if (SAFE_STYLE_PROPERTIES.has(property) && propertyValue) {
      cleanDeclarations.push(`${property}: ${propertyValue}`);
    }
  }

  return cleanDeclarations.length ? cleanDeclarations.join("; ") : null;
}

function sanitizeAttributes(element: Element, tagName: string) {
  for (const attribute of Array.from(element.attributes)) {
    const name = attribute.name.toLowerCase();
    const value = attribute.value;

    if (name.startsWith("on") || name === "srcset") {
      element.removeAttribute(attribute.name);
      continue;
    }

    if (name === "style") {
      const style = cleanStyle(value);
      if (style) {
        element.setAttribute("style", style);
      } else {
        element.removeAttribute(attribute.name);
      }
      continue;
    }

    if (tagName === "a" && name === "href") {
      const url = absoluteUrl(value, LINK_PROTOCOLS);
      if (url) {
        element.setAttribute("href", url);
      } else {
        element.removeAttribute(attribute.name);
      }
      continue;
    }

    if (tagName === "img" && name === "src") {
      const url = absoluteUrl(value, IMAGE_PROTOCOLS);
      if (url) {
        element.setAttribute("src", url);
      } else {
        element.removeAttribute(attribute.name);
      }
      continue;
    }

    if (tagName === "img" && (name === "alt" || name === "title")) {
      continue;
    }

    if (tagName === "img" && (name === "width" || name === "height")) {
      const dimension = cleanDimension(value);
      if (dimension) {
        element.setAttribute(name, dimension);
      } else {
        element.removeAttribute(attribute.name);
      }
      continue;
    }

    if ((tagName === "td" || tagName === "th") && (name === "colspan" || name === "rowspan")) {
      const span = value.trim();
      if (/^\d{1,2}$/.test(span)) {
        element.setAttribute(name, span);
      } else {
        element.removeAttribute(attribute.name);
      }
      continue;
    }

    if (!GLOBAL_ATTRIBUTES.has(name)) {
      element.removeAttribute(attribute.name);
    }
  }

  if (tagName === "a" && element.hasAttribute("href")) {
    element.setAttribute("target", "_blank");
    element.setAttribute("rel", "noopener noreferrer");
  }

  if (tagName === "img" && element.hasAttribute("src")) {
    element.setAttribute("loading", "lazy");
    element.setAttribute("decoding", "async");
  }
}

function sanitizeNode(node: ChildNode) {
  if (node.nodeType === Node.COMMENT_NODE) {
    node.remove();
    return;
  }

  if (node.nodeType !== Node.ELEMENT_NODE) {
    return;
  }

  const element = node as Element;
  const tagName = element.tagName.toLowerCase();

  if (DROP_WITH_CONTENT_TAGS.has(tagName)) {
    element.remove();
    return;
  }

  for (const child of Array.from(element.childNodes)) {
    sanitizeNode(child);
  }

  if (!ALLOWED_TAGS.has(tagName)) {
    element.replaceWith(...Array.from(element.childNodes));
    return;
  }

  sanitizeAttributes(element, tagName);
}

export function sanitizeBodyHtml(html: string | null | undefined): string {
  if (!html?.trim()) {
    return "";
  }

  const template = document.createElement("template");
  template.innerHTML = html;

  for (const child of Array.from(template.content.childNodes)) {
    sanitizeNode(child);
  }

  return template.innerHTML.trim();
}
