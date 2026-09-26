"use client";
// The BUYER area. A supplier/admin/shopkeeper/partner has their own panel, so
// this section redirects them there instead of giving the same person two
// rival "my account" homes (/account and /panel/…).
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import PanelLayout from "@/components/PanelLayout";
import { useAuth } from "@/lib/auth";
import { homeForRole } from "@/lib/roles";

const ITEMS = [
  { href: "/account", label: "پیشخوان" },
  { href: "/account/orders", label: "سفارش‌های من" },
  { href: "/account/addresses", label: "آدرس‌ها" },
  { href: "/account/favorites", label: "علاقه‌مندی‌ها" },
  { href: "/account/rare-parts", label: "قطعات نایاب" },
  { href: "/account/profile", label: "پروفایل" },
];

export default function AccountLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading || !user) return;
    const home = homeForRole(user.role);
    if (home !== "/account") router.replace(home);
  }, [user, loading, router]);

  return <PanelLayout items={ITEMS}>{children}</PanelLayout>;
}
