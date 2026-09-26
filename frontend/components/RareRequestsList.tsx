"use client";
// The signed-in user's rare-part requests — shown inside the profile panels.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { faDate } from "@/lib/format";

const BADGE: Record<string, [string, string]> = {
  new: ["purple", "جدید"],
  searching: ["amber", "در حال پیگیری"],
  found: ["green", "پیدا شد ✓"],
  unavailable: ["red", "موجود نیست"],
};

export default function RareRequestsList() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/catalog/rare-requests/")
      .then((d) => setRows(d.results || d))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="panel">
      <div className="between" style={{ marginBottom: 18, paddingBottom: 14, borderBottom: "1px solid var(--line)" }}>
        <h2 style={{ margin: 0, fontSize: 19, fontWeight: 800 }}>درخواست‌های قطعه نایاب</h2>
        <Link href="/rare-part" className="btn btn-purple" style={{ height: 42, padding: "0 18px" }}>+ درخواست جدید</Link>
      </div>

      {loading ? (
        <div className="skel" style={{ height: 90 }} />
      ) : rows.length ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {rows.map((r) => {
            const b = BADGE[r.status] || ["purple", r.status_display];
            return (
              <div key={r.id} style={{ display: "flex", gap: 12, alignItems: "flex-start", background: "var(--paper)", borderRadius: 14, padding: 14, borderRight: `4px solid var(--${b[0] === "green" ? "green" : b[0] === "red" ? "red" : b[0] === "amber" ? "amber" : "purple-2"})` }}>
                {r.image && (
                  <img src={r.image} alt="" style={{ width: 62, height: 62, borderRadius: 11, objectFit: "cover", border: "1px solid var(--line)", flexShrink: 0 }} />
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="between">
                    <b style={{ fontSize: 14.5 }}>{r.part_name}</b>
                    <span className={`badge ${b[0]}`}>{b[1]}</span>
                  </div>
                  <div style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 5 }}>
                    {r.car_name} {r.car_model} · برند: {r.brand} · {faDate(r.created_at)}
                  </div>
                  {r.admin_note && (
                    <div style={{ marginTop: 8, fontSize: 13, background: "var(--card)", borderRadius: 10, padding: "8px 12px" }}>
                      💬 پاسخ تامین‌کننده: {r.admin_note}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="center-empty">
          <div style={{ fontSize: 40 }}>🔍</div>
          <p>هنوز درخواستی ثبت نکرده‌اید.</p>
          <Link href="/rare-part" className="btn btn-orange" style={{ height: 44, padding: "0 22px" }}>ثبت اولین درخواست</Link>
        </div>
      )}
    </div>
  );
}
