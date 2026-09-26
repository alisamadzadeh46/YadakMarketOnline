"use client";
import Link from "next/link";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { addToCart } from "@/lib/ui";
import { toFa } from "@/lib/format";
import ProductCard, { Product } from "@/components/ProductCard";
import NiceSelect from "@/components/NiceSelect";
import Pagination from "@/components/Pagination";
import PriceField from "@/components/PriceField";

type Named = { id: number; name: string };
type Brand = Named;
type Category = Named & { product_count: number };
type Color = Named & { hex_code: string };
type Car = Named & { brand_name: string };

const SORTS: Record<string, string> = {
  "-created_at": "جدیدترین",
  price: "ارزان‌ترین",
  "-price": "گران‌ترین",
  "-rating_avg": "بیشترین امتیاز",
  "-sold_count": "پرفروش‌ترین",
};

function toggle(list: number[], id: number): number[] {
  return list.includes(id) ? list.filter((x) => x !== id) : [...list, id];
}

// The chips render Persian digits, so a shopper naturally types «۲۴» while a
// keyboard may produce "24" — normalise both sides before comparing.
const FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
const normDigits = (v: string) =>
  v.replace(/[۰-۹]/g, (d) => String(FA_DIGITS.indexOf(d))).trim();

function matchCarton(n: number, query: string): boolean {
  const q = normDigits(query);
  return !q || String(n).includes(q);
}

// useSearchParams must sit inside a Suspense boundary in the App Router.
export default function ShopPage() {
  return (
    <Suspense fallback={<div className="center-empty">در حال بارگذاری…</div>}>
      <Shop />
    </Suspense>
  );
}

