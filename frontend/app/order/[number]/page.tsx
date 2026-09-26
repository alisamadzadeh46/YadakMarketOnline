"use client";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorMessage, errorStatus } from "@/lib/api";
import { toast } from "@/lib/ui";
import { money, toFa, faDate, faDateTime } from "@/lib/format";
import CheckoutSteps from "@/components/CheckoutSteps";

const PAY_LABEL: Record<string, string> = {
  online: "پرداخت آنلاین",
  card_to_card: "کارت به کارت",
  credit: "خرید اعتباری",
};

const STATUS_BADGE: Record<string, string> = {
  pending_payment: "amber",
  receipt_uploaded: "purple",
  confirmed: "green",
  processing: "amber",
  shipped: "green",
  delivered: "green",
  canceled: "red",
  credit: "purple",
};

// Order lifecycle as the buyer experiences it. `canceled` and `credit` are not
// points on this line, so they render their own banner instead.
const FLOW = [
  { key: "placed", label: "ثبت سفارش" },
  { key: "paid", label: "پرداخت" },
  { key: "processing", label: "آماده‌سازی" },
  { key: "shipped", label: "ارسال" },
  { key: "delivered", label: "تحویل" },
];
// Number of steps already COMPLETED — the step at this index is the one in
// progress. `delivered` is 5 (past the end) so the whole line reads as done.
const REACHED: Record<string, number> = {
  pending_payment: 1, receipt_uploaded: 1,
  confirmed: 2, credit: 2, processing: 2,
  shipped: 3, delivered: 5,
};

function OrderProgress({ status }: { status: string }) {
  const at = REACHED[status] ?? 0;
  return (
    <ol className="oflow" aria-label="وضعیت سفارش">
      {FLOW.map((s, i) => (
        <li key={s.key} className={i < at ? "done" : i === at ? "now" : ""}>
          <span className="oflow-dot">
            {i < at ? (
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.5 10 17.5 19.5 7.5" /></svg>
            ) : (
              toFa(i + 1)
            )}
          </span>
          <span className="oflow-lbl">{s.label}</span>
        </li>
      ))}
    </ol>
  );
}

/** Official gateway badges, served from our own /public — no CSP entry needed
 *  and nothing breaks if the provider's CDN is unreachable from Iran. */
function GatewayLogo({ id }: { id: string }) {
  const src =
    id === "zarinpal" ? "/zarinpal-trust.png"
    : id === "bitpay" ? "/bitpay-trust.svg"
    : "";
  if (!src) return null;
  return <img src={src} alt="" aria-hidden style={{ height: 40, width: "auto" }} />;
}

