import { ArrowUp } from "lucide-react";
import { useEffect, useState } from "react";

const SHOW_AFTER_SCROLL_Y = 96;
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

export function BackToTopButton() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const syncVisibility = () => {
      setVisible(window.scrollY > SHOW_AFTER_SCROLL_Y);
    };

    syncVisibility();
    window.addEventListener("scroll", syncVisibility, { passive: true });
    return () => window.removeEventListener("scroll", syncVisibility);
  }, []);

  if (!visible) {
    return null;
  }

  const handleClick = () => {
    const prefersReducedMotion = window.matchMedia(REDUCED_MOTION_QUERY).matches;
    window.scrollTo({
      top: 0,
      behavior: prefersReducedMotion ? "auto" : "smooth"
    });
  };

  return (
    <button
      type="button"
      aria-label="Back to top"
      title="Back to top"
      onClick={handleClick}
      className="fixed bottom-4 right-4 z-40 inline-flex h-11 w-11 items-center justify-center rounded-md border border-stone-300 bg-[#fffdf8] text-stone-800 shadow-lg shadow-stone-950/10 transition hover:bg-white hover:text-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:ring-offset-2 focus:ring-offset-[#f6f3ed] sm:bottom-5 sm:right-5"
    >
      <ArrowUp className="h-5 w-5" />
    </button>
  );
}
