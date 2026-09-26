"use client";
// Owner-only control: which suppliers may offer card-to-card (bank receipt) payment.
// Online payment is always available (once the gateway is configured); this
// page is purely about switching card-to-card ON per supplier — a supplier
// cannot grant this to themselves from their own settings page anymore.
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import { toFa } from "@/lib/format";

type Row = { supplier_id: number; supplier_name: string; phone: string; receipt_payment_enabled: boolean };

export default function SupplierPaymentMethodsPage() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  const load = () => api.get<Row[]>("/suppliers/payment-methods-admin/").then(setRows).catch(() => {});
  useEffect(() => { load(); }, []);

  const toggle = async (row: Row) => {
    setBusy(row.supplier_id);
    try {
      await api.patch("/suppliers/payment-methods-admin/", {
        supplier_id: row.supplier_id,
        receipt_payment_enabled: !row.receipt_payment_enabled,
      });
      setRows((prev) => prev!.map((r) => r.supplier_id === row.supplier_id ? { ...r, receipt_payment_enabled: !r.receipt_payment_enabled } : r));
      toast("ذخیره شد ✓");
    } catch (e) {
      toast(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };

  if (!rows) return <div className="skel" style={{ height: 300 }} />;

  return (
    <div>
      <h2 style={{ margin: "0 0 6px", fontSize: 19, fontWeight: 800 }}>روش پرداخت فروشگاه‌ها</h2>
      <p style={{ margin: "0 0 16px", fontSize: 13, color: "var(--muted)", lineHeight: 1.9 }}>
        پرداخت آنلاین همیشه فعال است. فیش بانکی (کارت به کارت) فقط برای تامین‌کنندگانی که اینجا روشن کنید، در دسترس خریدار قرار می‌گیرد.
        اگر سبد خرید شامل چند تامین‌کننده باشد، فیش بانکی فقط زمانی نمایش داده می‌شود که همه آن‌ها فعال باشند.
      </p>
      <div className="panel tablewrap">
        <table className="tbl">
          <thead><tr><th>تامین‌کننده</th><th>موبایل</th><th>فیش بانکی (کارت به کارت)</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.supplier_id}>
                <td>{r.supplier_name}</td>
                <td className="mono">{toFa(r.phone)}</td>
                <td>
                  <label style={{ display: "inline-flex", alignItems: "center", gap: 8, cursor: busy === r.supplier_id ? "wait" : "pointer" }}>
                    <input type="checkbox" checked={r.receipt_payment_enabled} disabled={busy === r.supplier_id} onChange={() => toggle(r)} style={{ accentColor: "var(--purple)", width: 18, height: 18 }} />
                    <span className={`badge ${r.receipt_payment_enabled ? "green" : "red"}`}>{r.receipt_payment_enabled ? "فعال" : "غیرفعال"}</span>
                  </label>
                </td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={3} style={{ textAlign: "center", color: "var(--muted)", padding: 20 }}>هیچ تامین‌کننده‌ای ثبت نشده است.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
