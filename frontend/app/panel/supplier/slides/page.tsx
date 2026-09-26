"use client";
// Home-page slider management: create/edit/delete slides with image upload.
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import { toFa } from "@/lib/format";

const EMPTY = { badge: "", title: "", highlight: "", text: "", button_text: "", button_link: "", order: 0, is_active: true };

export default function SupplierSlides() {
  const [rows, setRows] = useState<any[]>([]);
  const [form, setForm] = useState<any>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => api.get("/cms/manage/slides/").then((d) => setRows(d.results || d));
  useEffect(() => { load(); }, []);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const fd = new FormData();
      for (const k of ["badge", "title", "highlight", "text", "button_text", "button_link", "order"]) fd.append(k, form[k] ?? "");
      fd.append("is_active", form.is_active ? "true" : "false");
      if (file) fd.append("image", file);
      if (form.id) await api.patch(`/cms/manage/slides/${form.id}/`, fd);
      else await api.post("/cms/manage/slides/", fd);
      toast("اسلاید ذخیره شد ✓");
      setForm(null); setFile(null); load();
    } catch (err) { toast(errorMessage(err)); }
    finally { setBusy(false); }
  };

  const remove = async (id: number) => {
    if (!confirm("این اسلاید حذف شود؟")) return;
    await api.del(`/cms/manage/slides/${id}/`);
    load();
  };

  return (
    <div>
      <div className="between" style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 19, fontWeight: 800 }}>اسلایدر صفحه اصلی</h2>
        <button className="btn btn-purple" style={{ height: 42, padding: "0 18px" }} onClick={() => setForm({ ...EMPTY, order: rows.length })}>+ اسلاید جدید</button>
      </div>

      {form && (
        <form className="panel" style={{ marginBottom: 16 }} onSubmit={save}>
          <div className="fgrid">
            <div className="field"><label>برچسب کوچک</label><input className="inp" value={form.badge} onChange={(e) => setForm({ ...form, badge: e.target.value })} placeholder="مثلا: ویژه همکاران" /></div>
            <div className="field"><label>ترتیب</label><input className="inp" type="number" value={form.order} onChange={(e) => setForm({ ...form, order: e.target.value })} /></div>
            <div className="field"><label>عنوان *</label><input className="inp" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
            <div className="field"><label>بخش نارنجی عنوان</label><input className="inp" value={form.highlight} onChange={(e) => setForm({ ...form, highlight: e.target.value })} /></div>
            <div className="field full"><label>متن</label><textarea className="inp" rows={2} value={form.text} onChange={(e) => setForm({ ...form, text: e.target.value })} /></div>
            <div className="field"><label>متن دکمه</label><input className="inp" value={form.button_text} onChange={(e) => setForm({ ...form, button_text: e.target.value })} /></div>
            <div className="field"><label>لینک دکمه</label><input className="inp" dir="ltr" value={form.button_link} onChange={(e) => setForm({ ...form, button_link: e.target.value })} placeholder="/shop" /></div>
            <div className="field full"><label>تصویر (اختیاری)</label><input className="inp" type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] || null)} /></div>
          </div>
          <label style={{ display: "flex", gap: 7, alignItems: "center", fontSize: 13.5, cursor: "pointer", marginBottom: 12 }}>
            <input type="checkbox" checked={!!form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} style={{ accentColor: "var(--purple)" }} /> فعال
          </label>
          <div className="row">
            <button className="btn btn-purple" style={{ height: 44, padding: "0 22px" }} disabled={busy}>{busy ? "..." : "ذخیره"}</button>
            <button type="button" className="btn btn-ghost" style={{ height: 44, padding: "0 18px" }} onClick={() => setForm(null)}>انصراف</button>
          </div>
        </form>
      )}

      <div className="panel tablewrap">
        <table className="tbl">
          <thead><tr><th>ترتیب</th><th>عنوان</th><th>برچسب</th><th>وضعیت</th><th>عملیات</th></tr></thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id}>
                <td className="mono">{toFa(s.order)}</td>
                <td><b>{s.title}</b> {s.highlight && <span style={{ color: "var(--orange)" }}>{s.highlight}</span>}</td>
                <td>{s.badge || "—"}</td>
                <td>{s.is_active ? <span className="badge green">فعال</span> : <span className="badge amber">غیرفعال</span>}</td>
                <td>
                  <div className="list-actions">
                    <button className="act-edit" onClick={() => { setForm({ ...s }); setFile(null); }}>ویرایش</button>
                    <button className="act-del" onClick={() => remove(s.id)}>حذف</button>
                  </div>
                </td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--muted)" }}>اسلایدی تعریف نشده — اسلایدر پیش‌فرض سایت نمایش داده می‌شود.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
