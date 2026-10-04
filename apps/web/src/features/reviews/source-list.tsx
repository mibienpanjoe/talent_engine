import type { components } from "../../lib/api.generated";
type Detail = components["schemas"]["ApplicationDetail"];
const groups = [
  { kind: "document", label: "Documents" },
  { kind: "portfolio", label: "Pages publiques" },
  { kind: "github", label: "Dépôts GitHub" },
  { kind: "answer", label: "Réponses au formulaire" },
  { kind: "human_note", label: "Observations humaines" },
] as const;

export function SourceList({ dossier }: { dossier: Detail }) {
  const uploads = dossier.uploads ?? [];
  const questions = dossier.snapshot.configuration.questions;
  return (
    <section className="review-section" aria-labelledby="sources-title">
      <h2 id="sources-title">Documents et sources du dossier</h2>
      <p>Vérifiez les éléments disponibles et consultez leurs originaux. Les passages cités pour chaque critère se trouvent dans « Appréciations et preuves ».</p>
      {groups.map(group => {
        const sources = (dossier.sources ?? []).filter(source => source.kind === group.kind);
        if (!sources.length) return null;
        const unavailable = sources.filter(source => source.state !== "available").length;
        return (
          <details className="source-group" key={group.kind} open={group.kind !== "answer" || unavailable > 0}>
            <summary>{group.label} · {sources.length}{unavailable > 0 && <span className="source-warning"> · {unavailable} à vérifier</span>}</summary>
            <ul className="source-status-list">
              {sources.map((source) => {
                const file = uploads.find((f) => f.id === source.upload_id);
                const question = questions.find(
                  (q) => q.id === source.question_ids[0],
                );
                return (
                  <li key={source.id}>
                    <h3 className="source-title">
                      {file?.filename ?? question?.label ?? (source.kind === "human_note" ? "Observation du reviewer" : "Source du dossier")}
                    </h3>
                    <p className={`source-reading-status source-reading-status--${source.state}`}>
                      {source.state === "available"
                        ? source.kind === "human_note" ? "Observation enregistrée" : "Contenu disponible pour l’analyse"
                        : source.state === "unreadable"
                          ? "Le contenu n’a pas pu être lu"
                          : source.error_code === "external_retrieval_pending"
                            ? "Lien reçu, contenu pas encore récupéré"
                            : source.state === "blocked" ? "Accès bloqué" : "Contenu indisponible"}
                      {source.ocr_pages.length > 0 &&
                        ` · ${source.ocr_pages.length} page(s) nécessitant une transcription.`}
                    </p>
                    <div className="inline-actions source-links">
                      {file && (
                        <a href={`/api/v1/uploads/${file.id}/download`} target="_blank" rel="noopener noreferrer">
                          Consulter le document original ↗
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
                          Consulter la page recueillie ↗
                        </a>
                      )}
                      {source.extraction_metadata?.github?.commit && (
                        <a href={`${source.extraction_metadata.github.repository}/tree/${source.extraction_metadata.github.commit}`} target="_blank" rel="noopener noreferrer">
                          Consulter le dépôt analysé ↗
                        </a>
                      )}
                    </div>
                    {source.extraction_metadata?.github && <p>La contribution personnelle du candidat reste à vérifier.</p>}
                    {source.extraction_metadata?.ocr?.some(
                      (attempt) => attempt.status === "succeeded",
                    ) && (
                      <p>
                        Document transcrit automatiquement à partir d’images. Consultez l’original pour vérifier
                        la transcription.
                      </p>
                    )}
                    <details className="provenance-details">
                      <summary>Détails de la collecte</summary>
                      <p>Méthode de lecture : {source.extractor_version}</p>
                      {source.extraction_metadata?.github && (
                        <>
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
          </details>
        );
      })}
    </section>
  );
}
