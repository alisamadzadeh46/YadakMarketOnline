"use client";
import Link from "next/link";
import PasswordField from "@/components/PasswordField";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { IUser, IPart } from "@/components/Icon";
import { SITE } from "@/lib/site";

export default function Register() {
  const { login } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", phone: "", password: "", requested_role: "customer" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await api.post("/accounts/register/", form, { auth: false });
      await login(form.phone, form.password);
      router.push(form.requested_role === "shopkeeper" ? "/panel/shop" : "/");
    } catch (e) {
      setErr(errorMessage(e));
      setBusy(false);
    }
  };

  return (
    <div className="authwrap view">
      <div className="panel">
        <div style={{ textAlign: "center", marginBottom: 22 }}>
          <img src="/logo-full.png" alt={SITE.name} style={{ height: 92, width: "auto", margin: "0 auto 12px", display: "block" }} />
          <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }}>ساخت حساب کاربری</h1>
          <p style={{ color: "var(--muted)", fontSize: 13.5, marginTop: 6 }}>به {SITE.name} بپیوندید</p>
        </div>
        <form onSubmit={submit}>
          <div className="field"><label>نام و نام خانوادگی / فروشگاه</label><input className="inp" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required /></div>
          <div className="field"><label>شماره موبایل</label><input className="inp" dir="ltr" style={{ textAlign: "right" }} placeholder="09xxxxxxxxx" pattern="09\d{9}" data-error="شماره موبایل معتبر نیست (مثال: 09123456789)" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} required /></div>
          <div className="field"><label>رمز عبور</label><PasswordField value={form.password} onChange={(v) => setForm({ ...form, password: v })} minLength={9} autoComplete="new-password" dataError="رمز عبور باید حداقل ۹ کاراکتر باشد." required /></div>
          <div className="field">
            <label>نوع حساب</label>
            <div className="rolepick">
              {[
                { v: "customer", t: "کاربر عادی", s: "خرید خرده‌فروشی، فعال‌سازی فوری", icon: <IUser size={20} /> },
                { v: "shopkeeper", t: "فروشگاه لوازم یدکی", s: "خرید عمده و قیمت پلکانی — نیازمند تایید", icon: <IPart size={20} /> },
              ].map((o) => (
                <button
                  type="button"
                  key={o.v}
                  className={`rolecard ${form.requested_role === o.v ? "on" : ""}`}
                  onClick={() => setForm({ ...form, requested_role: o.v })}
                >
                  <span className="rc-ic">{o.icon}</span>
                  <span className="rc-txt"><b>{o.t}</b><span>{o.s}</span></span>
                  <span className="rc-check" aria-hidden>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
                  </span>
                </button>
              ))}
            </div>
          </div>
          {err && <div className="err">{err}</div>}
          {form.requested_role === "shopkeeper" && (
            <div style={{ fontSize: 12.5, color: "var(--muted)", marginBottom: 10 }}>
              حساب فروشگاه پس از بارگذاری مدارک و تایید تامین‌کننده فعال می‌شود.
            </div>
          )}
          <button className="btn btn-orange" style={{ width: "100%", height: 48 }} disabled={busy}>{busy ? "در حال ثبت…" : "ثبت‌نام"}</button>
        </form>
        <div style={{ textAlign: "center", marginTop: 16, fontSize: 13.5, color: "var(--muted)" }}>
          حساب دارید؟ <Link href="/login" style={{ color: "var(--purple)", fontWeight: 700 }}>ورود</Link>
        </div>
      </div>
    </div>
  );
}
