"use client";
// Landing page after the bank redirects back. The backend has already verified
// the charge server-side (see apps.payments.views.PaymentCallbackView) before
// sending the buyer here — this page only reads its own query string to decide
// which state to render, it never re-decides success/failure itself.
//
// On success it doubles as the buyer's payment receipt (printable), so it
// fetches the order to show the real amount, bank reference and timestamp
// rather than a bare "it worked" message.
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { toast } from "@/lib/ui";
import { faDateTime, money, toFa } from "@/lib/format";
import { PRIMARY_PHONE, SITE } from "@/lib/site";

type Txn = {
  gateway_display?: string;
  ref_id?: string;
  card_number?: string;
  amount?: number;
  status?: string;
  created_at?: string;
};
type Order = {
  number: string;
  total: number;
  paid_at?: string;
  created_at?: string;
  status_display?: string;
  items?: { id: number }[];
  payment_transactions?: Txn[];
};

function CopyRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="payres-row">
      <span className="payres-k">{label}</span>
      <button
        type="button"
        className={`payres-v copyable${mono ? " mono" : ""}`}
        onClick={() => {
          navigator.clipboard?.writeText(value).then(() => toast(`${label} کپی شد ✓`));
        }}
        title="برای کپی کلیک کنید"
      >
        {value}
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <rect x="9" y="9" width="12" height="12" rx="2" />
          <path d="M5 15V5a2 2 0 0 1 2-2h10" />
        </svg>
      </button>
    </div>
  );
}

