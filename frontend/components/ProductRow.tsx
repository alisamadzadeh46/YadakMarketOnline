"use client";
// A single-row product carousel with prev/next arrows.
//
// Native horizontal scrolling does the heavy lifting (so touch swipe and
// keyboard both work for free); the arrows just nudge scrollLeft by one
// "page". Layout is RTL, so scrollLeft counts negatively — hence the Math.abs
// arithmetic when working out whether an end has been reached.
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import ProductCard, { Product } from "./ProductCard";
import { addToCart } from "@/lib/ui";

export default function ProductRow({
  title,
  items,
  href = "/shop",
  accent = "var(--purple)",
  loading = false,
  emptyText,
}: {
  title: string;
  items: Product[];
  href?: string;
  accent?: string;
  loading?: boolean;
  emptyText?: string;
}) {
  const track = useRef<HTMLDivElement>(null);
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(false);

  const sync = useCallback(() => {
    const el = track.current;
    if (!el) return;
    const pos = Math.abs(el.scrollLeft);
    const max = el.scrollWidth - el.clientWidth;
    setAtStart(pos < 8);
    setAtEnd(pos > max - 8);
  }, []);

  useEffect(() => {
    sync();
    const el = track.current;
    if (!el) return;
    el.addEventListener("scroll", sync, { passive: true });
    window.addEventListener("resize", sync);
    return () => {
      el.removeEventListener("scroll", sync);
      window.removeEventListener("resize", sync);
    };
  }, [sync, items.length]);

  const nudge = (dir: 1 | -1) => {
    const el = track.current;
    if (!el) return;
    // Scroll by ~90% of a viewport so a partial card stays visible as a hint.
    el.scrollBy({ left: dir * el.clientWidth * 0.9, behavior: "smooth" });
  };

  // When there is nothing to show: hide entirely UNLESS a caller wants the
  // section kept with a fallback message (product page keeps "related products").
  const empty = !loading && !items.length;
  if (empty && !emptyText) return null;

  return (
    <section>
      <div className="sec-head">
        <h2>
          <span className="bar" style={{ background: `linear-gradient(${accent},var(--orange))` }} />
          {title}
        </h2>
        <div className="row" style={{ gap: 8, alignItems: "center" }}>
          <Link href={href}>مشاهده همه ›</Link>
          <div className="rowbtns" style={empty ? { display: "none" } : undefined}>
            {/* RTL: "previous" moves the track to the right. */}
            <button onClick={() => nudge(1)} disabled={atStart} aria-label="قبلی">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 6l6 6-6 6" /></svg>
            </button>
            <button onClick={() => nudge(-1)} disabled={atEnd} aria-label="بعدی">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 6l-6 6 6 6" /></svg>
            </button>
          </div>
        </div>
      </div>

      {empty ? (
        <div className="prow-empty">{emptyText}</div>
      ) : (
      <div className="prow-wrap">
        <div className="prow" ref={track}>
          {loading
            ? Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="skel prow-item" style={{ height: 320 }} />
              ))
            : items.map((p) => (
                <div className="prow-item" key={p.id}>
                  <ProductCard p={p} onAdd={(pr) => addToCart(pr.id, pr.min_order_qty)} />
                </div>
              ))}
        </div>
      </div>
      )}
    </section>
  );
}
