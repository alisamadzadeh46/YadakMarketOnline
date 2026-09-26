// Server component wrapper for the product page.
//
// Two jobs, both of which must happen on the SERVER so a crawler that does not
// run JavaScript still sees them in the raw HTML:
//   1. real <title>/<meta description> per product (SEO)
//   2. the IranMarket (iranmarket.app) product meta tags
//
// The page itself is a client component ("use client") and therefore cannot
// export generateMetadata — hence this layout.
import type { Metadata } from "next";
import { SITE } from "@/lib/site";

const API =
  process.env.INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://web:8000/api";
const SITE_URL = SITE.url;

type Product = {
  name: string;
  sku: string;
  price: number;
  compare_at_price?: number | null;
  discount_percent?: number;
  stock?: number;
  in_stock?: boolean;
  warranty_text?: string;
  brand?: { name?: string } | string | null;
  category?: { name?: string; slug?: string } | null;
  short_description?: string;
  description?: string;
  rating_avg?: number;
  rating_count?: number;
  images?: { image: string }[];
};

/** The slug exactly once-encoded, whatever shape it arrived in.
 *
 * `params.slug` is the raw URL segment, i.e. ALREADY percent-encoded for a
 * Persian slug. Running encodeURIComponent() on it again produced
 * «%25D9%2584…» in the canonical, og:url and every JSON-LD url — links that
 * do not match the page they describe. Decoding first makes this idempotent.
 */
function canonicalSlug(raw: string): string {
  let decoded = raw;
  try {
    decoded = decodeURIComponent(raw);
  } catch {
    // Malformed escape sequence — fall back to the raw segment.
  }
  return encodeURIComponent(decoded);
}

async function getProduct(slug: string): Promise<Product | null> {
  try {
    const res = await fetch(
      `${API}/catalog/products/${encodeURIComponent(slug)}/`,
      { next: { revalidate: 900 } }
    );
    if (!res.ok) return null;
    return (await res.json()) as Product;
  } catch {
    return null;
  }
}


/** schema.org Product + Offer. Only fields we can state truthfully are
 *  emitted — a fabricated rating or a price on an unpriced part is exactly
 *  what gets rich results revoked. */
function productJsonLd(p: Product, slug: string) {
  const brand = typeof p.brand === "string" ? p.brand : p.brand?.name || "";
  const images = (p.images || []).map((i) =>
    `${SITE_URL}${new URL(i.image || "", SITE_URL).pathname}`
  );
  const inStock = (p.stock ?? 0) > 0 || p.in_stock;
  const data: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: p.name,
    sku: p.sku,
    description: (p.short_description || p.description || "").slice(0, 500) || undefined,
    image: images.length ? images : undefined,
    category: p.category?.name,
    url: `${SITE_URL}/product/${slug}`,
  };
  if (brand) data.brand = { "@type": "Brand", name: brand };
  if (p.sku) data.mpn = p.sku;
  if (p.price > 0) {
    data.offers = {
      "@type": "Offer",
      url: `${SITE_URL}/product/${slug}`,
      priceCurrency: "IRR",
      // schema.org wants the smallest currency unit; the store keeps Toman.
      price: String(p.price * 10),
      availability: inStock
        ? "https://schema.org/InStock"
        : "https://schema.org/OutOfStock",
      itemCondition: "https://schema.org/NewCondition",
      seller: { "@type": "Organization", name: SITE.name },
    };
  }
  if (p.rating_count && p.rating_count > 0 && p.rating_avg) {
    data.aggregateRating = {
      "@type": "AggregateRating",
      ratingValue: String(p.rating_avg),
      reviewCount: String(p.rating_count),
    };
  }
  return data;
}

function breadcrumbJsonLd(p: Product, slug: string) {
  const crumbs = [
    { name: "صفحه اصلی", item: SITE_URL },
    { name: "فروشگاه", item: `${SITE_URL}/shop` },
  ];
  if (p.category?.name) {
    crumbs.push({ name: p.category.name, item: `${SITE_URL}/shop?category=${p.category.slug || ""}` });
  }
  crumbs.push({ name: p.name, item: `${SITE_URL}/product/${slug}` });
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: crumbs.map((c, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: c.name,
      item: c.item,
    })),
  };
}

