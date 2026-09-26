"use client";
// Trust-building content the homepage lacked: the real purchase steps (facts
// about how this specific store works, not marketing fluff) plus the actual
// part brands carried on the site — pulled live, never invented.
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

type Brand = { id: number; name: string };

const STEPS = [
  { n: "۱", t: "انتخاب و افزودن به سبد", s: "قطعه موردنظر را با قیمت عمده به سبد اضافه کنید." },
  { n: "۲", t: "ثبت آدرس و روش پرداخت", s: "کارت‌به‌کارت، پرداخت آنلاین یا خرید اعتباری (فروشگاه‌های تأییدشده)." },
  { n: "۳", t: "تایید پرداخت", s: "فیش یا تراکنش آنلاین در کوتاه‌ترین زمان بررسی و تایید می‌شود." },
  { n: "۴", t: "ارسال سریع", s: "بسته‌بندی و ارسال به سراسر کشور با پست پیشتاز یا تیپاکس." },
];

export default function TrustSection() {
  const [brands, setBrands] = useState<Brand[]>([]);

  useEffect(() => {
    api.get<Brand[]>("/catalog/brands/", { auth: false }).then(setBrands).catch(() => {});
  }, []);

  return (
    <section className="trust-sec">
      <div className="sec-head"><h2><span className="bar" style={{ background: "linear-gradient(var(--purple),var(--orange))" }} />مراحل خرید عمده</h2></div>
      <div className="steps-row">
        {STEPS.map((s) => (
          <div className="step" key={s.n}>
            <div className="step-n mono">{s.n}</div>
            <div><b>{s.t}</b><span>{s.s}</span></div>
          </div>
        ))}
      </div>

      {brands.length > 0 && (
        <div className="brandband">
          <span className="bb-label">برندهای موجود در فروشگاه:</span>
          <div className="bb-chips">
            {brands.map((b) => (
              <Link key={b.id} href={`/shop?brand=${b.id}`} className="bb-chip">{b.name}</Link>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
