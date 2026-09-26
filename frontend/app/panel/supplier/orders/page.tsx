"use client";
// Fulfillment console: filter by status, review the uploaded receipt,
// confirm payment, mark shipped.
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import { money, toFa, faDate } from "@/lib/format";
import OrderDetails from "@/components/OrderDetails";
import Pagination from "@/components/Pagination";
import { usePage } from "@/lib/usePage";

const STATUSES: [string, string][] = [
  ["", "همه"], ["pending_payment", "در انتظار پرداخت"], ["receipt_uploaded", "فیش آپلودشده"],
  ["confirmed", "تایید شده"], ["processing", "در حال پردازش"], ["shipped", "ارسال شده"],
  ["delivered", "تحویل شده"], ["credit", "اعتباری"], ["canceled", "لغو شده"],
];

// Sent as ?page_size= and used for the "showing X–Y of Z" line, so the two can
// never drift. Deliberately smaller than the site-wide default of 24: this is a
// work queue the supplier processes row by row, not a catalogue to skim.
const PAGE_SIZE = 10;

// Colour per state so the queue is scannable: amber = waiting on someone,
// green = money/goods moved, red = dead.
const STATUS_BADGE: Record<string, string> = {
  pending_payment: "amber", receipt_uploaded: "purple", confirmed: "green",
  processing: "amber", shipped: "green", delivered: "green",
  canceled: "red", credit: "purple",
};

