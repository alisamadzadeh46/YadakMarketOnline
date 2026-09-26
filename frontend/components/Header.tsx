"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money, toFa } from "@/lib/format";
import { ICart, IMenu, ISearch, IUser } from "./Icon";
import CatIcon from "./CatIcon";

const NAV = [
  { href: "/", label: "صفحه اصلی" },
  { href: "/shop", label: "فروشگاه" },
  { href: "/rare-part", label: "قطعه نایاب" },
  { href: "/blog", label: "وبلاگ" },
];

import { homeForRole, profileHrefForRole } from "@/lib/roles";
import { SITE } from "@/lib/site";

const panelHref = homeForRole;

export default function Header() {
  const { user, cartCount, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [q, setQ] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [sug, setSug] = useState<any>(null);
  // Categories live in the header now instead of a home-page section.
  const [cats, setCats] = useState<any[]>([]);
  const [catOpen, setCatOpen] = useState(false);

  useEffect(() => {
    api.get("/catalog/categories/", { auth: false }).then(setCats).catch(() => {});
  }, []);

  // Debounced live autocomplete against /catalog/suggest/.
  useEffect(() => {
    if (q.trim().length < 2) { setSug(null); return; }
    const t = setTimeout(() => {
      api.get(`/catalog/suggest/?q=${encodeURIComponent(q.trim())}`, { auth: false })
        .then(setSug)
        .catch(() => setSug(null));
    }, 280);
    return () => clearTimeout(t);
  }, [q]);

  const goSuggest = (href: string) => {
    setSug(null); setQ("");
    router.push(href);
  };

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSug(null);
    router.push(`/shop?search=${encodeURIComponent(q)}`);
    setMenuOpen(false);
  };

  return (
    <>
      <header className="site">
        <div className="wrap hdr">
          <button className="menu-btn icon-btn" onClick={() => setMenuOpen(true)} aria-label="منو"><IMenu size={20} /></button>

          <Link href="/" className="logo">
            <div className="mk"><img src="/logo-mark.png" alt={SITE.name} className="mk-img" /></div>
            <div>
              <div className="nm">{SITE.name}</div>
              <div className="sb mono">AUTO PARTS · B2B</div>
            </div>
          </Link>

          <div className="searchwrap">
            <form className="search" style={{ maxWidth: "100%" }} onSubmit={submitSearch}>
              <ISearch />
              <input value={q} onChange={(e) => setQ(e.target.value)} onBlur={() => setTimeout(() => setSug(null), 200)} placeholder="جست‌وجوی نام قطعه، کد فنی، برند یا خودرو..." />
            </form>
            {sug ? (
              (sug.products?.length || sug.brands?.length || sug.categories?.length) ? (
                <div className="suggest">
                  {sug.products?.map((p: any, i: number) => (
                    <button key={`p${i}`} onMouseDown={() => goSuggest(`/product/${encodeURIComponent(p.slug)}`)}>
                      <span className="s-thumb">
                        {p.thumbnail ? <img src={p.thumbnail} alt="" /> : <span className="noimg" />}
                      </span>
                      <span className="s-info">
                        <span className="s-name">{p.name}</span>
                        <span className="s-meta mono">{p.brand} · {p.sku}</span>
                      </span>
                      <span className="s-right">
                        <span className="s-price mono">{money(p.price)} ت</span>
                        <span className={`s-stock ${p.in_stock ? "ok" : "no"}`}>{p.in_stock ? "موجود" : "ناموجود"}</span>
                      </span>
                    </button>
                  ))}
                  {sug.categories?.map((c: any, i: number) => (
                    <button key={`c${i}`} onMouseDown={() => goSuggest(`/shop?category=${c.id}`)}>
                      <span className="s-name">📁 دسته «{c.name}»</span><span className="s-meta">مشاهده دسته</span>
                    </button>
                  ))}
                  {sug.brands?.map((b: any, i: number) => (
                    <button key={`b${i}`} onMouseDown={() => goSuggest(`/shop?brand=${b.id}`)}>
                      <span className="s-name">🏷 برند {b.name}</span><span className="s-meta">مشاهده برند</span>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="suggest">
                  <div className="s-empty">
                    <span>نتیجه‌ای برای «{q}» پیدا نشد.</span>
                    <button
                      className="btn btn-orange"
                      style={{ height: 38, padding: "0 16px", fontSize: 12.5, marginTop: 10 }}
                      onMouseDown={() => goSuggest(`/rare-part?name=${encodeURIComponent(q)}`)}
                    >
                      ثبت درخواست این قطعه ›
                    </button>
                  </div>
                </div>
              )
            ) : null}
          </div>

          <div className="hactions">
            {user ? (
              <>
                {/* Clicking your own name goes to YOUR profile, whatever the role. */}
                <Link href={profileHrefForRole(user.role)} className="btn btn-orange" style={{ height: 48, padding: "0 16px", fontSize: 14 }}>
                  <IUser /> <span>{user.full_name || "پروفایل"}</span>
                </Link>
                <button className="icon-btn" onClick={logout} title="خروج">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" /></svg>
                </button>
              </>
            ) : (
              <Link className="btn btn-orange" href="/login" style={{ height: 48, padding: "0 18px", fontSize: 14 }}>
                <IUser /> <span>ورود / ثبت‌نام</span>
              </Link>
            )}
            <Link className="icon-btn" href="/cart">
              <ICart />
              {cartCount > 0 && <span className="cbadge">{toFa(cartCount)}</span>}
            </Link>
          </div>
        </div>

        <div className="navrow">
          <div className="wrap nav">
            {/* Category mega-menu. Hover opens it on desktop; click works on
                touch devices where hover never fires. */}
            <div
              className={`catmenu ${catOpen ? "open" : ""}`}
              onMouseEnter={() => setCatOpen(true)}
              onMouseLeave={() => setCatOpen(false)}
            >
              <button className="catbtn" onClick={() => setCatOpen((v) => !v)} aria-expanded={catOpen}>
                <IMenu /> دسته‌بندی محصولات
                <svg className="chev" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6" /></svg>
              </button>
              {catOpen && (
                <div className="catpanel">
                  <div className="catgrid">
                    {cats.map((c: any) => (
                      <Link key={c.id} href={`/shop?category=${c.id}`} className="catlink" onClick={() => setCatOpen(false)}>
                        <CatIcon k={c.icon} name={c.name} size={19} />
                        <span className="cl-name">{c.name}</span>
                        <span className="cl-count mono">{toFa(c.product_count)}</span>
                      </Link>
                    ))}
                  </div>
                  <Link href="/shop" className="catall" onClick={() => setCatOpen(false)}>مشاهده همه محصولات ›</Link>
                </div>
              )}
            </div>
            <nav>
              {NAV.map((n, i) => {
                const active = n.href === "/" ? pathname === "/" : pathname?.startsWith(n.href);
                return (
                  <Link key={i} href={n.href} className={active ? "on" : ""} aria-current={active ? "page" : undefined}>
                    {n.label}
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>
      </header>

      {/* Mobile slide-in menu */}
      <div className={`mobile-overlay ${menuOpen ? "open" : ""}`} onClick={() => setMenuOpen(false)} />
      <aside className={`mobile-drawer ${menuOpen ? "open" : ""}`}>
        <div className="drawer-top">
          <b>منو</b>
          <button className="icon-btn" style={{ width: 38, height: 38, borderRadius: 11 }} onClick={() => setMenuOpen(false)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6 6 18M6 6l12 12" /></svg>
          </button>
        </div>
        <form className="search" style={{ display: "flex", marginBottom: 12 }} onSubmit={submitSearch}>
          <ISearch /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="جستجو…" />
        </form>
        {NAV.map((n, i) => {
          const active = n.href === "/" ? pathname === "/" : pathname?.startsWith(n.href);
          return (
            <Link key={i} href={n.href} className={active ? "on" : ""} aria-current={active ? "page" : undefined}
                  onClick={() => setMenuOpen(false)}>{n.label}</Link>
          );
        })}
        <Link href={user ? panelHref(user.role) : "/login"} onClick={() => setMenuOpen(false)}>{user ? "پنل من" : "ورود / ثبت‌نام"}</Link>

        {/* The desktop mega-menu is hover-based and unreachable here, so the
            drawer carries its own scrollable copy of the category list. */}
        {cats.length > 0 && (
          <>
            <div className="drawer-h">دسته‌بندی محصولات</div>
            <div className="drawer-cats">
              {cats.map((c: any) => (
                <Link key={c.id} href={`/shop?category=${c.id}`} onClick={() => setMenuOpen(false)}>
                  <CatIcon k={c.icon} name={c.name} size={16} />
                  <span className="cl-name">{c.name}</span>
                  <span className="cl-count mono">{toFa(c.product_count)}</span>
                </Link>
              ))}
            </div>
          </>
        )}
      </aside>
    </>
  );
}
