import type { ReactNode } from "react";
import { Brand } from "./brand";
export function SiteHeader({ children }: { children?: ReactNode }) {
  return <header className="site-header"><div className="page-width header-inner"><Brand />{children}</div></header>;
}
