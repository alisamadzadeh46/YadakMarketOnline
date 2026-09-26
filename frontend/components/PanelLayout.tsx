"use client";
// Shared dashboard shell: sticky sidebar (horizontal scroller on mobile)
// with the signed-in user's identity and a highlighted active item.
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { useAuth } from "@/lib/auth";

export type PanelItem = { href: string; label: string; icon?: React.ReactNode; adminOnly?: boolean };

export default function PanelLayout({
  items,
  children,
  requireRole,
}: {
  items: PanelItem[];
  children: React.ReactNode;
  requireRole?: string[];
}) {
  const { user, loading } = useAuth();
  const path = usePathname();
  const router = useRouter();
  const navRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (loading) return;
    if (!user) { router.replace("/login"); return; }
    if (requireRole && !requireRole.includes(user.role)) { router.replace("/"); return; }
    // A non-admin who deep-links to an admin-only section is bounced to the
    // panel home, so hiding the nav item can't be bypassed by typing the URL.
    if (user.role !== "admin") {
      const adminItem = items.find((it) => it.adminOnly && path === it.href);
      if (adminItem) router.replace(items[0]?.href || "/");
    }
  }, [user, loading, requireRole, router, items, path]);

  // On phones the rail is a horizontal scroller (see .psb in globals.css).
  // With sixteen sections the current one is often past the right edge, so the
  // panel opened looking like it was on some other page. Pull it into view.
  useEffect(() => {
    const active = navRef.current?.querySelector<HTMLElement>("a.on");
    if (!active) return;
    const nav = navRef.current!;
    if (nav.scrollWidth <= nav.clientWidth) return; // desktop rail: nothing to scroll
    active.scrollIntoView({ block: "nearest", inline: "center" });
  }, [path, user]);

  // The redirects above live in an effect, which runs AFTER this render — so
  // checking only `!user` let a signed-in user with the wrong role paint the
  // whole dashboard for a frame before being bounced. Withhold the shell until
  // the role is actually confirmed; the API is role-checked too, but the UI
  // should never flash a panel the visitor has no right to.
  const allowed = !!user && (!requireRole || requireRole.includes(user.role));
  if (!allowed) return <div className="center-empty">در حال بارگذاری…</div>;

  // Owner (admin) sees every section; a plain supplier only the store-scoped ones.
  const isAdmin = user.role === "admin";
  const visible = items.filter((it) => !it.adminOnly || isAdmin);

  return (
    <div className="playout view">
      <aside className="psb">
        <div className="who">
          <div className="av">{(user.full_name || "؟").slice(0, 1)}</div>
          <div>
            <div className="nm">{user.full_name || user.phone}</div>
            <div className="rl">{user.role_display}</div>
          </div>
        </div>
        <nav ref={navRef}>
          {visible.map((it) => (
            <Link key={it.href} href={it.href} className={path === it.href ? "on" : ""}>
              {it.icon} {it.label}
            </Link>
          ))}
        </nav>
      </aside>
      <div style={{ minWidth: 0 }}>{children}</div>
    </div>
  );
}
