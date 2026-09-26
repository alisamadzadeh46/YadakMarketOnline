// Global route-level loading skeleton (App Router suspense fallback).
export default function Loading() {
  return (
    <div style={{ padding: "10px 0" }}>
      <div className="skel" style={{ height: 320, borderRadius: 26, marginBottom: 18 }} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 16 }}>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="skel" style={{ height: 260 }} />
        ))}
      </div>
    </div>
  );
}