function Shop() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [brands, setBrands] = useState<Brand[]>([]);
  const [cats, setCats] = useState<Category[]>([]);
  const [colors, setColors] = useState<Color[]>([]);
  const [sizes, setSizes] = useState<Named[]>([]);
  const [cars, setCars] = useState<Car[]>([]);
  const [cartons, setCartons] = useState<number[]>([]);

  const [category, setCategory] = useState<number | null>(null);
  const [selBrands, setSelBrands] = useState<number[]>([]);
  const [selColors, setSelColors] = useState<number[]>([]);
  const [selSizes, setSelSizes] = useState<number[]>([]);
  const [selCars, setSelCars] = useState<number[]>([]);
  const [selCartons, setSelCartons] = useState<number[]>([]);
  const [inStock, setInStock] = useState(false);
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [sort, setSort] = useState("-created_at");
  const [search, setSearch] = useState("");
  const [catQuery, setCatQuery] = useState("");
  const [carQuery, setCarQuery] = useState("");
  const [cartonQuery, setCartonQuery] = useState("");

  const [products, setProducts] = useState<Product[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const [page, setPage] = useState(1);
  // True only after the URL has been read into state. Both the "reset to page 1"
  // and the URL-write effects stay dormant while this is on, so restoring the
  // URL cannot trigger them and wipe the page/filters we just restored.
  const hydrated = useRef(false);
  const hydrating = useRef(true);

  // Restore the full shop state from the URL. Keyed on useSearchParams, which —
  // unlike a manual popstate listener — Next.js updates on EVERY navigation:
  // first mount, browser Back/Forward, and our own router.replace. That is what
  // makes returning from a product page land back on the exact page + filters.
  const spKey = searchParams.toString();
  useEffect(() => {
    hydrating.current = true;
    const sp = new URLSearchParams(spKey);
    const nums = (k: string) =>
      (sp.get(k) || "").split(",").filter(Boolean).map(Number);
    setCategory(sp.get("category") ? Number(sp.get("category")) : null);
    setSelBrands(nums("brand"));
    setSelColors(nums("color"));
    setSelSizes(nums("size"));
    setSelCars(nums("car"));
    setSelCartons(nums("carton"));
    setInStock(sp.get("in_stock") === "true");
    setMinPrice(sp.get("min_price") || "");
    setMaxPrice(sp.get("max_price") || "");
    setSearch(sp.get("search") || "");
    setSort(sp.get("ordering") || "-created_at");
    setPage(sp.get("page") ? Math.max(1, Number(sp.get("page"))) : 1);
    hydrated.current = true;
    sessionStorage.setItem("shopReturn", `/shop${spKey ? `?${spKey}` : ""}`);
    // Release after React flushes these updates (and the query they recompute),
    // so the reset/write effects treat this as hydration, not a user action.
    const t = setTimeout(() => { hydrating.current = false; }, 0);
    return () => clearTimeout(t);
  }, [spKey]);

  // Load facets once.
  useEffect(() => {
    api.get("/catalog/brands/").then(setBrands).catch(() => {});
    api.get("/catalog/categories/").then(setCats).catch(() => {});
    api.get("/catalog/colors/").then(setColors).catch(() => {});
    api.get("/catalog/sizes/").then(setSizes).catch(() => {});
    api.get("/catalog/cars/").then(setCars).catch(() => {});
    api.get("/catalog/cartons/").then(setCartons).catch(() => {});
  }, []);

  const query = useMemo(() => {
    const p = new URLSearchParams();
    if (category) p.set("category", String(category));
    if (selBrands.length) p.set("brand", selBrands.join(","));
    if (selColors.length) p.set("color", selColors.join(","));
    if (selSizes.length) p.set("size", selSizes.join(","));
    if (selCars.length) p.set("car", selCars.join(","));
    if (selCartons.length) p.set("carton", selCartons.join(","));
    if (inStock) p.set("in_stock", "true");
    if (minPrice) p.set("min_price", minPrice);
    if (maxPrice) p.set("max_price", maxPrice);
    if (search) p.set("search", search);
    p.set("ordering", sort);
    return p.toString();
  }, [category, selBrands, selColors, selSizes, selCars, selCartons, inStock, minPrice, maxPrice, sort, search]);

  // A user changing a filter jumps back to page 1. During hydration the query
  // also changes (we just restored the filters), so skip it then — otherwise
  // restoring page 13 would immediately be reset to 1.
  useEffect(() => {
    if (hydrating.current) return;
    setPage(1);
  }, [query]);

  // Mirror the whole state into the URL so back/forward and a shared link both
  // reproduce this exact view. replaceState (not push) so the back button steps
  // between real navigations, not every filter tweak.
  useEffect(() => {
    if (!hydrated.current || hydrating.current) return;
    const next = `${query}${page > 1 ? `&page=${page}` : ""}`;
    // Only write when the state actually diverged from the URL, so our own
    // replace doesn't echo back through useSearchParams into a loop.
    if (next !== spKey) {
      // router.replace (not history.replaceState) so Next.js' own router stays
      // in sync — otherwise Next still thinks this entry is bare "/shop" and
      // pressing Back after a product page restored page 1.
      router.replace(`/shop?${next}`, { scroll: false });
      sessionStorage.setItem("shopReturn", `/shop?${next}`);
    }
  }, [query, page, spKey, router]);

  // Sequence guard: on arrival the shop briefly fires an unfiltered request
  // (initial state) and then the filtered one, and whichever resolves LAST wins.
  // Without this the stale unfiltered response could overwrite the filtered
  // results — the "URL is right but filters aren't applied until I toggle
  // something" bug. Only the newest request is allowed to update the list.
  const reqSeq = useRef(0);
  const load = useCallback(() => {
    const mine = ++reqSeq.current;
    setLoading(true);
    api
      .get(`/catalog/products/?${query}&page=${page}`)
      .then((d) => {
        if (mine !== reqSeq.current) return; // superseded by a newer request
        setProducts(d.results);
        setCount(d.count);
      })
      .finally(() => {
        if (mine === reqSeq.current) setLoading(false);
      });
  }, [query, page]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="view">
      <div className="crumb"><Link href="/">خانه</Link><span>/</span><span style={{ color: "var(--ink)" }}>فروشگاه</span></div>
      <div className="shop">
        <aside className="panel filters">
          <h3 style={{ margin: "0 0 18px", fontSize: 16, fontWeight: 800 }}>فیلترها</h3>

          <div className="fgroup">
            <div className="flabel">محدوده قیمت (تومان)</div>
            <div style={{ display: "flex", gap: 8 }}>
              <PriceField placeholder="از" value={minPrice} onChange={setMinPrice} style={{ fontSize: 13 }} />
              <PriceField placeholder="تا" value={maxPrice} onChange={setMaxPrice} style={{ fontSize: 13 }} />
            </div>
          </div>

          <div className="fgroup">
            <div className="flabel">دسته‌بندی</div>
            {/* 40 categories is too many to eyeball, so this list is searchable
                and scrolls inside its own box. */}
            <input className="fsearch" placeholder="جستجوی دسته‌بندی…" value={catQuery} onChange={(e) => setCatQuery(e.target.value)} />
            <div className="fcol fscroll">
              <button className={!category ? "on" : ""} onClick={() => setCategory(null)}>همه محصولات</button>
              {cats
                .filter((c) => !catQuery.trim() || c.name.includes(catQuery.trim()))
                .map((c) => (
                  <button key={c.id} className={category === c.id ? "on" : ""} onClick={() => setCategory(c.id)}>
                    {c.name} <span className="mono" style={{ color: category === c.id ? "#fff" : "var(--muted)", fontSize: 11 }}>{toFa(c.product_count)}</span>
                  </button>
                ))}
            </div>
          </div>

          <div className="fgroup">
            <div className="flabel">برند</div>
            <div className="fchips fscroll">
              {brands.map((b) => (
                <button key={b.id} className={selBrands.includes(b.id) ? "on" : ""} onClick={() => setSelBrands(toggle(selBrands, b.id))}>{b.name}</button>
              ))}
            </div>
          </div>

          <div className="fgroup">
            <div className="flabel">مناسب برای خودرو</div>
            <input className="fsearch" placeholder="جستجوی خودرو…" value={carQuery} onChange={(e) => setCarQuery(e.target.value)} />
            <div className="fchips fscroll">
              {cars.filter((c) => !carQuery.trim() || c.name.includes(carQuery.trim()) || (c.brand_name || "").includes(carQuery.trim())).map((c) => (
                <button key={c.id} className={selCars.includes(c.id) ? "on" : ""} onClick={() => setSelCars(toggle(selCars, c.id))}>{c.name}</button>
              ))}
            </div>
          </div>

          {/* Facets with nothing to show are hidden rather than left as empty boxes. */}
          {colors.length > 0 && (
            <div className="fgroup">
              <div className="flabel">رنگ</div>
              <div className="fchips fscroll">
                {colors.map((c) => (
                  <button key={c.id} className={selColors.includes(c.id) ? "on" : ""} onClick={() => setSelColors(toggle(selColors, c.id))}>{c.name}</button>
                ))}
              </div>
            </div>
          )}

          {sizes.length > 0 && (
            <div className="fgroup">
              <div className="flabel">سایز</div>
              <div className="fchips fscroll">
                {sizes.map((s) => (
                  <button key={s.id} className={selSizes.includes(s.id) ? "on" : ""} onClick={() => setSelSizes(toggle(selSizes, s.id))}>{s.name}</button>
                ))}
              </div>
            </div>
          )}

          {cartons.length > 0 && (
            <div className="fgroup">
              <div className="flabel">تعداد در کارتن</div>
              <input
                className="fsearch"
                inputMode="numeric"
                placeholder="جستجوی تعداد کارتن…"
                value={cartonQuery}
                onChange={(e) => setCartonQuery(e.target.value)}
              />
              <div className="fchips fscroll">
                {cartons.filter((n) => matchCarton(n, cartonQuery)).map((n) => (
                  <button key={n} className={selCartons.includes(n) ? "on" : ""} onClick={() => setSelCartons(toggle(selCartons, n))}>{toFa(n)} عددی</button>
                ))}
              </div>
            </div>
          )}

          <label className="fgroup" style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <input type="checkbox" checked={inStock} onChange={(e) => setInStock(e.target.checked)} style={{ accentColor: "var(--purple)", width: 17, height: 17 }} />
            <span style={{ fontSize: 13.5, fontWeight: 600 }}>فقط کالاهای موجود</span>
          </label>
        </aside>

        <div>
          <div className="shopbar">
            <div style={{ fontSize: 13.5, color: "var(--ink-soft)" }}>
              <b className="mono">{toFa(count)}</b> کالا یافت شد
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
              <span style={{ color: "var(--muted)" }}>مرتب‌سازی:</span>
              <NiceSelect
                value={sort}
                onChange={setSort}
                options={Object.entries(SORTS).map(([value, label]) => ({ value, label }))}
                style={{ minWidth: 170 }}
              />
            </div>
          </div>

          {loading ? (
            <div className="grid shopgrid">
              {[1, 2, 3, 4, 5, 6].map((i) => (<div key={i} className="skel" style={{ height: 300 }} />))}
            </div>
          ) : products.length ? (
            <>
              <div className="grid shopgrid">
                {products.map((p) => (<ProductCard key={p.id} p={p} onAdd={(pr) => addToCart(pr.id, pr.min_order_qty)} />))}
              </div>
              <Pagination page={page} count={count} onChange={(p) => { setPage(p); window.scrollTo({ top: 0, behavior: "smooth" }); }} />
            </>
          ) : (
            <div className="panel center-empty">
              <div style={{ fontSize: 42 }}>🔍</div>
              <b style={{ display: "block", margin: "8px 0 6px", color: "var(--ink)" }}>کالایی با این فیلترها یافت نشد</b>
              <p style={{ marginTop: 0 }}>قطعه موردنظرتان را پیدا نکردید؟ برایتان پیدایش می‌کنیم.</p>
              <a href="/rare-part" className="btn btn-orange" style={{ height: 46, padding: "0 24px" }}>ثبت درخواست قطعه نایاب</a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
