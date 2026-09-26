"use client";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, errorMessage } from "@/lib/api";
import { addToCart, toast } from "@/lib/ui";
import { useAuth } from "@/lib/auth";
import { faDate, money, rating, toFa } from "@/lib/format";
import { ICart, IPart, IShield, IStar, ITruck } from "@/components/Icon";
import StarInput from "@/components/StarInput";
import ProductRow from "@/components/ProductRow";
import Lightbox from "@/components/Lightbox";
import { Product } from "@/components/ProductCard";
import { PRIMARY_PHONE, SITE } from "@/lib/site";

// Shown when the API returns no seller for a product.
const FALLBACK_SELLER = SITE.sellerName || SITE.name;

export default function ProductDetail() {
  const params = useParams<{ slug: string }>();
  // useParams returns the raw (already URL-encoded) segment; decode once so we
  // don't double-encode when calling the API.
  const slug = decodeURIComponent(params.slug);
  const { user } = useAuth();
  const [p, setP] = useState<any>(null);
  const [qty, setQty] = useState(1);
  const [galIdx, setGalIdx] = useState(0);
  const [tab, setTab] = useState<"desc" | "spec" | "review">("desc");
  const [reviews, setReviews] = useState<any[]>([]);
  const [form, setForm] = useState({ rating: 5, title: "", body: "" });
  const [related, setRelated] = useState<Product[]>([]);
  const [lightbox, setLightbox] = useState(false);
  const [allCars, setAllCars] = useState(false);
  // Track gallery images whose file failed to load, so a broken URL falls back
  // to the placeholder instead of showing the browser's broken-image glyph.
  const [galBroken, setGalBroken] = useState<Record<number, boolean>>({});
  // The colour swatch the shopper picked (product.colors id, or null = none
  // picked / product has no colour options). Drives both the gallery filter
  // below and what gets attached to the cart line.
  const [selectedColor, setSelectedColor] = useState<number | null>(null);
  // Where the "shop" breadcrumb goes back to — the shop remembers the exact
  // page + filters the shopper was on, so leaving a product returns them there.
  const [shopHref, setShopHref] = useState("/shop");
  useEffect(() => {
    const saved = sessionStorage.getItem("shopReturn");
    if (saved) setShopHref(saved);
  }, []);

  const loadReviews = useCallback(
    () => api.get(`/catalog/products/${encodeURIComponent(slug)}/reviews/`).then(setReviews).catch(() => {}),
    [slug],
  );

  useEffect(() => {
    setTab("desc"); setGalIdx(0); setAllCars(false); setGalBroken({}); setSelectedColor(null);
    api.get(`/catalog/products/${encodeURIComponent(slug)}/`).then((d) => {
      setP(d);
      setQty(d.min_order_qty);
      // One swatch reads as "chosen" from the start, matching how every other
      // shop with colour options behaves — an unpicked row of dots looks
      // unfinished, not neutral.
      if (d.colors?.length) setSelectedColor(d.colors[0].id);
    });
    loadReviews();
    // Ranked server-side by shared car fitment, category and availability.
    setRelated([]);
    api
      .get(`/catalog/products/${encodeURIComponent(slug)}/related/`, { auth: false })
      .then(setRelated)
      .catch(() => setRelated([]));
  }, [slug, loadReviews]);

  if (!p) return <div className="center-empty">در حال بارگذاری…</div>;

  // Tier-aware unit price: bigger quantities unlock cheaper wholesale steps.
  const tierPrice = (q: number) => {
    let best = p.price;
    for (const t of p.tiers || []) if (q >= t.min_qty && t.price < best) best = t.price;
    return best;
  };
  const unitPrice = tierPrice(qty);
  const cars = p.compatible_cars || [];
  const allImages = p.images || [];
  // Photos tagged with the chosen colour, if any exist — otherwise the whole
  // gallery, so a product with no colour-specific photos yet never goes blank
  // just because a swatch is "selected".
  const colorMatches = selectedColor != null ? allImages.filter((i: any) => i.color === selectedColor) : [];
  const images = colorMatches.length ? colorMatches : allImages;
  const galImg = images.length ? images[Math.min(galIdx, images.length - 1)] : null;
  const variants: any[] = p.variants || [];
  const shownCars = allCars ? cars : cars.slice(0, 8);
  // A part is "available" only when it is both in stock AND priced. Anything
  // else is an inquiry item: the whole buy flow is replaced by a supply-request
  // box, never a disabled version of the purchase UI.
  const available = p.stock > 0 && p.price > 0;
  const rarePartHref = `/rare-part?name=${encodeURIComponent(p.name)}&sku=${encodeURIComponent(p.sku)}`;

  const pickColor = (id: number) => {
    setSelectedColor(id);
    setGalIdx(0);       // the image list just changed under it
    setGalBroken({});
  };

  const submitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/catalog/reviews/", { product: p.id, ...form });
      toast("نظر شما ثبت شد و پس از تایید نمایش داده می‌شود");
      setForm({ rating: 5, title: "", body: "" });
    } catch (err) {
      toast(errorMessage(err));
    }
  };

  return (
    <div className="view pdp">
      <div className="crumb pdp-crumb">
        <Link href="/">خانه</Link><span>›</span>
        <a href={shopHref}>فروشگاه</a><span>›</span>
        {p.category?.name && <><a href={`/shop?category=${p.category?.id}`}>{p.category.name}</a><span>›</span></>}
        <span className="cur">{toFa(p.name)}</span>
      </div>

      <div className="pd">
        {/* ---------- Gallery ---------- */}
        <div className="pd-media">
          <div
            className={`gal ${images.length ? "zoomable" : ""}`}
            onClick={() => images.length && setLightbox(true)}
            title={images.length ? "برای بزرگ‌نمایی کلیک کنید" : undefined}
          >
            {galImg && !galBroken[galImg.id]
              ? <img
                  key={galImg.id}
                  src={galImg.image}
                  alt={p.name}
                  width={1000}
                  height={1000}
                  decoding="async"
                  fetchPriority="high"
                  style={{ animation: "fadeUp .3s ease" }}
                  onError={() => setGalBroken((b) => ({ ...b, [galImg.id]: true }))}
                />
              : <span className="noimg"><IPart size={54} /><span>تصویر محصول ثبت نشده است</span></span>}
            {!available && <span className="tag oos-tag">ناموجود</span>}
            {available && p.discount_percent > 0 && <span className="tag" style={{ top: 14, right: 14, fontSize: 14, padding: "6px 12px" }}>٪{toFa(p.discount_percent)} تخفیف</span>}
            {images.length ? (
              <span className="gal-zoom" aria-hidden>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><path d="M8 11h6M11 8v6M21 21l-4.3-4.3" /></svg>
              </span>
            ) : null}
          </div>
          {images.length > 1 && (
            <div className="thumbs">
              {images.map((img: any, i: number) => (
                <div key={img.id} className={i === galIdx ? "on" : ""} onClick={() => setGalIdx(i)}>
                  <img src={img.image} alt={img.alt || ""} width={120} height={120} loading="lazy" decoding="async" />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ---------- Info ---------- */}
        <div className="pd-info">
          {/* rating / sold row */}
          <div className="pd-rate">
            {p.rating_count > 0 ? (
              <><span className="stars"><IStar size={16} /></span><b>{rating(p.rating_avg)}</b><span className="muted">({toFa(p.rating_count)} نظر)</span></>
            ) : (
              <span className="badge green">جدید</span>
            )}
            {p.sold_count > 0 && <span className="muted">· {toFa(p.sold_count)} فروش موفق</span>}
          </div>

          {/* 1) name */}
          <h1 className="pd-title">{toFa(p.name)}</h1>

          {/* brand + sku */}
          <div className="pd-meta">
            <a href={`/shop?brand=${p.brand?.id}`} className="pd-brand">{p.brand?.name}</a>
            <span className="pd-sku mono">کد فنی: {toFa(p.sku)}</span>
          </div>

          {/* Colour swatches: pick one → gallery jumps to that colour's photos
              (falls back to the shared gallery when none are tagged yet), and
              the choice travels with the line into cart/checkout/orders. */}
          {p.colors?.length > 1 && (
            <div className="pd-options">
              <div className="pd-options-label">
                رنگ:
                <span className="pd-options-val">
                  {toFa(p.colors.find((c: any) => c.id === selectedColor)?.name || "")}
                </span>
              </div>
              <div className="pd-swatches">
                {p.colors.map((c: any) => (
                  <button
                    key={c.id}
                    type="button"
                    className={`pd-swatch ${c.id === selectedColor ? "on" : ""}`}
                    style={{ ["--sw" as any]: c.hex_code || "#ccc" }}
                    title={c.name}
                    aria-label={c.name}
                    onClick={() => pickColor(c.id)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* "Other options" — sibling products of the same part with a
              different bracket/material (each its own SKU and price), e.g. metal vs
              fibre-reinforced polymer. Clicking one navigates to that product,
              which brings its own price, stock and gallery along for free. */}
          {variants.length > 1 && (
            <div className="pd-options">
              <div className="pd-options-label">
                {toFa(p.variant_label ? "گزینه" : "گزینه‌های دیگر")}:
                <span className="pd-options-val">{toFa(p.variant_label || "")}</span>
              </div>
              <div className="pd-variants">
                {variants.map((v) => (
                  <Link
                    key={v.id}
                    href={`/product/${encodeURIComponent(v.slug)}`}
                    className={`pd-variant ${v.is_current ? "on" : ""}`}
                  >
                    {toFa(v.label)}
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Unavailable → an inquiry / supply-request box replaces the whole
              buy flow (no qty, no total, no cart, no shipping perks). */}
          {!available ? (
            <div className="pd-unavail">
              <div className="ua-head">
                <span className="ua-ic">
                  {/* Feather-style outline bell — clean, symmetric, instantly
                      reads as «notify me when it's back». Centered on its own
                      line, above the text, so it never reads as pinned to the
                      top edge of the card. */}
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                    <path d="M13.73 21a2 2 0 0 1-3.46 0" />
                  </svg>
                </span>
                <b>این کالا در حال حاضر موجود نیست</b>
                <span className="ua-desc">{p.price > 0 ? "می‌توانید درخواست تأمین ثبت کنید تا هنگام موجود شدن به شما اطلاع دهیم." : "قیمت پس از تأمین کالا اعلام می‌شود. برای پیگیری درخواست تأمین ثبت کنید."}</span>
              </div>
              <div className="ua-actions">
                <a href={rarePartHref} className="btn btn-purple ua-primary"><IPart size={18} /> ثبت درخواست تأمین کالا</a>
                {PRIMARY_PHONE && (
                  <a href={`tel:${PRIMARY_PHONE.dial}`} className="btn btn-ghost ua-secondary">📞 استعلام از فروشنده</a>
                )}
              </div>
            </div>
          ) : (
          <div className="pd-buybox">
            <div className="pd-priceline">
              {p.price > 0 ? (
                <>
                  <div className="pd-price">
                    <span className="mono num">{money(unitPrice)}</span>
                    <span className="cur">تومان</span>
                  </div>
                  {unitPrice < p.price
                    ? <span className="badge green">قیمت عمده فعال شد ✓</span>
                    : p.compare_at_price ? <span className="mono old">{money(p.compare_at_price)}</span> : null}
                </>
              ) : (
                <span className="pd-callprice">برای استعلام قیمت تماس بگیرید</span>
              )}
              <span className={`pd-stock ${p.stock > 0 ? "ok" : "no"}`}>
                {p.stock > 0 ? `${toFa(p.stock)} عدد موجود` : "ناموجود"}
              </span>
            </div>

            {p.tiers?.length > 0 && p.price > 0 && (
              <div className="pd-tiers">
                <div className="pd-tiers-h">💰 قیمت پلکانی — هرچه بیشتر بخرید، ارزان‌تر</div>
                <table className="tbl">
                  <tbody>
                    <tr>
                      <td>۱ تا {toFa(p.tiers[0].min_qty - 1)} {p.unit === "liter" ? "لیتر" : "عدد"}</td>
                      <td className="mono end">{money(p.price)} تومان</td>
                    </tr>
                    {p.tiers.map((t: any, i: number) => (
                      <tr key={i} className={qty >= t.min_qty && tierPrice(qty) === t.price ? "on" : ""}>
                        <td>از {toFa(t.min_qty)} به بالا</td>
                        <td className="mono end win">{money(t.price)} تومان</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* qty + add to cart */}
            <div className="pd-actions">
              <div className="qtybox">
                <button aria-label="کاهش" onClick={() => setQty((q) => Math.max(p.min_order_qty, q - 1))}>−</button>
                <span className="mono qv">{toFa(qty)}</span>
                <button aria-label="افزایش" onClick={() => setQty((q) => q + 1)}>+</button>
              </div>
              <button className="btn btn-purple pd-add" onClick={() => addToCart(p.id, qty, selectedColor)}>
                <ICart size={22} /> افزودن به سبد خرید
              </button>
            </div>

            {/* live total — the one derived number, updates on qty change */}
            <div className="pd-total">
              <span className="muted">مبلغ کل ({toFa(qty)} عدد):</span>
              <span className="mono val">{money(unitPrice * qty)} تومان</span>
            </div>

            {/* 15) trust chips next to the buy button */}
            <div className="pd-trust">
              <span><IShield size={15} /> ضمانت اصالت</span>
              <span><ITruck size={15} /> ارسال سریع</span>
              <span>🛡 ۶ ماه گارانتی</span>
              <span>↩ ۷ روز مرجوعی</span>
              {p.carton_qty ? <span>📦 کارتن {toFa(p.carton_qty)} عددی</span> : null}
              <span>حداقل سفارش: {toFa(p.min_order_qty)}</span>
            </div>
          </div>
          )}

          {/* 3) fitment as a distinct box with show-all */}
          {cars.length > 0 && (
            <div className="fitment">
              <div className="fit-head">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M5 13l1.6-4.5A2 2 0 0 1 8.5 7h7a2 2 0 0 1 1.9 1.5L19 13v5h-2.5v-1.5h-9V18H5z" /><circle cx="7.8" cy="15" r="1" /><circle cx="16.2" cy="15" r="1" /></svg>
                مناسب برای خودروهای: <span className="fit-count">{toFa(cars.length)} خودرو</span>
              </div>
              <div className="fit-chips">
                {shownCars.map((c: any) => (
                  <a key={c.id} href={`/shop?car=${c.id}`} title={`همه قطعات ${c.name}`}>{c.name}</a>
                ))}
                {cars.length > 8 && (
                  <button type="button" className="fit-more" onClick={() => setAllCars((v) => !v)}>
                    {allCars ? "بستن" : `+ ${toFa(cars.length - 8)} مورد دیگر`}
                  </button>
                )}
              </div>
            </div>
          )}

          {/* 13) seller card with real stats */}
          <div className="seller-card">
            <div className="sc-top">
              <div className="sc-av"><IPart size={20} /></div>
              <div className="sc-body">
                <div className="sc-name">{p.seller?.name || FALLBACK_SELLER} <span className="sc-verified"><IShield size={12} /> تایید شده</span></div>
                <div className="sc-stats">
                  {p.seller?.products != null && <span>{toFa(p.seller.products)} کالا</span>}
                  {p.seller?.rating != null && <span className="sc-rate"><IStar size={12} /> {toFa(p.seller.rating)}</span>}
                  <span>ضمانت اصالت و پشتیبانی</span>
                </div>
              </div>
            </div>
            {/* Out-of-stock: give the shopper real next steps with this seller. */}
            {!available && (
              <div className="sc-actions">
                {PRIMARY_PHONE && <a href={`tel:${PRIMARY_PHONE.dial}`}>استعلام موجودی</a>}
                <a href={rarePartHref}>درخواست تأمین</a>
                <a href="/shop">محصولات فروشنده</a>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ---------- Tabs ---------- */}
      <div className="panel pd-tabs-panel">
        <div className="tabs">
          <button className={tab === "desc" ? "on" : ""} onClick={() => setTab("desc")}>توضیحات محصول</button>
          <button className={tab === "spec" ? "on" : ""} onClick={() => setTab("spec")}>مشخصات فنی</button>
          <button className={tab === "review" ? "on" : ""} onClick={() => setTab("review")}>نظرات ({toFa(reviews.length)})</button>
        </div>
        <div className="pd-tabbody">
          {tab === "desc" && (
            <>
              {/* Identity first — the three facts a buyer checks before reading
                  any prose: what it is, whose brand, which part number. */}
              <dl className="pd-idlist">
                <dt>نام محصول</dt><dd>{toFa(p.name)}</dd>
                <dt>برند</dt><dd>{toFa(p.brand?.name || "—")}</dd>
                <dt>کد فنی</dt><dd className="mono">{toFa(p.sku)}</dd>
              </dl>
              {/* whiteSpace:pre-line keeps the paragraph breaks the supplier
                  typed — plain HTML collapses runs of whitespace and drops
                  newlines, which glued the whole description into one block. */}
              {(p.description || p.short_description) && (
                <p style={{ lineHeight: 2.1, color: "var(--ink-soft)", margin: "16px 0 0", whiteSpace: "pre-line" }}>
                  {toFa(p.description || p.short_description)}
                </p>
              )}
            </>
          )}
          {tab === "spec" && (
            <table className="spectable">
              <tbody>
                <tr><th>نام کالا</th><td>{toFa(p.name)}</td></tr>
                <tr><th>کد فنی</th><td className="mono">{toFa(p.sku)}</td></tr>
                <tr><th>برند</th><td>{toFa(p.brand?.name || "—")}</td></tr>
                <tr><th>دسته‌بندی</th><td>{toFa(p.category?.name || "—")}</td></tr>
                {p.authenticity && <tr><th>وضعیت اصالت</th><td style={{ color: "var(--green)", fontWeight: 700 }}>{toFa(p.authenticity)}</td></tr>}
                <tr><th>گارانتی</th><td>{toFa(p.warranty_text || "۶ ماه گارانتی شرکتی، قابل تعویض")}</td></tr>
                <tr><th>شرایط مرجوعی</th><td>۷ روز مهلت بازگشت کالای سالم</td></tr>
                {p.carton_qty ? <tr><th>تعداد در کارتن</th><td className="mono">{toFa(p.carton_qty)} عدد</td></tr> : null}
                <tr><th>حداقل سفارش</th><td className="mono">{toFa(p.min_order_qty)} عدد</td></tr>
                {cars.length > 0 && <tr><th>مناسب برای</th><td>{toFa(cars.map((c: any) => c.name).join("، "))}</td></tr>}
                {p.attributes?.map((a: any, i: number) => (
                  <tr key={i}><th>{toFa(a.name)}</th><td>{toFa(a.value)} {toFa(a.unit || "")}</td></tr>
                ))}
              </tbody>
            </table>
          )}
          {tab === "review" && (
            <div>
              {reviews.map((r) => (
                <div key={r.id} style={{ padding: "14px 0", borderBottom: "1px solid var(--line)" }}>
                  <div className="between"><b>{r.user_name || "کاربر"}</b><span className="stars">{"★".repeat(r.rating)}</span></div>
                  {r.title && <div style={{ fontWeight: 600, marginTop: 6 }}>{r.title}</div>}
                  <div style={{ color: "var(--ink-soft)", marginTop: 6, fontSize: 14 }}>{r.body}</div>
                  <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 6 }}>{faDate(r.created_at)}</div>
                </div>
              ))}
              {!reviews.length && <div style={{ color: "var(--muted)" }}>هنوز نظری ثبت نشده است. اولین نفری باشید که نظر می‌دهد.</div>}

              {user ? (
                <form onSubmit={submitReview} style={{ marginTop: 22, borderTop: "1px solid var(--line)", paddingTop: 18 }}>
                  <div className="flabel">ثبت نظر شما</div>
                  <div className="field" style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <span style={{ fontSize: 13.5, color: "var(--muted)" }}>امتیاز شما:</span>
                    <StarInput value={form.rating} onChange={(rating) => setForm({ ...form, rating })} />
                  </div>
                  <div className="field"><input className="inp" placeholder="عنوان" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
                  <div className="field"><textarea className="inp" rows={3} placeholder="متن نظر" value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} required /></div>
                  <button className="btn btn-purple" style={{ height: 44, padding: "0 20px" }}>ارسال نظر</button>
                </form>
              ) : (
                <div style={{ marginTop: 20, padding: "26px 20px", borderRadius: 16, background: "var(--purple-soft)", border: "1px dashed var(--purple-line)", textAlign: "center" }}>
                  <div style={{ width: 52, height: 52, borderRadius: 15, margin: "0 auto 10px", background: "linear-gradient(135deg,var(--purple),var(--purple-2))", color: "#fff", display: "grid", placeItems: "center" }}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><path d="M21 11.5a8.4 8.4 0 0 1-9 8.4 8.6 8.6 0 0 1-3.5-.7L3 21l1.8-4.4A8.4 8.4 0 1 1 21 11.5z" /></svg>
                  </div>
                  <b style={{ display: "block", marginBottom: 6 }}>نظر شما برای بقیه خریداران ارزشمند است</b>
                  <p style={{ margin: "0 0 14px", fontSize: 13, color: "var(--muted)" }}>برای ثبت نظر و امتیاز، ابتدا وارد حساب کاربری شوید.</p>
                  <a href="/login" className="btn btn-purple" style={{ height: 44, padding: "0 26px" }}>ورود / ثبت‌نام</a>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Related are always in-stock (filtered server-side). When the main part
          is unavailable they become the recommended buyable alternatives. */}
      <div className="pd-related">
        <ProductRow
          title={available ? "محصولات مرتبط" : "محصولات جایگزین موجود"}
          items={related}
          href={`/shop?category=${p.category?.id}`}
          emptyText="محصول مرتبطی برای این کالا یافت نشد."
        />
      </div>

      {lightbox && images.length ? (
        <Lightbox
          images={images}
          index={Math.min(galIdx, images.length - 1)}
          alt={p.name}
          onIndex={setGalIdx}
          onClose={() => setLightbox(false)}
        />
      ) : null}
    </div>
  );
}
