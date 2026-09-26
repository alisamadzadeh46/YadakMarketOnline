"use client";
// Landing page for the emailed reset link: reads ?token=… from the URL and
// exchanges it for a new password. The token itself is validated server-side —
// this page only collects the new password and reports what the API says.
import Link from "next/link";
import PasswordField from "@/components/PasswordField";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { toast } from "@/lib/ui";
import { SITE } from "@/lib/site";

export default function ResetPassword() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  // null = still checking, true/false = server's verdict on the link.
  const [linkOk, setLinkOk] = useState<boolean | null>(null);
  const [linkReason, setLinkReason] = useState("");

  useEffect(() => {
    // Read from window.location to avoid the useSearchParams Suspense rule.
    const sp = new URLSearchParams(window.location.search);
    const t = sp.get("token") || "";
    setToken(t);
    if (!t) { setLinkOk(false); setLinkReason("invalid"); return; }
    // Check the link BEFORE showing a password form — an expired link must say
    // so up front, not after the user has typed a new password.
    api.get(`/accounts/password-reset/email/verify/?token=${encodeURIComponent(t)}`, { auth: false })
      .then((r: any) => { setLinkOk(!!r.valid); setLinkReason(r.reason || ""); })
      .catch(() => { setLinkOk(false); setLinkReason("invalid"); });
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    if (password !== confirm) {
      setErr("رمز عبور و تکرار آن یکسان نیستند.");
      return;
    }
    setBusy(true);
    try {
      await api.post("/accounts/password-reset/email/confirm/", { token, new_password: password }, { auth: false });
      toast("رمز عبور تغییر کرد ✓ حالا وارد شوید");
      router.push("/login");
    } catch (ex: any) {
      setErr(ex.message);
      setBusy(false);
    }
  };

  if (token === null || linkOk === null) return <div className="center-empty">در حال بررسی لینک بازیابی…</div>;

  const REASON_FA: Record<string, string> = {
    expired: "مهلت ۳۰ دقیقه‌ای این لینک به پایان رسیده است.",
    used: "این لینک قبلاً یک بار استفاده شده است.",
    invalid: "لینک بازیابی نامعتبر است یا ناقص باز شده.",
  };

  return (
    <div className="authwrap view">
      <div className="panel">
        <div style={{ textAlign: "center", marginBottom: 22 }}>
          <img src="/logo-full.png" alt={SITE.name} style={{ height: 92, width: "auto", margin: "0 auto 12px", display: "block" }} />
          <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }}>انتخاب رمز عبور جدید</h1>
          <p style={{ color: "var(--muted)", fontSize: 13.5, marginTop: 6 }}>رمز تازه‌ای برای حساب خود انتخاب کنید</p>
        </div>

        {!linkOk ? (
          <div style={{ textAlign: "center", padding: "10px 8px 4px" }}>
            <div style={{ width: 56, height: 56, borderRadius: 16, margin: "0 auto 14px", background: "var(--red)", color: "#fff", display: "grid", placeItems: "center" }}>
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><circle cx="12" cy="12" r="9" /><path d="M12 7v6M12 16.5h.01" /></svg>
            </div>
            <b style={{ display: "block", marginBottom: 8 }}>لینک بازیابی معتبر نیست</b>
            <p style={{ fontSize: 13, color: "var(--muted)", lineHeight: 2, margin: "0 0 16px" }}>
              {REASON_FA[linkReason] || REASON_FA.invalid} لطفاً دوباره درخواست بازیابی ثبت کنید.
            </p>
            <Link href="/forgot-password" className="btn btn-purple" style={{ height: 46, padding: "0 24px" }}>
              درخواست لینک جدید
            </Link>
          </div>
        ) : (
          <form onSubmit={submit}>
            <div className="field">
              <label>رمز عبور جدید</label>
              <PasswordField value={password} onChange={setPassword} minLength={9}
                autoComplete="new-password" dataError="رمز عبور باید حداقل ۹ کاراکتر باشد." required />
            </div>
            <div className="field">
              <label>تکرار رمز عبور جدید</label>
              <PasswordField value={confirm} onChange={setConfirm} minLength={9}
                autoComplete="new-password" required />
            </div>
            {err && <div className="err">{err}</div>}
            <button className="btn btn-orange" style={{ width: "100%", height: 48, marginTop: 8 }} disabled={busy}>
              {busy ? "در حال ذخیره…" : "تغییر رمز عبور"}
            </button>
          </form>
        )}

        <div style={{ textAlign: "center", marginTop: 14, fontSize: 13.5, color: "var(--muted)" }}>
          <Link href="/login" style={{ color: "var(--purple)", fontWeight: 700 }}>بازگشت به ورود</Link>
        </div>
      </div>
    </div>
  );
}
