// Shared step indicator for the cart -> checkout -> order flow, so the buyer
// always knows where they are and how many steps remain.
import { toFa } from "@/lib/format";

const STEPS = ["سبد خرید", "اطلاعات ارسال و پرداخت", "تأیید و ثبت سفارش"];

export default function CheckoutSteps({ active }: { active: 0 | 1 | 2 }) {
  return (
    <div className="csteps-wrap">
      <div className="csteps">
        {STEPS.map((label, i) => (
          <div key={i} className={`cstep ${i < active ? "done" : i === active ? "on" : ""}`}>
            <span className="cstep-dot">{i < active ? "✓" : toFa(i + 1)}</span>
            <span className="cstep-label">{label}</span>
            {i < STEPS.length - 1 && <span className={`cstep-line ${i < active ? "done" : ""}`} />}
          </div>
        ))}
      </div>
    </div>
  );
}
