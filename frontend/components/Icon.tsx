// A tiny inline-SVG icon set (no icon-font/CDN dependency).
type P = { size?: number; className?: string };

export const ISearch = ({ size = 19 }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
);
export const IUser = ({ size = 17 }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
);
export const ICart = ({ size = 21 }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="9" cy="21" r="1" /><circle cx="20" cy="21" r="1" /><path d="M1 1h4l2.7 13.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L23 6H6" /></svg>
);
export const IStar = ({ size = 14 }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l3 6.5 7 .9-5 4.9 1.2 7-6.2-3.4L5.8 21l1.2-7-5-4.9 7-.9z" /></svg>
);
// YadakMart brand mark: a hex nut (auto parts) framing a bold "Y" monogram.
// White nut + orange Y reads instantly at any size and matches the palette.
export const ILogo = ({ size = 26 }: P) => (
  <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
    {/* outer hex nut */}
    <path d="M24 3.5 41.7 13.7v20.6L24 44.5 6.3 34.3V13.7z" stroke="#fff" strokeWidth="3" strokeLinejoin="round" />
    {/* inner thread hint */}
    <path d="M24 10.5 35.7 17.2v13.6L24 37.5 12.3 30.8V17.2z" stroke="rgba(255,255,255,.35)" strokeWidth="1.6" strokeLinejoin="round" />
    {/* Y monogram */}
    <path d="M16.5 15.5 24 24.5l7.5-9" stroke="#FF8A3D" strokeWidth="4.4" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M24 24.5v8.5" stroke="#FF8A3D" strokeWidth="4.4" strokeLinecap="round" />
  </svg>
);
export const IMenu = ({ size = 16 }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" /></svg>
);
export const ICheck = ({ size = 15 }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M5 12l5 5L20 7" /></svg>
);
export const IPart = ({ size = 60 }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.3"><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="3.4" /><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" /></svg>
);
export const IShield = ({ size = 24 }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 2l8 3v6c0 5-3.4 8.4-8 11-4.6-2.6-8-6-8-11V5z" /><path d="M9 12l2 2 4-4" /></svg>
);
export const ITruck = ({ size = 24 }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="1" y="6" width="14" height="11" rx="1.5" /><path d="M15 9h4l3 3v5h-7" /><circle cx="6" cy="18" r="1.8" /><circle cx="18" cy="18" r="1.8" /></svg>
);
export const ICredit = ({ size = 24 }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="2" y="5" width="20" height="14" rx="2" /><path d="M2 10h20" /></svg>
);
