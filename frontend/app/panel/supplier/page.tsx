"use client";
// Supplier (Omidi) dashboard: live counters, a 7-day sales chart, low-stock
// alerts and quick actions.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { money, toFa } from "@/lib/format";
import { useAuth } from "@/lib/auth";

function WeekChart({ data }: { data: { date: string; total: number; count: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.total));
  const W = 560, H = 170, pad = 8;
  const bw = (W - pad * 2) / data.length;
  const day = (iso: string) =>
    new Intl.DateTimeFormat("fa-IR", { weekday: "short" }).format(new Date(iso));
  return (
    <svg viewBox={`0 0 ${W} ${H + 26}`} style={{ width: "100%", height: "auto" }}>
      {data.map((d, i) => {
        const h = Math.max(4, (d.total / max) * H);
        const x = pad + i * bw + bw * 0.18;
        return (
          <g key={d.date}>
            <rect x={x} y={H - h} width={bw * 0.64} height={h} rx="7"
              fill={d.total ? "url(#gbar)" : "var(--purple-soft)"}>
              <title>{`${d.date}: ${d.total.toLocaleString()} تومان (${d.count} سفارش)`}</title>
            </rect>
            <text x={x + bw * 0.32} y={H + 18} textAnchor="middle" fontSize="11"
              fill="var(--muted)" style={{ fontFamily: "inherit" }}>{day(d.date)}</text>
          </g>
        );
      })}
      <defs>
        <linearGradient id="gbar" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--orange-2)" />
          <stop offset="100%" stopColor="var(--purple-2)" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export default function SupplierHome() {
  const { user } = useAuth();
  // The User payload carries `role` only (see lib/auth.tsx) — the owner is the
  // admin role, which is exactly what PanelLayout gates the adminOnly items on.
  const isOwner = user?.role === "admin";
  const [s, setS] = useState<any>(null);
  useEffect(() => { api.get("/suppliers/dashboard/").then(setS).catch(() => {}); }, []);

  if (!s) return <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(190px,1fr))" }}>{[1, 2, 3, 4].map((i) => <div key={i} className="skel" style={{ height: 90 }} />)}</div>;

  const CARDS = [
    { v: toFa(s.orders_pending_receipt), k: "فیش در انتظار تایید", href: "/panel/supplier/orders", hot: s.orders_pending_receipt > 0 },
    { v: toFa(s.shops_pending), k: "فروشگاه در انتظار تایید", href: "/panel/supplier/shops", hot: s.shops_pending > 0 },
    { v: toFa(s.orders_total), k: "کل سفارش‌ها", href: "/panel/supplier/orders" },
    { v: toFa(s.products_total), k: "محصولات", href: "/panel/supplier/products" },
    { v: money(s.credit_outstanding), k: "مطالبات اعتباری (تومان)", href: "/panel/supplier/credit" },
    { v: toFa(s.credit_invoices_open), k: "فاکتور اعتباری باز", href: "/panel/supplier/credit" },
  ];

  return (
    <div>
      <div className="panel" style={{ marginBottom: 16, background: "linear-gradient(120deg,var(--purple-deep),var(--purple-2))", color: "#fff", border: "none" }}>
        <div className="between">
          <div>
            {/* "Content and credit" are owner-only sections; promising them to a
                plain supplier describes a panel they cannot reach. */}
            <b style={{ fontSize: 18 }}>
              {isOwner ? "پنل مدیریت سایت" : `پنل ${user?.full_name || "تامین‌کننده"}`}
            </b>
            <div style={{ opacity: .85, fontSize: 13.5, marginTop: 6 }}>
              {isOwner
                ? "مدیریت کامل فروشگاه، محتوا و اعتبار — همه در یک‌جا."
                : "محصولات، سفارش‌ها و درآمد فروشگاه شما — همه در یک‌جا."}
            </div>
          </div>
          <div className="row">
            <Link href="/panel/supplier/products" className="btn" style={{ height: 42, padding: "0 16px", background: "rgba(255,255,255,.14)", color: "#fff", fontSize: 13 }}>+ محصول</Link>
            {/* Blog is an owner-only section (adminOnly in the panel nav), so a
                plain supplier must not be offered a shortcut into it — the
                route bounces them straight back out. */}
            {isOwner && (
              <Link href="/panel/supplier/blog" className="btn btn-orange" style={{ height: 42, padding: "0 16px", fontSize: 13 }}>+ مقاله</Link>
            )}
          </div>
        </div>
      </div>

      <div className="statgrid" style={{ marginBottom: 18 }}>
        {CARDS.map((c, i) => (
          <Link key={i} href={c.href} className="stat" style={c.hot ? { borderColor: "var(--orange)" } : undefined}>
            <div><div className="v mono" style={c.hot ? { color: "var(--orange)" } : undefined}>{c.v}</div><div className="k">{c.k}</div></div>
          </Link>
        ))}
      </div>

      <div className="cols-2">
        <div className="panel">
          <div className="between" style={{ marginBottom: 10 }}>
            <b>فروش ۷ روز اخیر</b>
            <span className="mono" style={{ fontSize: 12.5, color: "var(--muted)" }}>
              مجموع: {money(s.sales_week.reduce((a: number, d: any) => a + d.total, 0))} تومان
            </span>
          </div>
          <WeekChart data={s.sales_week} />
        </div>

        <div className="panel">
          <div className="between" style={{ marginBottom: 10 }}>
            <b>⚠ موجودی رو به اتمام</b>
            <Link href="/panel/supplier/products" style={{ fontSize: 12.5, color: "var(--purple)", fontWeight: 700 }}>مدیریت ›</Link>
          </div>
          {s.low_stock.length ? (
            <div className="tablewrap">
              <table className="tbl">
                <tbody>
                  {s.low_stock.map((p: any) => (
                    <tr key={p.id}>
                      <td className="wrap">{p.name}</td>
                      <td><span className={`badge ${p.stock === 0 ? "red" : "amber"}`}>{p.stock === 0 ? "ناموجود" : `${toFa(p.stock)} عدد`}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ color: "var(--muted)", fontSize: 13.5 }}>موجودی همه کالاها کافی است ✓</div>
          )}
        </div>
      </div>
    </div>
  );
}
