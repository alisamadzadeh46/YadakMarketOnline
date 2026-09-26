"use client";
// Contact page: info cards + a form that lands in the supplier's inbox.
import { useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import StaticPage from "@/components/StaticPage";
import { SITE } from "@/lib/site";

const EMPTY = { name: "", phone: "", email: "", subject: "", message: "" };

export default function Contact() {
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/cms/contact/", form, { auth: false });
      toast("پیام شما ارسال شد ✓ به‌زودی پاسخ می‌دهیم");
      setForm(EMPTY);
    } catch (err) { toast(errorMessage(err)); }
    finally { setBusy(false); }
  };

  return (
    <StaticPage title="تماس با ما" intro="پاسخگوی شما هستیم — از مشاوره فنی تا پیگیری سفارش.">
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(210px,1fr))", marginBottom: 24 }}>
        {SITE.contact.phones.length > 0 && (
          <div className="panel" style={{ textAlign: "center" }}>
            <div style={{ fontSize: 26 }}>📞</div><b>تلفن تماس</b>
            <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 4 }}>
              {SITE.contact.phones.map((phone) => (
                <a key={phone.dial} className="mono" dir="ltr" href={`tel:${phone.dial}`} style={{ color: "var(--purple)", fontWeight: 700 }}>
                  {phone.display}
                </a>
              ))}
            </div>
          </div>
        )}
        <div className="panel" style={{ textAlign: "center" }}><div style={{ fontSize: 26 }}>🕘</div><b>ساعت پاسخگویی</b><div style={{ color: "var(--muted)", marginTop: 6, fontSize: 13 }}>{SITE.contact.hours}</div></div>
        {(SITE.contact.city || SITE.contact.address) && (
          <div className="panel" style={{ textAlign: "center" }}>
            <div style={{ fontSize: 26 }}>📍</div><b>دفتر مرکزی</b>
            <div style={{ color: "var(--muted)", marginTop: 6, fontSize: 13, lineHeight: 1.9 }}>
              {SITE.contact.city}{SITE.contact.city && SITE.contact.address && <br />}{SITE.contact.address}
            </div>
          </div>
        )}
      </div>

      <form className="panel" onSubmit={submit}>
        <b style={{ display: "block", marginBottom: 14 }}>ارسال پیام</b>
        <div className="fgrid">
          <div className="field"><label>نام و نام خانوادگی *</label><input className="inp" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
          <div className="field"><label>موبایل</label><input className="inp" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
          <div className="field"><label>ایمیل</label><input className="inp" type="email" dir="ltr" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
          <div className="field"><label>موضوع *</label><input className="inp" required value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} /></div>
          <div className="field full"><label>متن پیام *</label><textarea className="inp" rows={4} required value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} /></div>
        </div>
        <button className="btn btn-orange" style={{ height: 48, padding: "0 28px" }} disabled={busy}>{busy ? "در حال ارسال…" : "ارسال پیام"}</button>
      </form>
    </StaticPage>
  );
}
