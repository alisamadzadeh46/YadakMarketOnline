import Link from "next/link";

export default function NotFound() {
  return (
    <div className="center-empty view" style={{ padding: "100px 20px" }}>
      <div style={{ fontSize: 88, fontWeight: 900, color: "var(--purple)" }}>۴۰۴</div>
      <h1 style={{ fontSize: 22, fontWeight: 800 }}>صفحه مورد نظر پیدا نشد</h1>
      <p style={{ color: "var(--muted)" }}>ممکن است آدرس اشتباه باشد یا صفحه حذف شده باشد.</p>
      <Link className="btn btn-purple" href="/" style={{ height: 48, padding: "0 24px" }}>بازگشت به خانه</Link>
    </div>
  );
}
