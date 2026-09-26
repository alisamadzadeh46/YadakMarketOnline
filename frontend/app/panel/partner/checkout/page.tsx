"use client";
// Site-wide VAT + flat shipping cost — owner-only. Snapshotted onto every
// order at checkout time, so changing this never rewrites past orders.
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import PriceField from "@/components/PriceField";
import { toast } from "@/lib/ui";
import { money } from "@/lib/format";

type Setting = { vat_percent: string; shipping_cost: number; updated_at: string };

const SAMPLE = 5_000_000;

export default function CheckoutSettingsPage() {
  const [s, setS] = useState<Setting | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => { api.get<Setting>("/orders/checkout-settings/").then(setS).catch(() => {}); }, []);

  if (!s) return <div className="skel" style={{ height: 300 }} />;
  const set = (patch: Partial<Setting>) => setS({ ...s, ...patch });

  const save = async () => {
    setSaving(true);
    try {
      const data = await api.patch<Setting>("/orders/checkout-settings/", {
        vat_percent: s.vat_percent,
        shipping_cost: s.shipping_cost,
      });
      setS(data);
      toast("تنظیمات مالی ذخیره شد ✓");
    } catch (e) {
      toast(errorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <h2 style={{ margin: "0 0 6px", fontSize: 19, fontWeight: 800 }}>مالیات و هزینه ارسال</h2>
      <p style={{ margin: "0 0 16px", fontSize: 13, color: "var(--muted)", lineHeight: 1.9 }}>
        این مقادیر روی هر سفارش جدید اعمال می‌شود؛ سفارش‌های قبلی تغییر نمی‌کنند.
      </p>

      <div className="cols-2">
        <div className="panel">
          <b>مالیات بر ارزش‌افزوده</b>
          <div className="field" style={{ marginTop: 12 }}>
            <label>درصد مالیات</label>
            <input className="inp mono" type="number" step="0.5" min={0} max={100} value={s.vat_percent}
              onChange={(e) => set({ vat_percent: e.target.value })} />
          </div>
          <div className="specrow">
            <span>مثال: روی خرید {money(SAMPLE)} تومانی</span>
            <b className="mono" style={{ color: "var(--orange)" }}>
              {money(Math.round(SAMPLE * Number(s.vat_percent) / 100))} تومان
            </b>
          </div>
        </div>

        <div className="panel">
          <b>هزینه ارسال</b>
          <div className="field" style={{ marginTop: 12 }}>
            <label>هزینه ثابت ارسال (تومان)</label>
            <PriceField className="inp mono" value={String(s.shipping_cost ?? "")}
              onChange={(v) => set({ shipping_cost: v === "" ? 0 : +v })} />
          </div>
          <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.9 }}>
            صفر یعنی ارسال رایگان. خریدهای اعتباری مشمول هزینه ارسال نمی‌شوند.
          </p>
        </div>
      </div>

      <button className="btn btn-purple" style={{ height: 46, padding: "0 26px", marginTop: 16 }} disabled={saving} onClick={save}>
        {saving ? "در حال ذخیره…" : "ذخیره تنظیمات"}
      </button>
    </div>
  );
}
