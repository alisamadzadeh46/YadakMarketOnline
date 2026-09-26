"use client";
import PanelLayout from "@/components/PanelLayout";

// The revenue-share partner manages their commission; payment gateway,
// payment methods and checkout costs are site-wide settings that the backend
// only accepts from the site owner, so they are hidden from a plain partner.
const ITEMS = [
  { href: "/panel/partner", label: "پیشخوان درآمد" },
  { href: "/panel/partner/ledger", label: "دفتر پورسانت" },
  { href: "/panel/partner/settings", label: "تنظیم درصد" },
  { href: "/panel/partner/gateway", label: "درگاه پرداخت آنلاین", adminOnly: true },
  { href: "/panel/partner/payment-methods", label: "روش پرداخت فروشگاه‌ها", adminOnly: true },
  { href: "/panel/partner/checkout", label: "مالیات و هزینه ارسال", adminOnly: true },
];

export default function PartnerLayout({ children }: { children: React.ReactNode }) {
  return (
    <PanelLayout items={ITEMS} requireRole={["partner", "admin"]}>
      {children}
    </PanelLayout>
  );
}