export default function OrderPage() {
  const { number } = useParams<{ number: string }>();
  const [order, setOrder] = useState<any>(null);
  const [pay, setPay] = useState<any>(null);
  const [left, setLeft] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [ref, setRef] = useState("");
  const [payBusy, setPayBusy] = useState(false);
  const [gateways, setGateways] = useState<{ id: string; title: string; subtitle: string }[]>([]);
  const [gateway, setGateway] = useState("");
  const [notFound, setNotFound] = useState(false);
  const router = useRouter();
  const timer = useRef<ReturnType<typeof setInterval>>(undefined);

  // An order belongs to one buyer. The API enforces that (401 when signed out,
  // and the queryset is filtered to request.user), but the page used to sit on
  // "loading…" forever in that case instead of saying so — send the
  // visitor to sign in, and back here afterwards.
  const load = useCallback(() =>
    api.get(`/orders/orders/${number}/`)
      .then((o) => { setOrder(o); setLeft(o.seconds_left); })
      .catch((err) => {
        if (errorStatus(err) === 401 || errorStatus(err) === 403) {
          router.replace(`/login?next=${encodeURIComponent(`/order/${number}`)}`);
        } else if (errorStatus(err) === 404) {
          setNotFound(true);
        } else {
          toast(errorMessage(err, "بارگذاری سفارش با خطا مواجه شد."));
        }
      }), [number, router]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    // Supplier's card/account/IBAN for the card-to-card box (panel-editable).
    api.get("/suppliers/payment-info/").then(setPay).catch(() => {});
    // Which gateways the owner currently offers, and which is preselected.
    api.get("/payments/gateways/")
      .then((r) => { setGateways(r.gateways || []); setGateway(r.default || r.gateways?.[0]?.id || ""); })
      .catch(() => {});
  }, [number]);

  const copy = (v: string, label: string) => {
    navigator.clipboard?.writeText(v).then(() => toast(`${label} کپی شد ✓`));
  };

  useEffect(() => {
    if (order?.status === "pending_payment" && left > 0) {
      timer.current = setInterval(() => setLeft((s) => Math.max(0, s - 1)), 1000);
      return () => clearInterval(timer.current);
    }
  }, [order, left]);

  if (notFound)
    return (
      <div className="center-empty">
        سفارشی با این کد رهگیری برای حساب شما پیدا نشد.
      </div>
    );
  if (!order) return <div className="center-empty">در حال بارگذاری…</div>;

  const mm = String(Math.floor(left / 60)).padStart(2, "0");
  const ss = String(left % 60).padStart(2, "0");
  // Newest attempt first (the API orders by -created_at).
  const lastTxn = order.payment_transactions?.[0];
  const paidTxn = order.payment_transactions?.find((t: any) => t.status === "success");
  const unpaid = order.status === "pending_payment" || order.status === "receipt_uploaded";

  const payOnline = async () => {
    setPayBusy(true);
    try {
      const r = await api.post(`/payments/start/${number}/`, gateway ? { gateway } : {});
      window.location.href = r.redirect_url;
    } catch (err) {
      toast(errorMessage(err));
      setPayBusy(false);
    }
  };

  const upload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return toast("لطفا تصویر فیش را انتخاب کنید");
    const fd = new FormData();
    fd.append("image", file);
    if (ref) fd.append("reference_number", ref);
    try {
      await api.post(`/orders/orders/${number}/receipt/`, fd);
      toast("فیش با موفقیت آپلود شد ✓");
      load();
    } catch (err) {
      toast(errorMessage(err));
    }
  };

  return (
    <div className="view" style={{ maxWidth: 720, margin: "0 auto" }}>
      {/* CheckoutSteps is the *checkout funnel*; once the order exists and is
          paid it says nothing useful. Show the real order lifecycle instead. */}
      {unpaid ? <CheckoutSteps active={2} /> : null}

      <div className="ohead panel">
        <div className="ohead-top">
          <div>
            <span className="ohead-k">کد رهگیری سفارش</span>
            <h1 className="mono">{toFa(order.number)}</h1>
          </div>
          <span className={`badge ${STATUS_BADGE[order.status] || "purple"}`}>{order.status_display}</span>
        </div>
        <div className="ohead-meta">
          <span>تاریخ ثبت: <b>{faDateTime(order.created_at)}</b></span>
          <span>روش پرداخت: <b>{PAY_LABEL[order.payment_method] || order.payment_method}</b></span>
          <span>مبلغ: <b className="mono">{money(order.total)} تومان</b></span>
        </div>
        {order.status === "canceled" ? (
          <div className="ohead-note red">این سفارش لغو شده و موجودی کالاها بازگردانده شده است.</div>
        ) : (
          <OrderProgress status={order.status} />
        )}
      </div>

      {/* A failed/cancelled gateway attempt must be visible, not silently
          swallowed — the buyer needs to know the last try didn't go through. */}
      {order.status === "pending_payment" && lastTxn && lastTxn.status === "failed" && (
        <div className="panel payfail" style={{ marginTop: 16 }}>
          <div className="payfail-head">
            <span className="payfail-ic">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><circle cx="12" cy="12" r="9" /><path d="M15 9l-6 6M9 9l6 6" /></svg>
            </span>
            <div>
              <b>آخرین تلاش پرداخت ناموفق بود</b>
              <span>مبلغی از حساب شما کسر نشده است. اگر مبلغی کسر شده باشد، طی ۷۲ ساعت به‌صورت خودکار بازمی‌گردد.</span>
            </div>
          </div>
          <div className="payfail-meta">
            <span>درگاه: {lastTxn.gateway_display}</span>
            <span>وضعیت: {lastTxn.status_display}</span>
            <span>زمان: {faDate(lastTxn.created_at)}</span>
          </div>
        </div>
      )}

      {order.status === "pending_payment" && order.payment_method === "online" && (
        <div className="panel" style={{ marginTop: 16, textAlign: "center" }}>
          <div style={{ color: "var(--muted)", fontSize: 14 }}>مهلت باقی‌مانده برای پرداخت</div>
          <div className="mono" style={{ fontSize: 40, fontWeight: 800, color: left > 0 ? "var(--purple)" : "var(--red)", letterSpacing: 2, margin: "6px 0 14px" }}>
            {toFa(mm)}:{toFa(ss)}
          </div>
          <div className="mono" style={{ fontSize: 22, fontWeight: 800, color: "var(--purple-ink)", marginBottom: 18 }}>
            {money(order.total)} <span style={{ fontSize: 13, fontWeight: 600, color: "var(--muted)" }}>تومان</span>
          </div>
          {left > 0 ? (
            <>
              {/* Gateway picker. Rendered only when there is a real choice —
                  a single-option "choice" is just a click the buyer has to
                  make for nothing. */}
              {gateways.length > 1 && (
                <div className="gwpick">
                  <div className="gwpick-t">درگاه پرداخت را انتخاب کنید</div>
                  <div className="gwpick-list">
                    {gateways.map((g) => (
                      <button
                        key={g.id}
                        type="button"
                        className={`gwcard${gateway === g.id ? " on" : ""}`}
                        onClick={() => setGateway(g.id)}
                        aria-pressed={gateway === g.id}
                      >
                        <span className="gwcard-logo">
                          <GatewayLogo id={g.id} />
                        </span>
                        <span className="gwcard-txt">
                          <b>{g.title}</b>
                          <i>{g.subtitle}</i>
                        </span>
                        <span className="gwcard-dot" aria-hidden />
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <button className="btn btn-orange" style={{ maxWidth: 320, width: "100%", height: 52, fontSize: 15, margin: "0 auto" }} disabled={payBusy} onClick={payOnline}>
                {payBusy ? "در حال انتقال به درگاه…" : "پرداخت آنلاین ›"}
              </button>
              <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 12 }}>
                به‌صورت امن به درگاه بانکی منتقل می‌شوید. اگر پرداخت ناموفق بود، تا پایان همین مهلت می‌توانید دوباره تلاش کنید.
              </div>
            </>
          ) : (
            <div className="badge red" style={{ margin: "0 auto" }}>مهلت به پایان رسید — سفارش لغو خواهد شد.</div>
          )}
        </div>
      )}

      {order.status === "pending_payment" && order.payment_method !== "online" && (
        <div className="panel" style={{ marginTop: 16, textAlign: "center" }}>
          <div style={{ color: "var(--muted)", fontSize: 14 }}>مهلت باقی‌مانده برای آپلود فیش واریزی</div>
          <div className="mono" style={{ fontSize: 48, fontWeight: 800, color: left > 0 ? "var(--purple)" : "var(--red)", letterSpacing: 2 }}>
            {toFa(mm)}:{toFa(ss)}
          </div>
          <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 12 }}>مبلغ قابل پرداخت: <b className="mono" style={{ color: "var(--purple-ink)", fontSize: 16 }}>{money(order.total)}</b> تومان</div>

          {/* card-to-card destination — pulled live from the supplier panel */}
          {pay && (pay.card_number || pay.iban) && (
            <div style={{ maxWidth: 460, margin: "0 auto 18px", borderRadius: 16, overflow: "hidden", textAlign: "right", background: "linear-gradient(130deg,var(--purple-deep),var(--purple-2))", color: "#fff", padding: 18 }}>
              <div style={{ fontSize: 12.5, opacity: .8, marginBottom: 10 }}>اطلاعات واریز — {pay.card_holder || "فروشگاه امیدی"}</div>
              {pay.card_number && (
                <div className="between" style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: 12 }}>شماره کارت</span>
                  <button className="mono" onClick={() => copy(pay.card_number, "شماره کارت")} title="کپی"
                    style={{ direction: "ltr", letterSpacing: 2, fontSize: 16, fontWeight: 700, color: "#fff", background: "rgba(255,255,255,.12)", borderRadius: 9, padding: "6px 12px" }}>
                    {toFa(pay.card_number.replace(/(\d{4})(?=\d)/g, "$1-"))} ⧉
                  </button>
                </div>
              )}
              {pay.account_number && (
                <div className="between" style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: 12 }}>شماره حساب</span>
                  <button className="mono" onClick={() => copy(pay.account_number, "شماره حساب")} style={{ direction: "ltr", fontSize: 13.5, color: "#fff", background: "rgba(255,255,255,.12)", borderRadius: 9, padding: "6px 12px" }}>{toFa(pay.account_number)} ⧉</button>
                </div>
              )}
              {pay.iban && (
                <div className="between">
                  <span style={{ fontSize: 12 }}>شبا</span>
                  <button className="mono" onClick={() => copy(pay.iban.startsWith("IR") ? pay.iban : "IR" + pay.iban, "شماره شبا")} style={{ direction: "ltr", fontSize: 12.5, color: "#fff", background: "rgba(255,255,255,.12)", borderRadius: 9, padding: "6px 12px" }}>
                    {pay.iban.startsWith("IR") ? pay.iban : "IR" + toFa(pay.iban)} ⧉
                  </button>
                </div>
              )}
            </div>
          )}
          {left > 0 ? (
            <form onSubmit={upload} style={{ maxWidth: 420, margin: "0 auto", textAlign: "right" }}>
              <div className="field"><label>تصویر فیش واریزی</label><input className="inp" type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] || null)} /></div>
              <div className="field"><label>شماره پیگیری (اختیاری)</label><input className="inp" value={ref} onChange={(e) => setRef(e.target.value)} /></div>
              <button className="btn btn-orange" style={{ width: "100%", height: 48 }}>آپلود فیش</button>
            </form>
          ) : (
            <div className="badge red" style={{ margin: "0 auto" }}>مهلت به پایان رسید — سفارش لغو خواهد شد.</div>
          )}
        </div>
      )}

      {order.status === "receipt_uploaded" && (
        <div className="panel" style={{ marginTop: 16 }}>
          <div className="badge purple">فیش شما ثبت شد و در انتظار تایید تامین‌کننده است.</div>
        </div>
      )}

      <div className="panel print-area" style={{ marginTop: 16 }}>
        <div className="between">
          <b>اقلام سفارش</b>
          <button className="btn btn-ghost no-print" style={{ height: 38, padding: "0 16px", fontSize: 12.5 }} onClick={() => window.print()}>🖨 چاپ فاکتور</button>
        </div>
        <div style={{ marginTop: 14, display: "flex", flexDirection: "column" }}>
          {order.items.map((it: any, i: number) => (
            <div key={it.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "13px 2px", borderBottom: i < order.items.length - 1 ? "1px solid var(--line)" : "none", flexWrap: "wrap" }}>
              <a href={`/product/${encodeURIComponent(it.product_slug)}`} style={{ width: 58, height: 58, borderRadius: 12, overflow: "hidden", flexShrink: 0, border: "1px solid var(--line)", background: "linear-gradient(135deg,#fff,var(--purple-soft))", display: "grid", placeItems: "center" }}>
                {it.thumbnail
                  ? <img src={it.thumbnail} alt={it.product_name} style={{ width: "100%", height: "100%", objectFit: "contain", padding: 6 }} />
                  : <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="var(--purple-2)" strokeWidth="1.4"><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="3.4" /></svg>}
              </a>
              <div style={{ flex: 1, minWidth: 160 }}>
                <a href={`/product/${encodeURIComponent(it.product_slug)}`} className="cart-name" style={{ fontWeight: 600, fontSize: 14, lineHeight: 1.7, display: "block" }}>
                  {toFa(it.product_name)}
                  {it.color_name && <span className="cart-color-tag">{toFa(it.color_name)}</span>}
                </a>
                <span className="os-qty-badge mono" style={{ marginTop: 5 }}>{toFa(it.quantity)} عدد × {money(it.unit_price)} تومان</span>
              </div>
              <b className="mono" style={{ minWidth: 100, textAlign: "left", fontSize: 15 }}>{money(it.line_total)} <span style={{ fontSize: 11, color: "var(--muted)", fontWeight: 400 }}>تومان</span></b>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8, fontSize: 13.5 }}>
          <div className="between"><span style={{ color: "var(--muted)" }}>جمع کالاها</span><span className="mono">{money(order.subtotal)} تومان</span></div>
          {order.discount_amount > 0 && (
            <div className="between" style={{ color: "var(--green)" }}><span>تخفیف ({order.coupon_code})</span><span className="mono">- {money(order.discount_amount)}</span></div>
          )}
          {order.tax_amount > 0 && (
            <div className="between"><span style={{ color: "var(--muted)" }}>مالیات بر ارزش‌افزوده</span><span className="mono">{money(order.tax_amount)} تومان</span></div>
          )}
          <div className="between"><span style={{ color: "var(--muted)" }}>هزینه ارسال</span><span className="mono">{order.shipping_cost > 0 ? `${money(order.shipping_cost)} تومان` : "رایگان"}</span></div>
        </div>
        <div className="between" style={{ marginTop: 12, paddingTop: 12, borderTop: "1px dashed var(--line)", fontSize: 17, fontWeight: 800 }}>
          <span>مبلغ نهایی</span><span className="mono">{money(order.total)} تومان</span>
        </div>
      </div>

      <div className="ocards">
        {/* Payment receipt — only meaningful once money actually moved. */}
        {paidTxn && (
          <div className="panel ocard">
            <b className="ocard-t">اطلاعات پرداخت</b>
            <div className="ocard-rows">
              <div><span>درگاه</span><b>{paidTxn.gateway_display}</b></div>
              {paidTxn.ref_id && (
                <div>
                  <span>شماره پیگیری بانکی</span>
                  <button className="ocard-copy mono" onClick={() => copy(paidTxn.ref_id, "شماره پیگیری")}>{toFa(paidTxn.ref_id)} ⧉</button>
                </div>
              )}
              {paidTxn.card_number && (
                <div><span>کارت پرداخت‌کننده</span><b className="mono" dir="ltr">{toFa(paidTxn.card_number)}</b></div>
              )}
              <div><span>مبلغ</span><b className="mono">{money(paidTxn.amount)} تومان</b></div>
              <div><span>زمان پرداخت</span><b>{faDateTime(order.paid_at || paidTxn.created_at)}</b></div>
            </div>
          </div>
        )}

        <div className="panel ocard">
          <b className="ocard-t">اطلاعات ارسال</b>
          <div className="ocard-rows">
            <div><span>تحویل‌گیرنده</span><b>{order.ship_to_name}</b></div>
            <div>
              <span>شماره تماس</span>
              <button className="ocard-copy mono" onClick={() => copy(order.ship_to_phone, "شماره تماس")} dir="ltr">{toFa(order.ship_to_phone)} ⧉</button>
            </div>
            <div><span>شهر</span><b>{order.ship_to_city}</b></div>
          </div>
          <div className="ocard-addr">{order.ship_to_address}</div>
        </div>
      </div>
    </div>
  );
}
