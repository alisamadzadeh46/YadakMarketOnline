"use client";
import PanelLayout from "@/components/PanelLayout";
import NewOrderAlert from "@/components/NewOrderAlert";

// adminOnly items are the site-wide controls only the owner (admin) should
// touch. A regular supplier sees just their own store: orders, their products,
// shop approvals, coupons and credit. Categories/blog/slider/comms/settings and
// the revenue panel stay with the owner. PanelLayout filters by role.
const ITEMS = [
  { href: "/panel/supplier", label: "پیشخوان" },
  { href: "/panel/supplier/reports", label: "گزارش فروش" },
  { href: "/panel/supplier/earnings", label: "درآمد و پورسانت" },
  { href: "/panel/supplier/orders", label: "سفارش‌ها" },
  { href: "/panel/supplier/rare-parts", label: "قطعه نایاب" },
  { href: "/panel/supplier/shops", label: "فروشگاه‌ها و احراز هویت", adminOnly: true },
  { href: "/panel/supplier/products", label: "محصولات" },
  { href: "/panel/supplier/coupons", label: "کدهای تخفیف" },
  { href: "/panel/supplier/credit", label: "اعتبار و تسویه", adminOnly: true },
  { href: "/panel/supplier/categories", label: "دسته‌بندی‌ها", adminOnly: true },
  { href: "/panel/supplier/blog", label: "بلاگ و سئو", adminOnly: true },
  { href: "/panel/supplier/slides", label: "اسلایدر", adminOnly: true },
  { href: "/panel/partner", label: "درآمد من (پورسانت)", adminOnly: true },
  { href: "/panel/supplier/sms", label: "ارتباطات (پیامک/پیام)", adminOnly: true },
  { href: "/panel/supplier/settings", label: "تنظیمات", adminOnly: true },
  { href: "/panel/supplier/profile", label: "پروفایل من" },
];

export default function SupplierLayout({ children }: { children: React.ReactNode }) {
  return (
    <PanelLayout items={ITEMS} requireRole={["supplier", "admin"]}>
      <NewOrderAlert />
      {children}
    </PanelLayout>
  );
}
