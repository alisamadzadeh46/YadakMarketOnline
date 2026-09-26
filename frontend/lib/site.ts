// Business identity, contact details and trust badges of this deployment.
//
// Everything here comes from NEXT_PUBLIC_* environment variables, so no real
// phone number, address, social account or trust-seal code lives in the
// source code. Next.js inlines these values at build time (see .env.example
// and frontend/Dockerfile.prod). Optional values that are not configured make
// the matching UI element disappear instead of rendering a broken link.

function list(value: string | undefined): string[] {
  return (value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export type ContactPhone = {
  /** Digits dialled by the `tel:` link, e.g. 02100000000. */
  dial: string;
  /** Human readable form shown on the page. */
  display: string;
};

/** "02100000000|021-0000 0000" -> { dial, display }; the display part is optional. */
function parsePhone(entry: string): ContactPhone {
  const [dial, display] = entry.split("|").map((part) => part.trim());
  return { dial: dial.replace(/[^\d+]/g, ""), display: display || dial };
}

export const SITE = {
  name: process.env.NEXT_PUBLIC_SITE_NAME || "یدک مارکت آنلاین",
  shortName: process.env.NEXT_PUBLIC_SITE_SHORT_NAME || "یدک مارکت",
  tagline: process.env.NEXT_PUBLIC_SITE_TAGLINE || "پخش عمده لوازم یدکی خودرو",
  url: (process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000").replace(/\/$/, ""),

  /** Seller shown on product pages and invoices when a product has no supplier profile. */
  sellerName: process.env.NEXT_PUBLIC_SELLER_NAME || "",

  contact: {
    phones: list(process.env.NEXT_PUBLIC_CONTACT_PHONES).map(parsePhone),
    city: process.env.NEXT_PUBLIC_CONTACT_CITY || "",
    address: process.env.NEXT_PUBLIC_CONTACT_ADDRESS || "",
    hours: process.env.NEXT_PUBLIC_CONTACT_HOURS || "شنبه تا پنجشنبه ۹ تا ۱۸",
  },

  social: {
    telegram: process.env.NEXT_PUBLIC_TELEGRAM_URL || "",
    bale: process.env.NEXT_PUBLIC_BALE_URL || "",
  },

  trust: {
    /** eNamad badge: the `id` and `Code` query values of the official snippet. */
    enamadId: process.env.NEXT_PUBLIC_ENAMAD_ID || "",
    enamadCode: process.env.NEXT_PUBLIC_ENAMAD_CODE || "",
    /** eNamad domain-ownership meta tag value. */
    enamadMeta: process.env.NEXT_PUBLIC_ENAMAD_META || "",
    bitpayCertificateUrl: process.env.NEXT_PUBLIC_BITPAY_TRUST_URL || "",
    zarinpalTrustUrl: process.env.NEXT_PUBLIC_ZARINPAL_TRUST_URL || "",
  },
} as const;

/** The site host without protocol, for printed material such as invoices. */
export const SITE_HOST = SITE.url.replace(/^https?:\/\//, "");

/** First configured phone, used by "call the seller" buttons. */
export const PRIMARY_PHONE: ContactPhone | undefined = SITE.contact.phones[0];

/** City and address joined for one-line display. */
export const FULL_ADDRESS = [SITE.contact.city, SITE.contact.address].filter(Boolean).join(" - ");
