import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import "./globals.css";
export const metadata: Metadata = { title: "Talent Engine", description: "Évaluer avec des preuves, décider avec discernement." };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="fr"><body className={GeistSans.variable}><a className="skip-link" href="#main">Aller au contenu</a>{children}</body></html>;
}
