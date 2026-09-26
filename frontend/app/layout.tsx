import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import Toaster from "@/components/Toaster";
import TopLoader from "@/components/TopLoader";
import FormValidator from "@/components/FormValidator";
import { SITE } from "@/lib/site";

// Vazirmatn ships with the repo (app/fonts/*.woff2) and is loaded with
// next/font/local. next/font/google would reach out to fonts.googleapis.com at
// BUILD time, which fails on a server without free access to Google — the build
// breaks and nothing deploys. Local files keep both the build and the browser
// fully offline-safe.
// next/font parses this call statically, so every entry has to be a literal —
// no loops, no template strings, no shared constants.
// Only the weights the stylesheet actually uses are declared: next/font
// preloads every face listed here, so shipping 300/500/900 (which nothing
// referenced) cost ~240KB of font before first paint for nothing.
const vazir = localFont({
  src: [
    { path: "./fonts/vazirmatn-400-arabic.woff2", weight: "400", style: "normal" },
    { path: "./fonts/vazirmatn-400-latin.woff2", weight: "400", style: "normal" },
    { path: "./fonts/vazirmatn-600-arabic.woff2", weight: "600", style: "normal" },
    { path: "./fonts/vazirmatn-600-latin.woff2", weight: "600", style: "normal" },
    { path: "./fonts/vazirmatn-700-arabic.woff2", weight: "700", style: "normal" },
    { path: "./fonts/vazirmatn-700-latin.woff2", weight: "700", style: "normal" },
    { path: "./fonts/vazirmatn-800-arabic.woff2", weight: "800", style: "normal" },
    { path: "./fonts/vazirmatn-800-latin.woff2", weight: "800", style: "normal" },
  ],
  variable: "--font-vazir",
  display: "swap",
});

const SITE_URL = SITE.url;

const SITE_TITLE = `${SITE.name} | ${SITE.tagline}`;
const SITE_DESC =
  "خرید عمده لوازم یدکی خودرو با ضمانت اصالت، قیمت پلکانی و تحویل سریع برای فروشگاه‌ها و تعمیرگاه‌ها.";

export const metadata: Metadata = {
  // metadataBase resolves every relative URL below (and in child pages) against
  // the real domain, so a shared link never points at localhost.
  metadataBase: new URL(SITE_URL),
  title: SITE_TITLE,
  description: SITE_DESC,
  alternates: { canonical: "/" },
  // Without these, a link to the home page shared in Telegram/WhatsApp showed
  // the bare domain and no image, while product pages previewed properly.
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: SITE.name,
    title: SITE_TITLE,
    description: SITE_DESC,
    locale: "fa_IR",
    images: [{ url: "/logo-full.png", width: 700, height: 667, alt: SITE.name }],
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_TITLE,
    description: SITE_DESC,
    images: ["/logo-full.png"],
  },
  robots: { index: true, follow: true },
  // eNamad (e-trust seal) ownership meta tag — backup to the /<code>.txt file.
  other: SITE.trust.enamadMeta ? { enamad: SITE.trust.enamadMeta } : {},
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fa" dir="rtl" className={vazir.variable}>
      <head>
        {/* Site-level structured data: identifies the business to Google and
            enables the sitelinks search box. Static, so it costs nothing. */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "Organization",
            name: SITE.name,
            url: SITE_URL,
            logo: `${SITE_URL}/logo-full.png`,
            description: SITE.tagline,
            ...((SITE.contact.city || SITE.contact.address) && {
              address: {
                "@type": "PostalAddress",
                addressLocality: SITE.contact.city,
                addressCountry: "IR",
                streetAddress: SITE.contact.address,
              },
            }),
            ...(SITE.contact.phones.length > 0 && {
              contactPoint: {
                "@type": "ContactPoint",
                telephone: SITE.contact.phones[0].dial,
                contactType: "customer service",
                areaServed: "IR",
                availableLanguage: ["fa"],
              },
            }),
            // sameAs lists the profiles Google should treat as this business.
            sameAs: [SITE.social.telegram, SITE.social.bale].filter(Boolean),
          }) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "WebSite",
            name: SITE.name,
            url: SITE_URL,
            inLanguage: "fa-IR",
            potentialAction: {
              "@type": "SearchAction",
              target: { "@type": "EntryPoint", urlTemplate: `${SITE_URL}/shop?q={search_term_string}` },
              "query-input": "required name=search_term_string",
            },
          }) }}
        />
      </head>
      <body>
        <AuthProvider>
          <TopLoader />
          <FormValidator />
          <Header />
          <main className="wrap">{children}</main>
          <Footer />
          <Toaster />
        </AuthProvider>
      </body>
    </html>
  );
}
