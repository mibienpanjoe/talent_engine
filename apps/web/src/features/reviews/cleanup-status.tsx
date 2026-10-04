"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { components } from "../../lib/api.generated";
import { Button } from "../../components/ui/button";
export function CleanupStatus({
  requests,
}: {
  requests: components["schemas"]["Cleanup"][];
}) {
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);
  const pending = requests.filter((r) => r.state !== "completed");
  useEffect(() => {
    if (!pending.length) return;
    const timer = setInterval(() => router.refresh(), 10000);
    return () => clearInterval(timer);
  }, [pending.length, router]);
  if (!requests.length) return null;
  return (
    <section className="review-section" aria-label="Suivi des suppressions">
      <h2>Nettoyage des dossiers supprimés</h2>
      <p role="status">
        {pending.length
          ? `${pending.length} nettoyage(s) en cours. Les dossiers sont déjà retirés de la revue.`
          : "Les nettoyages récents sont terminés."}
      </p>
      <Button
        variant="secondary"
        onClick={() => {
          setExpanded(true);
          router.refresh();
        }}
      >
        Actualiser le suivi
      </Button>
      {(pending.length > 0 || expanded) && (
        <ul>
          {requests.map((r) => (
            <li key={r.id}>
              Demande du{" "}
              {new Date(r.created_at).toLocaleString("fr-FR", {
                timeZone: "UTC",
              })}{" "}
              UTC :{" "}
              {r.state === "completed"
                ? "données effacées et vérifiées"
                : r.incident
                  ? "incident de nettoyage, reprise automatique programmée"
                  : r.state === "waiting"
                    ? "reprise automatique programmée"
                    : "nettoyage en attente"}
              .
              {r.next_attempt_at && (
                <>
                  {" "}
                  Prochaine tentative :{" "}
                  {new Date(r.next_attempt_at).toLocaleString("fr-FR", {
                    timeZone: "UTC",
                  })}{" "}
                  UTC.
                </>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
