import Link from "next/link";
import { SiteHeader } from "../components/site-header";
import { Button } from "../components/ui/button";

export default function NotFound() {
  return (
    <>
      <SiteHeader />
      <main id="main" className="page-width hero">
        <h1>Page introuvable</h1>
        <p>Ce lien ne donne accès à aucune page disponible.</p>
        <Button asChild><Link href="/">Revenir à l’accueil</Link></Button>
      </main>
    </>
  );
}
