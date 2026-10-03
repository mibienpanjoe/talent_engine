import { AlertTriangle, CheckCircle2, Info } from "lucide-react";
import type { ReactNode } from "react";
export function Alert({ children, tone = "danger" }: { children: ReactNode; tone?: "danger" | "neutral" | "success" }) {
  const Icon = tone === "danger" ? AlertTriangle : tone === "success" ? CheckCircle2 : Info;
  return <div className={`ui-alert ui-alert--${tone}`} role={tone === "danger" ? "alert" : "status"}>
    <Icon aria-hidden="true" size={20} strokeWidth={1.5} /><div>{children}</div>
  </div>;
}
