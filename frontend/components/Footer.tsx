import Link from "next/link";
import { SITE } from "@/lib/site";
import NewsletterForm from "./NewsletterForm";

// Current Solar Hijri year for the copyright line, e.g. 1405 in Persian digits.
const COPYRIGHT_YEAR = new Intl.DateTimeFormat("fa-IR-u-ca-persian", { year: "numeric" }).format(new Date());

/** Escape a value for use inside a single-quoted URL attribute. */
function urlParam(value: string): string {
  return encodeURIComponent(value).replace(/'/g, "%27");
}

/** eNamad's official badge snippet, kept byte-for-byte in the shape its validator expects. */
function enamadMarkup(id: string, code: string): string {
  const query = `id=${urlParam(id)}&Code=${urlParam(code)}`;
  return (
    `<a referrerpolicy='origin' target='_blank' href='https://trustseal.enamad.ir/?${query}'>` +
    `<img referrerpolicy='origin' src='https://trustseal.enamad.ir/logo.aspx?${query}' ` +
    `alt='نماد اعتماد الکترونیکی' style='cursor:pointer;height:96px' code='${urlParam(code)}'></a>`
  );
}

export default function Footer() {
  return (
    <footer className="site">
      <div className="wrap ftop">
        <div>
          <div className="logo" style={{ marginBottom: 14 }}>
            <div className="mk"><img src="/logo-mark.png" alt={SITE.name} className="mk-img" /></div>
            <div>
              <div className="nm" style={{ color: "#fff" }}>{SITE.name}</div>
              <div className="sb mono">AUTO PARTS · B2B</div>
            </div>
          </div>
          <p style={{ fontSize: 13.5, lineHeight: 2, color: "#C9BEE3" }}>
            پلتفرم پخش عمده لوازم یدکی خودرو با بیش از ۱۲٬۰۰۰ کد کالای اصل از برندهای معتبر
            جهانی. تأمین مطمئن برای فروشگاه‌ها و تعمیرگاه‌ها با قیمت پلکانی و ضمانت اصالت.
          </p>
          <div className="fsocial">
            {SITE.social.telegram && (
              <a href={SITE.social.telegram} target="_blank" rel="noopener noreferrer" title="تلگرام" aria-label="تلگرام">
                <svg width="19" height="19" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M21.7 3.4 2.9 10.6c-1.1.4-1.1 1.1-.2 1.4l4.7 1.5 1.8 5.5c.2.6.1.9.8.9.5 0 .7-.2 1-.5l2.3-2.2 4.8 3.5c.9.5 1.5.2 1.7-.8l3.1-14.6c.3-1.2-.5-1.8-1.2-1.5zM7.7 13.2l10.4-6.6c.5-.3.9-.1.6.2l-8.9 8-.3 3.7-1.8-5.3z" />
                </svg>
              </a>
            )}
            {SITE.social.bale && (
              <a href={SITE.social.bale} target="_blank" rel="noopener noreferrer" title="بله" aria-label="بله">
                <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 11.5a8.4 8.4 0 0 1-9 8.4 8.6 8.6 0 0 1-3.5-.7L3 21l1.8-4.4A8.4 8.4 0 1 1 21 11.5z" />
                </svg>
              </a>
            )}
          </div>
        </div>
        <div>
          <h4>دسترسی سریع</h4>
          <ul>
            <li><Link href="/">صفحه اصلی</Link></li>
            <li><Link href="/shop">فروشگاه</Link></li>
            <li><Link href="/blog">وبلاگ فنی</Link></li>
            <li><Link href="/rare-part">درخواست قطعه نایاب</Link></li>
            <li><Link href="/login">ورود همکاران</Link></li>
          </ul>
        </div>
        <div>
          <h4>پشتیبانی</h4>
          <ul>
            <li><Link href="/pages/guide">راهنمای خرید عمده</Link></li>
            <li><Link href="/pages/cooperation">شرایط همکاری فروش</Link></li>
            <li><Link href="/pages/shipping">رویه ارسال و مرجوعی</Link></li>
            <li><Link href="/pages/contact">تماس با ما</Link></li>
          </ul>
        </div>
        <div>
          <h4>خبرنامه</h4>
          <p style={{ fontSize: 13.5, lineHeight: 2, color: "#C9BEE3", margin: 0 }}>
            {/* dir=ltr keeps the digits from being reordered inside RTL text. */}
            {SITE.contact.phones.map((phone) => (
              <span key={phone.dial}>
                📞 <a href={`tel:${phone.dial}`} className="mono" dir="ltr">{phone.display}</a><br />
              </span>
            ))}
            با انتشار هر مقاله جدید، باخبر شوید.
          </p>
          <NewsletterForm />
        </div>
      </div>
      {/* Trust badges. Each one is rendered only when it is configured. */}
      <div className="ftrust">
        {SITE.trust.enamadId && SITE.trust.enamadCode && (
          // Raw markup so eNamad's exact <a><img> structure is preserved for its validator.
          <div dangerouslySetInnerHTML={{ __html: enamadMarkup(SITE.trust.enamadId, SITE.trust.enamadCode) }} />
        )}
        {SITE.trust.bitpayCertificateUrl && (
          <a href={SITE.trust.bitpayCertificateUrl} target="_blank" rel="noopener">
            <img src="/bitpay-trust.svg" alt="نماد اعتماد بیت‌پی" style={{ height: 96, width: "auto" }} />
          </a>
        )}
        {/* ZarinPal's badge is served from our own /public rather than their CDN:
            no extra img-src entry in the CSP, and it can't vanish if their CDN
            is unreachable from inside Iran. The link still points at ZarinPal's
            trust page, which is what actually proves the merchant is real. */}
        {SITE.trust.zarinpalTrustUrl && (
          <a href={SITE.trust.zarinpalTrustUrl} target="_blank" rel="noopener">
            <img src="/zarinpal-trust.png" alt="پرداخت امن با زرین‌پال" style={{ height: 96, width: "auto" }} />
          </a>
        )}
      </div>
      <div className="fbot">
        <span>© {COPYRIGHT_YEAR} {SITE.name} — تمامی حقوق محفوظ است.</span>
        <span className="fsep">·</span>
        <Link href="/pages/terms">شرایط استفاده</Link>
        <span className="fsep">·</span>
        <Link href="/pages/privacy">حریم خصوصی</Link>
      </div>
      {/* Developer credit. rel=noopener stops the opened tab from reaching back
          through window.opener; noreferrer keeps our URL out of their logs. */}
      <div className="fcredit">
        طراحی و توسعه توسط{" "}
        <a
          href="https://github.com/alisamadzadeh46"
          target="_blank"
          rel="noopener noreferrer"
          dir="ltr"
        >
          alisamadzadeh
        </a>
      </div>
    </footer>
  );
}
