"use client";
// Password recovery: phone (validated against registered users) -> SMS code
// with a 2-minute countdown -> resend / edit-number once it expires.
import Link from "next/link";
import PasswordField from "@/components/PasswordField";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { toast } from "@/lib/ui";
import { toFa } from "@/lib/format";
import { SITE } from "@/lib/site";

const WINDOW_SECONDS = 120;

export default function ForgotPassword() {
  const router = useRouter();
  const [mode, setMode] = useState<"sms" | "email">("sms");
  const [email, setEmail] = useState("");
  const [emailSent, setEmailSent] = useState("");
  const [step, setStep] = useState<1 | 2>(1);
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [left, setLeft] = useState(WINDOW_SECONDS);
  const timer = useRef<ReturnType<typeof setInterval>>(undefined);

  const startTimer = () => {
    setLeft(WINDOW_SECONDS);
    clearInterval(timer.current);
    timer.current = setInterval(() => setLeft((s) => Math.max(0, s - 1)), 1000);
  };
  useEffect(() => () => clearInterval(timer.current), []);

  const requestCode = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setErr(""); setBusy(true);
    try {
      // Backend 404s when the phone isn't registered — surfaced as an error.
      await api.post("/accounts/password-reset/request/", { phone }, { auth: false });
      toast("کد بازیابی پیامک شد");
      setStep(2);
      startTimer();
    } catch (ex: any) { setErr(ex.message); }
    finally { setBusy(false); }
  };

  const requestEmailLink = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      const r = await api.post("/accounts/password-reset/email/request/", { email }, { auth: false });
      setEmailSent(r.detail || "لینک بازیابی ارسال شد.");
      toast("ایمیل بازیابی ارسال شد ✓");
    } catch (ex: any) { setErr(ex.message); }
    finally { setBusy(false); }
  };

  const confirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      await api.post("/accounts/password-reset/confirm/", { phone, code, new_password: password }, { auth: false });
      toast("رمز عبور تغییر کرد ✓ حالا وارد شوید");
      router.push("/login");
    } catch (ex: any) { setErr(ex.message); setBusy(false); }
  };

  const mm = String(Math.floor(left / 60)).padStart(2, "0");
  const ss = String(left % 60).padStart(2, "0");

  return (
    <div className="authwrap view">
      <div className="panel">
        <div style={{ textAlign: "center", marginBottom: 22 }}>
          <img src="/logo-full.png" alt={SITE.name} style={{ height: 92, width: "auto", margin: "0 auto 12px", display: "block" }} />
          <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }}>بازیابی رمز عبور</h1>
          <p style={{ color: "var(--muted)", fontSize: 13.5, marginTop: 6 }}>
            {mode === "email"
              ? "ایمیل حساب را وارد کنید تا لینک بازیابی ارسال شود"
              : step === 1 ? "شماره موبایل حساب را وارد کنید تا کد پیامک شود" : `کد برای ${toFa(phone)} پیامک شد`}
          </p>
        </div>

        {/* Recovery-method switcher */}
        <div className="pwmode">
          <button type="button" className={mode === "sms" ? "on" : ""}
            onClick={() => { setMode("sms"); setErr(""); setEmailSent(""); }}>پیامک</button>
          <button type="button" className={mode === "email" ? "on" : ""}
            onClick={() => { setMode("email"); setErr(""); setStep(1); }}>ایمیل</button>
        </div>

        {mode === "email" ? (
          emailSent ? (
            <div style={{ textAlign: "center", padding: "18px 8px" }}>
              <div style={{ width: 56, height: 56, borderRadius: 16, margin: "0 auto 12px", background: "var(--green)", color: "#fff", display: "grid", placeItems: "center" }}>
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6"><path d="M5 12l5 5L20 7" /></svg>
              </div>
              <b style={{ display: "block", marginBottom: 8 }}>ایمیل بازیابی ارسال شد</b>
              <p style={{ fontSize: 13, color: "var(--muted)", lineHeight: 2, margin: 0 }}>{emailSent}</p>
              <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 10 }}>اگر ایمیل را نمی‌بینید، پوشه Spam را هم بررسی کنید.</p>
              <button type="button" className="btn btn-ghost" style={{ height: 42, padding: "0 18px", marginTop: 14, fontSize: 13 }}
                onClick={() => setEmailSent("")}>ارسال مجدد</button>
            </div>
          ) : (
            <form onSubmit={requestEmailLink}>
              <div className="field">
                <label>ایمیل حساب</label>
                <input className="inp" type="email" dir="ltr" style={{ textAlign: "right" }}
                  placeholder="you@example.com" value={email}
                  onChange={(e) => setEmail(e.target.value)} required />
              </div>
              {err && <div className="err">{err}</div>}
              <button className="btn btn-orange" style={{ width: "100%", height: 48, marginTop: 8 }} disabled={busy}>
                {busy ? "در حال ارسال…" : "ارسال لینک بازیابی"}
              </button>
              <p style={{ fontSize: 12, color: "var(--muted)", textAlign: "center", marginTop: 10, lineHeight: 1.9 }}>
                لینک تا ۳۰ دقیقه معتبر است و فقط یک بار قابل استفاده است.
              </p>
            </form>
          )
        ) : step === 1 ? (
          <form onSubmit={requestCode}>
            <div className="field"><label>شماره موبایل</label><input className="inp" dir="ltr" style={{ textAlign: "right" }} placeholder="09xxxxxxxxx" pattern="09\d{9}" data-error="شماره موبایل معتبر نیست (مثال: 09123456789)" value={phone} onChange={(e) => setPhone(e.target.value)} required /></div>
            {err && <div className="err">{err}</div>}
            <button className="btn btn-orange" style={{ width: "100%", height: 48, marginTop: 8 }} disabled={busy}>{busy ? "..." : "ارسال کد"}</button>
          </form>
        ) : (
          <form onSubmit={confirm}>
            {/* countdown */}
            <div style={{ textAlign: "center", marginBottom: 14 }}>
              {left > 0 ? (
                <div style={{ display: "inline-flex", alignItems: "center", gap: 8, background: "var(--purple-soft)", borderRadius: 12, padding: "8px 16px" }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--purple)" strokeWidth="2"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
                  <b className="mono" style={{ fontSize: 17, color: "var(--purple)", letterSpacing: 1 }}>{toFa(mm)}:{toFa(ss)}</b>
                </div>
              ) : (
                <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
                  <button type="button" className="btn btn-orange" style={{ height: 42, padding: "0 18px", fontSize: 13 }} onClick={() => requestCode()}>ارسال مجدد کد</button>
                  <button type="button" className="btn btn-ghost" style={{ height: 42, padding: "0 18px", fontSize: 13 }} onClick={() => { setStep(1); setCode(""); setErr(""); }}>ویرایش شماره</button>
                </div>
              )}
            </div>
            <div className="field"><label>کد ۶ رقمی پیامک‌شده</label>
              <input
                className="inp mono"
                dir="ltr"
                style={{ textAlign: "center", letterSpacing: 8, fontSize: 20, fontWeight: 700 }}
                maxLength={6}
                // one-time-code + name=otp stops the browser autofilling the
                // phone number into this field; digits are shown in Persian.
                autoComplete="one-time-code"
                name="otp"
                inputMode="numeric"
                placeholder="——————"
                value={toFa(code)}
                onChange={(e) => {
                  const latin = e.target.value
                    .replace(/[۰-۹]/g, (d) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(d)))
                    .replace(/\D/g, "")
                    .slice(0, 6);
                  setCode(latin);
                }}
                required
                disabled={left === 0}
              />
            </div>
            <div className="field"><label>رمز عبور جدید</label><PasswordField value={password} onChange={setPassword} minLength={9} autoComplete="new-password" dataError="رمز عبور باید حداقل ۹ کاراکتر باشد." required disabled={left === 0} /></div>
            {err && <div className="err">{err}</div>}
            <button className="btn btn-orange" style={{ width: "100%", height: 48, marginTop: 8 }} disabled={busy || left === 0}>{busy ? "..." : "تغییر رمز عبور"}</button>
          </form>
        )}

        <div style={{ textAlign: "center", marginTop: 14, fontSize: 13.5, color: "var(--muted)" }}>
          <Link href="/login" style={{ color: "var(--purple)", fontWeight: 700 }}>بازگشت به ورود</Link>
        </div>
      </div>
    </div>
  );
}