export async function generateMetadata(
  { params }: { params: Promise<{ slug: string }> }
): Promise<Metadata> {
  const { slug } = await params;
  const p = await getProduct(decodeURIComponent(slug));
  if (!p) return { title: `محصول | ${SITE.name}` };
  const safeSlug = canonicalSlug(slug);

  const brand = typeof p.brand === "string" ? p.brand : p.brand?.name || "";
  const parts = [p.name, brand && `برند ${brand}`, p.sku && `کد فنی ${p.sku}`]
    .filter(Boolean)
    .join(" — ");
  const url = `${SITE_URL}/product/${safeSlug}`;
  const description = `خرید عمده ${parts} با ضمانت اصالت از ${SITE.name}.`;
  const ogImages = (p.images || [])
    .slice(0, 4)
    .map((i) => (`${SITE_URL}${new URL(i.image || "", SITE_URL).pathname}`));

  return {
    title: `${p.name} | ${SITE.name}`,
    description,
    alternates: { canonical: url },
    keywords: [p.name, brand, p.sku, p.category?.name, "خرید عمده لوازم یدکی"]
      .filter(Boolean) as string[],
    // Social preview: without these, a link shared in Telegram/WhatsApp shows
    // the bare domain instead of the part and its photo.
    openGraph: {
      // Stays "website": Next validates this value at runtime and throws
      // «Invalid OpenGraph type: product», which silently drops the ENTIRE
      // metadata object — title, canonical and all — for the route. The
      // product semantics that actually drive rich results live in the
      // Product JSON-LD below, which is what Google reads.
      type: "website",
      url,
      siteName: SITE.name,
      title: `${p.name} | ${SITE.name}`,
      description,
      locale: "fa_IR",
      images: ogImages.length ? ogImages : undefined,
    },
    twitter: {
      card: ogImages.length ? "summary_large_image" : "summary",
      title: p.name,
      description,
      images: ogImages.length ? ogImages : undefined,
    },
    robots: { index: true, follow: true, "max-image-preview": "large" },
  };
}

export default async function ProductLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const p = await getProduct(decodeURIComponent(slug));
  if (!p) return <>{children}</>;
  const safeSlug = canonicalSlug(slug);

  // iranmarket.app reads the price BEFORE discount and the discount percent
  // separately, so send compare_at_price when there is one.
  const listPrice = p.compare_at_price && p.compare_at_price > p.price
    ? p.compare_at_price
    : p.price;
  const available = (p.stock ?? 0) > 0 || p.in_stock ? 1 : 0;
  const imageList = (p.images || []).map((i) =>
    `${SITE_URL}${new URL(i.image || "", SITE_URL).pathname}`
  );
  const images = imageList.join(",");
  const guarantee = p.warranty_text || "ضمانت اصالت کالا";

  return (
    <>
      {/* Torob (torob.com) — reads name="..." tags, and unlike IranMarket wants
          the CURRENT selling price in product_price with the pre-discount one
          in product_old_price. Different attribute (name vs property), so the
          two feeds coexist without either crawler misreading the other's. */}
      <meta name="product_id" content={p.sku} />
      <meta name="product_name" content={p.name} />
      <meta name="product_price" content={String(p.price)} />
      {listPrice > p.price && (
        <meta name="product_old_price" content={String(listPrice)} />
      )}
      <meta name="availability" content={available ? "instock" : "outofstock"} />
      <meta name="guarantee" content={guarantee} />

      {/* IranMarket (iranmarket.app) — hoisted into <head> by Next.js */}
      <meta property="product_title" content={p.name} />
      <meta property="product_price" content={String(listPrice)} />
      <meta property="product_id" content={p.sku} />
      <meta property="product_available" content={String(available)} />
      <meta property="product_off" content={String(p.discount_percent || 0)} />
      {p.category?.name && (
        <meta property="product_category" content={p.category.name} />
      )}
      {images && <meta property="product_image" content={images} />}
      <meta property="product_guarantee" content={guarantee} />

      {/* Structured data. This is what earns the price/availability/rating
          chips under a Google result — meta tags alone never produce them. */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(productJsonLd(p, safeSlug)) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd(p, safeSlug)) }}
      />
      {children}
    </>
  );
}
