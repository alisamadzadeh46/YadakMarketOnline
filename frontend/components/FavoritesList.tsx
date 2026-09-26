"use client";
// Wishlist grid with remove + add-to-cart.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { addToCart, toast } from "@/lib/ui";
import { toFa } from "@/lib/format";
import ProductCard from "./ProductCard";

export default function FavoritesList() {
  const [items, setItems] = useState<any[]>([]);
  const load = () => api.get("/catalog/favorites/").then((d) => setItems(d.results || d));
  useEffect(() => { load(); }, []);

  const remove = async (id: number) => {
    await api.del(`/catalog/favorites/${id}/`);
    toast("از علاقه‌مندی‌ها حذف شد");
    load();
  };

  return (
    <div className="panel">
      <div className="between" style={{ marginBottom: 18, paddingBottom: 14, borderBottom: "1px solid var(--line)" }}>
        <h2 style={{ margin: 0, fontSize: 19, fontWeight: 800 }}>علاقه‌مندی‌های من</h2>
        <span className="badge purple mono">{toFa(items.length)} کالا</span>
      </div>
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))" }}>
        {items.map((f) => (
          <div key={f.id} style={{ position: "relative" }}>
            <ProductCard p={f.product_detail} onAdd={(p) => addToCart(p.id, p.min_order_qty)} />
            <button
              onClick={() => remove(f.id)}
              style={{ position: "absolute", top: 10, left: 10, background: "var(--card)", border: "1px solid var(--line)", borderRadius: 10, width: 32, height: 32, display: "grid", placeItems: "center", color: "var(--red)", zIndex: 2 }}
              title="حذف از علاقه‌مندی"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
          </div>
        ))}
        {!items.length && (
          <div className="center-empty" style={{ gridColumn: "1 / -1" }}>
            <div style={{ fontSize: 42 }}>🤍</div>
            <p>لیست علاقه‌مندی شما خالی است.</p>
            <a className="btn btn-purple" href="/shop" style={{ height: 44, padding: "0 22px" }}>مشاهده محصولات</a>
          </div>
        )}
      </div>
    </div>
  );
}
