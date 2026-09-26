"use client";
import PanelLayout from "@/components/PanelLayout";

const ITEMS = [
  { href: "/panel/shop", label: "پیشخوان" },
  { href: "/panel/shop/orders", label: "خریدها" },
  { href: "/panel/shop/accounting", label: "حسابداری" },
  { href: "/panel/shop/addresses", label: "آدرس‌ها" },
  { href: "/panel/shop/favorites", label: "علاقه‌مندی‌ها" },
  { href: "/panel/shop/rare-parts", label: "قطعات نایاب" },
  { href: "/panel/shop/profile", label: "پروفایل و احراز هویت" },
];

export default function ShopPanelLayout({ children }: { children: React.ReactNode }) {
  return <PanelLayout items={ITEMS} requireRole={["shopkeeper", "admin"]}>{children}</PanelLayout>;
}
