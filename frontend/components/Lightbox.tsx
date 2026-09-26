"use client";
// Full-screen product image viewer with zoom & pan, in the style shoppers know
// from large Iranian marketplaces.
//
// Interactions supported:
//   * wheel / pinch     -> zoom around the pointer
//   * drag              -> pan (only meaningful while zoomed in)
//   * double-click/tap  -> toggle between fit and 2.5x
//   * arrow keys        -> previous / next image
//   * Esc               -> close
//
// Zoom is applied as a CSS transform on the <img>, so there is no re-decoding
// and it stays smooth on a phone.
import { useCallback, useEffect, useRef, useState } from "react";

const MIN = 1;
const MAX = 5;
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

export default function Lightbox({
  images,
  index,
  alt,
  onClose,
  onIndex,
}: {
  images: { id?: number; image: string }[];
  index: number;
  alt: string;
  onClose: () => void;
  onIndex: (i: number) => void;
}) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null);
  const pinch = useRef<{ dist: number; zoom: number } | null>(null);
  const stage = useRef<HTMLDivElement>(null);
  // Mirrors "a drag or pinch is in progress" as state: refs do not trigger a
  // render, so the cursor and transition must not be derived from them.
  const [gesturing, setGesturing] = useState(false);

  const reset = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  // A different image always starts fitted again.
  useEffect(reset, [index, reset]);

  const step = useCallback(
    (dir: 1 | -1) => {
      if (images.length < 2) return;
      onIndex((index + dir + images.length) % images.length);
    },
    [index, images.length, onIndex]
  );

  // Keyboard + body scroll lock while open.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      // RTL layout: ArrowLeft advances, ArrowRight goes back.
      else if (e.key === "ArrowLeft") step(1);
      else if (e.key === "ArrowRight") step(-1);
      else if (e.key === "+" || e.key === "=") setZoom((z) => clamp(z + 0.5, MIN, MAX));
      else if (e.key === "-") setZoom((z) => clamp(z - 0.5, MIN, MAX));
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose, step]);

  // Zoom toward the cursor so the point under it stays put.
  const wheelZoom = (e: React.WheelEvent) => {
    e.preventDefault();
    const box = stage.current?.getBoundingClientRect();
    if (!box) return;
    const next = clamp(zoom * (e.deltaY < 0 ? 1.18 : 1 / 1.18), MIN, MAX);
    const ox = e.clientX - box.left - box.width / 2;
    const oy = e.clientY - box.top - box.height / 2;
    const ratio = next / zoom;
    setPan(next === MIN ? { x: 0, y: 0 } : { x: ox - (ox - pan.x) * ratio, y: oy - (oy - pan.y) * ratio });
    setZoom(next);
  };

  const onPointerDown = (e: React.PointerEvent) => {
    if (zoom === MIN) return;
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
    drag.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y };
    setGesturing(true);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (!drag.current) return;
    setPan({
      x: drag.current.px + (e.clientX - drag.current.x),
      y: drag.current.py + (e.clientY - drag.current.y),
    });
  };
  const endDrag = () => { drag.current = null; setGesturing(false); };

  // Two-finger pinch on touch devices.
  const touchStart = (e: React.TouchEvent) => {
    if (e.touches.length !== 2) return;
    const [a, b] = [e.touches[0], e.touches[1]];
    pinch.current = { dist: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY), zoom };
    setGesturing(true);
  };
  const touchMove = (e: React.TouchEvent) => {
    if (e.touches.length !== 2 || !pinch.current) return;
    const [a, b] = [e.touches[0], e.touches[1]];
    const dist = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
    const next = clamp(pinch.current.zoom * (dist / pinch.current.dist), MIN, MAX);
    setZoom(next);
    if (next === MIN) setPan({ x: 0, y: 0 });
  };
  const touchEnd = () => { pinch.current = null; setGesturing(false); };

  const toggleZoom = () => (zoom > MIN ? reset() : setZoom(2.5));

  return (
    <div className="lb" onClick={onClose}>
      <div className="lb-bar" onClick={(e) => e.stopPropagation()}>
        {/* dir=ltr: the string is «5 / 11», but inside the RTL bar the browser
            reorders it to «11 / 5» and it reads as the wrong image number. */}
        <span className="lb-count mono" dir="ltr">
          {images.length > 1 ? `${index + 1} / ${images.length}` : ""}
        </span>
        <div className="lb-tools">
          <button onClick={() => setZoom((z) => clamp(z - 0.5, MIN, MAX))} disabled={zoom <= MIN} aria-label="کوچک‌نمایی" title="کوچک‌نمایی">
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><path d="M8 11h6M21 21l-4.3-4.3" /></svg>
          </button>
          <span className="lb-pct mono">{Math.round(zoom * 100)}٪</span>
          <button onClick={() => setZoom((z) => clamp(z + 0.5, MIN, MAX))} disabled={zoom >= MAX} aria-label="بزرگ‌نمایی" title="بزرگ‌نمایی">
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><path d="M8 11h6M11 8v6M21 21l-4.3-4.3" /></svg>
          </button>
          <button onClick={reset} disabled={zoom === MIN} aria-label="اندازه اصلی" title="اندازه اصلی">
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 9V5a2 2 0 0 1 2-2h4M21 9V5a2 2 0 0 0-2-2h-4M3 15v4a2 2 0 0 0 2 2h4M21 15v4a2 2 0 0 1-2 2h-4" /></svg>
          </button>
          <button onClick={onClose} aria-label="بستن" title="بستن (Esc)">
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
          </button>
        </div>
      </div>

      <div
        className="lb-stage"
        ref={stage}
        onClick={(e) => e.stopPropagation()}
        onWheel={wheelZoom}
        onDoubleClick={toggleZoom}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerLeave={endDrag}
        onTouchStart={touchStart}
        onTouchMove={touchMove}
        onTouchEnd={touchEnd}
        style={{ cursor: zoom > MIN ? (gesturing ? "grabbing" : "grab") : "zoom-in" }}
      >
        <img
          src={images[index]?.image}
          alt={alt}
          draggable={false}
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transition: gesturing ? "none" : "transform .18s ease-out",
          }}
        />
      </div>

      {images.length > 1 && (
        <>
          <button className="lb-nav next" onClick={(e) => { e.stopPropagation(); step(1); }} aria-label="بعدی">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 6l-6 6 6 6" /></svg>
          </button>
          <button className="lb-nav prev" onClick={(e) => { e.stopPropagation(); step(-1); }} aria-label="قبلی">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 6l6 6-6 6" /></svg>
          </button>
          <div className="lb-thumbs" onClick={(e) => e.stopPropagation()}>
            {images.map((img, i) => (
              <button key={img.id ?? i} className={i === index ? "on" : ""} onClick={() => onIndex(i)}>
                <img src={img.image} alt="" draggable={false} />
              </button>
            ))}
          </div>
        </>
      )}

      <div className="lb-hint">برای بزرگ‌نمایی دوبار کلیک کنید یا از اسکرول استفاده کنید</div>
    </div>
  );
}
