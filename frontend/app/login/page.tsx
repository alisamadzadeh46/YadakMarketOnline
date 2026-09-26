"use client";
import Link from "next/link";
import PasswordField from "@/components/PasswordField";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { SITE } from "@/lib/site";
import { errorMessage, errorStatus } from "@/lib/api";
import { safeNextPath } from "@/lib/ui";

export default function Login() {
  const { login } = useAuth();
  const router = useRouter();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await login(phone, password);
      // Guarded pages send the visitor here with ?next=… so they land back
      // where they were headed. Only same-site paths are honoured — an
      // absolute URL in the query string would be an open-redirect.
      // Read the query directly rather than via useSearchParams(), which would
      // force this page behind a Suspense boundary at build time.
      router.push(safeNextPath(new URLSearchParams(window.location.search).get("next")));
    } catch (e) {
      // Only a rejected login is about the credentials; a throttled or failed
      // request must not tell the user their password is wrong.
      setErr(errorStatus(e) === 401 ? "شماره موبایل یا رمز عبور نادرست است." : errorMessage(e));
      setBusy(false);
    }
  };

  return (
    <div className="authwrap view">
      <div className="panel">
        <div style={{ textAlign: "center", marginBottom: 22 }}>
          <img src="/logo-full.png" alt={SITE.name} style={{ height: 92, width: "auto", margin: "0 auto 12px", display: "block" }} />
          <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }}>ورود به {SITE.name}</h1>
          <p style={{ color: "var(--muted)", fontSize: 13.5, marginTop: 6 }}>با شماره موبایل و رمز عبور وارد شوید</p>
        </div>
        <form onSubmit={submit}>
          <div className="field"><label>شماره موبایل</label><input className="inp" dir="ltr" style={{ textAlign: "right" }} placeholder="09xxxxxxxxx" pattern="09\d{9}" data-error="شماره موبایل معتبر نیست (مثال: 09123456789)" value={phone} onChange={(e) => setPhone(e.target.value)} required /></div>
          <div className="field"><label>رمز عبور</label><PasswordField value={password} onChange={setPassword} autoComplete="current-password" required /></div>
          {err && <div className="err">{err}</div>}
          <button className="btn btn-orange" style={{ width: "100%", height: 48, marginTop: 8 }} disabled={busy}>{busy ? "در حال ورود…" : "ورود"}</button>
        </form>
        <div style={{ textAlign: "center", marginTop: 14 }}>
          <Link href="/forgot-password" style={{ color: "var(--purple)", fontSize: 13, fontWeight: 600 }}>فراموشی رمز عبور؟</Link>
        </div>
        <div style={{ textAlign: "center", marginTop: 10, fontSize: 13.5, color: "var(--muted)" }}>
          حساب ندارید؟ <Link href="/register" style={{ color: "var(--purple)", fontWeight: 700 }}>ثبت‌نام</Link>
        </div>
      </div>
    </div>
  );
}
