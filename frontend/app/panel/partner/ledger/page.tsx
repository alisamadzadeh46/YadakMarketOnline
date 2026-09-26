"use client";
// The commission ledger: one row per sale, with settlement actions and CSV.
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import { money, toFa, faDate } from "@/lib/format";
import Pagination from "@/components/Pagination";
import NiceSelect from "@/components/NiceSelect";
import { usePage } from "@/lib/usePage";

type Row = {
  id: number; order_number: string; order_total: number; order_status: string;
  buyer_name: string; buyer_role: string; buyer_role_display: string;
  base_amount: number; effective_rate: string; amount: number;
  status: string; status_display: string; paid_at?: string; created_at: string;
};

const STATUSES: [string, string][] = [
  ["", "همه"], ["earned", "قابل دریافت"], ["paid", "تسویه‌شده"],
  ["pending", "در انتظار تسویه سفارش"], ["void", "باطل‌شده"],
];

const BADGE: Record<string, string> = {
  earned: "amber", paid: "green", pending: "purple", void: "red",
};

export default function PartnerLedger() {
  const [rows, setRows] = useState<Row[]>([]);
  const [count, setCount] = useState(0);
  const [status, setStatus] = useState("");
  const [role, setRole] = useState("");
  const [days, setDays] = useState("");
  const [q, setQ] = useState("");
  // The search box is applied on submit, not on every keystroke.
  const [query, setQuery] = useState("");
  const [page, setPage] = usePage([status, role, days, query]);

  const load = useCallback(() => {
    const qs = new URLSearchParams({ page: String(page) });
    if (status) qs.set("status", status);
    if (role) qs.set("role", role);
    if (days) qs.set("days", days);
    if (query) qs.set("q", query);
    api.get(`/commissions/ledger/?${qs}`)
      .then((d) => { setRows(d.results || d); setCount(d.count ?? 0); })
      .catch(() => {});
  }, [page, status, role, days, query]);
  useEffect(() => { load(); }, [load]);

  const markPaid = async (id: number) => {
    try {
      await api.post(`/commissions/entries/${id}/mark-paid/`);
      toast("به‌عنوان تسویه‌شده ثبت شد ✓");
      load();
    } catch (e) { toast(errorMessage(e)); }
  };

  const exportCsv = () => {
    const head = ["سفارش", "خریدار", "نوع", "مبلغ سفارش", "درصد", "سهم شما", "وضعیت", "تاریخ"];
    const lines = rows.map((r) =>
      [r.order_number, r.buyer_name, r.buyer_role_display, r.base_amount,
       r.effective_rate, r.amount, r.status_display, r.created_at].join(",")
    );
    const blob = new Blob(["﻿" + [head.join(","), ...lines].join("\n")], {
      type: "text/csv;charset=utf-8",
    });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `commissions-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const pageTotal = rows.reduce((n, r) => n + (r.status === "void" ? 0 : r.amount), 0);

  return (
    <div>
      <div className="between" style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 19, fontWeight: 800 }}>دفتر پورسانت</h2>
        <button className="btn btn-ghost" style={{ height: 40, padding: "0 16px", fontSize: 13 }} onClick={exportCsv}>
          ⬇ خروجی اکسل (CSV)
        </button>
      </div>

      <div className="shopbar">
        <div className="fchips">
          {STATUSES.map(([v, l]) => (
            <button key={v} className={status === v ? "on" : ""} onClick={() => setStatus(v)}>{l}</button>
          ))}
        </div>
        <NiceSelect value={role} onChange={setRole} style={{ minWidth: 160 }}
          options={[
            { value: "", label: "همه خریداران" },
            { value: "shopkeeper", label: "فروشگاه‌ها" },
            { value: "customer", label: "کاربران عادی" },
          ]} />
        <NiceSelect value={days} onChange={setDays} style={{ minWidth: 150 }}
          options={[
            { value: "", label: "از ابتدا" },
            { value: "7", label: "۷ روز اخیر" },
            { value: "30", label: "۳۰ روز اخیر" },
            { value: "90", label: "۹۰ روز اخیر" },
          ]} />
        <form onSubmit={(e) => { e.preventDefault(); setQuery(q.trim()); }} style={{ display: "flex", gap: 8, flex: 1, minWidth: 180 }}>
          <input className="inp" placeholder="جستجوی شماره سفارش…" value={q} onChange={(e) => setQ(e.target.value)} />
          <button className="btn btn-purple" style={{ height: 42, padding: "0 16px", fontSize: 13 }}>جستجو</button>
        </form>
      </div>

      <div className="panel">
        <div className="between" style={{ marginBottom: 10 }}>
          <b>{toFa(count)} ردیف</b>
          <span className="mono" style={{ fontSize: 12.5, color: "var(--muted)" }}>
            جمع این صفحه: {money(pageTotal)} تومان
          </span>
        </div>
        <div className="tablewrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>سفارش</th><th>خریدار</th><th>مبلغ سفارش</th><th>درصد</th>
                <th>سهم شما</th><th>وضعیت</th><th>تاریخ</th><th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td className="mono">{toFa(r.order_number)}</td>
                  {/* nowrap: the wrapper already scrolls, and breaking a name
                      mid-word reads terribly on a phone. */}
                  <td>
                    {r.buyer_name}
                    <div style={{ fontSize: 11.5, color: "var(--muted)" }}>{r.buyer_role_display}</div>
                  </td>
                  <td className="mono">{money(r.base_amount)}</td>
                  <td className="mono">{toFa(r.effective_rate)}٪</td>
                  <td className="mono"><b style={{ color: "var(--purple)" }}>{money(r.amount)}</b></td>
                  <td><span className={`badge ${BADGE[r.status] || "purple"}`}>{r.status_display}</span></td>
                  <td>{faDate(r.created_at)}</td>
                  <td>
                    {r.status === "earned" && (
                      <button className="act-edit" onClick={() => markPaid(r.id)}>ثبت تسویه</button>
                    )}
                  </td>
                </tr>
              ))}
              {!rows.length && (
                <tr><td colSpan={8} style={{ textAlign: "center", color: "var(--muted)", padding: 30 }}>
                  ردیفی با این فیلترها پیدا نشد.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
        <Pagination page={page} count={count} onChange={setPage} />
      </div>
    </div>
  );
}
