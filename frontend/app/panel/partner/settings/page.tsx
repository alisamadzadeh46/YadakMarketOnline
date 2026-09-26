"use client";
// The partner's own control room: change the share percentage, per-buyer-type
// rates and per-category overrides. Every change applies to future orders only.
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import { money, toFa } from "@/lib/format";
import NiceSelect from "@/components/NiceSelect";

type Setting = {
  is_active: boolean;
  default_rate: string;
  rate_for_shopkeeper: string | null;
  rate_for_customer: string | null;
  min_rate: string;
  max_rate: string;
  accrue_on_credit_order: boolean;
  notify_on_new_commission: boolean;
  beneficiary_name: string;
  beneficiary_phone: string;
  beneficiary_email: string;
};

type Category = { id: number; name: string };
type CatRate = { id: number; category: number; category_name: string; rate: string };

// A live example makes an abstract percentage concrete.
const SAMPLE = 5_000_000;

export default function PartnerSettings() {
  const [s, setS] = useState<Setting | null>(null);
  const [saving, setSaving] = useState(false);
  const [cats, setCats] = useState<Category[]>([]);
  const [rates, setRates] = useState<CatRate[]>([]);
  const [newCat, setNewCat] = useState("");
  const [newRate, setNewRate] = useState("");

  const loadRates = () => api.get<CatRate[]>("/commissions/category-rates/").then(setRates).catch(() => {});

  useEffect(() => {
    api.get<Setting>("/commissions/settings/").then(setS).catch(() => {});
    api.get<Category[]>("/catalog/categories/").then(setCats).catch(() => {});
    loadRates();
  }, []);

  if (!s) return <div className="skel" style={{ height: 380 }} />;

  const min = Number(s.min_rate), max = Number(s.max_rate);
  const set = (patch: Partial<Setting>) => setS({ ...s, ...patch });

  const save = async () => {
    setSaving(true);
    try {
      const data = await api.patch<Setting>("/commissions/settings/", {
        is_active: s.is_active,
        default_rate: s.default_rate,
        rate_for_shopkeeper: s.rate_for_shopkeeper === "" ? null : s.rate_for_shopkeeper,
        rate_for_customer: s.rate_for_customer === "" ? null : s.rate_for_customer,
        min_rate: s.min_rate,
        max_rate: s.max_rate,
        accrue_on_credit_order: s.accrue_on_credit_order,
        notify_on_new_commission: s.notify_on_new_commission,
      });
      setS(data);
      toast("تنظیمات ذخیره شد ✓");
    } catch (e) {
      toast(errorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const addRate = async () => {
    if (!newCat || !newRate) return toast("دسته‌بندی و درصد را وارد کنید.");
    try {
      await api.post("/commissions/category-rates/", { category: +newCat, rate: newRate });
      setNewCat(""); setNewRate(""); loadRates();
      toast("درصد دسته‌بندی ثبت شد ✓");
    } catch (e) { toast(errorMessage(e)); }
  };

  const delRate = async (id: number) => {
    try { await api.del(`/commissions/category-rates/${id}/`); loadRates(); }
    catch (e) { toast(errorMessage(e)); }
  };

  return (
    <div>
      <h2 style={{ margin: "0 0 16px", fontSize: 19, fontWeight: 800 }}>تنظیم درصد سهم شما</h2>

      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="between" style={{ marginBottom: 4 }}>
          <b>حساب دریافت‌کننده</b>
          <span className={`badge ${s.is_active ? "green" : "red"}`}>
            {s.is_active ? "فعال" : "غیرفعال"}
          </span>
        </div>
        <div className="specrow"><span>نام</span><b>{s.beneficiary_name || "—"}</b></div>
        <div className="specrow"><span>ایمیل</span><b dir="ltr">{s.beneficiary_email || "—"}</b></div>
        <div className="specrow"><span>موبایل (نام کاربری ورود)</span><b className="mono" dir="ltr">{s.beneficiary_phone ? toFa(s.beneficiary_phone) : "—"}</b></div>
      </div>

      <div className="cols-2">
        <div className="panel">
          <b>درصد پیش‌فرض روی هر فروش</b>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, margin: "14px 0 6px" }}>
            <span className="mono" style={{ fontSize: 40, fontWeight: 800, color: "var(--purple)" }}>
              {toFa(s.default_rate)}
            </span>
            <span style={{ fontSize: 20, fontWeight: 800, color: "var(--purple)" }}>٪</span>
          </div>
          <input
            type="range"
            min={min} max={max} step={0.5}
            value={Number(s.default_rate)}
            onChange={(e) => set({ default_rate: e.target.value })}
            style={{ width: "100%", accentColor: "var(--purple)" }}
          />
          <div className="between" style={{ fontSize: 12, color: "var(--muted)" }}>
            <span className="mono">{toFa(min)}٪</span>
            <span className="mono">{toFa(max)}٪</span>
          </div>
          <div className="specrow" style={{ marginTop: 14 }}>
            <span>مثال: از یک فروش {money(SAMPLE)} تومانی</span>
            <b className="mono" style={{ color: "var(--orange)" }}>
              {money(Math.round(SAMPLE * Number(s.default_rate) / 100))} تومان
            </b>
          </div>
        </div>

        <div className="panel">
          <b>درصد اختصاصی بر اساس نوع خریدار</b>
          <p style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 2, margin: "8px 0 14px" }}>
            خالی بگذارید تا همان درصد پیش‌فرض اعمال شود.
          </p>
          <div className="field">
            <label>فروشگاه‌های لوازم یدکی (٪)</label>
            <input className="inp mono" type="number" step="0.5" min={min} max={max}
              value={s.rate_for_shopkeeper ?? ""} placeholder="پیش‌فرض"
              onChange={(e) => set({ rate_for_shopkeeper: e.target.value })} />
          </div>
          <div className="field">
            <label>کاربران عادی (٪)</label>
            <input className="inp mono" type="number" step="0.5" min={min} max={max}
              value={s.rate_for_customer ?? ""} placeholder="پیش‌فرض"
              onChange={(e) => set({ rate_for_customer: e.target.value })} />
          </div>
          <div className="fgrid">
            <div className="field">
              <label>حداقل مجاز (٪)</label>
              <input className="inp mono" type="number" step="0.5" value={s.min_rate}
                onChange={(e) => set({ min_rate: e.target.value })} />
            </div>
            <div className="field">
              <label>حداکثر مجاز (٪)</label>
              <input className="inp mono" type="number" step="0.5" value={s.max_rate}
                onChange={(e) => set({ max_rate: e.target.value })} />
            </div>
          </div>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 16 }}>
        <b>رفتار سیستم</b>
        <label className="specrow" style={{ cursor: "pointer", marginTop: 10 }}>
          <span>محاسبه پورسانت فعال باشد</span>
          <input type="checkbox" checked={s.is_active} onChange={(e) => set({ is_active: e.target.checked })} />
        </label>
        <label className="specrow" style={{ cursor: "pointer" }}>
          <span>سهم خریدهای اعتباری بلافاصله قطعی شود (نه بعد از تسویه فروشگاه)</span>
          <input type="checkbox" checked={s.accrue_on_credit_order} onChange={(e) => set({ accrue_on_credit_order: e.target.checked })} />
        </label>
        <label className="specrow" style={{ cursor: "pointer" }}>
          <span>پیامک اطلاع‌رسانی برای هر پورسانت جدید</span>
          <input type="checkbox" checked={s.notify_on_new_commission} onChange={(e) => set({ notify_on_new_commission: e.target.checked })} />
        </label>
        <button className="btn btn-purple" style={{ height: 46, padding: "0 26px", marginTop: 14 }} disabled={saving} onClick={save}>
          {saving ? "در حال ذخیره…" : "ذخیره تنظیمات"}
        </button>
      </div>

      <div className="panel" style={{ marginTop: 16 }}>
        <b>درصد اختصاصی برای دسته‌بندی‌ها</b>
        <p style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 2, margin: "8px 0 12px" }}>
          مثلا ۲۰٪ روی فیلتر و ۶٪ روی لاستیک. این درصد بر درصد پیش‌فرض اولویت دارد.
        </p>
        <div className="row" style={{ marginBottom: 12 }}>
          <NiceSelect value={newCat} onChange={setNewCat} style={{ minWidth: 180, flex: 1 }}
            options={[{ value: "", label: "انتخاب دسته‌بندی…" },
              ...cats.map((c) => ({ value: String(c.id), label: c.name }))]} />
          <input className="inp mono" style={{ flex: 1, minWidth: 120 }} type="number" step="0.5"
            placeholder="درصد" value={newRate} onChange={(e) => setNewRate(e.target.value)} />
          <button className="btn btn-ghost" style={{ height: 42, padding: "0 18px" }} onClick={addRate}>افزودن</button>
        </div>
        <div className="tablewrap">
          <table className="tbl">
            <tbody>
              {rates.map((r) => (
                <tr key={r.id}>
                  <td className="wrap">{r.category_name}</td>
                  <td className="mono"><b>{toFa(r.rate)}٪</b></td>
                  <td><button className="act-del" onClick={() => delRate(r.id)}>حذف</button></td>
                </tr>
              ))}
              {!rates.length && (
                <tr><td colSpan={3} style={{ color: "var(--muted)", textAlign: "center", padding: 20 }}>
                  هنوز درصد اختصاصی ثبت نشده — همه دسته‌بندی‌ها با درصد پیش‌فرض حساب می‌شوند.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
