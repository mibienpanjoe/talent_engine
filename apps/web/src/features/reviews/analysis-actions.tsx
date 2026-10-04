"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import type { components } from "../../lib/api.generated";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Alert } from "../../components/ui/alert";
import { useActionKey } from "./use-action-key";
type Detail = components["schemas"]["ApplicationDetail"];
export function AnalysisActions({ dossier }: { dossier: Detail }) {
  const router = useRouter();
  const actionKey = useActionKey();
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const active = ["queued", "collecting", "evaluating"].includes(
    dossier.application.processing_state,
  );
  const baseRun =
    dossier.effective_evaluation?.run_id ?? dossier.analyses?.[0]?.id;
  const failed =
    dossier.sources?.filter(
      (s) =>
        s.state !== "available" ||
        s.error_code ||
        s.extraction_metadata?.web?.some((p) => p.status === "failed") ||
        s.extraction_metadata?.ocr?.some((p) => p.status === "failed") ||
        s.extraction_metadata?.github?.files.some((f) => f.status === "failed"),
    ) ?? [];
  async function request(reason: "retry_sources" | "reanalyze") {
    if (!baseRun) return;
    setBusy(true);
    setError("");
    const body = {
      review_revision: dossier.application.review_revision,
      effective_evaluation_id:
        dossier.application.effective_evaluation_id ?? null,
      reason,
      base_run_id: baseRun,
      source_ids: reason === "retry_sources" ? selected : [],
    };
    try {
      const csrf = await api.GET("/api/v1/access/csrf");
      if (!csrf.data) throw new Error();
      const result = await api.POST(
        "/api/v1/applications/{application_id}/analyses",
        {
          params: { path: { application_id: dossier.application.id } },
          headers: {
            "X-CSRF-Token": csrf.data.csrf_token,
            "If-Match": `"${dossier.application.review_revision}"`,
            "Idempotency-Key": actionKey(body),
          },
          body,
        },
      );
      if (result.data) router.refresh();
      else
        setError(
          result.response.status === 409
            ? "Une analyse est active ou le dossier a changé. Rechargez la fiche."
            : "La relance a été refusée. Vérifiez les sources sélectionnées.",
        );
    } catch {
      setError(
        "La réponse est incertaine. Réessayez la même demande ou actualisez le traitement.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="review-section">
      <h2>Relancer l’analyse</h2>
      <p>
        Une nouvelle analyse conservera le résultat effectif jusqu’à son
        activation. Les sources déjà recueillies seront réutilisées.
      </p>
      {active ? (
        <p role="status">
          Une analyse est déjà en cours. Consultez sa progression puis
          actualisez la fiche.
        </p>
      ) : (
        <>
          {failed.length > 0 && (
            <fieldset className="question-choices">
              <legend>Sources à récupérer à nouveau</legend>
              {failed.map((source) => (
                <label className="source-choice" key={source.id}>
                  <input
                    type="checkbox"
                    disabled={busy}
                    checked={selected.includes(source.id)}
                    onChange={(e) =>
                      setSelected((current) =>
                        e.target.checked
                          ? [...current, source.id]
                          : current.filter((id) => id !== source.id),
                      )
                    }
                  />
                  {dossier.uploads?.find((f) => f.id === source.upload_id)
                    ?.filename ??
                    dossier.snapshot.configuration.questions.find(
                      (q) => q.id === source.question_ids[0],
                    )?.label ??
                    "Source indisponible"}
                </label>
              ))}
            </fieldset>
          )}
          <div className="inline-actions">
            {failed.length > 0 && (
              <Button
                disabled={busy || !selected.length}
                onClick={() => request("retry_sources")}
              >
                Relancer les sources sélectionnées
              </Button>
            )}
            <Button
              variant="secondary"
              disabled={busy || !baseRun}
              onClick={() => request("reanalyze")}
            >
              Relancer l’évaluation
            </Button>
          </div>
        </>
      )}
      {error && <Alert tone="danger">{error}</Alert>}
    </section>
  );
}
