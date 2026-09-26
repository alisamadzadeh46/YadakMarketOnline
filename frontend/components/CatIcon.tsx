// Per-category icon + colour identity.
//
// Two ways a category gets its icon:
//   1. Category.icon holds one of the keys below (written by the price-list
//      importer — keep in sync with ICON_HINTS in
//      backend/apps/catalog/management/commands/import_pricelist.py).
//   2. If that field is empty or unknown, the category NAME is matched instead.
//      Every category created by hand has an empty icon field, so without this
//      the whole menu fell back to one generic hex nut — eight different body
//      parts all wearing the same badge.
//
// The glyphs draw the part itself (a brake disc with its caliper, a wheel arch,
// a chassis ladder), not an abstract shape: at 16–19px the reader should be
// able to tell what they are about to click.
const COLORS: Record<string, [string, string]> = {
  // ---- body & chassis (what this shop actually sells) ----
  brakepad: ["#FDEAEA", "#D63C3C"],
  grille: ["#EDE7FB", "#5B2E9E"],
  door: ["#E7F0FE", "#2F53E6"],
  fender: ["#E6F5EE", "#1F9D63"],
  bumper: ["#FDECE0", "#F26A1B"],
  chassis: ["#EFEDF5", "#4A4360"],
  cooling: ["#E7F6F3", "#0E8C7A"],
  hubcap: ["#FFF3DC", "#C98A00"],
  glass: ["#E9F2FD", "#1F6FEB"],
  mirror: ["#F0E9FC", "#6D3BC0"],
  light: ["#FFF6D9", "#B98600"],
  suspension: ["#E8EEFB", "#3A5BB8"],
  oil: ["#FBF0E3", "#A9701A"],
  battery: ["#E6F5EE", "#158A57"],
  // ---- electrical / signal ----
  sensor: ["#EDE7FB", "#5B2E9E"],
  socket: ["#E7F0FE", "#2F53E6"],
  relay: ["#FDF1E0", "#B27A00"],
  switch: ["#FBE9F1", "#C0397A"],
  wire: ["#E6F5EE", "#1F9D63"],
  fuse: ["#FDEAEA", "#D63C3C"],
  coil: ["#F0E9FC", "#6D3BC0"],
  spark: ["#FFF3DC", "#C98A00"],
  // ---- fuel / mechanical ----
  injector: ["#E9F2FD", "#1F6FEB"],
  pump: ["#E7F6F3", "#0E8C7A"],
  motor: ["#F3EAFB", "#8330C4"],
  filter: ["#FDECE0", "#F26A1B"],
  part: ["#EFEDF5", "#4A4360"],
};

/** Persian name → icon key. First match wins, so specific patterns come before
 *  loose ones. «فن» is a regex rather than a substring because it also opens
 *  «فنر» (a spring) and «فنی» (as in کد فنی). */
const NAME_RULES: Array<[RegExp, string]> = [
  [/لنت|ترمز|دیسک/, "brakepad"],
  [/جلوپنجره|جلو پنجره|آرم/, "grille"],
  [/گلگیر|رکاب|شلگیر/, "fender"],
  [/سپر/, "bumper"],
  [/شاسی|رام|سینی/, "chassis"],
  [/خنک|رادیات|(^|\s)فن(\s|$|‌)/, "cooling"],
  [/قالپاق|تزئین|تزیین|رینگ/, "hubcap"],
  [/درب|بدنه|کاپوت|صندوق/, "door"],
  [/شیشه|برف\s?پاک/, "glass"],
  [/آینه/, "mirror"],
  [/تعلیق|فرمان|کمک\s?فنر|فنر|بلبرینگ/, "suspension"],
  [/روغن|روانکار|گریس|ضدیخ/, "oil"],
  [/باتری|برق|دینام|استارت/, "battery"],
  [/چراغ|نور|پروژکتور|پرژکتور/, "light"],
  [/فیلتر|صافی/, "filter"],
  [/سنسور/, "sensor"],
  [/فیوز/, "fuse"],
  [/کویل|وایر/, "coil"],
  [/شمع/, "spark"],
  [/پمپ/, "pump"],
  [/موتور|دینام/, "motor"],
];

function keyFromName(name?: string): string | null {
  if (!name) return null;
  for (const [pattern, key] of NAME_RULES) if (pattern.test(name)) return key;
  return null;
}

