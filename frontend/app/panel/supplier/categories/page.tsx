"use client";
// Category + brand management (create / rename / activate / delete).
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import { toFa } from "@/lib/format";
import Pagination from "@/components/Pagination";
import { usePage } from "@/lib/usePage";

const PAGE_SIZE = 8;

function CrudList({ title, endpoint, withOrder, withEnglish }: { title: string; endpoint: string; withOrder?: boolean; withEnglish?: boolean }) {
  const [rows, setRows] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [nameEn, setNameEn] = useState("");
  const [q, setQ] = useState("");
  const [editing, setEditing] = useState<any>(null);

  const load = useCallback(
    () => api.get(endpoint).then((d) => setRows(d.results || d)).catch((e) => toast(errorMessage(e))),
    [endpoint],
  );
  useEffect(() => { load(); }, [load]);

  // Filtered client-side: both lists are small and unpaginated server-side, so
  // this is instant and avoids a request per keystroke.
  const needle = q.trim().toLowerCase();
  const filtered = needle
    ? rows.filter((r) =>
        (r.name || "").toLowerCase().includes(needle) ||
        (r.name_en || "").toLowerCase().includes(needle))
    : rows;
  const [page, setPage] = usePage([q]);
  const visible = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    await api.post(endpoint, withEnglish ? { name, name_en: nameEn } : { name });
    setName(""); setNameEn(""); toast("افزوده شد ✓"); load();
  };
  const save = async () => {
    await api.patch(`${endpoint}${editing.id}/`, {
      name: editing.name,
      ...(withOrder ? { order: editing.order } : {}),
      ...(withEnglish ? { name_en: editing.name_en || "" } : {}),
    });
    setEditing(null); toast("ذخیره شد ✓"); load();
  };
  const remove = async (id: number) => {
    if (!confirm("حذف شود؟ (اگر محصولی به آن وصل باشد حذف نمی‌شود)")) return;
    try { await api.del(`${endpoint}${id}/`); toast("حذف شد"); load(); }
    catch (e) { toast(errorMessage(e, "قابل حذف نیست — به محصولات متصل است.")); }
  };

  return (
    <div className="panel" style={{ marginBottom: 16 }}>
      <b style={{ display: "block", marginBottom: 12 }}>{title} <span className="mono" style={{ color: "var(--muted)", fontSize: 12 }}>({toFa(filtered.length)}{needle ? ` از ${toFa(rows.length)}` : ""})</span></b>
      <div className="row" style={{ marginBottom: 12 }}>
        <input
          className="inp"
          style={{ flex: 1, minWidth: 180 }}
          placeholder={withEnglish ? "جست‌وجو (فارسی یا انگلیسی)…" : "جست‌وجو…"}
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        {q && (
          <button type="button" className="btn btn-ghost" style={{ height: 44, padding: "0 16px" }} onClick={() => setQ("")}>
            پاک کردن
          </button>
        )}
      </div>
      <form className="row" style={{ marginBottom: 14 }} onSubmit={create}>
        <input className="inp" style={{ flex: 1, minWidth: 150 }} placeholder="نام جدید…" value={name} onChange={(e) => setName(e.target.value)} />
        {withEnglish && (
          <input className="inp" style={{ flex: 1, minWidth: 150 }} dir="ltr" placeholder="English name (optional)" value={nameEn} onChange={(e) => setNameEn(e.target.value)} />
        )}
        <button className="btn btn-purple" style={{ height: 44, padding: "0 20px" }}>افزودن</button>
      </form>
      <div className="tablewrap">
        <table className="tbl">
          <tbody>
            {visible.map((r) => (
              <tr key={r.id}>
                <td style={{ width: "100%" }}>
                  {editing?.id === r.id
                    ? (
                      <div className="row" style={{ gap: 6 }}>
                        <input className="inp" value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} />
                        {withEnglish && (
                          <input className="inp" dir="ltr" placeholder="English" value={editing.name_en || ""} onChange={(e) => setEditing({ ...editing, name_en: e.target.value })} />
                        )}
                      </div>
                    )
                    : (
                      <>
                        <b>{r.name}</b>
                        {withEnglish && r.name_en && (
                          <span className="mono" dir="ltr" style={{ color: "var(--muted)", fontSize: 12, marginInlineStart: 8 }}>
                            {r.name_en}
                          </span>
                        )}
                      </>
                    )}
                </td>
                <td>
                  <div className="list-actions">
                    {editing?.id === r.id
                      ? <button className="act-edit" style={{ background: "var(--purple)", color: "#fff" }} onClick={save}>ذخیره</button>
                      : <button className="act-edit" onClick={() => setEditing({ ...r })}>ویرایش</button>}
                    <button className="act-del" onClick={() => remove(r.id)}>حذف</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination page={page} count={filtered.length} pageSize={PAGE_SIZE} onChange={setPage} />
    </div>
  );
}

export default function SupplierCategories() {
  return (
    <div>
      <h2 style={{ margin: "0 0 16px", fontSize: 19, fontWeight: 800 }}>دسته‌بندی‌ها و برندها</h2>
      <CrudList title="دسته‌بندی محصولات" endpoint="/catalog/manage/categories/" withOrder />
      <CrudList title="برندها" endpoint="/catalog/manage/brands/" withEnglish />
      <CrudList title="دسته‌بندی بلاگ" endpoint="/blog/manage/categories/" />
    </div>
  );
}
