"use client";
// Customer dashboard: greeting, quick stats and the latest orders.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money, toFa, faDate } from "@/lib/format";
import { ICart, IStar, IUser } from "@/components/Icon";
import { SITE } from "@/lib/site";

export default function AccountHome() {
  const { user } = useAuth();
  const [orders, setOrders] = useState<any[]>([]);
  const [favCount, setFavCount] = useState(0);

  useEffect(() => {
    api.get("/orders/orders/").then((d) => setOrders(d.results || d)).catch(() => {});
    api.get("/catalog/favorites/").then((d) => setFavCount((d.results || d).length)).catch(() => {});
  }, []);

  const open = orders.filter((o) => ["pending_payment", "receipt_uploaded"].includes(o.status)).length;

  return (
    <div>
      <div className="panel" style={{ marginBottom: 16, background: "linear-gradient(120deg,var(--purple-deep),var(--purple-2))", color: "#fff", border: "none" }}>
        <b style={{ fontSize: 18 }}>سلام {user?.full_name || "کاربر"} عزیز 👋</b>
        <div style={{ opacity: .85, fontSize: 13.5, marginTop: 6 }}>به پیشخوان حساب کاربری {SITE.shortName} خوش آمدید.</div>
      </div>

      <div className="statgrid" style={{ marginBottom: 20 }}>
        <div className="stat"><div className="ic"><ICart size={22} /></div><div><div className="v mono">{toFa(orders.length)}</div><div className="k">کل سفارش‌ها</div></div></div>
        <div className="stat"><div className="ic" style={{ background: "var(--orange-soft)", color: "var(--orange)" }}><IUser size={22} /></div><div><div className="v mono">{toFa(open)}</div><div className="k">سفارش در جریان</div></div></div>
        <div className="stat"><div className="ic" style={{ background: "#E7F6EE", color: "var(--green)" }}><IStar size={22} /></div><div><div className="v mono">{toFa(favCount)}</div><div className="k">علاقه‌مندی‌ها</div></div></div>
      </div>

      <div className="between" style={{ marginBottom: 12 }}>
        <b style={{ fontSize: 16 }}>آخرین سفارش‌ها</b>
        <Link href="/account/orders" style={{ color: "var(--purple)", fontSize: 13, fontWeight: 700 }}>همه ›</Link>
      </div>
      <div className="panel tablewrap">
        <table className="tbl">
          <thead><tr><th>شماره</th><th>تاریخ</th><th>مبلغ</th><th>وضعیت</th></tr></thead>
          <tbody>
            {orders.slice(0, 5).map((o) => (
              <tr key={o.id}>
                <td className="mono"><Link href={`/order/${o.number}`} style={{ color: "var(--purple)" }}>{toFa(o.number)}</Link></td>
                <td>{faDate(o.created_at)}</td>
                <td className="mono">{money(o.total)}</td>
                <td><span className="badge purple">{o.status_display}</span></td>
              </tr>
            ))}
            {!orders.length && <tr><td colSpan={4} style={{ textAlign: "center", color: "var(--muted)" }}>هنوز سفارشی ثبت نکرده‌اید.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
