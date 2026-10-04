import Link from "next/link";
import { notFound } from "next/navigation";
import { reviewerApi } from "../../../../lib/server-api";
import { SiteHeader } from "../../../../components/site-header";
import { AccountDialog } from "../../../../features/access/account-dialog";
import { PolicyDetails } from "../../../../features/campaigns/policy-details";
import { EvaluationDetails } from "../../../../features/reviews/evaluation-details";
import { DecisionEditor } from "../../../../features/reviews/decision-editor";
import { ReviewHistory } from "../../../../features/reviews/review-history";
import { RefreshButton } from "../../../../features/campaigns/refresh-button";
export default async function ApplicationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { client, reviewer } = await reviewerApi();
  const result = await client.GET("/api/v1/applications/{application_id}", {
    params: { path: { application_id: id } },
    signal: AbortSignal.timeout(5000),
  });
  if (result.response.status === 404 || result.response.status === 422)
    notFound();
  if (!result.data) throw new Error("Application unavailable");
  const {
    application: a,
    answers,
    snapshot,
    uploads = [],
    analyses = [],
  } = result.data;
  const questions = snapshot.configuration.questions;
  return (
    <>
      <SiteHeader>
        <AccountDialog login={reviewer.login} expiresAt={reviewer.expires_at} />
      </SiteHeader>
      <main id="main" className="page-width campaign-editor">
        <Link href={`/review/campaigns/${a.campaign_id}/applications`}>
          ← Les dossiers
        </Link>
        <p className="eyebrow">
          {a.mode === "test" ? "Essai privé" : "Candidature réelle"}
        </p>
        <h1>{a.contact.name}</h1>
        <p>{a.contact.email}</p>
        <p>
          {snapshot.configuration.title} · version {snapshot.version}
        </p>
        <p role="status">
          {
            {
              queued: "Reçue, en attente d’analyse.",
              collecting: "Collecte en cours.",
              evaluating: "Évaluation en cours.",
              completed: "Analyse disponible.",
              completed_partial: "Analyse partielle.",
              failed:
                "Un incident de traitement est survenu. Le dossier reste enregistré.",
            }[a.processing_state]
          }
        </p>
        <DecisionEditor key={`decision:${a.review_revision}`} application={a} />
        <EvaluationDetails dossier={result.data} />
        <ReviewHistory
          key={`history:${a.review_revision}`}
          dossier={result.data}
        />
        <section aria-label="Progression du traitement" className="empty-state">
          <h2>Traitement du dossier</h2>
          {analyses.length === 0 ? (
            <p>La tâche est enregistrée, en attente d’acquisition.</p>
          ) : (
            analyses.map((run) => (
              <section key={run.id}>
                {run.error_code && (
                  <p role="alert">
                    {["evaluation_unavailable", "llm_not_configured"].includes(
                      run.error_code,
                    )
                      ? "Le service d’évaluation n’est pas configuré. Vos données restent enregistrées."
                      : run.error_code === "attempts_exhausted"
                        ? "Les trois tentatives de traitement ont été épuisées. Le dossier reste enregistré."
                        : "Une étape du traitement a échoué. Le dossier reste enregistré."}
                  </p>
                )}
                {run.next_attempt_at && (
                  <p>
                    Nouvelle tentative prévue le{" "}
                    {new Date(run.next_attempt_at).toLocaleString("fr-FR", {
                      timeZone: "UTC",
                    })}{" "}
                    UTC.
                  </p>
                )}
                <ol>
                  {run.steps.map((step) => (
                    <li key={step.name}>
                      {(
                        {
                          extract_answers: "Réponses",
                          source_manifest: "Sources reçues",
                          evaluate: "Évaluation",
                        } as Record<string, string>
                      )[step.name] ?? "Traitement"}
                      {" : "}
                      {
                        (
                          {
                            queued: "en attente",
                            running: "en cours",
                            waiting: "reprise programmée",
                            succeeded: "enregistrées",
                            failed: "incident",
                          } as Record<string, string>
                        )[step.state]
                      }
                      {step.attempts > 0 && ` · tentative ${step.attempts}/3`}
                      {step.error_code === "provider_rate_limited" &&
                        " · quota fournisseur atteint"}
                    </li>
                  ))}
                </ol>
              </section>
            ))
          )}
        </section>
        <RefreshButton />
        <PolicyDetails snapshotId={a.snapshot_id} />
        {(result.data.pending_evaluation_ids?.length ?? 0) > 0 && (
          <p>
            Une nouvelle analyse est disponible, en attente d’activation. Le
            résultat effectif reste celui affiché ci-dessus.
          </p>
        )}
        {(result.data.sources?.length ?? 0) > 0 && (
          <section className="review-section">
            <h2>Sources de cette analyse</h2>
            <ul className="source-status-list">
              {result.data.sources?.map((source) => {
                const file = uploads.find((f) => f.id === source.upload_id);
                const question = questions.find(
                  (q) => q.id === source.question_ids[0],
                );
                return (
                  <li key={source.id}>
                    <strong>
                      {file?.filename ?? question?.label ?? "Source du dossier"}
                    </strong>
                    <p>
                      {source.state === "available"
                        ? "Texte recueilli"
                        : source.state === "unreadable"
                          ? "Document illisible"
                          : source.error_code === "external_retrieval_pending"
                            ? "Lien reçu, récupération à effectuer"
                            : "Source indisponible"}
                      {source.ocr_pages.length > 0 &&
                        ` · OCR nécessaire pour ${source.ocr_pages.length} page(s) sans texte.`}
                    </p>
                    {file && (
                      <a href={`/api/v1/uploads/${file.id}/download`}>
                        Document original
                      </a>
                    )}
                    {source.extraction_metadata?.web?.find(
                      (page) => page.status === "succeeded",
                    ) && (
                      <a
                        href={
                          source.extraction_metadata.web.find(
                            (page) => page.status === "succeeded",
                          )!.url
                        }
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Page publique recueillie
                      </a>
                    )}
                    {source.extraction_metadata?.ocr?.some(
                      (attempt) => attempt.status === "succeeded",
                    ) && (
                      <p>
                        Texte obtenu par OCR. Consultez l’original pour vérifier
                        la transcription.
                      </p>
                    )}
                    <details className="provenance-details">
                      <summary>Version de la source</summary>
                      <p>{source.extractor_version}</p>
                      {source.extraction_metadata?.github && (
                        <>
                          <p>Contribution personnelle à vérifier séparément.</p>
                          <a
                            href={`${source.extraction_metadata.github.repository}/tree/${source.extraction_metadata.github.commit}`}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            Dépôt au commit recueilli
                          </a>
                          <p className="hash-text">
                            Commit : {source.extraction_metadata.github.commit}
                          </p>
                          <p>
                            Recueilli le{" "}
                            {new Date(
                              source.extraction_metadata.github.fetched_at,
                            ).toLocaleString("fr-FR", { timeZone: "UTC" })}{" "}
                            UTC.
                          </p>
                          {source.extraction_metadata.github.files.map(
                            (file) => (
                              <p key={file.path}>
                                {file.path} ·{" "}
                                {file.status === "succeeded"
                                  ? "Recueilli"
                                  : "Indisponible"}
                                {file.error_code && ` (${file.error_code})`}
                              </p>
                            ),
                          )}
                        </>
                      )}
                      {source.extraction_metadata?.web?.map((page, index) => (
                        <p key={index}>
                          {page.url} ·{" "}
                          {page.status === "succeeded"
                            ? "Recueillie"
                            : page.error_code === "url_blocked"
                              ? "Accès réseau bloqué"
                              : page.error_code === "source_javascript_required"
                                ? "Rendu JavaScript nécessaire, non pris en charge"
                                : page.error_code === "source_access_restricted"
                                  ? "Accès protégé"
                                  : "Page indisponible"}{" "}
                          ·{" "}
                          {new Date(page.fetched_at).toLocaleString("fr-FR", {
                            timeZone: "UTC",
                          })}{" "}
                          UTC.
                        </p>
                      ))}
                      <p className="hash-text">
                        Empreinte originale : {source.content_hash}
                      </p>
                      {source.extraction_metadata?.ocr?.map((attempt) => (
                        <p key={attempt.page}>
                          OCR · page {attempt.page} :{" "}
                          {attempt.status === "succeeded"
                            ? `${attempt.provider} / ${attempt.effective_model}`
                            : attempt.error_code === "provider_rate_limited"
                              ? "Quota fournisseur atteint"
                              : attempt.error_code === "llm_not_configured"
                                ? "Service OCR non configuré"
                                : attempt.error_code ===
                                    "source_budget_exceeded"
                                  ? "Budget de lecture atteint"
                                  : "Transcription indisponible"}
                          .
                        </p>
                      ))}
                    </details>
                  </li>
                );
              })}
            </ul>
          </section>
        )}
        <section className="empty-state">
          <h2>Réponses enregistrées</h2>
          {answers.map((answer) => {
            const q = questions.find((q) => q.id === answer.question_id);
            let text: string;
            if (answer.kind === "single_choice")
              text =
                q?.options?.find((o) => o.id === answer.value)?.label ??
                "Choix indisponible";
            else if (answer.kind === "multiple_choice")
              text =
                answer.value
                  .map(
                    (id) =>
                      q?.options?.find((o) => o.id === id)?.label ??
                      "Choix indisponible",
                  )
                  .join(", ") || "Aucun choix confirmé";
            else if (answer.kind === "file")
              text = `${answer.value.length} document(s)`;
            else text = String(answer.value);
            return (
              <section key={answer.question_id}>
                <h3>{q?.label ?? "Question"}</h3>
                <p className="preserve-lines">{text}</p>
                {answer.kind === "file" && (
                  <ul>
                    {uploads
                      .filter((file) => file.question_id === answer.question_id)
                      .map((file) => (
                        <li key={file.id}>
                          <a href={`/api/v1/uploads/${file.id}/download`}>
                            {file.filename}
                          </a>{" "}
                          · {Math.ceil(file.bytes / 1024)} Kio
                        </li>
                      ))}
                  </ul>
                )}
              </section>
            );
          })}
        </section>
      </main>
    </>
  );
}
