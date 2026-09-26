"use client";
// Blog manager with a Yoast-style SEO assistant: live score, colored
// checklist and one-click fixes coming from /api/seo/analyze/.
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import { toFa, faDate } from "@/lib/format";
import RichEditor from "@/components/RichEditor";
import NiceSelect from "@/components/NiceSelect";

const EMPTY = { title: "", category: "", excerpt: "", body: "", status: "draft", focus_keyword: "", meta_title: "", meta_description: "", slug: "" };
const DOT: Record<string, string> = { good: "var(--green)", ok: "var(--amber)", bad: "var(--red)" };

export default function SupplierBlog() {
  const [rows, setRows] = useState<any[]>([]);
  const [cats, setCats] = useState<any[]>([]);
  const [form, setForm] = useState<any>(null);
  const [seo, setSeo] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const load = () => api.get("/blog/manage/posts/").then((d) => setRows(d.results || d));
  useEffect(() => { load(); api.get("/blog/manage/categories/").then((d) => setCats(d.results || d)); }, []);

  const analyze = async (f = form) => {
    const r = await api.post("/seo/analyze/", {
      title: f.title, meta_title: f.meta_title, meta_description: f.meta_description,
      focus_keyword: f.focus_keyword, slug: f.slug, body: f.body,
    });
    setSeo(r);
    return r;
  };

  const applyFixes = async () => {
    if (!seo?.suggestions) return;
    const next = { ...form };
    for (const [k, v] of Object.entries(seo.suggestions)) if (v && !next[k]) next[k] = v;
    setForm(next);
    toast("پیشنهادها اعمال شد — دوباره تحلیل کنید");
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = { ...form, category: form.category || null };
      delete payload.cover; // file upload handled separately if needed
      if (form.id) await api.patch(`/blog/manage/posts/${form.id}/`, payload);
      else await api.post("/blog/manage/posts/", payload);
      toast("مقاله ذخیره شد ✓ (امتیاز سئو به‌روزرسانی شد)");
      setForm(null); setSeo(null); load();
    } catch (err) { toast(errorMessage(err)); }
    finally { setBusy(false); }
  };

  const remove = async (id: number) => {
    if (!confirm("این مقاله حذف شود؟")) return;
    await api.del(`/blog/manage/posts/${id}/`);
    load();
  };

  if (form) {
    return (
      <form className="view" onSubmit={save}>
        <div className="between" style={{ marginBottom: 16 }}>
          <h2 style={{ margin: 0, fontSize: 19, fontWeight: 800 }}>{form.id ? "ویرایش مقاله" : "مقاله جدید"}</h2>
          <button type="button" className="btn btn-ghost" style={{ height: 40, padding: "0 16px" }} onClick={() => { setForm(null); setSeo(null); }}>بازگشت</button>
        </div>

        <div className="cols-side">
          <div>
            <div className="panel" style={{ marginBottom: 14 }}>
              <div className="field"><label>عنوان *</label><input className="inp" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
              <div className="fgrid">
                <div className="field"><label>دسته‌بندی</label>
                  <NiceSelect value={String(form.category || "")} onChange={(v) => setForm({ ...form, category: v })}
                    options={[{ value: "", label: "— بدون دسته —" }, ...cats.map((c) => ({ value: String(c.id), label: c.name }))]} /></div>
                <div className="field"><label>وضعیت</label>
                  <NiceSelect value={form.status} onChange={(v) => setForm({ ...form, status: v })}
                    options={[{ value: "draft", label: "پیش‌نویس" }, { value: "published", label: "انتشار" }]} /></div>
              </div>
              <div className="field"><label>خلاصه</label><input className="inp" value={form.excerpt} onChange={(e) => setForm({ ...form, excerpt: e.target.value })} /></div>
              {form.id ? (
                <div className="field">
                  <label>تصویر شاخص (کاور)</label>
                  <input className="inp" type="file" accept="image/*" onChange={async (e) => {
                    const f = e.target.files?.[0];
                    if (!f) return;
                    const fd = new FormData();
                    fd.append("cover", f);
                    await api.patch(`/blog/manage/posts/${form.id}/`, fd);
                    toast("کاور به‌روزرسانی شد ✓");
                  }} />
                </div>
              ) : (
                <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 10 }}>کاور پس از ذخیره‌ی اولیه قابل بارگذاری است.</div>
              )}
              <div className="field">
                <label>متن مقاله * <span style={{ color: "var(--muted)", fontWeight: 400 }}>(ادیتور حرفه‌ای — تصویر و ویدئو هم درج کنید)</span></label>
                <RichEditor value={form.body} onChange={(body) => setForm({ ...form, body })} />
              </div>
            </div>
            <button className="btn btn-purple" style={{ height: 48, padding: "0 30px", fontSize: 15 }} disabled={busy}>{busy ? "..." : "ذخیره مقاله"}</button>
          </div>

          {/* SEO assistant (Yoast-like) */}
          <div className="panel" style={{ position: "sticky", top: 150 }}>
            <b style={{ display: "block", marginBottom: 12 }}>دستیار سئو</b>
            <div className="field"><label>کلمه کلیدی هدف</label><input className="inp" value={form.focus_keyword} onChange={(e) => setForm({ ...form, focus_keyword: e.target.value })} /></div>
            <div className="field"><label>اسلاگ</label><input className="inp" dir="ltr" value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} /></div>
            <div className="field"><label>عنوان سئو</label><input className="inp" value={form.meta_title} onChange={(e) => setForm({ ...form, meta_title: e.target.value })} /></div>
            <div className="field"><label>توضیح متا</label><textarea className="inp" rows={3} value={form.meta_description} onChange={(e) => setForm({ ...form, meta_description: e.target.value })} /></div>

            <button type="button" className="btn btn-orange" style={{ width: "100%", height: 44, marginBottom: 12 }} onClick={() => analyze()}>تحلیل سئو</button>

            {seo && (
              <>
                <div className="between" style={{ marginBottom: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 700 }}>امتیاز</span>
                  <b className="mono" style={{ fontSize: 20, color: seo.score >= 80 ? "var(--green)" : seo.score >= 50 ? "var(--amber)" : "var(--red)" }}>{toFa(seo.score)}/۱۰۰</b>
                </div>
                <div className="seo-meter" style={{ marginBottom: 12 }}>
                  <i style={{ width: `${seo.score}%`, background: seo.score >= 80 ? "var(--green)" : seo.score >= 50 ? "var(--amber)" : "var(--red)" }} />
                </div>
                {Object.keys(seo.suggestions || {}).length > 0 && (
                  <button type="button" className="btn btn-ghost" style={{ width: "100%", height: 40, marginBottom: 12, fontSize: 13 }} onClick={applyFixes}>✨ اعمال خودکار پیشنهادها</button>
                )}
                <div style={{ maxHeight: 300, overflow: "auto" }}>
                  {seo.checks.map((c: any) => (
                    <div className="checkline" key={c.id}>
                      <span className="dot" style={{ background: DOT[c.status] }} />
                      <span>{c.message}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </form>
    );
  }

  return (
    <div>
      <div className="between" style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 19, fontWeight: 800 }}>مدیریت بلاگ</h2>
        <button className="btn btn-purple" style={{ height: 42, padding: "0 18px" }} onClick={() => setForm({ ...EMPTY })}>+ مقاله جدید</button>
      </div>
      <div className="panel tablewrap">
        <table className="tbl">
          <thead><tr><th>عنوان</th><th>وضعیت</th><th>امتیاز سئو</th><th>بازدید</th><th>تاریخ</th><th>عملیات</th></tr></thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id}>
                <td className="wrap" style={{ maxWidth: 280 }}><b>{p.title}</b></td>
                <td>{p.status === "published" ? <span className="badge green">منتشر</span> : <span className="badge amber">پیش‌نویس</span>}</td>
                <td><b className="mono" style={{ color: p.seo_score >= 80 ? "var(--green)" : p.seo_score >= 50 ? "var(--amber)" : "var(--red)" }}>{toFa(p.seo_score)}</b></td>
                <td className="mono">{toFa(p.views)}</td>
                <td>{faDate(p.published_at || p.created_at)}</td>
                <td>
                  <div className="list-actions">
                    <button className="act-edit" onClick={() => { setForm({ ...EMPTY, ...p, category: p.category || "" }); setSeo(null); }}>ویرایش</button>
                    <button className="act-del" onClick={() => remove(p.id)}>حذف</button>
                  </div>
                </td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--muted)" }}>مقاله‌ای نیست.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
