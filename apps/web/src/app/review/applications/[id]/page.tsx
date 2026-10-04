import { SourceList } from "../../../../features/reviews/source-list";
import { DeleteApplication } from "../../../../features/reviews/delete-application";
import Link from "next/link";
import { notFound } from "next/navigation";
import { reviewerApi } from "../../../../lib/server-api";
import { SiteHeader } from "../../../../components/site-header";
import { AccountDialog } from "../../../../features/access/account-dialog";
import { PolicyDetails } from "../../../../features/campaigns/policy-details";
import { EvaluationDetails } from "../../../../features/reviews/evaluation-details";
import { AnalysisActions } from "../../../../features/reviews/analysis-actions";
import { VersionHistory } from "../../../../features/reviews/version-history";
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
          {a.mode === "test"
            ? "Essai privé"
            : result.data.effective_evaluation?.provenance.mode === "preloaded"
              ? "Dossier de démonstration"
              : "Candidature reçue"}
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
        <AnalysisActions
          key={`analysis:${a.review_revision}`}
          dossier={result.data}
        />
        <VersionHistory
          key={`versions:${a.review_revision}`}
          dossier={result.data}
        />
        <div className="inline-actions dossier-tools">
          <RefreshButton />
          <PolicyDetails snapshotId={a.snapshot_id} />
        </div>
        <DeleteApplication
          key={`delete:${a.review_revision}`}
          application={a}
        />
        {(result.data.sources?.length ?? 0) > 0 && <SourceList dossier={result.data} />}
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