export default function PaymentResult() {
  const [state, setState] = useState<{ order: string; ok: boolean } | null>(null);
  const [order, setOrder] = useState<Order | null>(null);
  const { refreshCart } = useAuth();

  useEffect(() => {
    const sp = new URLSearchParams(window.location.search);
    const num = sp.get("order") || "";
    setState({ order: num, ok: sp.get("ok") === "1" });
    // The cart is only emptied server-side once the charge verifies, so the
    // header badge has to be re-read either way: cleared on success, still
    // full on failure.
    refreshCart();
    if (num) api.get(`/orders/orders/${num}/`).then(setOrder).catch(() => {});
  }, [refreshCart]);

  const print = useCallback(() => window.print(), []);

  if (!state) return <div className="center-empty">در حال بررسی نتیجه پرداخت…</div>;

  const txn = order?.payment_transactions?.find((t) => t.status === "success")
    || order?.payment_transactions?.[0];
  const paidAt = order?.paid_at || txn?.created_at || order?.created_at;

  // ---- Failed / cancelled ---------------------------------------------------
  if (!state.ok) {
    return (
      <div className="view payres">
        <div className="payres-card">
          <div className="payres-hero fail">
            <span className="payres-ring" aria-hidden>
              <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </span>
            <h1>پرداخت انجام نشد</h1>
            <p>هیچ مبلغی از حساب شما کسر نشده است.</p>
          </div>

          <div className="payres-note">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden>
              <circle cx="9" cy="20" r="1.6" /><circle cx="18" cy="20" r="1.6" />
              <path d="M2 3h3l2.4 12.2a1.6 1.6 0 0 0 1.6 1.3h8.6a1.6 1.6 0 0 0 1.6-1.3L21 7H6" />
            </svg>
            <div>
              <b>سبد خرید شما دست‌نخورده باقی مانده است.</b>
              <span>می‌توانید بدون انتخاب دوباره کالاها، پرداخت را تکرار کنید.</span>
            </div>
          </div>

          <div className="payres-actions">
            {state.order ? (
              <Link href={`/order/${state.order}`} className="btn btn-purple">تلاش دوباره برای پرداخت</Link>
            ) : (
              <Link href="/cart" className="btn btn-purple">بازگشت به سبد خرید</Link>
            )}
            <Link href="/cart" className="btn btn-ghost">مشاهده سبد خرید</Link>
          </div>

          {PRIMARY_PHONE && (
            <div className="payres-help">
              مشکلی پیش آمد؟ با پشتیبانی تماس بگیرید:{" "}
              <a href={`tel:${PRIMARY_PHONE.dial}`} className="mono" dir="ltr">{PRIMARY_PHONE.display}</a>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ---- Success --------------------------------------------------------------
  return (
    <div className="view payres">
      <div className="payres-card">
        <div className="payres-hero ok">
          <span className="payres-ring" aria-hidden>
            <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12.5 10 17.5 19.5 7.5" className="payres-tick" />
            </svg>
          </span>
          <h1>پرداخت با موفقیت انجام شد</h1>
          <p>سفارش شما ثبت و تأیید شد. رسید پرداخت برای شما پیامک شد.</p>
        </div>

        <div className="payres-receipt">
          <div className="payres-receipt-h">
            <b>رسید پرداخت</b>
            <span>{SITE.name}</span>
          </div>

          {order ? (
            <>
              <div className="payres-amount">
                <span>مبلغ پرداخت‌شده</span>
                <b>{money(txn?.amount ?? order.total)} <i>تومان</i></b>
              </div>

              <div className="payres-rows">
                <CopyRow label="کد رهگیری سفارش" value={toFa(order.number)} mono />
                {txn?.ref_id && (
                  <CopyRow label="شماره پیگیری بانکی" value={toFa(txn.ref_id)} mono />
                )}
                {txn?.gateway_display && (
                  <div className="payres-row"><span className="payres-k">درگاه پرداخت</span><span className="payres-v">{txn.gateway_display}</span></div>
                )}
                {txn?.card_number && (
                  <div className="payres-row"><span className="payres-k">کارت پرداخت‌کننده</span><span className="payres-v mono" dir="ltr">{toFa(txn.card_number)}</span></div>
                )}
                <div className="payres-row"><span className="payres-k">تاریخ و ساعت</span><span className="payres-v">{faDateTime(paidAt)}</span></div>
                {!!order.items?.length && (
                  <div className="payres-row"><span className="payres-k">تعداد اقلام</span><span className="payres-v">{toFa(order.items.length)} قلم</span></div>
                )}
                <div className="payres-row"><span className="payres-k">وضعیت سفارش</span><span className="payres-v"><span className="badge green">{order.status_display || "پرداخت تایید شد"}</span></span></div>
              </div>
            </>
          ) : (
            <div className="payres-rows">
              <div className="payres-row"><span className="payres-k">کد رهگیری سفارش</span><span className="payres-v mono">{toFa(state.order)}</span></div>
              <div className="payres-row"><span className="payres-k">وضعیت</span><span className="payres-v"><span className="badge green">پرداخت تایید شد</span></span></div>
            </div>
          )}
        </div>

        <div className="payres-next">
          <b>مراحل بعدی</b>
          <ol>
            <li><span>۱</span><div><b>تأیید و آماده‌سازی</b><i>سفارش شما به فروشنده اعلام شد و بسته‌بندی می‌شود.</i></div></li>
            <li><span>۲</span><div><b>ارسال</b><i>پس از ارسال، کد رهگیری مرسوله برای شما پیامک می‌شود.</i></div></li>
            <li><span>۳</span><div><b>تحویل</b><i>وضعیت لحظه‌ای سفارش را از «سفارش‌های من» دنبال کنید.</i></div></li>
          </ol>
        </div>

        <div className="payres-actions">
          <Link href={state.order ? `/order/${state.order}` : "/account/orders"} className="btn btn-purple">
            مشاهده جزئیات سفارش
          </Link>
          <button type="button" className="btn btn-ghost" onClick={print}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden>
              <path d="M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-2" />
              <rect x="6" y="14" width="12" height="7" rx="1" />
            </svg>
            چاپ رسید
          </button>
          <Link href="/shop" className="btn btn-ghost">ادامه خرید</Link>
        </div>
      </div>
    </div>
  );
}
