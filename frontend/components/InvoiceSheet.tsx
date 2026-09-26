"use client";
// A real printable sales invoice.
//
// Printing the details dialog produced a screenshot of a scrollable UI: cut-off
// content, badges, buttons and a map on the paper. This is a separate document
// laid out for A4: business header, order/customer blocks, a proper line-item
// table with per-row numbering, the money summary, and a signature footer.
// It is display:none on screen and the only thing on the page when printing.
import { money, toFa, faDateTime } from "@/lib/format";
import { FULL_ADDRESS, SITE, SITE_HOST } from "@/lib/site";

const PAY_METHOD: Record<string, string> = {
  online: "پرداخت آنلاین",
  card_to_card: "کارت به کارت",
  credit: "خرید اعتباری",
};

export default function InvoiceSheet({ order }: { order: any }) {
  const items: any[] = order.items || [];
  const qtyTotal = items.reduce((n, i) => n + (i.quantity || 0), 0);
  const paid = (order.payment_transactions || []).find((t: any) => t.status === "success");

  return (
    <div className="invoice" id="invoice-sheet" aria-hidden>
      <header className="inv-head">
        <div className="inv-brand">
          <img src="/logo-full.png" alt={SITE.name} className="inv-logo" />
          <div>
            <b>{SITE.name}</b>
            <span>{SITE.tagline}</span>
            {FULL_ADDRESS && <span>{FULL_ADDRESS}</span>}
            {SITE.contact.phones.length > 0 && (
              <span dir="ltr" className="mono">{SITE.contact.phones.map((phone) => phone.display).join(" / ")}</span>
            )}
            <span>{SITE_HOST}</span>
          </div>
        </div>
        <div className="inv-title">
          <h1>فاکتور فروش</h1>
          <table className="inv-meta">
            <tbody>
              <tr><th>شماره فاکتور</th><td className="mono" dir="ltr">{toFa(order.number)}</td></tr>
              <tr><th>تاریخ صدور</th><td>{faDateTime(order.created_at)}</td></tr>
              <tr><th>وضعیت</th><td>{order.status_display}</td></tr>
            </tbody>
          </table>
        </div>
      </header>

      <section className="inv-parties">
        <div>
          <h2>مشخصات خریدار</h2>
          <table className="inv-kv">
            <tbody>
              <tr><th>نام</th><td>{order.ship_to_name || "—"}</td></tr>
              <tr><th>تلفن</th><td className="mono" dir="ltr">{toFa(order.ship_to_phone || "—")}</td></tr>
              <tr><th>شهر</th><td>{order.ship_to_city || "—"}</td></tr>
              <tr><th>نشانی</th><td>{order.ship_to_address || "—"}</td></tr>
            </tbody>
          </table>
        </div>
        <div>
          <h2>اطلاعات پرداخت</h2>
          <table className="inv-kv">
            <tbody>
              <tr><th>روش پرداخت</th><td>{PAY_METHOD[order.payment_method] || order.payment_method}</td></tr>
              <tr><th>وضعیت پرداخت</th><td>{paid ? "پرداخت‌شده" : "پرداخت‌نشده"}</td></tr>
              {paid?.gateway_display && <tr><th>درگاه</th><td>{paid.gateway_display}</td></tr>}
              {paid?.ref_id && <tr><th>شماره پیگیری</th><td className="mono" dir="ltr">{toFa(paid.ref_id)}</td></tr>}
              {order.paid_at && <tr><th>تاریخ پرداخت</th><td>{faDateTime(order.paid_at)}</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <table className="inv-items">
        <thead>
          <tr>
            <th style={{ width: "4%" }}>ردیف</th>
            <th style={{ width: "34%" }}>شرح کالا</th>
            <th style={{ width: "14%" }}>کد فنی</th>
            <th style={{ width: "14%" }}>برند</th>
            <th style={{ width: "8%" }}>تعداد</th>
            <th style={{ width: "13%" }}>قیمت واحد</th>
            <th style={{ width: "13%" }}>مبلغ کل</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it: any, i: number) => (
            <tr key={it.id}>
              <td className="mono">{toFa(i + 1)}</td>
              <td className="inv-name">
                {it.product_name}
                {it.color_name && <em>رنگ: {toFa(it.color_name)}</em>}
                {it.category && <em>{it.category}</em>}
              </td>
              <td className="mono" dir="ltr">{toFa(it.sku || "—")}</td>
              <td>{it.brand || "—"}</td>
              <td className="mono">{toFa(it.quantity)}</td>
              <td className="mono">{money(it.unit_price)}</td>
              <td className="mono">{money(it.line_total)}</td>
            </tr>
          ))}
          {!items.length && (
            <tr><td colSpan={7} style={{ textAlign: "center" }}>قلمی ثبت نشده است.</td></tr>
          )}
        </tbody>
        <tfoot>
          <tr>
            <th colSpan={4}>جمع</th>
            <th className="mono">{toFa(qtyTotal)}</th>
            <th />
            <th className="mono">{money(order.subtotal)}</th>
          </tr>
        </tfoot>
      </table>

      <section className="inv-totals">
        <table className="inv-kv inv-sum">
          <tbody>
            <tr><th>جمع کالاها</th><td className="mono">{money(order.subtotal)} تومان</td></tr>
            {order.discount_amount > 0 && (
              <tr><th>تخفیف {order.coupon_code ? `(${order.coupon_code})` : ""}</th><td className="mono">- {money(order.discount_amount)} تومان</td></tr>
            )}
            <tr><th>مالیات بر ارزش‌افزوده</th><td className="mono">{money(order.tax_amount || 0)} تومان</td></tr>
            <tr><th>هزینه ارسال</th><td className="mono">{order.shipping_cost > 0 ? `${money(order.shipping_cost)} تومان` : "رایگان"}</td></tr>
            <tr className="inv-grand"><th>مبلغ قابل پرداخت</th><td className="mono">{money(order.total)} تومان</td></tr>
          </tbody>
        </table>
      </section>

      <footer className="inv-foot">
        <div><span>مهر و امضای فروشنده</span></div>
        <div><span>امضای تحویل‌گیرنده</span></div>
      </footer>
      <p className="inv-note">
        این فاکتور به‌صورت الکترونیکی صادر شده و بدون مهر فروشنده معتبر است.
        در صورت مغایرت، حداکثر تا ۴۸ ساعت پس از تحویل اطلاع دهید.
      </p>
    </div>
  );
}
