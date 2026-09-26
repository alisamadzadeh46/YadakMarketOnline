"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import { useAuth } from "@/lib/auth";
import { money, toFa } from "@/lib/format";
import CheckoutSteps from "@/components/CheckoutSteps";
import { SITE } from "@/lib/site";

const EMPTY_ADDR = { title: "", receiver_name: "", receiver_phone: "", province: "", city: "", postal_code: "", line: "" };

export default function Checkout() {
  const { user, loading, refreshCart } = useAuth();
  const router = useRouter();
  const [cart, setCart] = useState<any>(null);
  const [addresses, setAddresses] = useState<any[]>([]);
  const [addrId, setAddrId] = useState<number | null>(null);
  const [newAddr, setNewAddr] = useState(EMPTY_ADDR);
  const [showAddr, setShowAddr] = useState(false);
  const [coupon, setCoupon] = useState("");
  const [couponBusy, setCouponBusy] = useState(false);
  const [appliedCoupon, setAppliedCoupon] = useState<{ code: string; discount: number } | null>(null);
  const [method, setMethod] = useState("online");
  const [pay, setPay] = useState<{ receipt: boolean; online: boolean }>({ receipt: false, online: true });
  const [checkoutCfg, setCheckoutCfg] = useState<{
    vat_percent: string;
    shipping_cost: number;
    payment_window_minutes: number;
  } | null>(null);
  const [agree, setAgree] = useState(false);
  const [busy, setBusy] = useState(false);
  const [addrError, setAddrError] = useState("");
  const [payError, setPayError] = useState("");
  const [agreeError, setAgreeError] = useState("");
  const agreeRef = useRef<HTMLLabelElement>(null);
  const addrRef = useRef<HTMLDivElement>(null);
  const payRef = useRef<HTMLDivElement>(null);
  const submittingRef = useRef(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
    if (user) {
      api.get("/orders/cart/").then(setCart);
      api.get("/orders/checkout-settings/").then(setCheckoutCfg).catch(() => {});
      api.get("/accounts/addresses/").then((d) => {
        const list = d.results || d;
        setAddresses(list);
        if (list.length) setAddrId(list[0].id);
        else setShowAddr(true);
      });
      // Which payment methods the owner currently allows for this cart.
      api.get("/suppliers/payment-info/").then((d) => {
        const m = d.methods || { receipt: false, online: true };
        setPay(m);
        setMethod(m.online ? "online" : m.receipt ? "card_to_card" : "online");
      }).catch(() => {});
    }
  }, [user, loading, router]);

  const saveAddr = async (e: React.FormEvent) => {
    e.preventDefault();
    const created = await api.post("/accounts/addresses/", newAddr);
    setAddresses([created, ...addresses]);
    setAddrId(created.id);
    setShowAddr(false);
    setNewAddr(EMPTY_ADDR);
    setAddrError("");
  };

  const applyCoupon = async () => {
    if (!coupon.trim()) return;
    setCouponBusy(true);
    try {
      const r = await api.post("/discounts/validate/", { code: coupon, amount: cart.subtotal });
      setAppliedCoupon({ code: coupon.trim(), discount: r.discount });
      toast("کد تخفیف با موفقیت اعمال شد ✓");
    } catch (e) {
      setAppliedCoupon(null);
      toast(errorMessage(e, "کد تخفیف نامعتبر است."));
    } finally {
      setCouponBusy(false);
    }
  };

  const removeCoupon = () => {
    setAppliedCoupon(null);
    setCoupon("");
  };

  const placeOrder = async () => {
    if (submittingRef.current) return;
    setAddrError(""); setPayError(""); setAgreeError("");
    if (!addrId) {
      setAddrError("لطفاً یک آدرس تحویل انتخاب کنید.");
      addrRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    if (!method || (method === "online" && !pay.online) || (method === "card_to_card" && !pay.receipt)) {
      setPayError("لطفاً روش پرداخت را مشخص کنید.");
      payRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    if (!agree) {
      setAgreeError("برای ادامه، لطفاً قوانین خرید و شرایط ارسال و مرجوعی را تأیید کنید.");
      agreeRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    submittingRef.current = true;
    setBusy(true);
    try {
      const order = await api.post("/orders/checkout/", {
        address_id: addrId,
        payment_method: method,
        coupon_code: appliedCoupon?.code || "",
      });
      refreshCart();
      router.push(`/order/${order.number}`);
    } catch (e) {
      toast(errorMessage(e));
      setBusy(false);
      submittingRef.current = false;
    }
  };

  if (!cart) return <div className="center-empty">در حال بارگذاری…</div>;
  const isCredit = method === "credit";
  const discount = appliedCoupon?.discount || 0;
  const taxable = cart.subtotal - discount;
  const vatPercent = checkoutCfg ? Number(checkoutCfg.vat_percent) : 0;
  const tax = checkoutCfg && taxable > 0 ? Math.round((taxable * vatPercent) / 100) : 0;
  const shipping = isCredit || !checkoutCfg ? 0 : checkoutCfg.shipping_cost;
  const paymentWindow = checkoutCfg?.payment_window_minutes ?? 30;
  const total = taxable + tax + shipping;
  const hasCartProblem = cart.items.some((it: any) => it.problem);

  const ctaText = busy
    ? "در حال ثبت…"
    : method === "online" ? "پرداخت و ثبت سفارش ←"
    : method === "card_to_card" ? "ثبت سفارش و دریافت اطلاعات واریز ←"
    : "ثبت سفارش اعتباری ←";

  return (
    <div className="view">
      <CheckoutSteps active={1} />
      <h1 style={{ fontSize: 24, fontWeight: 800 }}>تکمیل سفارش</h1>
      <div className="cols-cart">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {hasCartProblem && (
            <div className="panel" style={{ borderColor: "var(--red)", background: "#FEF2F2" }}>
              <b style={{ color: "var(--red)", fontSize: 13.5 }}>⚠ برخی کالاهای سبد شما مشکل دارند</b>
              <p style={{ fontSize: 12.5, color: "var(--ink-soft)", margin: "6px 0 0" }}>
                لطفاً به <a href="/cart" style={{ color: "var(--purple)", fontWeight: 700 }}>سبد خرید</a> برگردید و موجودی/تعداد را اصلاح کنید.
              </p>
            </div>
          )}

          <div className="panel" ref={addrRef}>
            <div className="between" style={{ marginBottom: 14 }}>
              <b>آدرس تحویل</b>
              <button className="btn btn-ghost" style={{ height: 36, padding: "0 14px", fontSize: 13 }} onClick={() => setShowAddr(!showAddr)}>+ افزودن آدرس جدید</button>
            </div>
            {addrError && <div className="field-error">{addrError}</div>}
            <div className="addr-grid">
              {addresses.map((a) => (
                <button type="button" key={a.id} aria-pressed={addrId === a.id} className={`addr-card ${addrId === a.id ? "on" : ""}`} onClick={() => { setAddrId(a.id); setAddrError(""); }}>
                  <span className="addr-check" aria-hidden>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
                  </span>
                  <b>{a.title}</b>
                  <span>{a.receiver_name} · {toFa(a.receiver_phone)}</span>
                  <span>{a.province}، {a.city}، {a.line}</span>
                  {a.postal_code && <span>کد پستی: {toFa(a.postal_code)}</span>}
                </button>
              ))}
            </div>
            {showAddr && (
              <form onSubmit={saveAddr} style={{ marginTop: 14, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <input className="inp" placeholder="عنوان (مثلا انبار)" required value={newAddr.title} onChange={(e) => setNewAddr({ ...newAddr, title: e.target.value })} />
                <input className="inp" placeholder="نام گیرنده" required value={newAddr.receiver_name} onChange={(e) => setNewAddr({ ...newAddr, receiver_name: e.target.value })} />
                <input className="inp" placeholder="موبایل گیرنده" required value={newAddr.receiver_phone} onChange={(e) => setNewAddr({ ...newAddr, receiver_phone: e.target.value })} />
                <input className="inp" placeholder="استان" required value={newAddr.province} onChange={(e) => setNewAddr({ ...newAddr, province: e.target.value })} />
                <input className="inp" placeholder="شهر" required value={newAddr.city} onChange={(e) => setNewAddr({ ...newAddr, city: e.target.value })} />
                <input className="inp" placeholder="کد پستی" value={newAddr.postal_code} onChange={(e) => setNewAddr({ ...newAddr, postal_code: e.target.value })} />
                <textarea className="inp" style={{ gridColumn: "1 / -1" }} placeholder="نشانی کامل" required value={newAddr.line} onChange={(e) => setNewAddr({ ...newAddr, line: e.target.value })} />
                <button className="btn btn-purple" style={{ height: 44, gridColumn: "1 / -1" }}>ذخیره آدرس</button>
              </form>
            )}
          </div>

          <div className="panel" ref={payRef}>
            <b>روش پرداخت</b>
            {payError && <div className="field-error">{payError}</div>}
            <div className="paymethods">
              {pay.online && (
                <button type="button" className={`pm-card ${method === "online" ? "on" : ""}`} onClick={() => { setMethod("online"); setPayError(""); }}>
                  <span className="pm-ic"><svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="2" y="5" width="20" height="14" rx="2.5" /><path d="M2 10h20" /></svg></span>
                  <span className="pm-txt"><b>پرداخت اینترنتی امن</b><span>پس از ثبت سفارش به درگاه بانکی منتقل می‌شوید — تا {toFa(paymentWindow)} دقیقه فرصت دارید.</span></span>
                </button>
              )}
              {pay.receipt && (
                <button type="button" className={`pm-card ${method === "card_to_card" ? "on" : ""}`} onClick={() => { setMethod("card_to_card"); setPayError(""); }}>
                  <span className="pm-ic"><svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="2" y="4" width="20" height="16" rx="2.5" /><path d="M2 9h20M6 15h4" /></svg></span>
                  <span className="pm-txt"><b>کارت به کارت</b><span>واریز به کارت فروشنده و آپلود فیش — تا {toFa(paymentWindow)} دقیقه فرصت دارید.</span></span>
                </button>
              )}
              {!pay.receipt && !pay.online && (
                <div style={{ fontSize: 13, color: "var(--muted)" }}>در حال حاضر روش پرداختی فعال نیست؛ لطفاً بعداً تلاش کنید.</div>
              )}
              {user?.role === "shopkeeper" && user?.is_approved && (
                <button type="button" className={`pm-card ${method === "credit" ? "on" : ""}`} onClick={() => { setMethod("credit"); setPayError(""); }}>
                  <span className="pm-ic"><svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></svg></span>
                  <span className="pm-txt"><b>خرید اعتباری</b><span>تسویه در مهلت تعیین‌شده توسط تامین‌کننده.</span></span>
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="panel os-panel cart-summary">
          <div className="between">
            <b>خلاصه سفارش <span className="os-count-badge">{toFa(cart.items.length)} قلم</span></b>
            <a href="/cart" style={{ fontSize: 12.5, fontWeight: 700, color: "var(--purple)" }}>ویرایش سبد خرید</a>
          </div>
          {/* item lines with image + link to the product page */}
          <div className="os-items">
            {cart.items.map((it: any) => (
              <div key={it.id} className="os-item">
                <a href={`/product/${encodeURIComponent(it.product_slug)}`} className="os-thumb">
                  {it.thumbnail ? <img src={it.thumbnail} alt="" style={{ width: "100%", height: "100%", objectFit: "contain", padding: 5 }} /> : <span className="noimg" style={{ height: "100%" }} />}
                </a>
                <div className="os-info">
                  <a href={`/product/${encodeURIComponent(it.product_slug)}`} className="os-name">{toFa(it.product_name)}</a>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                    <span className="os-qty-badge mono">{toFa(it.quantity)} عدد</span>
                    {it.color_name && <span className="cart-color-tag">{toFa(it.color_name)}</span>}
                  </div>
                </div>
                <b className="mono os-linetotal">{money(it.line_total)}</b>
              </div>
            ))}
          </div>
          <div style={{ margin: "14px 0" }}>
            {appliedCoupon ? (
              <div className="coupon-applied">
                <span>کد <b className="mono">{appliedCoupon.code}</b> اعمال شد</span>
                <button type="button" onClick={removeCoupon}>حذف</button>
              </div>
            ) : (
              <>
                <div className="flabel" style={{ marginBottom: 6 }}>کد تخفیف دارید؟</div>
                <div className="field" style={{ display: "flex", gap: 8 }}>
                  <input className="inp" placeholder="کد تخفیف" value={coupon} onChange={(e) => setCoupon(e.target.value)} disabled={couponBusy} />
                  <button className="btn btn-ghost" style={{ height: 44, padding: "0 16px", minWidth: 76 }} onClick={applyCoupon} disabled={couponBusy} type="button">
                    {couponBusy ? "…" : "اعمال"}
                  </button>
                </div>
              </>
            )}
          </div>
          <div className="os-breakdown">
            <div className="between"><span>جمع کالاها</span><span className="mono">{money(cart.subtotal)} تومان</span></div>
            {discount > 0 && <div className="between os-discount"><span>تخفیف</span><span className="mono">- {money(discount)} تومان</span></div>}
            <div className="between"><span>هزینه ارسال</span><span className="mono">{shipping > 0 ? `${money(shipping)} تومان` : "رایگان"}</span></div>
            {vatPercent > 0 && <div className="between"><span>مالیات بر ارزش‌افزوده (٪{toFa(vatPercent)})</span><span className="mono">{money(tax)} تومان</span></div>}
          </div>
          <div className="between os-total"><span>مبلغ نهایی قابل پرداخت</span><span className="mono">{money(total)} تومان</span></div>

          <label className={`agree-row ${agreeError ? "invalid" : ""}`} ref={agreeRef}>
            <input type="checkbox" checked={agree} onChange={(e) => { setAgree(e.target.checked); if (e.target.checked) setAgreeError(""); }} />
            <span>با ثبت سفارش، <a href="/pages/terms" target="_blank">قوانین خرید</a> و <a href="/pages/shipping" target="_blank">شرایط ارسال و مرجوعی</a> {SITE.shortName} را می‌پذیرم.</span>
          </label>
          {agreeError && <div className="field-error" style={{ marginTop: 8 }}>{agreeError}</div>}

          <button className="btn btn-orange cart-go" disabled={busy || hasCartProblem} onClick={placeOrder}>{ctaText}</button>
        </div>
      </div>
    </div>
  );
}
