"use client";
// Shopkeeper dashboard: approval banner (with a clear CTA), quick stats and
// the invoices closest to their due date.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money, toFa, faDate } from "@/lib/format";
import { ICart, ICredit, IShield } from "@/components/Icon";

export default function ShopHome() {
  const { user } = useAuth();
  const [orders, setOrders] = useState<any[]>([]);
  const [invoices, setInvoices] = useState<any[]>([]);

  useEffect(() => {
    api.get("/orders/orders/").then((d) => setOrders(d.results || d)).catch(() => {});
    api.get("/suppliers/my-invoices/?state=unsettled").then((d) => setInvoices(d.results || d)).catch(() => {});
  }, []);

  const outstanding = invoices.reduce((s, i) => s + i.amount, 0);

  return (
    <div>
      {!user?.is_approved && (
        <div className="panel" style={{ marginBottom: 16, borderColor: "#F5C9A8", background: "var(--orange-soft)", display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 240 }}>
            <b>حساب فروشگاه شما هنوز تایید نشده است.</b>
            <div style={{ fontSize: 13, marginTop: 6, color: "var(--ink-soft)" }}>
              برای فعال‌سازی خرید عمده و اعتباری، اطلاعات فروشگاه و مدارک را تکمیل کنید تا تامین‌کننده بررسی و تایید کند.
            </div>
          </div>
          <Link href="/panel/shop/profile" className="btn btn-orange" style={{ height: 46, padding: "0 22px" }}>تکمیل احراز هویت ›</Link>
        </div>
      )}

      <div className="statgrid" style={{ marginBottom: 20 }}>
        <div className="stat"><div className="ic"><ICart size={22} /></div><div><div className="v mono">{toFa(orders.length)}</div><div className="k">کل خریدها</div></div></div>
        <div className="stat"><div className="ic" style={{ background: "var(--orange-soft)", color: "var(--orange)" }}><ICredit size={22} /></div><div><div className="v mono">{money(outstanding)}</div><div className="k">بدهی اعتباری (تومان)</div></div></div>
        <div className="stat"><div className="ic" style={{ background: "#E7F6EE", color: "var(--green)" }}><IShield size={22} /></div><div><div className="v mono">{toFa(invoices.length)}</div><div className="k">فاکتور باز</div></div></div>
      </div>

      <div className="between" style={{ marginBottom: 12 }}>
        <b style={{ fontSize: 16 }}>نزدیک‌ترین سررسیدها</b>
        <Link href="/panel/shop/accounting" style={{ color: "var(--purple)", fontSize: 13, fontWeight: 700 }}>حسابداری ›</Link>
      </div>
      <div className="panel tablewrap">
        <table className="tbl">
          <thead><tr><th>سفارش</th><th>مبلغ</th><th>سررسید</th><th>مانده روز</th></tr></thead>
          <tbody>
            {invoices.slice(0, 5).map((i) => (
              <tr key={i.id}>
                <td className="mono">{toFa(i.order_number || "-")}</td>
                <td className="mono">{money(i.amount)}</td>
                <td>{faDate(i.due_date)}</td>
                <td>{i.is_overdue ? <span className="badge red">معوق</span> : <span className="mono">{toFa(i.days_to_due)} روز</span>}</td>
              </tr>
            ))}
            {!invoices.length && <tr><td colSpan={4} style={{ textAlign: "center", color: "var(--muted)" }}>فاکتور باز ندارید.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
