"use client";
// Partner dashboard: what the revenue share has earned, and where it came from.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { money, toFa } from "@/lib/format";

type Summary = {
  unpaid: number; paid: number; pending: number; this_month: number; lifetime: number;
  orders_count: number; current_rate: string; is_active: boolean;
  chart: { date: string; total: number }[];
  by_role: { buyer_role: string; total: number; orders: number }[];
};

const ROLE_FA: Record<string, string> = {
  shopkeeper: "فروشگاه‌های لوازم یدکی",
  customer: "کاربران عادی",
  supplier: "تامین‌کننده",
  admin: "مدیر",
  partner: "شریک",
};

function EarningsChart({ data }: { data: { date: string; total: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.total));
  const W = 640, H = 170, pad = 6;
  const bw = (W - pad * 2) / Math.max(1, data.length);
  const dayNum = (iso: string) =>
    new Intl.DateTimeFormat("fa-IR", { day: "numeric" }).format(new Date(iso));
  return (
    <svg viewBox={`0 0 ${W} ${H + 24}`} style={{ width: "100%", height: "auto" }}>
      <defs>
        <linearGradient id="pg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--orange-2)" />
          <stop offset="100%" stopColor="var(--purple-2)" />
        </linearGradient>
      </defs>
      {data.map((d, i) => {
        const h = Math.max(3, (d.total / max) * H);
        const x = pad + i * bw + bw * 0.17;
        return (
          <g key={d.date}>
            <rect x={x} y={H - h} width={Math.max(3, bw * 0.66)} height={h} rx="5"
              fill={d.total ? "url(#pg)" : "var(--purple-soft)"}>
              <title>{`${d.date}: ${d.total.toLocaleString()} تومان`}</title>
            </rect>
            <text x={x + bw * 0.33} y={H + 16} textAnchor="middle" fontSize="10" fill="var(--muted)">
              {dayNum(d.date)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

type SupplierRow = {
  supplier_id: number; supplier_name: string;
  sales: number; owner_commission: number; supplier_net: number; orders: number;
};

export default function PartnerHome() {
  const [s, setS] = useState<Summary | null>(null);
  const [bySupplier, setBySupplier] = useState<SupplierRow[]>([]);

  useEffect(() => {
    api.get<Summary>("/commissions/summary/").then(setS).catch(() => {});
    api.get<SupplierRow[]>("/commissions/by-supplier/").then(setBySupplier).catch(() => {});
  }, []);

  if (!s)
    return (
      <div className="statgrid">
        {[1, 2, 3, 4].map((i) => <div key={i} className="skel" style={{ height: 90 }} />)}
      </div>
    );

  const CARDS = [
    { v: money(s.unpaid), u: "تومان", k: "قابل دریافت", hot: s.unpaid > 0, href: "/panel/partner/ledger?status=earned" },
    { v: money(s.this_month), u: "تومان", k: "درآمد این ماه", href: "/panel/partner/ledger?days=30" },
    { v: money(s.lifetime), u: "تومان", k: "درآمد کل", href: "/panel/partner/ledger" },
    { v: money(s.paid), u: "تومان", k: "تسویه‌شده", href: "/panel/partner/ledger?status=paid" },
    { v: money(s.pending), u: "تومان", k: "در انتظار تسویه سفارش", href: "/panel/partner/ledger?status=pending" },
    { v: toFa(s.orders_count), u: "سفارش", k: "تعداد سفارش سهم‌دار", href: "/panel/partner/ledger" },
  ];
  const noDataYet = s.lifetime === 0 && s.orders_count === 0;

  return (
    <div>
      <div className="panel" style={{ marginBottom: 16, background: "linear-gradient(120deg,var(--purple-deep),var(--purple-2))", color: "#fff", border: "none" }}>
        <div className="between">
          <div>
            <b style={{ fontSize: 18 }}>پیشخوان درآمد شما</b>
            <div style={{ opacity: .85, fontSize: 13.5, marginTop: 6 }}>
              درصد فعلی: <b className="mono">{toFa(s.current_rate)}٪</b> از هر فروش
              {!s.is_active && " — در حال حاضر غیرفعال است"}
            </div>
          </div>
          <div className="row">
            <Link href="/panel/partner/settings" className="btn btn-orange" style={{ height: 42, padding: "0 16px", fontSize: 13 }}>
              تغییر درصد
            </Link>
          </div>
        </div>
      </div>

      {noDataYet && (
        <div className="panel" style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 12, padding: "16px 18px" }}>
          <span style={{ width: 38, height: 38, borderRadius: 11, background: "var(--purple-soft)", color: "var(--purple)", display: "grid", placeItems: "center", flexShrink: 0 }}>
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9" /><path d="M12 8v4M12 16h.01" /></svg>
          </span>
          <span style={{ fontSize: 13, color: "var(--ink-soft)" }}>هنوز هیچ سفارشی سهم پورسانت ثبت نکرده — به‌محض تایید اولین پرداخت (آنلاین یا فیش)، اعداد این صفحه به‌روز می‌شوند.</span>
        </div>
      )}

      <div className="statgrid" style={{ marginBottom: 18 }}>
        {CARDS.map((c, i) => (
          <Link key={i} href={c.href} className="stat"
            style={c.hot ? { borderColor: "var(--orange)" } : undefined}>
            <div>
              <div className="v mono" style={c.hot ? { color: "var(--orange)" } : undefined}>
                {c.v}<span className="stat-unit">{c.u}</span>
              </div>
              <div className="k">{c.k}</div>
            </div>
          </Link>
        ))}
      </div>

      <div className="cols-2">
        <div className="panel">
          <div className="between" style={{ marginBottom: 10 }}>
            <b>درآمد ۱۴ روز اخیر</b>
            <span className="mono" style={{ fontSize: 12.5, color: "var(--muted)" }}>
              مجموع: {money(s.chart.reduce((a, d) => a + d.total, 0))} تومان
            </span>
          </div>
          <EarningsChart data={s.chart} />
        </div>

        <div className="panel">
          <b>سهم شما به تفکیک نوع خریدار</b>
          <div style={{ marginTop: 12 }}>
            {s.by_role.length ? s.by_role.map((r) => (
              <div key={r.buyer_role} className="specrow">
                <span>{ROLE_FA[r.buyer_role] || r.buyer_role}
                  <span style={{ color: "var(--muted)", fontSize: 12 }}> ({toFa(r.orders)} سفارش)</span>
                </span>
                <b className="mono">{money(r.total)} تومان</b>
              </div>
            )) : (
              <div style={{ color: "var(--muted)", fontSize: 13.5 }}>هنوز فروشی ثبت نشده است.</div>
            )}
          </div>
        </div>
      </div>

      <div className="panel tablewrap" style={{ marginTop: 16 }}>
        <b style={{ display: "block", marginBottom: 10 }}>تفکیک فروش و پورسانت به‌ازای هر تامین‌کننده</b>
        <table className="tbl" style={{ minWidth: 620 }}>
          <thead><tr>
            <th>تامین‌کننده</th><th>سفارش</th><th>فروش کل</th><th>سهم شما (پورسانت)</th><th>سهم تامین‌کننده</th>
          </tr></thead>
          <tbody>
            {bySupplier.length ? bySupplier.map((r) => (
              <tr key={r.supplier_id}>
                <td style={{ whiteSpace: "nowrap" }}>{r.supplier_name}</td>
                <td className="mono">{toFa(r.orders)}</td>
                <td className="mono">{money(r.sales)}</td>
                <td className="mono" style={{ color: "var(--orange-2)", fontWeight: 700 }}>{money(r.owner_commission)}</td>
                <td className="mono" style={{ color: "var(--green)" }}>{money(r.supplier_net)}</td>
              </tr>
            )) : (
              <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--muted)", padding: "22px 0" }}>هنوز فروشی ثبت نشده است.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
