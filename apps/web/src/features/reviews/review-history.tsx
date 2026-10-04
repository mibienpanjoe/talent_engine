"use client";
import { useState } from "react";
import type { components } from "../../lib/api.generated";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Alert } from "../../components/ui/alert";
import { EvidenceButton } from "./evidence-button";
import { assessmentLabels, decisionLabels } from "./labels";
type Event = components["schemas"]["ReviewEvent"];
type Detail = components["schemas"]["ApplicationDetail"];
function display(value: Event["value"]): string {
  if (typeof value.level === "number") return `Niveau ${value.level} / 4`;
  const status = String(value.status ?? value.decision ?? "");
  return (
    (
      {
        ...assessmentLabels,
        ...decisionLabels,
        met: "Satisfaite",
        unmet: "Non satisfaite",
        unknown: "À vérifier",
      } as Record<string, string>
    )[status] ?? "Changement de version"
  );
}
export function ReviewHistory({ dossier }: { dossier: Detail }) {
  const [items, setItems] = useState<Event[]>();
  const [next, setNext] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function load(cursor?: string) {
    setBusy(true);
    setError("");
    try {
      const result = await api.GET(
        "/api/v1/applications/{application_id}/review-history",
        {
          params: {
            path: { application_id: dossier.application.id },
            query: { cursor },
          },
        },
      );
      if (result.data) {
        setItems((current) =>
          cursor ? [...(current ?? []), ...result.data!] : result.data,
        );
        setNext(result.response.headers.get("X-Next-Cursor"));
      } else setError("L’historique est indisponible. Réessayez.");
    } catch {
      setError("L’historique est indisponible. Réessayez.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="review-section">
      <h2>Historique de la revue</h2>
      <div className="inline-actions">
        <Button variant="secondary" disabled={busy} onClick={() => load()}>
          {busy ? "Chargement…" : "Consulter l’historique"}
        </Button>
        {next && (
          <Button variant="secondary" disabled={busy} onClick={() => load(next)}>
            Suite de l’historique
          </Button>
        )}
      </div>
      {error && <Alert tone="danger">{error}</Alert>}
      {items &&
        (items.length ? (
          <ol className="review-timeline">
            {items.map((item) => (
              <li key={item.id} className="review-event">
                <span className="review-event-kind">{item.kind === "decision" ? "Décision" : item.kind === "activation" ? "Analyse activée" : "Correction humaine"}</span>
                <h3>
                  {item.kind === "decision"
                    ? "Décision humaine"
                    : item.kind === "activation"
                      ? "Activation d’une analyse"
                      : (dossier.snapshot.configuration.requirements.find(
                          (r) => r.id === item.criterion_id,
                        )?.expectation ?? "Correction")}
                </h3>
                <p>
                  <span className="review-event-before">{display(item.previous)}</span> → <span className="review-event-after">{display(item.value)}</span>
                  {item.action === "restore_base" &&
                    " · retour à la base automatique"}
                </p>
                <p className="preserve-lines review-event-reason">{item.reason}</p>
                <p className="review-event-meta">
                  {new Date(item.created_at).toLocaleString("fr-FR", {
                    timeZone: "UTC",
                  })}{" "}
                  UTC · auteur {item.author_login ?? item.author_id}
                </p>
                {Array.isArray(item.value.evidence_ids) && (
                  <div className="inline-actions">
                    {item.value.evidence_ids.map((id, i) => (
                      <EvidenceButton
                        key={String(id)}
                        id={String(id)}
                        label={`Justificatif de la correction ${i + 1}`}
                        className="criterion-proof"
                      />
                    ))}
                  </div>
                )}
                <details className="provenance-details">
                  <summary>Version concernée</summary>
                  <p className="hash-text">
                    {item.evaluation_id ??
                      "Décision indépendante de l’évaluation"}
                  </p>
                </details>
              </li>
            ))}
          </ol>
        ) : (
          <p>Aucun changement humain enregistré.</p>
        ))}
    </section>
  );
}