function Glyph({ k, size = 28 }: { k: string; size?: number }) {
  const p = {
    width: size, height: size, viewBox: "0 0 24 24", fill: "none",
    stroke: "currentColor", strokeWidth: 1.7,
    strokeLinecap: "round" as const, strokeLinejoin: "round" as const,
  };
  switch (k) {
    // ---- body & chassis ----
    case "brakepad": // vented disc gripped by a caliper
      return <svg {...p}><circle cx="10.5" cy="12" r="7.5" /><circle cx="10.5" cy="12" r="2.6" /><path d="M17.4 7.8h1.9a1.6 1.6 0 0 1 1.6 1.6v5.2a1.6 1.6 0 0 1-1.6 1.6h-1.9" /></svg>;
    case "grille": // trapezoid radiator grille with bars and a centre badge
      return <svg {...p}><path d="M5 7h14l1.6 10H3.4z" /><path d="M4.1 10.5h15.8M4.7 13.8h14.6" /><circle cx="12" cy="12" r="1.6" /></svg>;
    case "door": // car door with window and handle
      return <svg {...p}><path d="M4 20V10a2 2 0 0 1 .9-1.7l5-3.3a2 2 0 0 1 1.1-.3H18a2 2 0 0 1 2 2V20z" /><path d="M8 9.5h8v4.2H8z" /><path d="M8.6 17h3.4" /></svg>;
    case "fender": // wheel arch over the wheel
      return <svg {...p}><path d="M2.6 18.5h18.8" /><path d="M4 18.5a8 8 0 0 1 16 0" /><circle cx="12" cy="18.5" r="3.1" /></svg>;
    case "bumper": // bumper bar on its two mounting brackets
      return <svg {...p}><path d="M3 10.5h18v3.6a2.4 2.4 0 0 1-2.4 2.4H5.4A2.4 2.4 0 0 1 3 14.1z" /><path d="M7.5 10.5V7.6M16.5 10.5V7.6" /></svg>;
    case "chassis": // ladder frame: two rails, three cross members
      return <svg {...p}><path d="M3 6.8h18M3 17.2h18" /><path d="M7.4 6.8v10.4M12 6.8v10.4M16.6 6.8v10.4" /></svg>;
    case "cooling": // radiator core with fins + filler neck
      return <svg {...p}><rect x="3.2" y="6" width="17.6" height="12.5" rx="2.2" /><path d="M8 6v12.5M12 6v12.5M16 6v12.5" /><path d="M9.5 6V3.6h5V6" /></svg>;
    case "hubcap": // rim, spokes, centre cap
      return <svg {...p}><circle cx="12" cy="12" r="8.6" /><circle cx="12" cy="12" r="2.2" /><path d="M12 3.4v6.4M12 14.2v6.4M3.4 12h6.4M14.2 12h6.4" /></svg>;
    case "glass": // windscreen with a wiper
      return <svg {...p}><path d="M5 17l2.2-8a2 2 0 0 1 1.9-1.5h5.8a2 2 0 0 1 1.9 1.5L19 17z" /><path d="M8 17l6.5-6.2" /></svg>;
    case "mirror": // door mirror on its arm
      return <svg {...p}><path d="M4.5 9.5h9.7a3 3 0 0 1 3 3v1.2a2.3 2.3 0 0 1-2.3 2.3H4.5z" /><path d="M4.5 7.5v11" /></svg>;
    case "light": // headlamp casting a beam
      return <svg {...p}><path d="M4 8.6h5.4a6 6 0 0 1 0 8.8H4z" /><path d="M13.5 9.5h6M13.5 13h6.5M13.5 16.5h6" /></svg>;
    case "suspension": // coil-over shock absorber
      return <svg {...p}><path d="M12 2.5v3M12 18.5v3" /><path d="M8.5 5.5h7M8.5 21.5h7" /><path d="M8.5 8.2h7M8.5 11h7M8.5 13.8h7M8.5 16.6h7" /><path d="M12 5.5v13" /></svg>;
    case "oil": // oil can with a drip
      return <svg {...p}><path d="M4 12.5h8.5l4.5-3v3H20a1 1 0 0 1 1 1v3a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z" /><path d="M8.5 12.5V9.5h4" /><path d="M12 21.5c1 0 1.6-.7 1.6-1.5S12 17.8 12 17.8s-1.6 1.4-1.6 2.2.6 1.5 1.6 1.5z" /></svg>;
    case "battery": // battery with terminals and charge bars
      return <svg {...p}><rect x="3" y="7.5" width="18" height="11" rx="2" /><path d="M7 7.5V5.5h3v2M14 7.5V5.5h3v2" /><path d="M7.5 13h3M16.5 13h-3M15 11.5v3" /></svg>;
    // ---- electrical / signal ----
    case "sensor": // probe body emitting a signal
      return <svg {...p}><rect x="8" y="3" width="8" height="10" rx="2" /><path d="M10 13v4M14 13v4M9 20h6" /><path d="M4.5 6.5a5 5 0 0 0 0 6M19.5 6.5a5 5 0 0 1 0 6" /></svg>;
    case "socket": // connector shell with pins
      return <svg {...p}><rect x="3" y="6" width="14" height="12" rx="2.5" /><path d="M17 10h2.5a2 2 0 0 1 0 4H17" /><path d="M7 10v4M11 10v4" /></svg>;
    case "relay": // cube with a bolt
      return <svg {...p}><rect x="4" y="4" width="16" height="16" rx="2.5" /><path d="M13 8l-3.5 4.5H12L10.5 16l3.7-4.7H12z" /></svg>;
    case "switch": // rocker switch
      return <svg {...p}><rect x="3" y="7" width="18" height="10" rx="5" /><circle cx="8.5" cy="12" r="2.7" /><path d="M15 10.5h3M15 13.5h3" /></svg>;
    case "wire": // twin leads
      return <svg {...p}><path d="M4 8c4 0 4 8 8 8s4-8 8-8" /><path d="M3.5 15.5h3M17.5 8.5h3" /></svg>;
    case "fuse": // blade fuse
      return <svg {...p}><rect x="6" y="4" width="12" height="16" rx="2" /><path d="M9 4V2.5M15 4V2.5M9 20v1.5M15 20v1.5" /><path d="M9.5 9l5 6" /></svg>;
    case "coil": // ignition coil windings
      return <svg {...p}><rect x="7" y="3" width="10" height="13" rx="2" /><path d="M7 6.5h10M7 9.5h10M7 12.5h10" /><path d="M12 16v3M10 21h4" /></svg>;
    case "spark": // spark plug
      return <svg {...p}><path d="M10 2.5h4V7h-4z" /><path d="M9 7h6v5H9z" /><path d="M10.5 12v3.5M13.5 12v3.5M12 15.5l-1.5 6" /></svg>;
    // ---- fuel / mechanical ----
    case "injector": // nozzle spraying
      return <svg {...p}><path d="M9 3h6v6l-1.5 3h-3L9 9z" /><path d="M12 12v3" /><path d="M9.5 19.5 12 17l2.5 2.5M12 17v4" /></svg>;
    case "pump": // pump housing + outlet
      return <svg {...p}><circle cx="11" cy="13" r="6" /><circle cx="11" cy="13" r="2.2" /><path d="M11 7V3h4M17 13h4" /></svg>;
    case "motor": // motor body with shaft
      return <svg {...p}><rect x="3" y="7" width="12" height="10" rx="2" /><circle cx="9" cy="12" r="2.2" /><path d="M15 12h5M6 7V4.5M12 7V4.5" /></svg>;
    case "filter": // filter canister
      return <svg {...p}><rect x="7" y="3" width="10" height="18" rx="2.5" /><path d="M7 8h10M7 12h10M7 16h10" /></svg>;
    default: // generic part — a hex nut, echoing the site logo
      return <svg {...p}><path d="M12 3l7.5 4.5v9L12 21l-7.5-4.5v-9z" /><circle cx="12" cy="12" r="3.2" /></svg>;
  }
}

export default function CatIcon({ k, name, size = 28 }: { k?: string; name?: string; size?: number }) {
  const key = (k && COLORS[k] && k) || keyFromName(name) || "part";
  const [bg, fg] = COLORS[key];
  return (
    <span
      className="caticon"
      style={{
        width: size * 2.05, height: size * 2.05, borderRadius: 18,
        background: bg, color: fg, display: "grid", placeItems: "center",
      }}
    >
      <Glyph k={key} size={size} />
    </span>
  );
}

/** Colour pair for a category, so other components share the same identity. */
export function catColors(k?: string, name?: string): [string, string] {
  return COLORS[(k && COLORS[k] && k) || keyFromName(name) || "part"];
}
