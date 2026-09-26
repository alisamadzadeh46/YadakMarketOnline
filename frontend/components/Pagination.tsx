"use client";
// Numbered pagination matching DRF's ?page= parameter.
import { toFa } from "@/lib/format";

export default function Pagination({
  page,
  count,
  pageSize = 24,
  onChange,
}: {
  page: number;
  count: number;
  pageSize?: number;
  onChange: (p: number) => void;
}) {
  const pages = Math.ceil(count / pageSize);
  if (pages <= 1) return null;

  // Windowed page list: 1 … p-1 p p+1 … N
  const items: (number | "…")[] = [];
  for (let i = 1; i <= pages; i++) {
    if (i === 1 || i === pages || Math.abs(i - page) <= 1) items.push(i);
    else if (items[items.length - 1] !== "…") items.push("…");
  }

  const BTN: React.CSSProperties = {
    minWidth: 38, height: 38, borderRadius: 11, fontWeight: 700, fontSize: 13.5,
    border: "1.5px solid var(--line)", background: "var(--card)", color: "var(--ink-soft)",
    display: "grid", placeItems: "center", padding: "0 8px",
  };

  return (
    <nav style={{ display: "flex", gap: 6, justifyContent: "center", marginTop: 22, flexWrap: "wrap" }} aria-label="صفحه‌بندی">
      <button style={{ ...BTN, opacity: page <= 1 ? 0.4 : 1 }} disabled={page <= 1} onClick={() => onChange(page - 1)}>‹ قبلی</button>
      {items.map((it, i) =>
        it === "…" ? (
          <span key={`e${i}`} style={{ ...BTN, border: "none", background: "none" }}>…</span>
        ) : (
          <button
            key={it}
            onClick={() => onChange(it)}
            style={it === page
              ? { ...BTN, background: "linear-gradient(135deg,var(--purple),var(--purple-2))", color: "#fff", border: "none" }
              : BTN}
            className="mono"
          >
            {toFa(it)}
          </button>
        )
      )}
      <button style={{ ...BTN, opacity: page >= pages ? 0.4 : 1 }} disabled={page >= pages} onClick={() => onChange(page + 1)}>بعدی ›</button>
    </nav>
  );
}
