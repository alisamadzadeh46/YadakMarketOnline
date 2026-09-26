// Shared shell for informational pages (guide, terms, shipping...).
export default function StaticPage({
  title,
  intro,
  children,
}: {
  title: string;
  intro?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="view" style={{ maxWidth: 820, margin: "0 auto" }}>
      <div style={{ borderRadius: "var(--r-lg)", padding: "clamp(22px,5vw,38px) clamp(18px,4vw,30px)", color: "#fff", marginBottom: 24, background: "radial-gradient(420px 220px at 85% 0%,rgba(255,138,61,.3),transparent),linear-gradient(130deg,var(--purple-deep),var(--purple-2))" }}>
        <h1 style={{ margin: 0, fontSize: "clamp(22px,3.4vw,30px)", fontWeight: 800 }}>{title}</h1>
        {intro && <p style={{ margin: "10px 0 0", opacity: .88, fontSize: 14.5, lineHeight: 2 }}>{intro}</p>}
      </div>
      {/* Content lives inside a proper card so it never floats on the page bg. */}
      <div className="panel post-html" style={{ padding: "clamp(18px,3.5vw,34px)" }}>{children}</div>
    </div>
  );
}
