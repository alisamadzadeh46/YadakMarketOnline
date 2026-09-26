"use client";
// Order details dialog for the fulfilment console.
//
// Rebuilt from a flat two-column dump into the order a manager actually reads:
// identity + status, then a scannable summary, then recipient, payment, items,
// and finally the money. Header and action bar stay pinned while the middle
// scrolls, so a twenty-line order cannot stretch the dialog off-screen.
import { useEffect, useRef } from "react";
import { toast } from "@/lib/ui";
import { money, toFa, faDateTime } from "@/lib/format";
import MapPicker from "@/components/MapPicker";
import InvoiceSheet from "@/components/InvoiceSheet";

const STATUS_BADGE: Record<string, string> = {
  pending_payment: "amber", receipt_uploaded: "purple", confirmed: "green",
  processing: "amber", shipped: "green", delivered: "green",
  canceled: "red", credit: "purple",
};

const PAY_METHOD: Record<string, string> = {
  online: "پرداخت آنلاین",
  card_to_card: "کارت به کارت",
  credit: "خرید اعتباری",
};

export type OrderAction = "confirm" | "process" | "ship" | "deliver" | "cancel";

/** Value + copy button. Bank references are long and RTL scrambles them, so
 *  each one renders LTR in the mono face. */
function CopyValue({ value, label, ltr }: { value: string; label: string; ltr?: boolean }) {
  return (
    <button
      type="button"
      className="od-copy mono"
      dir={ltr ? "ltr" : undefined}
      title={`کپی ${label}`}
      onClick={() => navigator.clipboard?.writeText(value).then(() => toast(`${label} کپی شد ✓`))}
    >
      {toFa(value)}
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <rect x="9" y="9" width="12" height="12" rx="2" /><path d="M5 15V5a2 2 0 0 1 2-2h10" />
      </svg>
    </button>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="od-row">
      <span className="od-row-k">{label}</span>
      <span className="od-row-v">{children}</span>
    </div>
  );
}

