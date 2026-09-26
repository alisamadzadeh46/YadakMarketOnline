"use client";
// Sales report: range chips, KPI cards, daily revenue chart, top products, CSV.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { money, toFa } from "@/lib/format";
import NiceSelect from "@/components/NiceSelect";

function DailyChart({ data }: { data: { date: string; total: number; count: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.total));
  const W = 720, H = 180, pad = 6;
  const bw = (W - pad * 2) / data.length;
  return (
    <svg viewBox={`0 0 ${W} ${H + 8}`} style={{ width: "100%", height: "auto" }}>
      <defs>
        <linearGradient id="rg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--orange-2)" /><stop offset="100%" stopColor="var(--purple-2)" />
        </linearGradient>
      </defs>
      {data.map((d, i) => {
        const h = Math.max(2, (d.total / max) * H);
        return (
          <rect key={d.date} x={pad + i * bw + bw * 0.15} y={H - h} width={Math.max(2, bw * 0.7)} height={h} rx="3"
            fill={d.total ? "url(#rg)" : "var(--purple-soft)"}>
            <title>{`${d.date}: ${d.total.toLocaleString()} تومان (${d.count} سفارش)`}</title>
          </rect>
        );
      })}
    </svg>
  );
}

const STATUS_FA: Record<string, string> = {
  pending_payment: "در انتظار پرداخت", receipt_uploaded: "فیش آپلودشده", confirmed: "تایید شده",
  processing: "در حال پردازش", shipped: "ارسال شده", delivered: "تحویل شده",
  canceled: "لغو شده", credit: "اعتباری",
};

export default function SupplierReports() {
  const [days, setDays] = useState(30);
  const [r, setR] = useState<any>(null);

  useEffect(() => {
    api.get(`/suppliers/reports/?days=${days}`).then(setR).catch(() => {});
  }, [days]);

  const exportCsv = () => {
    if (!r) return;
    const head = ["تاریخ", "فروش (تومان)", "تعداد سفارش"];
    const lines = r.series.map((d: any) => [d.date, d.total, d.count].join(","));
    const blob = new Blob(["﻿" + [head.join(","), ...lines].join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `sales-report-${days}d.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  if (!r) return <div className="skel" style={{ height: 400 }} />;

  return (
    <div>
      <h2 style={{ margin: "0 0 16px", fontSize: 19, fontWeight: 800 }}>گزارش فروش</h2>
      <div className="shopbar">
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
          <span style={{ color: "var(--muted)" }}>بازه زمانی:</span>
          <NiceSelect value={String(days)} onChange={(v) => setDays(+v)} style={{ minWidth: 140 }}
            options={[{ value: "7", label: "۷ روز اخیر" }, { value: "30", label: "۳۰ روز اخیر" }, { value: "90", label: "۹۰ روز اخیر" }]} />
        </div>
        <button className="btn btn-ghost" style={{ height: 40, padding: "0 16px", fontSize: 12.5 }} onClick={exportCsv}>⬇ خروجی CSV</button>
      </div>

      <div className="statgrid" style={{ marginBottom: 18 }}>
        <div className="stat"><div><div className="v mono" style={{ color: "var(--green)" }}>{money(r.revenue)}</div><div className="k">فروش کل (تومان)</div></div></div>
        <div className="stat"><div><div className="v mono">{toFa(r.orders)}</div><div className="k">سفارش موفق</div></div></div>
        <div className="stat"><div><div className="v mono">{money(r.avg_order)}</div><div className="k">میانگین هر سفارش</div></div></div>
        <div className="stat"><div><div className="v mono" style={{ color: "var(--red)" }}>{toFa(r.canceled)}</div><div className="k">لغو شده</div></div></div>
      </div>

      <div className="panel" style={{ marginBottom: 16 }}>
        <b style={{ display: "block", marginBottom: 12 }}>روند فروش روزانه</b>
        <DailyChart data={r.series} />
      </div>

      <div className="cols-2">
        <div className="panel tablewrap">
          <b style={{ display: "block", marginBottom: 10 }}>پرفروش‌ترین محصولات</b>
          <table className="tbl">
            <thead><tr><th>محصول</th><th>تعداد</th><th>درآمد</th></tr></thead>
            <tbody>
              {r.top_products.map((p: any) => (
                <tr key={p.product_id}>
                  <td className="wrap">{p.product_name}</td>
                  <td className="mono">{toFa(p.qty)}</td>
                  <td className="mono">{money(p.revenue)}</td>
                </tr>
              ))}
              {!r.top_products.length && <tr><td colSpan={3} style={{ textAlign: "center", color: "var(--muted)" }}>فروشی در این بازه نبود.</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="panel tablewrap">
          <b style={{ display: "block", marginBottom: 10 }}>تفکیک وضعیت سفارش‌ها</b>
          <table className="tbl">
            <thead><tr><th>وضعیت</th><th>تعداد</th><th>مبلغ</th></tr></thead>
            <tbody>
              {r.by_status.map((s: any) => (
                <tr key={s.status}>
                  <td><span className="badge purple">{STATUS_FA[s.status] || s.status}</span></td>
                  <td className="mono">{toFa(s.count)}</td>
                  <td className="mono">{money(s.total || 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
