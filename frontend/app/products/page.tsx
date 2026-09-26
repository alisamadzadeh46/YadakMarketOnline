// Plain server-rendered archive of every product.
//
// Price-comparison crawlers (iranmarket.app and friends) explicitly require a
// products page that works WITHOUT JavaScript — /shop is a client component
// with filters, so it cannot serve that purpose. This page is a pure server
// component: the full list is in the HTML source.
import Link from "next/link";
import type { Metadata } from "next";
import { SITE } from "@/lib/site";

const API =
  process.env.INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://web:8000/api";

export const revalidate = 3600;

export const metadata: Metadata = {
  title: `آرشیو همه محصولات | ${SITE.name}`,
  description: `فهرست کامل لوازم یدکی موجود در ${SITE.name} با قیمت عمده.`,
};

type Product = {
  id: number;
  name: string;
  slug: string;
  sku: string;
  brand?: string;
  price: number;
  in_stock?: boolean;
};

async function fetchAllProducts(cap = 5000): Promise<Product[]> {
  const out: Product[] = [];
  for (let page = 1; out.length < cap; page++) {
    let data: any;
    try {
      const res = await fetch(
        // Torob requires this archive to be ordered newest-first.
        `${API}/catalog/products/?page_size=60&ordering=-created_at&page=${page}`,
        { next: { revalidate: 3600 } }
      );
      if (!res.ok) break;
      data = await res.json();
    } catch {
      break;
    }
    const rows = data.results || data;
    if (!Array.isArray(rows) || rows.length === 0) break;
    out.push(...rows);
    if (!data.next) break;
  }
  return out;
}

const FA = "۰۱۲۳۴۵۶۷۸۹";
const toFa = (n: number | string) => String(n).replace(/\d/g, (d) => FA[+d]);
const money = (n: number) => toFa((n ?? 0).toLocaleString("en-US"));

export default async function ProductsArchive() {
  const products = await fetchAllProducts();

  return (
    <div className="view">
      <h1 style={{ fontSize: 24, fontWeight: 800, marginBottom: 6 }}>
        آرشیو همه محصولات
      </h1>
      <p style={{ color: "var(--muted)", fontSize: 13.5, marginBottom: 18 }}>
        فهرست کامل {toFa(products.length)} کالای موجود در {SITE.name}.
      </p>

      <div className="panel tablewrap">
        <table className="tbl" style={{ minWidth: 620 }}>
          <thead>
            <tr>
              <th>نام محصول</th>
              <th>برند</th>
              <th>کد فنی</th>
              <th>قیمت (تومان)</th>
              <th>وضعیت</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.id}>
                <td className="wrap">
                  <Link href={`/product/${encodeURIComponent(p.slug)}`}>
                    {toFa(p.name)}
                  </Link>
                </td>
                <td>{p.brand || "—"}</td>
                <td className="mono">{toFa(p.sku)}</td>
                <td className="mono">{p.price > 0 ? money(p.price) : "تماس بگیرید"}</td>
                <td>
                  <span className={`badge ${p.in_stock ? "green" : "red"}`}>
                    {p.in_stock ? "موجود" : "ناموجود"}
                  </span>
                </td>
              </tr>
            ))}
            {!products.length && (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", color: "var(--muted)", padding: 24 }}>
                  فهرست محصولات در دسترس نیست.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