export default function OrderDetails({
  order, onClose, onAct,
}: {
  order: any;
  onClose: () => void;
  onAct: (num: string, action: OrderAction) => void;
}) {
  const boxRef = useRef<HTMLDivElement>(null);

  // Esc closes; focus enters the dialog and is trapped while it is open.
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.stopPropagation(); onClose(); return; }
      if (e.key !== "Tab") return;
      const focusable = boxRef.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (!focusable?.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKey, true);
    // The page behind must not scroll while the dialog owns the screen.
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    boxRef.current?.querySelector<HTMLElement>("button")?.focus();
    return () => {
      document.removeEventListener("keydown", onKey, true);
      document.body.style.overflow = overflow;
      prev?.focus();
    };
  }, [onClose]);

  const txns: any[] = order.payment_transactions || [];
  const paid = txns.find((t) => t.status === "success");
  const items: any[] = order.items || [];
  const qtyTotal = items.reduce((n, i) => n + (i.quantity || 0), 0);
  const hasMap = order.ship_lat && order.ship_lng;

  return (
    <div className="omodal-back" onClick={onClose} role="presentation">
      {/* The printable document. Hidden on screen; @media print hides the app
          and shows only this, so "print invoice" yields a real invoice instead of
          a screenshot of a scrollable dialog. */}
      <InvoiceSheet order={order} />
      <div
        ref={boxRef}
        className="od"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="od-title"
      >
        <header className="od-head">
          <div>
            <h2 id="od-title">جزئیات سفارش</h2>
            <div className="od-num">
              <span>شماره سفارش:</span>
              <CopyValue value={order.number} label="شماره سفارش" ltr />
            </div>
          </div>
          <div className="od-head-l">
            <span className={`badge ${STATUS_BADGE[order.status] || "purple"}`}>{order.status_display}</span>
            <button type="button" className="od-x" onClick={onClose} title="بستن" aria-label="بستن پنجره">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
          </div>
        </header>

        <div className="od-body">
          <div className="od-quick">
            <div><span>مبلغ نهایی</span><b className="mono">{money(order.total)} تومان</b></div>
            <div><span>وضعیت پرداخت</span><b className={paid ? "ok" : "no"}>{paid ? "پرداخت‌شده" : "پرداخت‌نشده"}</b></div>
            <div><span>روش پرداخت</span><b>{PAY_METHOD[order.payment_method] || order.payment_method}</b></div>
            <div><span>تاریخ ثبت</span><b>{faDateTime(order.created_at)}</b></div>
            {/* Two tiles, not one. "1 line · 10 units" read as a single mangled
                number because the separator sits between two Persian digits. */}
            <div><span>تعداد اقلام</span><b>{toFa(items.length)} قلم</b></div>
            <div><span>مجموع تعداد</span><b>{toFa(qtyTotal)} عدد</b></div>
          </div>

          <section className="od-sec">
            <h3>اطلاعات گیرنده</h3>
            <div className="od-rows">
              <Row label="نام گیرنده">{order.ship_to_name || "—"}</Row>
              <Row label="شماره تماس">
                {order.ship_to_phone ? (
                  <span className="od-tel">
                    <a href={`tel:${order.ship_to_phone}`} className="od-call">تماس</a>
                    <CopyValue value={order.ship_to_phone} label="شماره تماس" ltr />
                  </span>
                ) : "—"}
              </Row>
              <Row label="شهر">{order.ship_to_city || "—"}</Row>
            </div>
            <div className="od-addr">
              <span>نشانی کامل</span>
              <p>{order.ship_to_address || "ثبت نشده"}</p>
            </div>
            {hasMap ? (
              <MapPicker lat={order.ship_lat} lng={order.ship_lng} readOnly height={200} />
            ) : (
              <div className="od-empty">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
                  <path d="M12 21s7-5.5 7-11a7 7 0 1 0-14 0c0 5.5 7 11 7 11Z" /><circle cx="12" cy="10" r="2.5" />
                </svg>
                <span>موقعیت روی نقشه برای این آدرس ثبت نشده است.</span>
              </div>
            )}
          </section>

          <section className="od-sec">
            <h3>{txns.length > 1 ? `تلاش‌های پرداخت (${toFa(txns.length)})` : "اطلاعات پرداخت"}</h3>
            {order.payment_method === "online" ? (
              txns.length ? (
                <div className="od-txns">
                  {txns.map((t: any) => (
                    <div key={t.id} className="od-txn">
                      <div className="od-txn-h">
                        <b>{t.gateway_display}</b>
                        <span className={`badge ${t.status === "success" ? "green" : t.status === "failed" ? "red" : "amber"}`}>{t.status_display}</span>
                      </div>
                      <div className="od-rows">
                        <Row label="مبلغ"><b className="mono">{money(t.amount)} تومان</b></Row>
                        {t.ref_id ? <Row label="شماره پیگیری"><CopyValue value={t.ref_id} label="شماره پیگیری" ltr /></Row> : null}
                        {t.card_number ? <Row label="شماره کارت"><span className="mono" dir="ltr">{toFa(t.card_number)}</span></Row> : null}
                        <Row label="زمان">{faDateTime(t.created_at)}</Row>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="od-empty"><span>هنوز تراکنشی برای این سفارش ثبت نشده است.</span></div>
              )
            ) : (
              <>
                {order.receipt?.image ? (
                  <a href={order.receipt.image} target="_blank" rel="noopener">
                    <img className="od-receipt" src={order.receipt.image} alt="فیش واریزی" />
                  </a>
                ) : (
                  <div className="od-empty"><span>فیش واریزی ثبت نشده است.</span></div>
                )}
                <div className="od-rows" style={{ marginTop: 10 }}>
                  <Row label="شماره پیگیری فیش">
                    {order.receipt?.reference_number
                      ? <CopyValue value={order.receipt.reference_number} label="شماره پیگیری" ltr />
                      : "—"}
                  </Row>
                </div>
              </>
            )}
          </section>

          <section className="od-sec">
            <h3>اقلام سفارش ({toFa(items.length)} قلم)</h3>
            <div className="od-items">
              {items.map((it: any) => (
                <div key={it.id} className="od-item">
                  <div className="od-item-th">
                    {it.thumbnail ? (
                      <img src={it.thumbnail} alt={it.product_name} width={64} height={64} loading="lazy" />
                    ) : (
                      <span className="od-item-ph" aria-label="بدون تصویر">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="3.4" /></svg>
                      </span>
                    )}
                  </div>
                  <div className="od-item-info">
                    <b className="od-item-name">{it.product_name}</b>
                    <div className="od-item-meta">
                      {it.brand ? <span className="badge purple">{it.brand}</span> : null}
                      {it.category ? <span className="od-item-cat">{it.category}</span> : null}
                      {it.color_name ? <span className="od-item-cat">رنگ: {toFa(it.color_name)}</span> : null}
                    </div>
                    {it.sku ? <div className="od-item-sub">کد فنی: <span className="mono" dir="ltr">{toFa(it.sku)}</span></div> : null}
                    {it.supplier_name ? <div className="od-item-sub">تأمین‌کننده: <b>{it.supplier_name}</b></div> : null}
                  </div>
                  <div className="od-item-money">
                    <span>تعداد: <b>{toFa(it.quantity)} عدد</b></span>
                    <span>قیمت واحد: <b className="mono">{money(it.unit_price)}</b></span>
                    <span className="od-item-sum">جمع: <b className="mono">{money(it.line_total)} تومان</b></span>
                  </div>
                </div>
              ))}
              {!items.length && <div className="od-empty"><span>قلمی ثبت نشده است.</span></div>}
            </div>
          </section>

          <section className="od-sec">
            <h3>خلاصه مالی</h3>
            <div className="od-sum">
              <div><span>جمع کالاها</span><b className="mono">{money(order.subtotal)} تومان</b></div>
              {order.discount_amount > 0 && (
                <div className="off"><span>تخفیف {order.coupon_code ? `(${order.coupon_code})` : ""}</span><b className="mono">- {money(order.discount_amount)} تومان</b></div>
              )}
              <div><span>مالیات بر ارزش‌افزوده</span><b className="mono">{money(order.tax_amount || 0)} تومان</b></div>
              <div>
                <span>هزینه ارسال</span>
                <b className={order.shipping_cost > 0 ? "mono" : "free"}>
                  {order.shipping_cost > 0 ? `${money(order.shipping_cost)} تومان` : "ارسال رایگان"}
                </b>
              </div>
              <div className="od-sum-total"><span>مبلغ نهایی</span><b className="mono">{money(order.total)} تومان</b></div>
            </div>
          </section>
        </div>

        <footer className="od-foot">
          <button type="button" className="btn btn-ghost" onClick={() => window.print()}>چاپ فاکتور</button>
          {order.status === "receipt_uploaded" && (
            <button type="button" className="btn btn-purple" onClick={() => onAct(order.number, "confirm")}>تایید پرداخت</button>
          )}
          {(order.status === "confirmed" || order.status === "credit") && (
            <button type="button" className="btn btn-purple" onClick={() => onAct(order.number, "process")}>شروع پردازش</button>
          )}
          {order.status === "processing" && (
            <button type="button" className="btn btn-orange" onClick={() => onAct(order.number, "ship")}>ارسال شد</button>
          )}
          {order.status === "shipped" && (
            <button type="button" className="btn btn-purple" onClick={() => onAct(order.number, "deliver")}>تحویل شد</button>
          )}
          <button type="button" className="btn btn-ghost od-close" onClick={onClose}>بستن</button>
        </footer>
      </div>
    </div>
  );
}
