// The shop page itself is a client component (filters, sorting, URL state), so
// it cannot export metadata — which meant it inherited the ROOT layout's title
// and description verbatim. Two of the site's most important pages were
// competing for the same query with identical meta. This layout gives the shop
// its own identity without touching the interactive page.
import type { Metadata } from "next";
import { SITE } from "@/lib/site";

const TITLE = `فروشگاه عمده لوازم یدکی خودرو | ${SITE.name}`;
const DESC =
  "جست‌وجو و خرید عمده لوازم یدکی خودرو بر اساس خودرو، برند و دسته‌بندی — با قیمت عمده، ضمانت اصالت و ارسال به سراسر کشور.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESC,
  alternates: { canonical: "/shop" },
  openGraph: {
    type: "website",
    url: "/shop",
    siteName: SITE.name,
    title: TITLE,
    description: DESC,
    locale: "fa_IR",
  },
  twitter: { card: "summary_large_image", title: TITLE, description: DESC },
};

export default function ShopLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
