"use client";
// Shop profile + KYC: business details form, document upload and review status.
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import ProfileForm from "@/components/ProfileForm";
import NiceSelect from "@/components/NiceSelect";

const EMPTY = { shop_name: "", owner_national_id: "", business_license_no: "", province: "", city: "", address: "", landline: "" };
const DOC_TYPES: [string, string][] = [
  ["national_card", "کارت ملی"],
  ["business_license", "جواز کسب"],
  ["shop_photo", "تصویر فروشگاه"],
  ["other", "سایر"],
];
const STATUS_BADGE: Record<string, [string, string]> = {
  pending: ["amber", "در انتظار بررسی"],
  approved: ["green", "تایید شده"],
  rejected: ["red", "رد شده"],
};

export default function ShopProfile() {
  const [profile, setProfile] = useState<any>(null);
  const [form, setForm] = useState<any>(EMPTY);
  const [exists, setExists] = useState(false);
  const [docType, setDocType] = useState("national_card");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () =>
    api.get("/accounts/shop-profile/")
      .then((d) => { setProfile(d); setForm(d); setExists(true); })
      .catch(() => setExists(false));

  useEffect(() => { load(); }, []);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (exists) await api.patch("/accounts/shop-profile/", form);
      else await api.post("/accounts/shop-profile/", form);
      toast("اطلاعات فروشگاه با موفقیت ذخیره شد ✓");
      // Refresh once so the approval banner and sidebar state update everywhere.
      setTimeout(() => window.location.reload(), 1100);
    } catch (err) { toast(errorMessage(err)); }
    finally { setBusy(false); }
  };

  const upload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return toast("فایل مدرک را انتخاب کنید");
    const fd = new FormData();
    fd.append("doc_type", docType);
    fd.append("file", file);
    try {
      await api.post("/accounts/kyc/upload/", fd);
      toast("مدرک بارگذاری شد ✓");
      setFile(null);
      load();
    } catch (err) { toast(errorMessage(err)); }
  };

  const badge = profile ? STATUS_BADGE[profile.status] : null;

  return (
    <div>
      <div className="between" style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 19, fontWeight: 800 }}>پروفایل فروشگاه و احراز هویت</h2>
        {badge && <span className={`badge ${badge[0]}`}>{badge[1]}</span>}
      </div>

      {profile?.status === "rejected" && profile.review_note && (
        <div className="panel" style={{ marginBottom: 16, borderColor: "#F1B5B5" }}>
          <b style={{ color: "var(--red)" }}>دلیل رد:</b> {profile.review_note}
        </div>
      )}

      <form className="panel" style={{ marginBottom: 16 }} onSubmit={save}>
        <b style={{ display: "block", marginBottom: 14 }}>۱) اطلاعات کسب‌وکار</b>
        <div className="fgrid">
          <div className="field"><label>نام فروشگاه *</label><input className="inp" required value={form.shop_name || ""} onChange={(e) => setForm({ ...form, shop_name: e.target.value })} /></div>
          <div className="field"><label>کد ملی مالک *</label><input className="inp" dir="ltr" style={{ textAlign: "right" }} required pattern="\d{10}" data-error="کد ملی باید ۱۰ رقم باشد." inputMode="numeric" value={form.owner_national_id || ""} onChange={(e) => setForm({ ...form, owner_national_id: e.target.value })} /></div>
          <div className="field"><label>شماره جواز کسب *</label><input className="inp" required minLength={4} data-error="شماره جواز کسب را کامل وارد کنید." value={form.business_license_no || ""} onChange={(e) => setForm({ ...form, business_license_no: e.target.value })} /></div>
          <div className="field"><label>تلفن ثابت *</label><input className="inp" dir="ltr" style={{ textAlign: "right" }} required pattern="0\d{9,10}" data-error="تلفن ثابت معتبر نیست (مثال: 02112345678)." inputMode="numeric" value={form.landline || ""} onChange={(e) => setForm({ ...form, landline: e.target.value })} /></div>
          <div className="field"><label>استان *</label><input className="inp" required value={form.province || ""} onChange={(e) => setForm({ ...form, province: e.target.value })} /></div>
          <div className="field"><label>شهر *</label><input className="inp" required value={form.city || ""} onChange={(e) => setForm({ ...form, city: e.target.value })} /></div>
          <div className="field full"><label>آدرس فروشگاه *</label><textarea className="inp" rows={2} required minLength={10} data-error="آدرس را کامل وارد کنید (حداقل ۱۰ کاراکتر)." value={form.address || ""} onChange={(e) => setForm({ ...form, address: e.target.value })} /></div>
        </div>
        <button className="btn btn-purple" style={{ height: 44, padding: "0 22px" }} disabled={busy}>{busy ? "..." : "ذخیره اطلاعات"}</button>
      </form>

      <div className="panel" style={{ marginBottom: 16 }}>
        <b style={{ display: "block", marginBottom: 6 }}>۲) بارگذاری مدارک</b>
        <div style={{ fontSize: 12.5, color: "var(--muted)", marginBottom: 14 }}>
          کارت ملی و جواز کسب برای تایید حساب الزامی است. پس از بارگذاری، تامین‌کننده بررسی و تایید می‌کند.
        </div>
        <form onSubmit={upload} className="row" style={{ alignItems: "flex-end" }}>
          <div className="field" style={{ margin: 0, minWidth: 180 }}>
            <label>نوع مدرک</label>
            <NiceSelect value={docType} onChange={setDocType} options={DOC_TYPES.map(([value, label]) => ({ value, label }))} />
          </div>
          <div className="field" style={{ margin: 0, flex: 1, minWidth: 200 }}>
            <label>فایل (تصویر یا PDF)</label>
            <input className="inp" type="file" accept="image/*,.pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </div>
          <button className="btn btn-orange" style={{ height: 46, padding: "0 22px" }}>بارگذاری</button>
        </form>

        {profile?.documents?.length ? (
          <div className="tablewrap" style={{ marginTop: 16 }}>
            <table className="tbl">
              <thead><tr><th>نوع مدرک</th><th>فایل</th></tr></thead>
              <tbody>
                {profile.documents.map((d: any) => (
                  <tr key={d.id}>
                    <td>{DOC_TYPES.find(([v]) => v === d.doc_type)?.[1] || d.doc_type}</td>
                    <td><a href={d.file} target="_blank" style={{ color: "var(--purple)", fontWeight: 700, fontSize: 13 }}>مشاهده فایل</a></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>

      <ProfileForm />
    </div>
  );
}
