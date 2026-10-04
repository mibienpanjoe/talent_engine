import Link from "next/link";
import { notFound } from "next/navigation";
import { reviewerApi } from "../../../../lib/server-api";
import { SiteHeader } from "../../../../components/site-header";
import { AccountDialog } from "../../../../features/access/account-dialog";
import { PolicyDetails } from "../../../../features/campaigns/policy-details";
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
  const { application: a, answers, snapshot, uploads = [] } = result.data;
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
        <RefreshButton />
        <PolicyDetails snapshotId={a.snapshot_id} />
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