export default function SupplierOrders() {
  const [rows, setRows] = useState<any[]>([]);
  const [status, setStatus] = useState("receipt_uploaded");
  const [open, setOpen] = useState<any>(null);
  const [count, setCount] = useState(0);

  const [page, setPage] = usePage([status]);

  const load = useCallback(() =>
    api.get(`/orders/supplier/orders/?page=${page}&page_size=${PAGE_SIZE}${status ? `&status=${status}` : ""}`)
      .then((d) => { setRows(d.results || d); setCount(d.count ?? 0); })
      .catch((e) => toast(errorMessage(e))), [page, status]);
  useEffect(() => { load(); }, [load]);

  const act = async (num: string, action: "confirm" | "process" | "ship" | "deliver" | "cancel") => {
    try { await api.post(`/orders/supplier/orders/${num}/${action}/`); toast("انجام شد ✓"); setOpen(null); load(); }
    catch (e) { toast(errorMessage(e, "عملیات با خطا مواجه شد.")); }
  };

  const cancelOrder = (o: any) => {
    if (!window.confirm(`آیا از لغو سفارش ${o.number} مطمئن هستید؟ موجودی کالاها بازگردانده می‌شود.`)) return;
    act(o.number, "cancel");
  };

  const CANCELABLE = ["pending_payment", "receipt_uploaded", "confirmed", "processing", "credit"];

  const exportCsv = () => {
    // BOM so Excel opens Persian text correctly.
    const head = ["شماره", "خریدار", "شهر", "مبلغ", "روش پرداخت", "وضعیت", "تاریخ"];
    const lines = rows.map((o) =>
      [o.number, o.ship_to_name, o.ship_to_city, o.total, o.payment_method, o.status_display, o.created_at].join(",")
    );
    const blob = new Blob(["﻿" + [head.join(","), ...lines].join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `orders-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <div>
      <div className="between" style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 19, fontWeight: 800 }}>مدیریت سفارش‌ها</h2>
        <button className="btn btn-ghost" style={{ height: 40, padding: "0 16px", fontSize: 13 }} onClick={exportCsv}>⬇ خروجی اکسل (CSV)</button>
      </div>
      <div className="shopbar">
        <div className="fchips">
          {STATUSES.map(([v, l]) => (<button key={v} className={status === v ? "on" : ""} onClick={() => setStatus(v)}>{l}</button>))}
        </div>
        <div style={{ fontSize: 13, color: "var(--muted)" }}>
          {count > 0 ? (
            <>
              نمایش <b className="mono">{toFa((page - 1) * PAGE_SIZE + 1)}</b>
              {" تا "}
              <b className="mono">{toFa(Math.min(page * PAGE_SIZE, count))}</b>
              {" از "}
              <b className="mono">{toFa(count)}</b> سفارش
            </>
          ) : (
            <>بدون نتیجه</>
          )}
        </div>
      </div>

      {/* Mobile: a 7-column table inside a horizontal scroller is unusable on a
          phone, so below 860px the same rows render as cards instead. Both are
          in the DOM; CSS picks one — keeps the action handlers identical. */}
      <div className="ordcards">
        {rows.map((o) => (
          <div key={o.id} className="ordcard">
            <div className="ordcard-h">
              <span className="mono">{toFa(o.number)}</span>
              <span className={`badge ${STATUS_BADGE[o.status] || "purple"}`}>{o.status_display}</span>
            </div>
            <div className="ordcard-b">
              <div><span>خریدار</span><b>{o.ship_to_name}</b></div>
              <div><span>شهر</span><b>{o.ship_to_city}</b></div>
              <div><span>مبلغ</span><b className="mono">{money(o.total)} تومان</b></div>
              <div><span>تاریخ</span><b>{faDate(o.created_at)}</b></div>
            </div>
            <div className="list-actions ordcard-a">
              {o.status === "receipt_uploaded" && <button className="act-edit" style={{ background: "var(--purple)", color: "#fff" }} onClick={() => act(o.number, "confirm")}>تایید پرداخت</button>}
              {(o.status === "confirmed" || o.status === "credit") && <button className="act-edit" onClick={() => act(o.number, "process")}>شروع پردازش</button>}
              {o.status === "processing" && <button className="act-edit" style={{ background: "var(--orange)", color: "#fff" }} onClick={() => act(o.number, "ship")}>ارسال شد</button>}
              {o.status === "shipped" && <button className="act-edit" style={{ background: "var(--green)", color: "#fff" }} onClick={() => act(o.number, "deliver")}>تحویل شد</button>}
              <button className="act-edit" onClick={() => setOpen(o)}>جزئیات کامل</button>
              {CANCELABLE.includes(o.status) && <button className="act-del" onClick={() => cancelOrder(o)}>لغو سفارش</button>}
            </div>
          </div>
        ))}
        {!rows.length && <div className="panel" style={{ textAlign: "center", color: "var(--muted)" }}>سفارشی نیست.</div>}
      </div>

      <div className="panel tablewrap ordtable">
        <table className="tbl">
          <thead><tr><th>شماره</th><th>خریدار</th><th>شهر</th><th>مبلغ</th><th>تاریخ</th><th>وضعیت</th><th>عملیات</th></tr></thead>
          <tbody>
            {rows.map((o) => (
              <tr key={o.id}>
                <td className="mono">{toFa(o.number)}</td>
                <td>{o.ship_to_name}</td>
                <td>{o.ship_to_city}</td>
                <td className="mono">{money(o.total)}</td>
                <td>{faDate(o.created_at)}</td>
                <td><span className={`badge ${STATUS_BADGE[o.status] || "purple"}`}>{o.status_display}</span></td>
                <td>
                  <div className="list-actions">
                          {o.status === "receipt_uploaded" && <button className="act-edit" style={{ background: "var(--purple)", color: "#fff" }} onClick={() => act(o.number, "confirm")}>تایید پرداخت</button>}
                    {(o.status === "confirmed" || o.status === "credit") && <button className="act-edit" onClick={() => act(o.number, "process")}>شروع پردازش</button>}
                    {o.status === "processing" && <button className="act-edit" style={{ background: "var(--orange)", color: "#fff" }} onClick={() => act(o.number, "ship")}>ارسال شد</button>}
                    {o.status === "shipped" && <button className="act-edit" style={{ background: "var(--green)", color: "#fff" }} onClick={() => act(o.number, "deliver")}>تحویل شد</button>}
                    <button className="act-edit" onClick={() => setOpen(o)}>جزئیات کامل</button>
                    {CANCELABLE.includes(o.status) && <button className="act-del" onClick={() => cancelOrder(o)}>لغو سفارش</button>}
                  </div>
                </td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={7} style={{ textAlign: "center", color: "var(--muted)" }}>سفارشی نیست.</td></tr>}
          </tbody>
        </table>
      </div>
      <Pagination page={page} count={count} pageSize={PAGE_SIZE} onChange={setPage} />

      {/* Details used to render *below* the pager, so clicking "payment details"
          looked like it did nothing — the panel was off-screen. It's a modal
          now, so it always appears where the supplier is looking. */}
      {open && <OrderDetails order={open} onClose={() => setOpen(null)} onAct={act} />}
    </div>
  );
}
