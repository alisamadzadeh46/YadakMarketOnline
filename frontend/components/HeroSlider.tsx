"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

type Slide = { badge: string; title: React.ReactNode; text: string; button_text?: string; button_link?: string };

// Fallback slides shown until the supplier defines slides in the CMS panel.
const SLIDES: Slide[] = [
  {
    badge: "مرجع پخش عمده لوازم یدکی",
    title: (<>قطعه اصل، قیمت عمده،<br /><span>تحویل سریع</span></>),
    text: "بیش از ۱۲٬۰۰۰ کد کالای اصل با ضمانت اصالت — عمده‌فروشی برای فروشگاه‌ها و تعمیرگاه‌ها.",
  },
  {
    badge: "نمایندگی رسمی برندها",
    title: (<>ضمانت اصالت،<br /><span>خرید مطمئن</span></>),
    text: "همه کالاها با فاکتور رسمی و مرجوعی ۷ روزه — پشتیبانی فنی برای فروشگاه‌ها و تعمیرگاه‌ها.",
  },
  {
    badge: "ویژه همکاران",
    title: (<>قیمت پلکانی عمده،<br /><span>پرداخت اعتباری</span></>),
    text: "با ثبت‌نام به‌عنوان فروشگاه، از قیمت عمده و خرید اعتباری بهره‌مند شوید.",
  },
];

const AUTOPLAY_MS = 5500;

export default function HeroSlider() {
  const [i, setI] = useState(0);
  const [slides, setSlides] = useState<Slide[]>(SLIDES);
  const [paused, setPaused] = useState(false);
  const touchX = useRef<number | null>(null);

  // Load CMS-managed slides; keep the static fallback when none exist.
  useEffect(() => {
    api.get("/cms/slides/", { auth: false }).then((rows: any[]) => {
      if (rows?.length) {
        setSlides(rows.map((r) => ({
          badge: r.badge,
          title: (<>{r.title}{r.highlight ? (<><br /><span>{r.highlight}</span></>) : null}</>),
          text: r.text,
          button_text: r.button_text,
          button_link: r.button_link,
        })));
      }
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (paused) return;
    const t = setInterval(() => setI((v) => (v + 1) % slides.length), AUTOPLAY_MS);
    return () => clearInterval(t);
  }, [slides.length, paused]);

  const next = () => setI((v) => (v + 1) % slides.length);
  const prev = () => setI((v) => (v - 1 + slides.length) % slides.length);

  const onTouchStart = (e: React.TouchEvent) => { touchX.current = e.touches[0].clientX; };
  const onTouchEnd = (e: React.TouchEvent) => {
    if (touchX.current == null) return;
    const dx = e.changedTouches[0].clientX - touchX.current;
    // RTL layout: a right-swipe (positive dx) should feel like "previous".
    if (Math.abs(dx) > 40) (dx > 0 ? prev : next)();
    touchX.current = null;
  };

  const s = slides[i % slides.length];
  return (
    <div
      className="hero-main"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
    >
      <div key={i} className="hero-slide">
        <span className="chip"><span className="dot" /> {s.badge}</span>
        <h1>{s.title}</h1>
        <p>{s.text}</p>
      </div>
      <div className="row" style={{ marginTop: 6 }}>
        <Link className="btn btn-orange" href="/shop" style={{ height: 56, padding: "0 26px", fontSize: 15.5 }}>مشاهده محصولات</Link>
        <Link className="btn hero-secondary" href="/register" style={{ height: 56, padding: "0 24px", fontSize: 14.5 }}>ثبت‌نام فروشگاه</Link>
      </div>

      {slides.length > 1 && (
        <div className="hero-dots">
          {slides.map((_, k) => (
            <button key={k} className={k === i ? "on" : ""} onClick={() => setI(k)} aria-label={`اسلاید ${k + 1}`} />
          ))}
        </div>
      )}
    </div>
  );
}
