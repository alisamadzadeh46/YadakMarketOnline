"use client";
// Supplier earnings: for every successful order, what the site owner took
// ("owner commission") and what is left for the supplier ("your share"). Snapshotted
// at purchase time, so it appears the moment an order is confirmed/paid.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { money, toFa, faDate } from "@/lib/format";
import NiceSelect from "@/components/NiceSelect";

const STATUS: Record<string, { label: string; cls: string }> = {
  earned: { label: "قطعی‌شده", cls: "green" },
  pending: { label: "در انتظار تسویه", cls: "orange" },
  paid: { label: "پرداخت‌شده", cls: "purple" },
  void: { label: "باطل", cls: "red" },
};

export default function SupplierEarnings() {
  const [days, setDays] = useState("90");
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [data, setData] = useState<any>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    const p = new URLSearchParams();
    if (days) p.set("days", days);
    if (status) p.set("status", status);
    if (q) p.set("q", q);
    p.set("page", String(page));
    api.get(`/suppliers/earnings/?${p.toString()}`).then(setData).catch(() => {});
  }, [days, status, q, page]);

  const exportCsv = () => {
    if (!data?.results?.length) return;
    const head = ["شماره سفارش", "تاریخ", "روش پرداخت", "فروش", "پورسانت مدیر", "سهم شما", "درصد", "وضعیت"];
    const lines = data.results.map((r: any) =>
      [r.order_number, r.created_at, r.payment_method, r.gross_amount, r.owner_commission, r.supplier_net, r.effective_rate, STATUS[r.status]?.label || r.status].join(","));
    const blob = new Blob(["﻿" + [head.join(","), ...lines].join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `earnings-${days}d.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  if (!data) return <div className="skel" style={{ height: 400 }} />;
  const s = data.summary;
  const pages = Math.max(1, Math.ceil(data.count / 20));

  return (
    <div>
      <h2 style={{ margin: "0 0 6px", fontSize: 19, fontWeight: 800 }}>درآمد و پورسانت</h2>
      <p style={{ margin: "0 0 16px", fontSize: 13, color: "var(--muted)", lineHeight: 1.9 }}>
        سهم شما از هر فروش، پس از کسر پورسانت مدیر سایت. این مبالغ در همان لحظهٔ تایید سفارش (آنلاین یا فیش) ثبت می‌شوند.
      </p>

      <div className="statgrid" style={{ marginBottom: 18 }}>
        <div className="stat"><div><div className="v mono">{money(s.sales_total)}</div><div className="k">فروش کل (تومان)</div></div></div>
        <div className="stat"><div><div className="v mono" style={{ color: "var(--orange-2)" }}>{money(s.owner_commission_total)}</div><div className="k">پورسانت مدیر سایت</div></div></div>
        <div className="stat"><div><div className="v mono" style={{ color: "var(--green)" }}>{money(s.net_total)}</div><div className="k">سهم خالص شما</div></div></div>
        <div className="stat"><div><div className="v mono">{money(s.net_this_month)}</div><div className="k">سهم این ماه</div></div></div>
      </div>

      <div className="statgrid" style={{ marginBottom: 18, gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))" }}>
        <div className="stat"><div><div className="v mono" style={{ color: "var(--purple-2)" }}>{money(s.net_paid)}</div><div className="k">تسویه‌شده با شما</div></div></div>
        <div className="stat"><div><div className="v mono" style={{ color: "var(--orange-2)" }}>{money(s.net_unpaid)}</div><div className="k">در انتظار تسویه</div></div></div>
        <div className="stat"><div><div className="v mono">{toFa(s.orders_count)}</div><div className="k">تعداد سفارش</div></div></div>
      </div>

      <div className="shopbar">
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <NiceSelect value={days} onChange={(v) => { setPage(1); setDays(v); }} style={{ minWidth: 130 }}
            options={[{ value: "30", label: "۳۰ روز اخیر" }, { value: "90", label: "۹۰ روز اخیر" }, { value: "365", label: "یک سال اخیر" }, { value: "", label: "همه" }]} />
          <NiceSelect value={status} onChange={(v) => { setPage(1); setStatus(v); }} style={{ minWidth: 140 }}
            options={[{ value: "", label: "همه وضعیت‌ها" }, { value: "earned", label: "قطعی‌شده" }, { value: "pending", label: "در انتظار تسویه" }, { value: "paid", label: "پرداخت‌شده" }]} />
          <input className="inp" style={{ height: 40, maxWidth: 180 }} placeholder="شماره سفارش…" value={q} onChange={(e) => { setPage(1); setQ(e.target.value); }} />
        </div>
        <button className="btn btn-ghost" style={{ height: 40, padding: "0 16px", fontSize: 12.5 }} onClick={exportCsv}>⬇ خروجی CSV</button>
      </div>

      <div className="panel tablewrap">
        <table className="tbl" style={{ minWidth: 720 }}>
          <thead><tr>
            <th>سفارش</th><th>تاریخ</th><th>پرداخت</th><th>فروش</th><th>پورسانت مدیر</th><th>سهم شما</th><th>درصد</th><th>وضعیت</th>
          </tr></thead>
          <tbody>
            {data.results.map((r: any) => (
              <tr key={r.id}>
                <td className="mono">{toFa(r.order_number)}</td>
                <td style={{ whiteSpace: "nowrap" }}>{faDate(r.created_at)}</td>
                <td style={{ fontSize: 12 }}>{r.payment_method}</td>
                <td className="mono">{money(r.gross_amount)}</td>
                <td className="mono" style={{ color: "var(--orange-2)" }}>−{money(r.owner_commission)}</td>
                <td className="mono" style={{ color: "var(--green)", fontWeight: 700 }}>{money(r.supplier_net)}</td>
                <td className="mono">٪{toFa(r.effective_rate)}</td>
                <td><span className={`badge ${STATUS[r.status]?.cls || "purple"}`}>{STATUS[r.status]?.label || r.status}</span></td>
              </tr>
            ))}
            {!data.results.length && <tr><td colSpan={8} style={{ textAlign: "center", color: "var(--muted)", padding: "26px 0" }}>هنوز فروشی ثبت نشده است.</td></tr>}
          </tbody>
        </table>
      </div>

      {pages > 1 && (
        <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 16 }}>
          <button className="btn btn-ghost" style={{ height: 38, padding: "0 14px" }} disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>قبلی</button>
          <span style={{ alignSelf: "center", fontSize: 13, color: "var(--muted)" }}>صفحه {toFa(page)} از {toFa(pages)}</span>
          <button className="btn btn-ghost" style={{ height: 38, padding: "0 14px" }} disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>بعدی</button>
        </div>
      )}
    </div>
  );
}
