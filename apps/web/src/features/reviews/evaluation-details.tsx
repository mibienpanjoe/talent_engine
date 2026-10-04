import type { components } from "../../lib/api.generated";
import { assessmentLabels, displayDecimal, eligibilityLabels } from "./labels";
import { EvidenceButton } from "./evidence-button";
type Detail = components["schemas"]["ApplicationDetail"];

export function EvaluationDetails({ dossier }: { dossier: Detail }) {
  const evaluation = dossier.effective_evaluation;
  if (!evaluation)
    return (
      <section className="review-section">
        <h2>Évaluation</h2>
        <p>Aucune évaluation disponible pour ce dossier.</p>
      </section>
    );
  const { calculation, provenance } = evaluation;
  const requirements = dossier.snapshot.configuration.requirements;
  function proof(id: string, index: number) {
    const excerpt = dossier.evidence?.find((e) => e.id === id);
    const source = dossier.sources?.find(
      (s) => s.id === excerpt?.source_version_id,
    );
    return (
      <EvidenceButton
        key={id}
        id={id}
        label={
          excerpt?.locator.kind === "pdf"
            ? `Preuve ${index + 1} · page ${excerpt.locator.page}`
            : `Preuve ${index + 1}`
        }
        uploadId={source?.upload_id}
      />
    );
  }
  return (
    <>
      <section className="review-section" aria-labelledby="evaluation-title">
        <h2 id="evaluation-title">Résultat effectif</h2>
        {provenance.mode === "preloaded" && (
          <p className="preloaded-notice">
            Exemple préchargé · {provenance.fixture_version}. Aucun appel modèle
            pour ce résultat.
          </p>
        )}
        <dl className="evaluation-metrics">
          <div>
            <dt>Évaluation</dt>
            <dd className="score-value">
              {calculation.score === null
                ? "Évaluation partielle"
                : `${displayDecimal(calculation.score, true)} / 100`}
            </dd>
          </div>
          <div>
            <dt>Couverture</dt>
            <dd>{displayDecimal(calculation.coverage)} %</dd>
          </div>
          <div>
            <dt>Disponibilité</dt>
            <dd>{eligibilityLabels[evaluation.eligibility]}</dd>
          </div>
          {dossier.application.rank !== null &&
            dossier.application.rank !== undefined && (
              <div>
                <dt>Rang parmi les prêts à examiner</dt>
                <dd>{dossier.application.rank}</dd>
              </div>
            )}
        </dl>
        {!calculation.complete && (
          <p>
            Bornes arithmétiques :{" "}
            {displayDecimal(calculation.lower_bound, true)} à{" "}
            {displayDecimal(calculation.upper_bound, true)} / 100. Elles
            indiquent les valeurs possibles selon les critères inconnus.
          </p>
        )}
        {calculation.alerts.length > 0 && (
          <ul className="review-alerts">
            {calculation.alerts.map((alert) => (
              <li key={alert.criterion_id}>
                {alert.code === "required_skill_unknown"
                  ? "Compétence indispensable à vérifier"
                  : "Compétence indispensable sous le seuil publié"}{" "}
                :{" "}
                {
                  requirements.find((r) => r.id === alert.criterion_id)
                    ?.expectation
                }
              </li>
            ))}
          </ul>
        )}
        {provenance.blocked_evidence_ids.length > 0 && (
          <p className="review-alerts">
            {provenance.blocked_evidence_ids.length} extrait(s) écarté(s)
            contenant des instructions adressées au modèle. Les documents
            originaux restent consultables.
          </p>
        )}
        {provenance.omitted_evidence_ids.length > 0 && (
          <p>
            {provenance.omitted_evidence_ids.length} extrait(s) supplémentaires
            non transmis au modèle lors de cette lecture ciblée. Consultez les
            documents originaux pour les vérifier.
          </p>
        )}
        <details className="provenance-details">
          <summary>Origine et précision de l’analyse</summary>
          <p>
            {provenance.mode === "preloaded"
              ? "Résultat fictif préchargé."
              : provenance.provider
                ? `Modèle effectif : ${provenance.provider} / ${provenance.effective_model}.`
                : "Traitement local, sans appel modèle."}
          </p>
          {provenance.requested_model && (
            <p>Modèle demandé : {provenance.requested_model}.</p>
          )}
          {provenance.retrieval && (
            <>
              <p>
                Recherche des passages : {provenance.retrieval.model} ·{" "}
                {provenance.retrieval.dimensions} dimensions.
              </p>
              <p>
                {provenance.evidence_ids.length} passage(s) transmis au modèle.{" "}
                {provenance.retrieval.cache_hits} vecteur(s) réutilisé(s),{" "}
                {provenance.retrieval.cache_misses} calculé(s).
              </p>
              <p>
                Cette lecture ciblée ne garantit pas une vérification exhaustive
                des sources.
              </p>
            </>
          )}
          <p>
            Politique : {evaluation.policy_version}. Consignes :{" "}
            {provenance.prompt_version}.
          </p>
          {calculation.score !== null && (
            <p>
              Score conservé : {calculation.score} / 100. Les rangs utilisent le
              rapport exact ; un affichage identique peut cacher une différence
              de précision.
            </p>
          )}
        </details>
      </section>
      <section className="review-section" aria-labelledby="criteria-title">
        <h2 id="criteria-title">Appréciations et preuves</h2>
        {evaluation.assessments.map((assessment) => (
          <article key={assessment.criterion_id} className="criterion-result">
            <h3>
              {requirements.find((r) => r.id === assessment.criterion_id)
                ?.expectation ?? "Exigence publiée"}
            </h3>
            <p className="criterion-level">
              {assessment.level === null
                ? assessmentLabels[assessment.status]
                : `Niveau ${assessment.level} / 4`}
            </p>
            <p>{assessment.rationale}</p>
            {assessment.uncertainties.length > 0 && (
              <ul>
                {assessment.uncertainties.map((uncertainty, i) => (
                  <li key={i}>{uncertainty}</li>
                ))}
              </ul>
            )}
            <div className="inline-actions">
              {assessment.evidence_ids.map(proof)}
            </div>
          </article>
        ))}
      </section>
      {evaluation.conditions.length > 0 && (
        <section className="review-section">
          <h2>Conditions de disponibilité</h2>
          {evaluation.conditions.map((condition) => {
            const question = dossier.snapshot.configuration.questions.find(
              (q) => q.id === condition.question_id,
            );
            const value = Array.isArray(condition.value)
              ? condition.value
                  .map(
                    (id) =>
                      question?.options?.find((o) => o.id === id)?.label ?? id,
                  )
                  .join(", ") || "Aucun créneau confirmé"
              : condition.value;
            return (
              <article
                key={condition.criterion_id}
                className="criterion-result"
              >
                <h3>
                  {
                    requirements.find((r) => r.id === condition.criterion_id)
                      ?.expectation
                  }
                </h3>
                <p>
                  {condition.status === "met"
                    ? "Satisfaite"
                    : condition.status === "unmet"
                      ? "Non satisfaite"
                      : "À vérifier"}{" "}
                  · {condition.required ? "Indispensable" : "Souhaitée"}
                </p>
                {value && <p>Réponse : {value}</p>}
                <p>{condition.rationale}</p>
                <div className="inline-actions">
                  {condition.evidence_ids?.map(proof)}
                </div>
              </article>
            );
          })}
        </section>
      )}
    </>
  );
}
