"use client";
// Digikala-style route-transition loader: a gradient progress bar on top plus
// a small spinning-gear chip. Starts when an internal link is clicked and
// finishes when the pathname actually changes.
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

export default function TopLoader() {
  const path = usePathname();
  const [state, setState] = useState<"idle" | "loading" | "done">("idle");
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Start on any same-origin link click that changes the route.
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
      const a = (e.target as HTMLElement).closest("a");
      if (!a) return;
      const href = a.getAttribute("href") || "";
      if (!href.startsWith("/") || a.target === "_blank") return;
      const next = href.split("?")[0].split("#")[0];
      if (next === location.pathname) return;
      setState("loading");
      // Safety: never let the bar hang forever (e.g. blocked navigation).
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setState("idle"), 12000);
    };
    document.addEventListener("click", onClick);
    return () => { document.removeEventListener("click", onClick); clearTimeout(timer.current); };
  }, []);

  // Pathname changed -> snap to 100% then fade out.
  useEffect(() => {
    setState((s) => (s === "loading" ? "done" : s));
    const t = setTimeout(() => setState("idle"), 350);
    return () => clearTimeout(t);
  }, [path]);

  const visible = state !== "idle";
  return (
    <>
      <div className={`toploader ${visible ? "on" : ""} ${state === "done" ? "done" : ""}`}>
        {visible && <i key={state === "loading" ? "l" : "d"} />}
      </div>
      <div className={`loader-gear ${state === "loading" ? "on" : ""}`}>
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <circle cx="12" cy="12" r="3.2" />
          <path d="M12 2v3M12 19v3M2 12h3M19 12h3M5.2 5.2l2.1 2.1M16.7 16.7l2.1 2.1M18.8 5.2l-2.1 2.1M7.3 16.7l-2.1 2.1" />
        </svg>
      </div>
    </>
  );
}
