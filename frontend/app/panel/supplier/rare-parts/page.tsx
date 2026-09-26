"use client";
// Rare-part requests console: filter by status, see the buyer's photo/details,
// set status + reply — switching to "found" texts the buyer automatically.
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import { toFa, faDate } from "@/lib/format";
import NiceSelect from "@/components/NiceSelect";
import Pagination from "@/components/Pagination";
import { usePage } from "@/lib/usePage";

const STATUSES = [
  { value: "new", label: "جدید" },
  { value: "searching", label: "در حال پیگیری" },
  { value: "found", label: "پیدا شد" },
  { value: "unavailable", label: "موجود نیست" },
];
const BADGE: Record<string, string> = { new: "purple", searching: "amber", found: "green", unavailable: "red" };

export default function SupplierRareParts() {
  const [rows, setRows] = useState<any[]>([]);
  const [state, setState] = useState("");
  const [count, setCount] = useState(0);
  const [notes, setNotes] = useState<Record<number, string>>({});

  const [page, setPage] = usePage([state]);

  const load = useCallback(() =>
    api.get(`/catalog/manage/rare-requests/?page=${page}${state ? `&status=${state}` : ""}`)
      .then((d) => { setRows(d.results || d); setCount(d.count ?? 0); })
      .catch((e) => toast(errorMessage(e))), [page, state]);
  useEffect(() => { load(); }, [load]);

  const update = async (r: any, status: string) => {
    try {
      await api.patch(`/catalog/manage/rare-requests/${r.id}/`, {
        status,
        admin_note: notes[r.id] ?? r.admin_note ?? "",
      });
      toast(status === "found" ? "ثبت شد ✓ پیامک «پیدا شد» برای مشتری ارسال گردید" : "وضعیت به‌روزرسانی شد ✓");
      load();
    } catch (e) { toast(errorMessage(e)); }
  };

  return (
    <div>
      <h2 style={{ margin: "0 0 16px", fontSize: 19, fontWeight: 800 }}>درخواست‌های قطعه نایاب</h2>

      <div className="shopbar">
        <div className="fchips">
          <button className={!state ? "on" : ""} onClick={() => setState("")}>همه</button>
          {STATUSES.map((s) => (
            <button key={s.value} className={state === s.value ? "on" : ""} onClick={() => setState(s.value)}>{s.label}</button>
          ))}
        </div>
        <div style={{ fontSize: 13, color: "var(--muted)" }}><b className="mono">{toFa(count)}</b> درخواست</div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {rows.map((r) => (
          <div key={r.id} className="panel" style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-start" }}>
            {r.image ? (
              <a href={r.image} target="_blank" style={{ flexShrink: 0 }}>
                <img src={r.image} alt="" style={{ width: 96, height: 96, borderRadius: 14, objectFit: "cover", border: "1px solid var(--line)" }} />
              </a>
            ) : (
              <div style={{ width: 96, height: 96, borderRadius: 14, background: "var(--purple-soft)", display: "grid", placeItems: "center", color: "var(--purple)", flexShrink: 0, fontSize: 30 }}>🔧</div>
            )}
            <div style={{ flex: 1, minWidth: 220 }}>
              <div className="between">
                <b style={{ fontSize: 15.5 }}>{r.part_name}</b>
                <span className={`badge ${BADGE[r.status] || "purple"}`}>{r.status_display}</span>
              </div>
              <div style={{ fontSize: 13, color: "var(--muted)", marginTop: 6, lineHeight: 2 }}>
                🚗 {r.car_name} {r.car_model} · 🏷 برند: <b>{r.brand}</b><br />
                👤 {r.user_name || "کاربر"} · <span className="mono">{toFa(r.user_phone)}</span> · {faDate(r.created_at)}
              </div>
              {r.note && <div style={{ fontSize: 13, marginTop: 6, background: "var(--paper)", borderRadius: 10, padding: "8px 12px" }}>{r.note}</div>}
            </div>
            <div style={{ minWidth: 240, display: "flex", flexDirection: "column", gap: 8 }}>
              <input className="inp" placeholder="پاسخ/توضیح برای مشتری…" defaultValue={r.admin_note}
                onChange={(e) => setNotes({ ...notes, [r.id]: e.target.value })} />
              <NiceSelect value={r.status} onChange={(v) => update(r, v)} options={STATUSES} />
            </div>
          </div>
        ))}
        {!rows.length && <div className="panel center-empty">درخواستی نیست.</div>}
      </div>
      <Pagination page={page} count={count} onChange={setPage} />
    </div>
  );
}
