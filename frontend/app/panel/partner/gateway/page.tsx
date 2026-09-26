"use client";
// Online payment gateway config — BitPay / ZarinPal merchant credentials.
// Owner-only (IsPaymentGatewayAdmin on the backend); switching the "active gateway"
// takes effect on the next checkout, no redeploy needed.
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import NiceSelect from "@/components/NiceSelect";

type Setting = {
  active_gateway: "none" | "bitpay" | "zarinpal";
  bitpay_api_key: string;
  bitpay_sandbox: boolean;
  zarinpal_merchant_id: string;
  zarinpal_sandbox: boolean;
  is_configured: boolean;
  updated_at: string;
};

export default function PaymentGatewaySettingsPage() {
  const [s, setS] = useState<Setting | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => { api.get<Setting>("/payments/settings/").then(setS).catch(() => {}); }, []);

  if (!s) return <div className="skel" style={{ height: 380 }} />;
  const set = (patch: Partial<Setting>) => setS({ ...s, ...patch });

  const save = async () => {
    setSaving(true);
    try {
      const data = await api.patch<Setting>("/payments/settings/", {
        active_gateway: s.active_gateway,
        bitpay_api_key: s.bitpay_api_key,
        bitpay_sandbox: s.bitpay_sandbox,
        zarinpal_merchant_id: s.zarinpal_merchant_id,
        zarinpal_sandbox: s.zarinpal_sandbox,
      });
      setS(data);
      toast("تنظیمات درگاه ذخیره شد ✓");
    } catch (e) {
      toast(errorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <h2 style={{ margin: "0 0 6px", fontSize: 19, fontWeight: 800 }}>درگاه پرداخت آنلاین</h2>
      <p style={{ margin: "0 0 16px", fontSize: 13, color: "var(--muted)", lineHeight: 1.9 }}>
        مشتری هنگام پرداخت آنلاین به همین درگاه هدایت می‌شود. فقط یکی از دو درگاه در هر لحظه فعال است.
      </p>

      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="between" style={{ marginBottom: 4 }}>
          <b>وضعیت درگاه</b>
          <span className={`badge ${s.is_configured && s.active_gateway !== "none" ? "green" : "red"}`}>
            {s.active_gateway === "none" ? "غیرفعال" : s.is_configured ? "آماده دریافت پرداخت" : "کد/مرچنت وارد نشده"}
          </span>
        </div>
        <div className="field" style={{ marginTop: 10 }}>
          <label>درگاه فعال</label>
          <NiceSelect value={s.active_gateway} onChange={(v) => set({ active_gateway: v as Setting["active_gateway"] })}
            options={[
              { value: "none", label: "غیرفعال" },
              { value: "bitpay", label: "بیت‌پی" },
              { value: "zarinpal", label: "زرین‌پال" },
            ]} />
        </div>
      </div>

      <div className="cols-2">
        <div className="panel">
          <b>بیت‌پی</b>
          <div className="field" style={{ marginTop: 12 }}>
            <label>کد API</label>
            <input className="inp mono" dir="ltr" value={s.bitpay_api_key} placeholder="xxxxx-xxxxx-xxxxx-xxxxxxxxxxxxxxxxxxxx"
              onChange={(e) => set({ bitpay_api_key: e.target.value })} />
          </div>
          <label className="specrow" style={{ cursor: "pointer" }}>
            <span>حالت آزمایشی (sandbox بیت‌پی)</span>
            <input type="checkbox" checked={s.bitpay_sandbox} onChange={(e) => set({ bitpay_sandbox: e.target.checked })} />
          </label>
        </div>

        <div className="panel">
          <b>زرین‌پال</b>
          <div className="field" style={{ marginTop: 12 }}>
            <label>مرچنت کد</label>
            <input className="inp mono" dir="ltr" value={s.zarinpal_merchant_id} placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              onChange={(e) => set({ zarinpal_merchant_id: e.target.value })} />
          </div>
          <label className="specrow" style={{ cursor: "pointer" }}>
            <span>حالت آزمایشی (sandbox زرین‌پال)</span>
            <input type="checkbox" checked={s.zarinpal_sandbox} onChange={(e) => set({ zarinpal_sandbox: e.target.checked })} />
          </label>
        </div>
      </div>

      <button className="btn btn-purple" style={{ height: 46, padding: "0 26px", marginTop: 16 }} disabled={saving} onClick={save}>
        {saving ? "در حال ذخیره…" : "ذخیره تنظیمات"}
      </button>
    </div>
  );
}
