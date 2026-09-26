"use client";
// Shop verification: review KYC info + documents, approve or reject.
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import { toFa } from "@/lib/format";
import Pagination from "@/components/Pagination";
import { usePage } from "@/lib/usePage";

const STATUS_BADGE: Record<string, [string, string]> = {
  pending: ["amber", "در انتظار بررسی"],
  approved: ["green", "تایید شده"],
  rejected: ["red", "رد شده"],
};

export default function SupplierShops() {
  const [rows, setRows] = useState<any[]>([]);
  const [state, setState] = useState("pending");
  const [open, setOpen] = useState<any>(null);
  const [note, setNote] = useState("");
  const [count, setCount] = useState(0);

  const [page, setPage] = usePage([state]);

  const load = useCallback(() =>
    api.get(`/accounts/supplier/shops/?page=${page}${state ? `&status=${state}` : ""}`)
      .then((d) => { setRows(d.results || d); setCount(d.count ?? 0); })
      .catch((e) => toast(errorMessage(e))), [page, state]);
  useEffect(() => { load(); }, [load]);

  const approve = async (id: number) => {
    await api.post(`/accounts/supplier/shops/${id}/approve/`);
    toast("فروشگاه تایید شد ✓ (خرید عمده فعال شد)");
    setOpen(null); load();
  };
  const reject = async (id: number) => {
    await api.post(`/accounts/supplier/shops/${id}/reject/`, { note });
    toast("پروفایل رد شد");
    setOpen(null); setNote(""); load();
  };

  return (
    <div>
      <h2 style={{ margin: "0 0 16px", fontSize: 19, fontWeight: 800 }}>فروشگاه‌ها و احراز هویت</h2>
      <div className="shopbar">
        <div className="fchips">
          {([["pending", "در انتظار بررسی"], ["approved", "تایید شده"], ["rejected", "رد شده"], ["", "همه"]] as [string, string][]).map(([v, l]) => (
            <button key={v} className={state === v ? "on" : ""} onClick={() => setState(v)}>{l}</button>
          ))}
        </div>
        <div style={{ fontSize: 13, color: "var(--muted)" }}><b className="mono">{toFa(count)}</b> فروشگاه</div>
      </div>

      <div className="panel tablewrap">
        <table className="tbl">
          <thead><tr><th>فروشگاه</th><th>مالک</th><th>موبایل</th><th>شهر</th><th>مدارک</th><th>وضعیت</th><th></th></tr></thead>
          <tbody>
            {rows.map((p) => {
              const b = STATUS_BADGE[p.status] || ["purple", p.status];
              return (
                <tr key={p.id}>
                  <td><b>{p.shop_name}</b></td>
                  <td>{p.full_name}</td>
                  <td className="mono">{toFa(p.phone)}</td>
                  <td>{p.city || "—"}</td>
                  <td className="mono">{toFa(p.documents?.length || 0)}</td>
                  <td><span className={`badge ${b[0]}`}>{b[1]}</span></td>
                  <td><button className="act-edit list-actions" onClick={() => setOpen(p)}>بررسی</button></td>
                </tr>
              );
            })}
            {!rows.length && <tr><td colSpan={7} style={{ textAlign: "center", color: "var(--muted)" }}>موردی نیست.</td></tr>}
          </tbody>
        </table>
      </div>
      <Pagination page={page} count={count} onChange={setPage} />

      {open && (
        <div className="panel" style={{ marginTop: 16 }}>
          <div className="between" style={{ marginBottom: 14 }}>
            <b style={{ fontSize: 16 }}>بررسی «{open.shop_name}»</b>
            <button className="act-del list-actions" onClick={() => setOpen(null)}>بستن</button>
          </div>
          <div className="fgrid" style={{ marginBottom: 14 }}>
            <div className="specrow"><span style={{ color: "var(--muted)" }}>مالک</span><b>{open.full_name}</b></div>
            <div className="specrow"><span style={{ color: "var(--muted)" }}>موبایل</span><b className="mono">{toFa(open.phone)}</b></div>
            <div className="specrow"><span style={{ color: "var(--muted)" }}>کد ملی</span><b className="mono">{toFa(open.owner_national_id || "—")}</b></div>
            <div className="specrow"><span style={{ color: "var(--muted)" }}>جواز کسب</span><b className="mono">{toFa(open.business_license_no || "—")}</b></div>
            <div className="specrow"><span style={{ color: "var(--muted)" }}>استان/شهر</span><b>{open.province || "—"}، {open.city || "—"}</b></div>
            <div className="specrow"><span style={{ color: "var(--muted)" }}>تلفن ثابت</span><b className="mono">{toFa(open.landline || "—")}</b></div>
            <div className="specrow full" style={{ gridColumn: "1 / -1" }}><span style={{ color: "var(--muted)" }}>آدرس</span><b>{open.address || "—"}</b></div>
          </div>

          <b style={{ display: "block", marginBottom: 8 }}>مدارک بارگذاری‌شده</b>
          {open.documents?.length ? (
            <div className="row" style={{ marginBottom: 14 }}>
              {open.documents.map((d: any) => (
                <a key={d.id} href={d.file} target="_blank" className="badge purple" style={{ padding: "9px 14px" }}>
                  {{ national_card: "کارت ملی", business_license: "جواز کسب", shop_photo: "تصویر فروشگاه", other: "سایر" }[d.doc_type as string] || d.doc_type} ↗
                </a>
              ))}
            </div>
          ) : (
            <div style={{ color: "var(--muted)", fontSize: 13.5, marginBottom: 14 }}>مدرکی بارگذاری نشده است.</div>
          )}

          <div className="row" style={{ alignItems: "flex-end" }}>
            <button className="btn btn-purple" style={{ height: 46, padding: "0 26px" }} onClick={() => approve(open.id)}>تایید فروشگاه ✓</button>
            <div style={{ flex: 1, minWidth: 220 }}>
              <input className="inp" placeholder="دلیل رد (اختیاری)" value={note} onChange={(e) => setNote(e.target.value)} />
            </div>
            <button className="btn" style={{ height: 46, padding: "0 22px", background: "#FBE7E7", color: "var(--red)" }} onClick={() => reject(open.id)}>رد</button>
          </div>
        </div>
      )}
    </div>
  );
}
