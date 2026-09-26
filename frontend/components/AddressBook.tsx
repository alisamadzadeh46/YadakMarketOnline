"use client";
// Full address CRUD used by both the customer account and the shop panel.
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import { toFa } from "@/lib/format";
import MapPicker from "./MapPicker";

const EMPTY = { title: "", receiver_name: "", receiver_phone: "", province: "", city: "", postal_code: "", line: "", lat: null, lng: null, is_default: false };

export default function AddressBook() {
  const [items, setItems] = useState<any[]>([]);
  const [form, setForm] = useState<any>(null); // null = closed, {} = create, {id} = edit
  const [busy, setBusy] = useState(false);

  const load = () => api.get("/accounts/addresses/").then((d) => setItems(d.results || d));
  useEffect(() => { load(); }, []);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (form.id) await api.patch(`/accounts/addresses/${form.id}/`, form);
      else await api.post("/accounts/addresses/", form);
      toast("آدرس ذخیره شد ✓");
      setForm(null);
      load();
    } catch (err) { toast(errorMessage(err)); }
    finally { setBusy(false); }
  };

  const remove = async (id: number) => {
    await api.del(`/accounts/addresses/${id}/`);
    toast("آدرس حذف شد");
    load();
  };

  const makeDefault = async (id: number) => {
    await api.patch(`/accounts/addresses/${id}/`, { is_default: true });
    load();
  };

  return (
    <div className="panel">
      <div className="between" style={{ marginBottom: 18, paddingBottom: 14, borderBottom: "1px solid var(--line)" }}>
        <h2 style={{ margin: 0, fontSize: 19, fontWeight: 800 }}>آدرس‌های من</h2>
        <button className="btn btn-purple" style={{ height: 42, padding: "0 18px" }} onClick={() => setForm({ ...EMPTY })}>+ آدرس جدید</button>
      </div>

      {form && (
        <form className="addr-form" style={{ marginBottom: 18, background: "var(--card)", borderRadius: 16, padding: 18, border: "1.5px dashed var(--purple-line)" }} onSubmit={save}>
          <div className="fgrid">
            <div className="field"><label>عنوان</label><input className="inp" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="مثلا: انبار مرکزی" /></div>
            <div className="field"><label>نام گیرنده</label><input className="inp" required value={form.receiver_name} onChange={(e) => setForm({ ...form, receiver_name: e.target.value })} /></div>
            <div className="field"><label>موبایل گیرنده</label><input className="inp" required value={form.receiver_phone} onChange={(e) => setForm({ ...form, receiver_phone: e.target.value })} placeholder="09xxxxxxxxx" /></div>
            <div className="field"><label>کد پستی</label><input className="inp" value={form.postal_code} onChange={(e) => setForm({ ...form, postal_code: e.target.value })} /></div>
            <div className="field"><label>استان</label><input className="inp" required value={form.province} onChange={(e) => setForm({ ...form, province: e.target.value })} /></div>
            <div className="field"><label>شهر</label><input className="inp" required value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></div>
            <div className="field full"><label>نشانی کامل</label><textarea className="inp" rows={2} required value={form.line} onChange={(e) => setForm({ ...form, line: e.target.value })} /></div>
            <div className="field full">
              <label>موقعیت روی نقشه (اختیاری) — روی نقشه کلیک کنید تا پین ثبت شود</label>
              <MapPicker lat={form.lat} lng={form.lng} onChange={(lat, lng) => setForm({ ...form, lat, lng })} />
              {form.lat && <div style={{ fontSize: 12, color: "var(--green)", marginTop: 6 }}>✓ موقعیت ثبت شد ({toFa(form.lat)}، {toFa(form.lng)})</div>}
            </div>
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, margin: "10px 0 14px", cursor: "pointer", fontSize: 13.5 }}>
            <input type="checkbox" checked={!!form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} style={{ accentColor: "var(--purple)", width: 16, height: 16 }} />
            آدرس پیش‌فرض باشد
          </label>
          <div className="row">
            <button className="btn btn-purple" style={{ height: 44, padding: "0 22px" }} disabled={busy}>{busy ? "..." : "ذخیره"}</button>
            <button type="button" className="btn btn-ghost" style={{ height: 44, padding: "0 18px" }} onClick={() => setForm(null)}>انصراف</button>
          </div>
        </form>
      )}

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(290px,1fr))" }}>
        {items.map((a) => (
          <div className="addr-card" key={a.id}>
            <div className="ahead">
              <span className="apin">
                <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0z" /><circle cx="12" cy="10" r="3" /></svg>
              </span>
              <b>{a.title}</b>
              {a.is_default
                ? <span className="badge green" style={{ marginRight: "auto" }}>پیش‌فرض</span>
                : <button className="mkdef" onClick={() => makeDefault(a.id)}>تنظیم پیش‌فرض</button>}
            </div>
            <div className="arow">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
              <span>{a.receiver_name} · <b className="mono">{toFa(a.receiver_phone)}</b></span>
            </div>
            <div className="arow">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
              <span>{a.province}، {a.city} {a.postal_code ? <span className="mono" style={{ color: "var(--muted)" }}>· کد پستی {toFa(a.postal_code)}</span> : null}</span>
            </div>
            <div className="arow" style={{ alignItems: "flex-start" }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 9.5 12 3l9 6.5V21H3z" /><path d="M9 21v-7h6v7" /></svg>
              <span style={{ lineHeight: 1.9 }}>{a.line}</span>
            </div>
            {a.lat && a.lng ? (
              <div style={{ marginTop: 10 }}>
                <MapPicker lat={a.lat} lng={a.lng} readOnly height={140} />
              </div>
            ) : null}
            <div className="list-actions" style={{ marginTop: 14, paddingTop: 12, borderTop: "1px dashed var(--line)" }}>
              <button className="act-edit" onClick={() => setForm({ ...a })}>✎ ویرایش</button>
              <button className="act-del" onClick={() => remove(a.id)}>حذف</button>
            </div>
          </div>
        ))}
        {!items.length && !form && (
          <div className="center-empty" style={{ gridColumn: "1 / -1" }}>
            <div style={{ fontSize: 42 }}>📍</div>
            <p>هنوز آدرسی ثبت نکرده‌اید.</p>
            <button className="btn btn-purple" style={{ height: 44, padding: "0 22px" }} onClick={() => setForm({ ...EMPTY })}>ثبت اولین آدرس</button>
          </div>
        )}
      </div>
    </div>
  );
}
