"use client";
// Settlement reminders hub: every unsettled invoice listed (paginated) with a
// one-click "send reminder SMS" per row, plus the reminder/card settings in a
// collapsible panel.
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import { money, toFa, faDate } from "@/lib/format";
import Pagination from "@/components/Pagination";

export default function SupplierSettings() {
  const [s, setS] = useState<any>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [busy, setBusy] = useState(false);
  const [rows, setRows] = useState<any[]>([]);
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [sending, setSending] = useState<number | null>(null);

  useEffect(() => { api.get("/suppliers/settings/").then(setS).catch(() => {}); }, []);
  const load = useCallback(() =>
    api.get(`/suppliers/invoices/?state=unsettled&page=${page}`)
      .then((d) => { setRows(d.results || d); setCount(d.count ?? 0); })
      .catch((e) => toast(errorMessage(e))), [page]);
  useEffect(() => { load(); }, [load]);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try { await api.patch("/suppliers/settings/", s); toast("تنظیمات ذخیره شد ✓"); setShowSettings(false); }
    catch (err) { toast(errorMessage(err)); }
    finally { setBusy(false); }
  };

  const remind = async (id: number) => {
    setSending(id);
    try {
      const r = await api.post(`/suppliers/invoices/${id}/remind/`);
      toast(r.detail || "پیامک ارسال شد ✓");
      load();
    } catch (err) { toast(errorMessage(err)); }
    finally { setSending(null); }
  };

  return (
    <div>
      <div className="between" style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 19, fontWeight: 800 }}>یادآوری تسویه و تنظیمات</h2>
        <button className="btn btn-ghost" style={{ height: 42, padding: "0 18px" }} onClick={() => setShowSettings(!showSettings)}>
          ⚙ تنظیمات پیامک و کارت {showSettings ? "▴" : "▾"}
        </button>
      </div>

      {showSettings && s && (
        <form className="panel view" style={{ marginBottom: 16 }} onSubmit={save}>
          <div className="fgrid">
            <div className="field">
              <label>چند روز قبل از سررسید، پیامک خودکار برود؟</label>
              <input className="inp" type="number" min={0} required value={s.default_reminder_days} onChange={(e) => setS({ ...s, default_reminder_days: +e.target.value })} />
              <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 6 }}>برای هر فروشگاه هم می‌توان جداگانه در بخش «اعتبار» تنظیم کرد.</div>
            </div>
            <div className="field" style={{ display: "flex", alignItems: "center" }}>
              <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer", margin: 0 }}>
                <input type="checkbox" checked={s.sms_reminders_enabled} onChange={(e) => setS({ ...s, sms_reminders_enabled: e.target.checked })} style={{ accentColor: "var(--purple)", width: 17, height: 17 }} />
                ارسال خودکار پیامک یادآوری فعال باشد
              </label>
            </div>
            <div className="field"><label>شماره کارت (کارت به کارت)</label><input className="inp" dir="ltr" pattern="\d{16}" data-error="شماره کارت باید ۱۶ رقم باشد." value={s.card_number || ""} onChange={(e) => setS({ ...s, card_number: e.target.value })} /></div>
            <div className="field"><label>به نام</label><input className="inp" value={s.card_holder || ""} onChange={(e) => setS({ ...s, card_holder: e.target.value })} /></div>
            <div className="field"><label>شماره حساب</label><input className="inp" dir="ltr" value={s.account_number || ""} onChange={(e) => setS({ ...s, account_number: e.target.value })} /></div>
            <div className="field"><label>شماره شبا (بدون IR)</label><input className="inp" dir="ltr" pattern="(IR)?\d{24}" data-error="شبا باید ۲۴ رقم باشد." value={s.iban || ""} onChange={(e) => setS({ ...s, iban: e.target.value })} /></div>
            <div className="field full">
              <label>قالب پیامک — متغیرها: {"{shop} {amount} {due} {days} {site}"}</label>
              <textarea className="inp" rows={3} value={s.reminder_template || ""} onChange={(e) => setS({ ...s, reminder_template: e.target.value })} placeholder="فروشگاه {shop} عزیز، مبلغ {amount} تومان تا تاریخ {due} (تا {days} روز دیگر) باید تسویه شود." />
            </div>

            {/* ---- Which payment methods the storefront offers ---- */}
            <div className="field full" style={{ borderTop: "1px solid var(--line)", paddingTop: 14, marginTop: 4 }}>
              <b style={{ display: "block", marginBottom: 4 }}>💳 روش‌های پرداخت فروشگاه</b>
              <span style={{ fontSize: 12.5, color: "var(--muted)" }}>اگر «فیش بانکی» روشن باشد، مشتری می‌تواند کارت‌به‌کارت کند؛ اگر خاموش باشد، فقط پرداخت آنلاین در دسترس است.</span>
            </div>
            <div className="field" style={{ display: "flex", alignItems: "center" }}>
              <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer", margin: 0 }}>
                <input type="checkbox" checked={s.receipt_payment_enabled} onChange={(e) => setS({ ...s, receipt_payment_enabled: e.target.checked })} style={{ accentColor: "var(--purple)", width: 17, height: 17 }} />
                پرداخت با فیش بانکی (کارت به کارت) فعال باشد
              </label>
            </div>
            <div className="field" style={{ display: "flex", alignItems: "center" }}>
              <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer", margin: 0 }}>
                <input type="checkbox" checked={s.online_payment_enabled} onChange={(e) => setS({ ...s, online_payment_enabled: e.target.checked })} style={{ accentColor: "var(--purple)", width: 17, height: 17 }} />
                پرداخت آنلاین (درگاه بانکی) فعال باشد
              </label>
            </div>

            {/* ---- New-order notifications to the supplier ---- */}
            <div className="field full" style={{ borderTop: "1px solid var(--line)", paddingTop: 14, marginTop: 4 }}>
              <b style={{ display: "block", marginBottom: 4 }}>📦 پیامک سفارش جدید به تامین‌کننده</b>
              <span style={{ fontSize: 12.5, color: "var(--muted)" }}>هر سفارش تازه به تامین‌کننده پیامک می‌شود و تا زمان تایید سفارش، طبق فاصلهٔ زیر تکرار می‌شود.</span>
            </div>
            <div className="field" style={{ display: "flex", alignItems: "center" }}>
              <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer", margin: 0 }}>
                <input type="checkbox" checked={s.order_notify_enabled} onChange={(e) => setS({ ...s, order_notify_enabled: e.target.checked })} style={{ accentColor: "var(--purple)", width: 17, height: 17 }} />
                ارسال پیامک سفارش جدید فعال باشد
              </label>
            </div>
            <div className="field">
              <label>فاصلهٔ یادآوری تا تایید سفارش (ساعت)</label>
              <input className="inp" type="number" min={1} max={72} value={s.order_reminder_hours ?? 3} onChange={(e) => setS({ ...s, order_reminder_hours: +e.target.value })} />
            </div>
            <div className="field"><label>نام تامین‌کننده (در پیامک «جناب آقای …»)</label><input className="inp" value={s.order_notify_name || ""} onChange={(e) => setS({ ...s, order_notify_name: e.target.value })} placeholder="محمدی" /></div>
            <div className="field"><label>موبایل دریافت پیامک (خالی = موبایل حساب تامین‌کننده)</label><input className="inp" dir="ltr" pattern="09\d{9}" data-error="شماره موبایل باید ۱۱ رقم و با ۰۹ باشد." value={s.order_notify_phone || ""} onChange={(e) => setS({ ...s, order_notify_phone: e.target.value })} placeholder="09xxxxxxxxx" /></div>
            <div className="field full">
              <label>قالب پیامک سفارش — متغیرها: {"{name} {items} {number} {site}"}</label>
              <textarea className="inp" rows={5} value={s.order_notify_template || ""} onChange={(e) => setS({ ...s, order_notify_template: e.target.value })} placeholder={"تامین کننده محترم، جناب آقای {name}\n{items}\nثبت شد. لطفا هرچه زودتر به تامین اقدام فرمایید.\nبا تشکر\n{site}"} />
              <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 6 }}>خالی بماند، از قالب پیش‌فرض بالا استفاده می‌شود. {"{items}"} فهرست «نام قطعه» و «تعداد» را می‌سازد.</div>
            </div>
          </div>
          <button className="btn btn-purple" style={{ height: 46, padding: "0 26px" }} disabled={busy}>{busy ? "..." : "ذخیره تنظیمات"}</button>
        </form>
      )}

      <div className="panel">
        <div className="between" style={{ marginBottom: 14, paddingBottom: 12, borderBottom: "1px solid var(--line)" }}>
          <b>تسویه‌های پرداخت‌نشده <span className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>({toFa(count)})</span></b>
          <span style={{ fontSize: 12.5, color: "var(--muted)" }}>با دکمه «ارسال یادآوری» همین حالا پیامک بفرستید.</span>
        </div>
        <div className="tablewrap">
          <table className="tbl">
            <thead><tr><th>فروشگاه</th><th>مبلغ</th><th>سررسید</th><th>مانده</th><th>آخرین یادآوری</th><th></th></tr></thead>
            <tbody>
              {rows.map((i) => (
                <tr key={i.id}>
                  <td><b>{i.shop_name}</b></td>
                  <td className="mono">{money(i.amount)}</td>
                  <td>{faDate(i.due_date)}</td>
                  <td>{i.is_overdue ? <span className="badge red">معوق</span> : <span className="mono">{toFa(i.days_to_due)} روز</span>}</td>
                  <td style={{ fontSize: 12 }}>{i.reminder_sent_at ? faDate(i.reminder_sent_at) : "—"}</td>
                  <td>
                    <button className="btn btn-orange" style={{ height: 36, padding: "0 14px", fontSize: 12.5 }} disabled={sending === i.id} onClick={() => remind(i.id)}>
                      {sending === i.id ? "در حال ارسال…" : "📨 ارسال یادآوری"}
                    </button>
                  </td>
                </tr>
              ))}
              {!rows.length && <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--muted)" }}>همه تسویه‌ها انجام شده ✓</td></tr>}
            </tbody>
          </table>
        </div>
        <Pagination page={page} count={count} onChange={setPage} />
      </div>
    </div>
  );
}
