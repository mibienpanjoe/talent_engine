"use client";
import { Alert } from "../components/ui/alert";
import { Button } from "../components/ui/button";
import { SiteHeader } from "../components/site-header";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return <><SiteHeader /><main id="main" className="page-width"><h1>Votre espace est indisponible.</h1><Alert>Le service n’a pas pu répondre. Réessayez dans un instant.</Alert><p><Button onClick={reset}>Réessayer</Button></p></main></>;
}
