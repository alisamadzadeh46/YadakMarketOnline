"use client";
// Editable identity card (name/email) + read-only account facts.
import { useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import { useAuth } from "@/lib/auth";
import { toFa, faDate } from "@/lib/format";

export default function ProfileForm() {
  const { user, reload } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [email, setEmail] = useState((user as any)?.email || "");
  const [busy, setBusy] = useState(false);

  if (!user) return null;

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.patch("/accounts/me/", { full_name: fullName, email });
      toast("پروفایل به‌روزرسانی شد ✓");
      reload();
    } catch (err) { toast(errorMessage(err)); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <h2 style={{ margin: "0 0 16px", fontSize: 19, fontWeight: 800 }}>پروفایل</h2>
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))", alignItems: "start" }}>
        <form className="panel" onSubmit={save}>
          <b style={{ display: "block", marginBottom: 14 }}>اطلاعات فردی</b>
          <div className="field"><label>نام و نام خانوادگی</label><input className="inp" value={fullName} onChange={(e) => setFullName(e.target.value)} /></div>
          <div className="field"><label>ایمیل (اختیاری)</label><input className="inp" type="email" dir="ltr" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
          <button className="btn btn-purple" style={{ height: 44, padding: "0 22px" }} disabled={busy}>{busy ? "..." : "ذخیره تغییرات"}</button>
        </form>
        <div className="panel">
          <b style={{ display: "block", marginBottom: 14 }}>اطلاعات حساب</b>
          <div className="specrow"><span style={{ color: "var(--muted)" }}>شماره موبایل</span><span className="mono" style={{ fontWeight: 700 }}>{toFa(user.phone)}</span></div>
          <div className="specrow"><span style={{ color: "var(--muted)" }}>نوع حساب</span><span className="badge purple">{user.role_display}</span></div>
          <div className="specrow"><span style={{ color: "var(--muted)" }}>وضعیت</span>{user.is_approved ? <span className="badge green">تایید شده</span> : <span className="badge amber">در انتظار تایید</span>}</div>
          <div className="specrow"><span style={{ color: "var(--muted)" }}>تاریخ عضویت</span><span>{faDate((user as any).date_joined)}</span></div>
        </div>
      </div>
    </div>
  );
}
