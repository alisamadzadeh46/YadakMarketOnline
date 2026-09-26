"use client";
// Communication hub: SMS delivery log, contact-form inbox, newsletter stats.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toFa, faDate } from "@/lib/format";
import Pagination from "@/components/Pagination";
import { usePage } from "@/lib/usePage";

const KIND: Record<string, string> = {
  settlement_reminder: "یادآوری تسویه",
  verification: "کد تایید",
  order: "سفارش",
  other: "سایر",
};

export default function SupplierComms() {
  const [tab, setTab] = useState<"sms" | "inbox" | "news">("sms");
  const [sms, setSms] = useState<any[]>([]);
  const [inbox, setInbox] = useState<any[]>([]);
  const [news, setNews] = useState<any>(null);
  const [count, setCount] = useState(0);

  const [page, setPage] = usePage([tab]);
  useEffect(() => {
    if (tab === "sms")
      api.get(`/suppliers/sms-logs/?page=${page}`)
        .then((d) => { setSms(d.results || d); setCount(d.count ?? 0); })
        .catch(() => {});
    if (tab === "inbox")
      api.get(`/cms/manage/contacts/?page=${page}`)
        .then((d) => { setInbox(d.results || d); setCount(d.count ?? 0); })
        .catch(() => {});
    if (tab === "news") api.get("/cms/manage/subscribers/").then(setNews).catch(() => {});
  }, [tab, page]);

  const markRead = async (id: number) => {
    await api.post(`/cms/manage/contacts/${id}/read/`);
    setInbox(inbox.map((m) => (m.id === id ? { ...m, is_read: true } : m)));
  };

  return (
    <div>
      <h2 style={{ margin: "0 0 16px", fontSize: 19, fontWeight: 800 }}>ارتباطات</h2>
      <div className="panel">
      <div className="segtabs" style={{ marginBottom: 18 }}>
        <button className={tab === "sms" ? "on" : ""} onClick={() => setTab("sms")}>پیامک‌های ارسالی</button>
        <button className={tab === "inbox" ? "on" : ""} onClick={() => setTab("inbox")}>پیام‌های تماس</button>
        <button className={tab === "news" ? "on" : ""} onClick={() => setTab("news")}>خبرنامه</button>
      </div>

      {tab === "sms" && (
        <div className="tablewrap">
          <table className="tbl">
            <thead><tr><th>گیرنده</th><th>متن</th><th>نوع</th><th>وضعیت</th><th>زمان</th></tr></thead>
            <tbody>
              {sms.map((m) => (
                <tr key={m.id}>
                  <td className="mono">{toFa(m.recipient)}</td>
                  <td className="wrap" style={{ maxWidth: 340, fontSize: 12.5 }}>{m.message}</td>
                  <td>{KIND[m.kind] || m.kind}</td>
                  <td>{m.is_sent ? <span className="badge green">ارسال شد</span> : <span className="badge red">ناموفق</span>}</td>
                  <td style={{ fontSize: 12 }}>{faDate(m.created_at)}</td>
                </tr>
              ))}
              {!sms.length && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--muted)" }}>پیامکی ارسال نشده است.</td></tr>}
            </tbody>
          </table>
          <Pagination page={page} count={count} pageSize={20} onChange={setPage} />
        </div>
      )}

      {tab === "inbox" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {inbox.map((m) => (
            <div key={m.id} style={{ background: "var(--paper)", borderRadius: 14, padding: 16, borderRight: `4px solid ${m.is_read ? "var(--line)" : "var(--orange)"}` }}>
              <div className="between">
                <b>{m.subject}</b>
                {!m.is_read && <button className="act-edit list-actions" onClick={() => markRead(m.id)}>علامت خوانده‌شده</button>}
              </div>
              <div style={{ fontSize: 12.5, color: "var(--muted)", margin: "6px 0 10px" }}>
                {m.name} · <span className="mono">{toFa(m.phone || "")}</span> {m.email && `· ${m.email}`} · {faDate(m.created_at)}
              </div>
              <div style={{ fontSize: 14, lineHeight: 2 }}>{m.message}</div>
            </div>
          ))}
          {!inbox.length && <div className="center-empty">پیامی دریافت نشده است.</div>}
          <Pagination page={page} count={count} onChange={setPage} />
        </div>
      )}

      {tab === "news" && news && (
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 16, padding: "14px 16px", borderRadius: 14, background: "var(--purple-soft)" }}>
            <span style={{ width: 46, height: 46, borderRadius: 13, background: "linear-gradient(135deg,var(--purple),var(--purple-2))", color: "#fff", display: "grid", placeItems: "center", fontSize: 20 }}>✉</span>
            <div>
              <b className="mono" style={{ fontSize: 22 }}>{toFa(news.count)}</b>
              <span style={{ marginRight: 8, fontWeight: 700 }}>مشترک فعال خبرنامه</span>
              <div style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 4 }}>با انتشار هر مقاله، ایمیل اطلاع‌رسانی به‌صورت خودکار برای همه ارسال می‌شود.</div>
            </div>
          </div>
          <div className="tablewrap">
            <table className="tbl">
              <thead><tr><th style={{ textAlign: "center" }}>ایمیل</th><th style={{ textAlign: "center" }}>تاریخ عضویت</th></tr></thead>
              <tbody>
                {news.latest.map((r: any, i: number) => (
                  <tr key={i}>
                    <td dir="ltr" className="mono" style={{ textAlign: "center", fontSize: 13 }}>{r.email}</td>
                    <td style={{ textAlign: "center" }}>{faDate(r.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}
