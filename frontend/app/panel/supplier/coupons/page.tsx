"use client";
// Discount-code manager: create/edit/toggle codes without Django admin.
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import PriceField from "@/components/PriceField";
import { toast } from "@/lib/ui";
import { money, toFa, faDate } from "@/lib/format";
import NiceSelect from "@/components/NiceSelect";
import Pagination from "@/components/Pagination";
import JalaliPicker from "@/components/JalaliPicker";
import { useAuth } from "@/lib/auth";

const in30days = () => new Date(Date.now() + 30 * 864e5).toISOString();
const EMPTY = () => ({
  code: "", kind: "percent", value: "", max_discount: "", min_order_amount: 0,
  usage_limit: "", per_user_limit: 1,
  valid_from: new Date().toISOString(), valid_to: in30days(), is_active: true,
});

export default function SupplierCoupons() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [rows, setRows] = useState<any[]>([]);
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [form, setForm] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() =>
    api.get(`/discounts/manage/coupons/?page=${page}`)
      .then((d) => { setRows(d.results || d); setCount(d.count ?? 0); })
      .catch((e) => toast(errorMessage(e))), [page]);
  useEffect(() => { load(); }, [load]);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = {
        ...form,
        max_discount: form.max_discount || null,
        usage_limit: form.usage_limit || null,
      };
      if (form.id) await api.patch(`/discounts/manage/coupons/${form.id}/`, payload);
      else await api.post("/discounts/manage/coupons/", payload);
      toast("کد تخفیف ذخیره شد ✓");
      setForm(null); load();
    } catch (err) { toast(errorMessage(err)); }
    finally { setBusy(false); }
  };

  const remove = async (id: number) => {
    if (!confirm("این کد حذف شود؟")) return;
    await api.del(`/discounts/manage/coupons/${id}/`);
    load();
  };

  return (
    <div>
      <div className="between" style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 19, fontWeight: 800 }}>کدهای تخفیف</h2>
        <button className="btn btn-purple" style={{ height: 42, padding: "0 18px" }} onClick={() => setForm(EMPTY())}>+ کد جدید</button>
      </div>

      {form && (
        <form className="panel" style={{ marginBottom: 16 }} onSubmit={save}>
          {/* Supplier coupons are scoped server-side to the supplier's own products. */}
          <div style={{ fontSize: 12.5, color: "var(--muted)", marginBottom: 12 }}>
            {isAdmin
              ? "کدهایی که مدیر سایت می‌سازد روی کل سبد خرید اعمال می‌شوند."
              : "این کد فقط روی محصولات خود شما در سبد خرید اعمال می‌شود."}
          </div>
          <div className="fgrid">
            <div className="field"><label>کد *</label><input className="inp" dir="ltr" style={{ textAlign: "right" }} required minLength={3} value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} placeholder="WELCOME15" /></div>
            <div className="field"><label>نوع تخفیف</label>
              <NiceSelect value={form.kind} onChange={(v) => setForm({ ...form, kind: v })}
                options={[{ value: "percent", label: "درصدی" }, { value: "fixed", label: "مبلغ ثابت (تومان)" }]} /></div>
            <div className="field"><label>{form.kind === "percent" ? "درصد تخفیف *" : "مبلغ تخفیف (تومان) *"}</label>{form.kind === "percent"
              ? <input className="inp" type="number" required min={1} max={100} value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} />
              : <PriceField required value={form.value} onChange={(v) => setForm({ ...form, value: v })} />}</div>
            {form.kind === "percent" && (
              <div className="field"><label>سقف تخفیف (تومان)</label><PriceField value={form.max_discount || ""} onChange={(v) => setForm({ ...form, max_discount: v })} /></div>
            )}
            <div className="field"><label>حداقل مبلغ سفارش (تومان)</label><PriceField value={form.min_order_amount} onChange={(v) => setForm({ ...form, min_order_amount: v })} /></div>
            <div className="field"><label>سقف کل استفاده</label><input className="inp" type="number" placeholder="خالی = نامحدود" value={form.usage_limit || ""} onChange={(e) => setForm({ ...form, usage_limit: e.target.value })} /></div>
            <div className="field"><label>سقف استفاده هر کاربر</label><input className="inp" type="number" min={1} value={form.per_user_limit} onChange={(e) => setForm({ ...form, per_user_limit: e.target.value })} /></div>
            <div className="field full"><label>شروع اعتبار (شمسی)</label>
              <JalaliPicker value={form.valid_from} onChange={(iso) => setForm({ ...form, valid_from: iso })} /></div>
            <div className="field full"><label>معتبر تا (شمسی) *</label>
              <JalaliPicker value={form.valid_to} onChange={(iso) => setForm({ ...form, valid_to: iso })} /></div>
          </div>
          <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer", marginBottom: 12, fontSize: 13.5 }}>
            <input type="checkbox" checked={!!form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} style={{ accentColor: "var(--purple)" }} /> فعال
          </label>
          <div className="row">
            <button className="btn btn-purple" style={{ height: 44, padding: "0 22px" }} disabled={busy}>{busy ? "..." : "ذخیره"}</button>
            <button type="button" className="btn btn-ghost" style={{ height: 44, padding: "0 18px" }} onClick={() => setForm(null)}>انصراف</button>
          </div>
        </form>
      )}

      <div className="panel tablewrap">
        <table className="tbl">
          <thead><tr><th>کد</th><th>دامنه</th><th>تخفیف</th><th>استفاده</th><th>شروع</th><th>اعتبار تا</th><th>وضعیت</th><th>عملیات</th></tr></thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id}>
                <td className="mono"><b>{c.code}</b></td>
                <td style={{ fontSize: 12 }}>{c.scope}</td>
                <td>{c.kind === "percent" ? `${toFa(c.value)}٪${c.max_discount ? ` (تا ${money(c.max_discount)})` : ""}` : `${money(c.value)} تومان`}</td>
                <td className="mono">{toFa(c.used_count)}{c.usage_limit ? ` / ${toFa(c.usage_limit)}` : ""}</td>
                <td style={{ fontSize: 12 }}>{faDate(c.valid_from)}</td>
                <td style={{ fontSize: 12 }}>{faDate(c.valid_to)}</td>
                <td>{c.is_active ? <span className="badge green">فعال</span> : <span className="badge red">غیرفعال</span>}</td>
                <td>
                  <div className="list-actions">
                    <button className="act-edit" onClick={() => setForm({ ...c })}>ویرایش</button>
                    <button className="act-del" onClick={() => remove(c.id)}>حذف</button>
                  </div>
                </td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={8} style={{ textAlign: "center", color: "var(--muted)" }}>کدی تعریف نشده.</td></tr>}
          </tbody>
        </table>
      </div>
      <Pagination page={page} count={count} onChange={setPage} />
    </div>
  );
}
