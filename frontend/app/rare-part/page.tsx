"use client";
// Rare-part request form. Tracking lives in the user's profile panel; after a
// successful submit a green alert appears and fades out after a few seconds.
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import PriceField from "@/components/PriceField";
import { useAuth } from "@/lib/auth";

const EMPTY = { part_name: "", quantity: "1", car_name: "", car_model: "", brand: "", note: "" };

export default function RarePart() {
  const { user, loading } = useAuth();
  const [form, setForm] = useState({ ...EMPTY });
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [success, setSuccess] = useState(false);
  const [err, setErr] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => () => clearTimeout(timer.current), []);

  // Prefill when arriving from an out-of-stock product page ("request supply").
  // Read from window.location to avoid the useSearchParams Suspense requirement.
  useEffect(() => {
    const sp = new URLSearchParams(window.location.search);
    const name = sp.get("name");
    const sku = sp.get("sku");
    if (name || sku) {
      setForm((f) => ({
        ...f,
        part_name: name || f.part_name,
        note: sku ? `کد فنی: ${sku}` : f.note,
      }));
    }
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => fd.append(k, v));
      if (file) fd.append("image", file);
      await api.post("/catalog/rare-requests/", fd);
      setForm({ ...EMPTY }); setFile(null);
      // Success alert that removes itself after 6 seconds.
      setSuccess(true);
      window.scrollTo({ top: 0, behavior: "smooth" });
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setSuccess(false), 6000);
    } catch (ex: any) { setErr(ex.message); }
    finally { setBusy(false); }
  };

  const profileHref = user?.role === "shopkeeper" ? "/panel/shop/rare-parts" : "/account/rare-parts";
  const isSupplierSide = user?.role === "supplier" || user?.role === "admin";

  return (
    <div className="view" style={{ maxWidth: 820, margin: "0 auto" }}>
      {/* hero */}
      <div style={{ borderRadius: "var(--r-lg)", padding: "36px 30px", color: "#fff", marginBottom: 22, background: "radial-gradient(420px 220px at 85% 0%,rgba(255,138,61,.3),transparent),linear-gradient(130deg,var(--purple-deep),var(--purple-2))" }}>
        <h1 style={{ margin: 0, fontSize: "clamp(22px,3.4vw,30px)", fontWeight: 800 }}>🔍 درخواست قطعه نایاب</h1>
        <p style={{ margin: "10px 0 0", opacity: .88, fontSize: 14.5, lineHeight: 2 }}>
          قطعه‌ای را می‌خواهید که در فروشگاه پیدا نکردید؟ مشخصاتش را ثبت کنید؛ تیم تامین ما آن را
          پیدا می‌کند و به‌محض موجود شدن، با پیامک خبرتان می‌کنیم.
        </p>
      </div>

      {/* auto-dismissing success alert */}
      {success && (
        <div className="view" style={{ display: "flex", alignItems: "center", gap: 12, background: "#E7F6EE", border: "1px solid #BFE7D2", color: "#146A43", borderRadius: 16, padding: "16px 18px", marginBottom: 18, fontWeight: 700 }}>
          <span style={{ width: 34, height: 34, borderRadius: 11, background: "var(--green)", color: "#fff", display: "grid", placeItems: "center", flexShrink: 0 }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6"><path d="M5 12l5 5L20 7" /></svg>
          </span>
          <div style={{ flex: 1 }}>
            درخواست شما با موفقیت ثبت شد!
            <div style={{ fontWeight: 400, fontSize: 12.5, marginTop: 3 }}>وضعیت پیگیری در <Link href={profileHref} style={{ color: "var(--green)", textDecoration: "underline" }}>پروفایل شما</Link> قابل مشاهده است؛ نتیجه هم پیامک می‌شود.</div>
          </div>
          <button onClick={() => setSuccess(false)} style={{ color: "#146A43", fontSize: 18, flexShrink: 0 }}>×</button>
        </div>
      )}

      {!loading && !user ? (
        <div className="panel center-empty" style={{ padding: "50px 20px" }}>
          <div style={{ fontSize: 42 }}>🔐</div>
          <b style={{ display: "block", margin: "8px 0 6px", color: "var(--ink)" }}>برای ثبت درخواست ابتدا وارد شوید</b>
          <p style={{ marginTop: 0 }}>ثبت‌نام رایگان است و کمتر از یک دقیقه طول می‌کشد.</p>
          <Link href="/login" className="btn btn-purple" style={{ height: 46, padding: "0 26px" }}>ورود / ثبت‌نام</Link>
        </div>
      ) : isSupplierSide ? (
        // Suppliers answer these requests — they don't file them.
        <div className="panel center-empty" style={{ padding: "50px 20px" }}>
          <div style={{ fontSize: 42 }}>🛠</div>
          <b style={{ display: "block", margin: "8px 0 6px", color: "var(--ink)" }}>ثبت درخواست قطعه نایاب مخصوص خریداران است</b>
          <p style={{ marginTop: 0 }}>شما به‌عنوان تامین‌کننده، درخواست‌های ثبت‌شده را در پنل خود بررسی و پاسخ می‌دهید.</p>
          <Link href="/panel/supplier/rare-parts" className="btn btn-purple" style={{ height: 46, padding: "0 26px" }}>مشاهده درخواست‌ها در پنل</Link>
        </div>
      ) : (
        <form className="panel" onSubmit={submit}>
          <div className="between" style={{ marginBottom: 14 }}>
            <b>مشخصات قطعه</b>
            <Link href={profileHref} style={{ fontSize: 12.5, fontWeight: 700, color: "var(--purple)" }}>مشاهده درخواست‌های قبلی ›</Link>
          </div>
          <div className="fgrid">
            <div className="field"><label>نام قطعه *</label><input className="inp" required minLength={3} data-error="نام قطعه را کامل بنویسید." placeholder="مثلا: پمپ بنزین" value={form.part_name} onChange={(e) => setForm({ ...form, part_name: e.target.value })} /></div>
            <div className="field"><label>تعداد موردنیاز *</label><PriceField className="inp mono" required value={form.quantity} onChange={(v) => setForm({ ...form, quantity: v })} /></div>
            <div className="field"><label>برند موردنیاز *</label><input className="inp" required placeholder="مثلا: BOSCH یا اصلی کارخانه" value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} /></div>
            <div className="field"><label>نام خودرو *</label><input className="inp" required placeholder="مثلا: پژو" value={form.car_name} onChange={(e) => setForm({ ...form, car_name: e.target.value })} /></div>
            <div className="field"><label>مدل خودرو *</label><input className="inp" required placeholder="مثلا: ۲۰۶ تیپ ۵ — ۱۳۹۵" value={form.car_model} onChange={(e) => setForm({ ...form, car_model: e.target.value })} /></div>
            <div className="field full"><label>تصویر قطعه (اختیاری — اگر نمونه‌اش را دارید)</label><input className="inp" type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] || null)} /></div>
            <div className="field full"><label>توضیحات بیشتر (اختیاری)</label><textarea className="inp" rows={3} placeholder="شماره فنی، وضعیت نو/استوک، تعداد موردنیاز و…" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} /></div>
          </div>
          {err && <div className="err">{err}</div>}
          <button className="btn btn-orange" style={{ height: 50, padding: "0 30px", fontSize: 15 }} disabled={busy}>
            {busy ? "در حال ثبت…" : "ثبت درخواست قطعه"}
          </button>
        </form>
      )}
    </div>
  );
}
