"use client";
import Link from "next/link";
import { Fragment, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { money, toFa } from "@/lib/format";
import { Product } from "@/components/ProductCard";
import ProductRow from "@/components/ProductRow";
import HeroSlider from "@/components/HeroSlider";
import CarFinder from "@/components/CarFinder";
import TrustSection from "@/components/TrustSection";
import { ICredit, IShield, ITruck } from "@/components/Icon";

type Stats = { products: number; brands: number; categories: number; shops: number };

// 1200 -> 1,200 ; 12000 -> 12K, rendered with Persian digits  (keeps the headline compact but truthful)
const compact = (n: number) =>
  n >= 1000 ? toFa((n / 1000).toFixed(n % 1000 === 0 ? 0 : 1)) + "K" : toFa(n);

const FEATURES = [
  { t: "ضمانت اصالت کالا", s: "تضمین ۱۰۰٪ اورجینال", icon: <IShield /> },
  { t: "ارسال به سراسر کشور", s: "پست پیشتاز و تیپاکس", icon: <ITruck /> },
  { t: "پرداخت اعتباری", s: "تسویه دوره‌ای همکاران", icon: <ICredit /> },
  { t: "ضمانت مرجوعی", s: "بازگشت ۷ روزه کالا", icon: <IShield /> },
];

const STAT_ITEMS: { key: keyof Stats; label: string }[] = [
  { key: "products", label: "کد کالا" },
  { key: "brands", label: "برند معتبر" },
  { key: "categories", label: "دسته‌بندی" },
  { key: "shops", label: "فروشنده فعال" },
];

export default function Home() {
  const [featured, setFeatured] = useState<Product[]>([]);
  const [newest, setNewest] = useState<Product[]>([]);
  const [loadingRows, setLoadingRows] = useState(true);
  const [stats, setStats] = useState<Stats | null>(null);
  const [promo, setPromo] = useState<Product | null>(null);

  useEffect(() => {
    api.get<Stats>("/catalog/stats/", { auth: false }).then(setStats).catch(() => {});
    // Ask for 16 so each carousel is comfortably past the 10-item minimum even
    // after out-of-stock items are filtered out.
    Promise.allSettled([
      api.get("/catalog/products/?ordering=-sold_count&page_size=16", { auth: false }),
      api.get("/catalog/products/?ordering=-created_at&page_size=16", { auth: false }),
    ])
      .then(([best, fresh]) => {
        const bestList: Product[] = best.status === "fulfilled" ? best.value.results || [] : [];
        const freshList: Product[] = fresh.status === "fulfilled" ? fresh.value.results || [] : [];
        setFeatured(bestList);
        setNewest(freshList);
        // The promo card shows a REAL discounted product — never an invented one.
        const discounted = [...bestList, ...freshList].find((p) => p.in_stock && p.discount_percent > 0);
        setPromo(discounted || null);
      })
      .finally(() => setLoadingRows(false));
  }, []);

  return (
    <div className="view">
      <section style={{ marginTop: 0 }}>
        <div className="hero">
          <HeroSlider />
          <div className="hero-side">
            {promo ? (
              <Link href={`/product/${encodeURIComponent(promo.slug)}`} className="promo promo-product">
                <div className="pp-top">
                  <span className="pp-badge">٪{toFa(promo.discount_percent)} تخفیف</span>
                  <div className="pp-img">
                    {promo.thumbnail
                      ? <img src={promo.thumbnail} alt={promo.name} />
                      : <span className="noimg" style={{ height: "100%" }} />}
                  </div>
                  <div className="pp-name">{toFa(promo.name)}</div>
                  <div className="pp-price">
                    <b className="mono">{money(promo.price)}</b> تومان
                    {promo.compare_at_price && <span className="mono old">{money(promo.compare_at_price)}</span>}
                  </div>
                </div>
                <span className="btn" style={{ background: "#fff", color: "var(--orange)", fontWeight: 800 }}>مشاهده و خرید ›</span>
              </Link>
            ) : (
              <Link href="/shop" className="promo">
                <div><div className="t">پیشنهاد ویژه این هفته</div><div className="b">مشاهده جدیدترین<br />تخفیف‌های فروشگاه</div></div>
                <span className="btn" style={{ background: "#fff", color: "var(--orange)", fontWeight: 800 }}>مشاهده تخفیف‌ها ›</span>
              </Link>
            )}

            {/* Live counts from the API — no invented numbers, no bare zero/dash. */}
            <div className="stats">
              {!stats
                ? STAT_ITEMS.map((s) => <div className="s skel" key={s.key} style={{ height: 46 }} />)
                : STAT_ITEMS.filter((s) => (stats[s.key] || 0) > 0).map((s, idx, arr) => (
                    <Fragment key={s.key}>
                      <div className="s">
                        <div className="v mono">{compact(stats[s.key])}</div>
                        <div className="k">{s.label}</div>
                      </div>
                      {idx < arr.length - 1 && <div className="sep" />}
                    </Fragment>
                  ))}
            </div>
          </div>
        </div>
        <div className="features">
          {FEATURES.map((f, i) => (
            <div className="feature" key={i}>
              <div className="ic">{f.icon}</div>
              <div><div className="tt">{f.t}</div><div className="ss">{f.s}</div></div>
            </div>
          ))}
        </div>
      </section>

      <CarFinder />

      <ProductRow
        title="پرفروش‌ترین قطعات"
        items={featured}
        loading={loadingRows}
        href="/shop?ordering=-sold_count"
      />

      <ProductRow
        title="جدیدترین قطعات"
        items={newest}
        loading={loadingRows}
        href="/shop?ordering=-created_at"
        accent="var(--orange)"
      />

      <TrustSection />
    </div>
  );
}
