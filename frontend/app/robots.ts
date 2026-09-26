import type { MetadataRoute } from "next";

const SITE = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3010";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // Private/panel areas must stay out of search results.
        disallow: ["/panel/", "/account", "/cart", "/checkout", "/order/", "/login", "/register", "/forgot-password"],
      },
    ],
    sitemap: `${SITE}/sitemap.xml`,
  };
}
