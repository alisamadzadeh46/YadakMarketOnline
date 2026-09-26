import type { MetadataRoute } from "next";

// Server-side data source: inside Docker the backend is reachable as "web";
// override with INTERNAL_API_URL in other environments.
const API =
  process.env.INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://web:8000/api";
const SITE = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3010";

async function fetchAll(path: string): Promise<any[]> {
  try {
    const res = await fetch(`${API}${path}`, { next: { revalidate: 3600 } });
    if (!res.ok) return [];
    const data = await res.json();
    return data.results || data;
  } catch {
    return [];
  }
}

/** Walk every page of a paginated list endpoint.
 *
 * The API caps page_size at 60, so one request could never cover the whole
 * catalogue — the sitemap used to silently ship only the first page.
 */
async function fetchPaginated(path: string, cap = 5000): Promise<any[]> {
  const out: any[] = [];
  for (let page = 1; out.length < cap; page++) {
    const sep = path.includes("?") ? "&" : "?";
    let data: any;
    try {
      const res = await fetch(`${API}${path}${sep}page=${page}`, {
        next: { revalidate: 3600 },
      });
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

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticPages: MetadataRoute.Sitemap = [
    { url: `${SITE}/`, changeFrequency: "daily", priority: 1 },
    { url: `${SITE}/shop`, changeFrequency: "daily", priority: 0.9 },
    { url: `${SITE}/products`, changeFrequency: "daily", priority: 0.9 },
    { url: `${SITE}/blog`, changeFrequency: "weekly", priority: 0.7 },
    { url: `${SITE}/rare-part`, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE}/pages/guide`, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE}/pages/cooperation`, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE}/pages/shipping`, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE}/pages/contact`, changeFrequency: "monthly", priority: 0.4 },
    { url: `${SITE}/pages/terms`, changeFrequency: "yearly", priority: 0.3 },
    { url: `${SITE}/pages/privacy`, changeFrequency: "yearly", priority: 0.3 },
  ];

  const [products, posts, categories] = await Promise.all([
    fetchPaginated("/catalog/products/?page_size=60"),
    fetchAll("/blog/posts/"),
    // Category listings are real landing pages ("bumpers and parts", "fenders" …)
    // and were missing entirely, so the only indexable depth was the handful
    // of published products.
    fetchAll("/catalog/categories/"),
  ]);

  return [
    ...staticPages,
    ...categories.map((c: any) => ({
      url: `${SITE}/shop?category=${c.id}`,
      changeFrequency: "weekly" as const,
      priority: 0.7,
    })),
    ...products.map((p: any) => ({
      url: `${SITE}/product/${encodeURIComponent(p.slug)}`,
      changeFrequency: "weekly" as const,
      priority: 0.8,
    })),
    ...posts.map((a: any) => ({
      url: `${SITE}/blog/${encodeURIComponent(a.slug)}`,
      changeFrequency: "monthly" as const,
      priority: 0.6,
    })),
  ];
}
