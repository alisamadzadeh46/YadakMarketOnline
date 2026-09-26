"use client";
import Link from "next/link";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="center-empty view" style={{ padding: "100px 20px" }}>
      <div style={{ fontSize: 88, fontWeight: 900, color: "var(--orange)" }}>۵۰۰</div>
      <h1 style={{ fontSize: 22, fontWeight: 800 }}>خطای غیرمنتظره‌ای رخ داد</h1>
      <p style={{ color: "var(--muted)" }}>لطفا دوباره تلاش کنید یا بعدا مراجعه کنید.</p>
      <div className="row" style={{ justifyContent: "center" }}>
        <button className="btn btn-purple" style={{ height: 48, padding: "0 24px" }} onClick={reset}>تلاش مجدد</button>
        <Link className="btn btn-ghost" href="/" style={{ height: 48, padding: "0 24px" }}>خانه</Link>
      </div>
    </div>
  );
}
