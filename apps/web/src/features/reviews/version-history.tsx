"use client";
import { useState } from "react";
import type { components } from "../../lib/api.generated";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Alert } from "../../components/ui/alert";
import { ActivationEditor } from "./activation-editor";
import { EvidenceButton } from "./evidence-button";
import { assessmentLabels, displayDecimal } from "./labels";
type Detail = components["schemas"]["ApplicationDetail"];
export function VersionHistory({ dossier }: { dossier: Detail }) {
  const [versions, setVersions] =
    useState<components["schemas"]["EvaluationVersion"][]>();
  const [history, setHistory] = useState<
    components["schemas"]["ReviewEvent"][]
  >([]);
  const [next, setNext] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function load(cursor?: string) {
    setBusy(true);
    setError("");
    try {
      const params = {
        params: { path: { application_id: dossier.application.id } },
      };
      const [result, changes] = await Promise.all([
        api.GET("/api/v1/applications/{application_id}/evaluation-versions", {
          ...params,
          params: { ...params.params, query: { cursor } },
        }),
        api.GET("/api/v1/applications/{application_id}/review-history", {
          ...params,
          params: { ...params.params, query: { active_only: true } },
        }),
      ]);
      if (!result.data || !changes.data) throw new Error();
      setVersions((current) =>
        cursor ? [...(current ?? []), ...result.data!] : result.data,
      );
      setNext(result.response.headers.get("X-Next-Cursor"));
      setHistory(changes.data);
    } catch {
      setError("Les versions n’ont pas pu être chargées. Réessayez.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="review-section">
      <h2>Versions de l’évaluation</h2>
      {(dossier.pending_evaluation_ids?.length ?? 0) > 0 && (
        <p role="status">
          Une nouvelle base est disponible à comparer. Le résultat effectif et
          ses corrections restent affichés.
        </p>
      )}
      <Button variant="secondary" disabled={busy} onClick={() => load()}>
        {busy ? "Chargement…" : "Comparer les analyses"}
      </Button>
      {next && (
        <Button variant="secondary" disabled={busy} onClick={() => load(next)}>
          Analyses plus anciennes
        </Button>
      )}
      {error && <Alert tone="danger">{error}</Alert>}
      {versions &&
        (versions.length ? (
          versions.map((version) => (
            <article className="criterion-result" key={version.base.id}>
              <h3>
                Analyse du{" "}
                {new Date(version.base.created_at).toLocaleString("fr-FR", {
                  timeZone: "UTC",
                })}{" "}
                UTC
                {version.base.id === dossier.application.effective_evaluation_id
                  ? " · effective"
                  : ""}
              </h3>
              <p>
                Base automatique :{" "}
                {version.base.calculation.score === null
                  ? "Évaluation partielle"
                  : `${displayDecimal(version.base.calculation.score, true)} / 100`}{" "}
                · couverture {displayDecimal(version.base.calculation.coverage)}{" "}
                %.
              </p>
              {version.corrected && (
                <p>
                  Avec corrections :{" "}
                  {version.corrected.calculation.score === null
                    ? "Évaluation partielle"
                    : `${displayDecimal(version.corrected.calculation.score, true)} / 100`}{" "}
                  · couverture{" "}
                  {displayDecimal(version.corrected.calculation.coverage)} %.
                </p>
              )}
              <details>
                <summary>Appréciations automatiques et preuves</summary>
                {version.base.assessments.map((item) => (
                  <div className="criterion-result" key={item.criterion_id}>
                    <h4>
                      {
                        dossier.snapshot.configuration.requirements.find(
                          (r) => r.id === item.criterion_id,
                        )?.expectation
                      }
                    </h4>
                    <p>
                      {item.level === null
                        ? assessmentLabels[item.status]
                        : `Niveau ${item.level} / 4`}{" "}
                      · {item.rationale}
                    </p>
                    <div className="inline-actions">
                      {item.evidence_ids.map((id, i) => (
                        <EvidenceButton
                          key={id}
                          id={id}
                          label={`Preuve ${i + 1}`}
                        />
                      ))}
                    </div>
                  </div>
                ))}
                {version.base.conditions.map((item) => (
                  <p key={item.criterion_id}>
                    {
                      dossier.snapshot.configuration.requirements.find(
                        (r) => r.id === item.criterion_id,
                      )?.expectation
                    }{" "}
                    :{" "}
                    {item.status === "met"
                      ? "Satisfaite"
                      : item.status === "unmet"
                        ? "Non satisfaite"
                        : "À vérifier"}
                    .
                  </p>
                ))}
              </details>
              {dossier.pending_evaluation_ids?.includes(version.base.id) && (
                <ActivationEditor
                  dossier={dossier}
                  version={version}
                  history={history}
                />
              )}
            </article>
          ))
        ) : (
          <p>Aucune évaluation terminée.</p>
        ))}
    </section>
  );
}
