"use client";
import Link from "next/link";
import { useState } from "react";
import { money, rating, toFa } from "@/lib/format";
import { ICart, IPart, IStar } from "./Icon";

export type Product = {
  id: number;
  name: string;
  slug: string;
  brand: string;
  sku: string;
  price: number;
  compare_at_price?: number;
  discount_percent: number;
  unit: string;
  min_order_qty: number;
  carton_qty?: number | null;
  rating_avg: string;
  rating_count: number;
  sold_count: number;
  in_stock: boolean;
  is_new?: boolean;
  thumbnail?: string | null;
};

export default function ProductCard({
  p,
  onAdd,
}: {
  p: Product;
  onAdd?: (p: Product) => void;
}) {
  const [imgOk, setImgOk] = useState(true);
  const [added, setAdded] = useState(false);
  const available = p.in_stock && p.price > 0;

  const handleAdd = () => {
    if (added) return;
    onAdd?.(p);
    setAdded(true);
    setTimeout(() => setAdded(false), 1800);
  };

  return (
    <div className="card">
      {/* 1) image */}
      <Link href={`/product/${encodeURIComponent(p.slug)}`} className="thumb" tabIndex={0}>
        {p.thumbnail && imgOk
          ? <img src={p.thumbnail} alt={p.name} loading="lazy" onError={() => setImgOk(false)} />
          : <span className="noimg"><IPart size={30} /><span>تصویر ثبت نشده است</span></span>}
        {!p.in_stock && <span className="tag oos-tag">ناموجود</span>}
        {p.in_stock && p.discount_percent > 0 && <span className="tag">٪{toFa(p.discount_percent)}</span>}
        {p.in_stock && !p.discount_percent && p.is_new && <span className="tag new-tag">جدید</span>}
      </Link>
      <div className="body">
        {/* 2) brand */}
        <div className="brand mono">{p.brand}</div>
        {/* 3) name */}
        <Link href={`/product/${encodeURIComponent(p.slug)}`} className="name">{toFa(p.name)}</Link>
        {/* 4) sku */}
        <div className="sku mono">{toFa(p.sku)}</div>
        {/* 5) stock status + rating, on one clear line */}
        <div className="rate">
          <span className={`stock-dot ${p.in_stock ? "ok" : "no"}`}>{p.in_stock ? "موجود" : "ناموجود"}</span>
          {p.rating_count > 0 && (
            <><span className="stars"><IStar /></span><b>{rating(p.rating_avg)}</b><span style={{ color: "var(--muted)" }}>({toFa(p.rating_count)})</span></>
          )}
          {p.sold_count > 0 && <span style={{ color: "var(--muted)" }}>· {toFa(p.sold_count)} فروش</span>}
        </div>
        <div style={{ marginTop: "auto" }}>
          {/* 6) price */}
          <div className="price">
            {available ? (
              <>
                <span className="now mono">{money(p.price)}</span>
                <span className="u">تومان</span>
                {p.compare_at_price ? <span className="old mono">{money(p.compare_at_price)}</span> : null}
              </>
            ) : (
              <span className="callprice">برای استعلام قیمت تماس بگیرید</span>
            )}
          </div>
          {/* 7) min order / carton qty */}
          <div className="moq">
            <span>حداقل سفارش: {toFa(p.min_order_qty)} {p.unit === "liter" ? "لیتر" : "عدد"}</span>
            {p.carton_qty ? <><span className="moq-sep">·</span><span>کارتن {toFa(p.carton_qty)} عددی</span></> : null}
          </div>
          {/* 8) action */}
          {available ? (
            <button className={`add ${added ? "added" : ""}`} onClick={handleAdd}>
              {added ? (
                <><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6"><path d="M5 12l5 5L20 7" /></svg> افزوده شد</>
              ) : (
                <><ICart size={16} /> افزودن به سبد</>
              )}
            </button>
          ) : (
            <Link href={`/product/${encodeURIComponent(p.slug)}`} className="add inquire">
              مشاهده و استعلام ›
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
