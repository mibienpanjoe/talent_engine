"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return <main id="main"><h1>Votre espace est indisponible.</h1><p role="alert">Le service n’a pas pu répondre. Réessayez dans un instant.</p><button onClick={reset}>Réessayer</button></main>;
}
