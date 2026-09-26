"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { toast } from "@/lib/ui";
import { useAuth } from "@/lib/auth";
import { money, toFa } from "@/lib/format";
import CheckoutSteps from "@/components/CheckoutSteps";

export default function CartPage() {
  const { user, loading, refreshCart } = useAuth();
  const router = useRouter();
  const [cart, setCart] = useState<any>(null);
  // Keyed by the cart LINE's own id, not the product id — two colours of the
  // same product are two rows, and only the one actually being changed
  // should grey out while its request is in flight.
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = () => api.get("/orders/cart/").then(setCart).catch(() => {});

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
    else if (user) load();
  }, [user, loading, router]);

  const setQty = async (item: any, quantity: number) => {
    setBusyId(item.id);
    try {
      await api.patch("/orders/cart/", { product: item.product, color: item.color, quantity });
      await load();
      refreshCart();
    } finally {
      setBusyId(null);
    }
  };
  const remove = async (item: any) => {
    if (!window.confirm(`«${item.product_name}» از سبد خرید حذف شود؟`)) return;
    setBusyId(item.id);
    try {
      await api.del("/orders/cart/", { product: item.product, color: item.color });
      await load();
      refreshCart();
      toast("کالا از سبد حذف شد");
    } finally {
      setBusyId(null);
    }
  };

  if (!cart) return <div className="center-empty">در حال بارگذاری…</div>;
  if (!cart.items.length)
    return (
      <div className="view" style={{ maxWidth: 560, margin: "40px auto" }}>
        <div className="panel center-empty" style={{ padding: "60px 30px" }}>
          <div style={{ fontSize: 48 }}>🛒</div>
          <b style={{ fontSize: 17, display: "block", margin: "10px 0 6px", color: "var(--ink)" }}>سبد خرید شما خالی است</b>
          <p style={{ marginTop: 0 }}>هنوز کالایی به سبد اضافه نکرده‌اید.</p>
          <Link className="btn btn-purple" href="/shop" style={{ height: 48, padding: "0 26px" }}>مشاهده محصولات</Link>
        </div>
      </div>
    );

  const hasProblem = cart.items.some((it: any) => it.problem);

  return (
    <div className="view">
      <CheckoutSteps active={0} />
      <h1 style={{ fontSize: 24, fontWeight: 800 }}>سبد خرید</h1>
      <div className="cols-cart">
        <div className="panel">
          {cart.items.map((it: any, i: number) => (
            <div key={it.id} className="cart-row" style={{ borderBottom: i < cart.items.length - 1 ? "1px solid var(--line)" : "none", opacity: busyId === it.id ? .6 : 1 }}>
              {/* thumbnail -> product page */}
              <Link href={`/product/${encodeURIComponent(it.product_slug)}`} className="cart-thumb">
                {it.thumbnail
                  ? <img src={it.thumbnail} alt={it.product_name} style={{ width: "100%", height: "100%", objectFit: "contain", padding: 6 }} />
                  : <span className="noimg" style={{ height: "100%" }}><span style={{ fontSize: 10 }}>تصویر ثبت نشده</span></span>}
              </Link>
              <div className="cart-info">
                <Link href={`/product/${encodeURIComponent(it.product_slug)}`} className="cart-name">
                  {toFa(it.product_name)}
                  {it.color_name && <span className="cart-color-tag">{toFa(it.color_name)}</span>}
                </Link>
                <dl className="cart-specs">
                  {it.brand_name && (<><dt>برند</dt><dd>{toFa(it.brand_name)}</dd></>)}
                  <dt>کد فنی</dt><dd className="mono">{toFa(it.sku)}</dd>
                  <dt>قیمت واحد</dt><dd className="mono">{money(it.unit_price)} تومان</dd>
                  {it.carton_qty ? (<><dt>کارتن</dt><dd className="mono">{toFa(it.carton_qty)} عددی</dd></>) : null}
                  {it.supplier_name && (<><dt>فروشنده</dt><dd>{toFa(it.supplier_name)}</dd></>)}
                </dl>
                {it.problem && <div className="cart-problem">⚠ {it.problem}</div>}
              </div>
              <div className="qtybox cart-qty" title="تعداد">
                <button aria-label="کاهش تعداد" disabled={it.quantity <= it.min_order_qty || busyId === it.id} onClick={() => setQty(it, it.quantity - 1)}>−</button>
                <span className="mono qv">{toFa(it.quantity)}</span>
                <button aria-label="افزایش تعداد" disabled={it.quantity >= it.stock || busyId === it.id} onClick={() => setQty(it, it.quantity + 1)}>+</button>
              </div>
              <div className="cart-linetotal">
                <span className="cart-linetotal-label">قیمت کل</span>
                <span className="mono">{money(it.line_total)}</span>
                <span className="cart-cur">تومان</span>
              </div>
              <button onClick={() => remove(it)} title="حذف از سبد" aria-label="حذف از سبد" className="cart-remove" disabled={busyId === it.id}>
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M8 6V4h8v2M6 6l1 14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-14M10 11v6M14 11v6" /></svg>
              </button>
            </div>
          ))}
          <div style={{ padding: "14px 4px 2px" }}>
            <Link href="/shop" className="cart-continue">← بازگشت به فروشگاه و افزودن کالای بیشتر</Link>
          </div>
        </div>
        <div className="panel cart-summary">
          <b style={{ fontSize: 15 }}>خلاصه سفارش</b>
          <div className="os-breakdown" style={{ marginTop: 12, paddingTop: 0, borderTop: "none" }}>
            <div className="between"><span>جمع کالاها</span><span className="mono">{money(cart.subtotal)} تومان</span></div>
            <div className="between"><span>هزینه ارسال</span><span style={{ color: "var(--muted)", fontSize: 12.5 }}>پس از انتخاب آدرس محاسبه می‌شود</span></div>
            <div className="between"><span>مالیات بر ارزش‌افزوده</span><span style={{ color: "var(--muted)", fontSize: 12.5 }}>در مرحله بعد محاسبه می‌شود</span></div>
          </div>
          <div className="between os-total"><span>مبلغ فعلی سفارش</span><span className="mono">{money(cart.subtotal)} تومان</span></div>
          {hasProblem && (
            <div className="cart-problem" style={{ marginTop: 10, fontSize: 12 }}>⚠ برخی کالاها مشکل دارند — پیش از ادامه بررسی کنید.</div>
          )}
          <Link
            className={`btn btn-orange cart-go ${hasProblem ? "disabled" : ""}`}
            href={hasProblem ? "#" : "/checkout"}
            aria-disabled={hasProblem}
            onClick={(e) => { if (hasProblem) { e.preventDefault(); toast("لطفاً ابتدا مشکلات سبد خرید را برطرف کنید."); } }}
          >
رفتن به تسویه‌حساب ←
          </Link>
        </div>
      </div>
    </div>
  );
}
