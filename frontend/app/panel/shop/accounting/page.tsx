"use client";
// Shop accounting: credit ledger with summary cards and the requested
// paid / unpaid / overdue / due-in-N-days filters.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { money, toFa, faDate } from "@/lib/format";
import NiceSelect from "@/components/NiceSelect";

export default function ShopAccounting() {
  const [all, setAll] = useState<any[]>([]);
  const [state, setState] = useState("");
  const [dueIn, setDueIn] = useState("");
  const [rows, setRows] = useState<any[]>([]);

  // Summary comes from the unfiltered list so the cards stay stable.
  useEffect(() => {
    api.get("/suppliers/my-invoices/").then((d) => setAll(d.results || d)).catch(() => {});
  }, []);

  useEffect(() => {
    const p = new URLSearchParams();
    if (state) p.set("state", state);
    if (dueIn) p.set("due_in", dueIn);
    api.get(`/suppliers/my-invoices/?${p}`).then((d) => setRows(d.results || d)).catch(() => setRows([]));
  }, [state, dueIn]);

  const unsettled = all.filter((i) => !i.is_settled);
  const overdue = unsettled.filter((i) => i.is_overdue);
  const paid = all.filter((i) => i.is_settled);

  return (
    <div>
      <h2 style={{ margin: "0 0 16px", fontSize: 19, fontWeight: 800 }}>حسابداری</h2>

      <div className="statgrid" style={{ marginBottom: 20 }}>
        <div className="stat"><div><div className="v mono" style={{ color: "var(--orange)" }}>{money(unsettled.reduce((s, i) => s + i.amount, 0))}</div><div className="k">بدهی جاری (تومان)</div></div></div>
        <div className="stat"><div><div className="v mono" style={{ color: "var(--red)" }}>{money(overdue.reduce((s, i) => s + i.amount, 0))}</div><div className="k">معوق (تومان)</div></div></div>
        <div className="stat"><div><div className="v mono" style={{ color: "var(--green)" }}>{money(paid.reduce((s, i) => s + i.amount, 0))}</div><div className="k">تسویه‌شده (تومان)</div></div></div>
        <div className="stat"><div><div className="v mono">{toFa(all.length)}</div><div className="k">کل فاکتورها</div></div></div>
      </div>

      <div className="shopbar">
        <div className="fchips">
          {([["", "همه"], ["unsettled", "تسویه‌نشده"], ["settled", "تسویه‌شده"], ["overdue", "معوق"]] as [string, string][]).map(([v, l]) => (
            <button key={v} className={state === v ? "on" : ""} onClick={() => setState(v)}>{l}</button>
          ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
          <span style={{ color: "var(--muted)" }}>سررسید تا</span>
          <NiceSelect value={dueIn} onChange={setDueIn} style={{ minWidth: 140 }}
            options={[{ value: "", label: "همه" }, { value: "3", label: "۳ روز آینده" }, { value: "7", label: "۷ روز آینده" }, { value: "10", label: "۱۰ روز آینده" }, { value: "30", label: "۳۰ روز آینده" }]} />
        </div>
      </div>

      <div className="panel tablewrap">
        <table className="tbl">
          <thead><tr><th>سفارش</th><th>مبلغ</th><th>صدور</th><th>سررسید</th><th>مانده روز</th><th>وضعیت</th></tr></thead>
          <tbody>
            {rows.map((i) => (
              <tr key={i.id}>
                <td className="mono">{toFa(i.order_number || "-")}</td>
                <td className="mono">{money(i.amount)}</td>
                <td>{faDate(i.issued_at)}</td>
                <td>{faDate(i.due_date)}</td>
                <td className="mono">{i.is_settled ? "—" : toFa(i.days_to_due)}</td>
                <td>{i.is_settled ? <span className="badge green">تسویه شد</span> : i.is_overdue ? <span className="badge red">معوق</span> : <span className="badge amber">در انتظار تسویه</span>}</td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--muted)" }}>فاکتوری یافت نشد.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
