"use client";
// Credit management: define per-shop credit terms, watch invoices, settle.
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import PriceField from "@/components/PriceField";
import { toast } from "@/lib/ui";
import { money, toFa, faDate } from "@/lib/format";
import NiceSelect from "@/components/NiceSelect";
import Pagination from "@/components/Pagination";
import { usePage } from "@/lib/usePage";

const EMPTY = { shop: "", credit_limit: "", settlement_days: 7, reminder_days: "" };

export default function SupplierCredit() {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [shops, setShops] = useState<any[]>([]);
  const [state, setState] = useState("unsettled");
  const [form, setForm] = useState<any>(null);
  const [invPage, setInvPage] = usePage([state]);
  const [invCount, setInvCount] = useState(0);

  const load = useCallback(() => {
    api.get("/suppliers/credit-accounts/").then((d) => setAccounts(d.results || d)).catch((e) => toast(errorMessage(e)));
    api.get(`/suppliers/invoices/?state=${state}&page=${invPage}`)
      .then((d) => { setInvoices(d.results || d); setInvCount(d.count ?? 0); })
      .catch((e) => toast(errorMessage(e)));
  }, [state, invPage]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    // Approved shops are the candidates for a credit account.
    api.get("/accounts/supplier/shops/?status=approved").then((d) => setShops(d.results || d));
  }, []);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = { ...form, reminder_days: form.reminder_days === "" ? null : form.reminder_days };
      if (form.id) await api.patch(`/suppliers/credit-accounts/${form.id}/`, payload);
      else await api.post("/suppliers/credit-accounts/", payload);
      toast("حساب اعتباری ذخیره شد ✓");
      setForm(null); load();
    } catch (err) { toast(errorMessage(err)); }
  };

  const settle = async (id: number) => {
    await api.post(`/suppliers/invoices/${id}/settle/`);
    toast("تسویه ثبت شد ✓");
    load();
  };

  return (
    <div>
      <div className="between" style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 19, fontWeight: 800 }}>اعتبار و تسویه فروشگاه‌ها</h2>
        <button className="btn btn-purple" style={{ height: 42, padding: "0 18px" }} onClick={() => setForm({ ...EMPTY })}>+ حساب اعتباری جدید</button>
      </div>

      {form && (
        <form className="panel" style={{ marginBottom: 16 }} onSubmit={save}>
          <div className="fgrid">
            <div className="field"><label>فروشگاه *</label>
              {form.id
                ? <input className="inp" disabled value={shops.find((s) => String(s.user_id) === String(form.shop))?.shop_name || "—"} />
                : <NiceSelect value={String(form.shop || "")} onChange={(v) => setForm({ ...form, shop: v })}
                    options={[{ value: "", label: "انتخاب…" }, ...shops.map((s) => ({ value: String(s.user_id), label: `${s.shop_name} — ${s.phone}` }))]} />}
            </div>
            <div className="field"><label>سقف اعتبار (تومان)</label><PriceField value={form.credit_limit} onChange={(v) => setForm({ ...form, credit_limit: v })} /></div>
            <div className="field"><label>مهلت تسویه (روز) — مثلا ۷ یا ۳۰</label><input className="inp" type="number" value={form.settlement_days} onChange={(e) => setForm({ ...form, settlement_days: e.target.value })} /></div>
            <div className="field"><label>روز یادآوری پیامک (خالی = پیش‌فرض)</label><input className="inp" type="number" value={form.reminder_days ?? ""} onChange={(e) => setForm({ ...form, reminder_days: e.target.value })} placeholder="مثلا ۲ یا ۳" /></div>
          </div>
          <div className="row">
            <button className="btn btn-purple" style={{ height: 44, padding: "0 22px" }}>ذخیره</button>
            <button type="button" className="btn btn-ghost" style={{ height: 44, padding: "0 18px" }} onClick={() => setForm(null)}>انصراف</button>
          </div>
        </form>
      )}

      <div className="panel tablewrap" style={{ marginBottom: 20 }}>
        <b style={{ display: "block", marginBottom: 10 }}>حساب‌های اعتباری</b>
        <table className="tbl">
          <thead><tr><th>فروشگاه</th><th>سقف</th><th>مهلت تسویه</th><th>یادآوری</th><th>بدهی جاری</th><th></th></tr></thead>
          <tbody>
            {accounts.map((a) => (
              <tr key={a.id}>
                <td><b>{a.shop_name}</b> <span className="mono" style={{ color: "var(--muted)", fontSize: 11 }}>{toFa(a.shop_phone)}</span></td>
                <td className="mono">{money(a.credit_limit)}</td>
                <td className="mono">{toFa(a.settlement_days)} روز</td>
                <td className="mono">{toFa(a.effective_reminder_days)} روز قبل</td>
                <td className="mono" style={{ color: a.outstanding > 0 ? "var(--orange)" : "var(--green)" }}>{money(a.outstanding)}</td>
                <td><button className="act-edit list-actions" onClick={() => setForm({ ...a })}>ویرایش</button></td>
              </tr>
            ))}
            {!accounts.length && <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--muted)" }}>هنوز حسابی تعریف نشده.</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="panel" style={{ marginBottom: 0 }}>
        <div className="between" style={{ marginBottom: 14, paddingBottom: 12, borderBottom: "1px solid var(--line)" }}>
          <b>فاکتورهای اعتباری <span className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>({toFa(invCount)})</span></b>
          <div className="fchips">
            {([["unsettled", "باز"], ["overdue", "معوق"], ["settled", "تسویه‌شده"], ["", "همه"]] as [string, string][]).map(([v, l]) => (
              <button key={v} className={state === v ? "on" : ""} onClick={() => setState(v)}>{l}</button>
            ))}
          </div>
        </div>
        <div className="tablewrap">
        <table className="tbl">
          <thead><tr><th>فروشگاه</th><th>سفارش</th><th>مبلغ</th><th>سررسید</th><th>وضعیت</th><th></th></tr></thead>
          <tbody>
            {invoices.map((i) => (
              <tr key={i.id}>
                <td>{i.shop_name}</td>
                <td className="mono">{toFa(i.order_number || "-")}</td>
                <td className="mono">{money(i.amount)}</td>
                <td>{faDate(i.due_date)}</td>
                <td>{i.is_settled ? <span className="badge green">تسویه</span> : i.is_overdue ? <span className="badge red">معوق</span> : <span className="badge amber">باز</span>}</td>
                <td>{!i.is_settled && <button className="act-edit list-actions" style={{ background: "var(--green)", color: "#fff" }} onClick={() => settle(i.id)}>ثبت تسویه</button>}</td>
              </tr>
            ))}
            {!invoices.length && <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--muted)" }}>فاکتوری نیست.</td></tr>}
          </tbody>
        </table>
        </div>
        <Pagination page={invPage} count={invCount} onChange={setInvPage} />
      </div>
    </div>
  );
}
