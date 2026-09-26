"use client";
// Buyer-side orders list with status filter chips.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import { money, toFa, faDate } from "@/lib/format";
import Pagination from "./Pagination";
import { usePage } from "@/lib/usePage";

const STATUSES: [string, string][] = [
  ["", "همه"],
  ["pending_payment", "در انتظار پرداخت"],
  ["receipt_uploaded", "در انتظار تایید"],
  ["confirmed", "پرداخت شده"],
  ["processing", "در حال پردازش"],
  ["shipped", "ارسال شده"],
  ["delivered", "تحویل شده"],
  ["credit", "اعتباری"],
  ["canceled", "لغو شده"],
];
const BADGE: Record<string, string> = {
  pending_payment: "amber", receipt_uploaded: "purple", confirmed: "green",
  processing: "amber", shipped: "green", delivered: "green", canceled: "red", credit: "purple",
};

export default function OrdersTable() {
  const [orders, setOrders] = useState<any[]>([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [count, setCount] = useState(0);

  const [page, setPage] = usePage([status]);
  useEffect(() => {
    setLoading(true);
    api.get(`/orders/orders/?page=${page}${status ? `&status=${status}` : ""}`)
      .then((d) => { setOrders(d.results || d); setCount(d.count ?? 0); })
      .finally(() => setLoading(false));
  }, [status, page]);

  return (
    <div>
      <h2 style={{ margin: "0 0 16px", fontSize: 19, fontWeight: 800 }}>سفارش‌های من</h2>
      <div className="shopbar">
        <div className="fchips">
          {STATUSES.map(([v, l]) => (
            <button key={v} className={status === v ? "on" : ""} onClick={() => setStatus(v)}>{l}</button>
          ))}
        </div>
        <div style={{ fontSize: 13, color: "var(--muted)" }}><b className="mono">{toFa(count)}</b> سفارش</div>
      </div>
      <div className="panel tablewrap">
        <table className="tbl">
          <thead><tr><th>شماره</th><th>تاریخ</th><th>مبلغ</th><th>روش</th><th>وضعیت</th><th></th></tr></thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.id}>
                <td className="mono">{toFa(o.number)}</td>
                <td>{faDate(o.created_at)}</td>
                <td className="mono">{money(o.total)}</td>
                <td>{o.payment_method === "credit" ? "اعتباری" : "کارت به کارت"}</td>
                <td><span className={`badge ${BADGE[o.status] || "purple"}`}>{o.status_display}</span></td>
                <td>
                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <Link href={`/order/${o.number}`} style={{ color: "var(--purple)", fontWeight: 700, fontSize: 13 }}>جزئیات</Link>
                    <button
                      title="افزودن دوباره اقلام این سفارش به سبد"
                      style={{ fontSize: 12.5, fontWeight: 700, color: "var(--orange)" }}
                      onClick={async () => {
                        try {
                          const r = await api.post(`/orders/orders/${o.number}/reorder/`);
                          toast(r.detail);
                          window.dispatchEvent(new Event("ym-cart-changed"));
                        } catch (e) { toast(errorMessage(e)); }
                      }}
                    >⟳ سفارش مجدد</button>
                  </div>
                </td>
              </tr>
            ))}
            {!orders.length && !loading && <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--muted)" }}>سفارشی یافت نشد.</td></tr>}
          </tbody>
        </table>
      </div>
      <Pagination page={page} count={count} onChange={setPage} />
    </div>
  );
}
