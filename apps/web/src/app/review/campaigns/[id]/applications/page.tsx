import { CleanupStatus } from "../../../../../features/reviews/cleanup-status";
import Link from "next/link";
import { notFound } from "next/navigation";
import { reviewerApi } from "../../../../../lib/server-api";
import { SiteHeader } from "../../../../../components/site-header";
import { AccountDialog } from "../../../../../features/access/account-dialog";
import { RefreshButton } from "../../../../../features/campaigns/refresh-button";
import { Button } from "../../../../../components/ui/button";
import {
  viewLabels,
  decisionLabels,
  processingLabels,
  eligibilityLabels,
  displayDecimal,
} from "../../../../../features/reviews/labels";

type Search = {
  cursor?: string;
  view?: string;
  decision?: string;
  processing_state?: string;
};
function known<T extends object>(
  value: string | undefined,
  choices: T,
): keyof T | undefined {
  return value && Object.hasOwn(choices, value)
    ? (value as keyof T)
    : undefined;
}
export default async function ApplicationsPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<Search>;
}) {
  const { id } = await params;
  const search = await searchParams;
  const view = known(search.view, viewLabels) ?? "all";
  const decision = known(search.decision, decisionLabels);
  const processingState = known(search.processing_state, processingLabels);
  function url(nextView = view, cursor?: string) {
    const query = new URLSearchParams({ view: nextView });
    if (decision) query.set("decision", decision);
    if (processingState) query.set("processing_state", processingState);
    if (cursor) query.set("cursor", cursor);
    return `/review/campaigns/${id}/applications?${query}`;
  }
  const { client, reviewer } = await reviewerApi();
  const [result, cleanups] = await Promise.all([
    client.GET("/api/v1/campaigns/{campaign_id}/applications", {
      params: {
        path: { campaign_id: id },
        query: {
          limit: 25,
          view,
          ...(decision ? { decision } : {}),
          ...(processingState ? { processing_state: processingState } : {}),
          ...(search.cursor ? { cursor: search.cursor } : {}),
        },
      },
      signal: AbortSignal.timeout(5000),
    }),
    client
      .GET("/api/v1/campaigns/{campaign_id}/cleanup-requests", {
        params: { path: { campaign_id: id } },
        signal: AbortSignal.timeout(5000),
      })
      .catch(() => ({ data: undefined })),
  ]);

  if (result.response.status === 404 || result.response.status === 422)
    notFound();
  const changed =
    result.error?.error.code === "cursor_invalidated" ||
    result.error?.error.code === "invalid_cursor";
  if (!result.data && !changed) throw new Error("Applications unavailable");
  return (
    <>
      <SiteHeader>
        <AccountDialog login={reviewer.login} expiresAt={reviewer.expires_at} />
      </SiteHeader>
      <main id="main" className="page-width">
        <Link href={`/review/campaigns/${id}`}>← La campagne</Link>
        <h1>Candidatures reçues</h1>
        {cleanups.data && <CleanupStatus requests={cleanups.data} />}
        {changed ? (
          <section className="empty-state">
            <h2>La liste a changé.</h2>
            <p>Les dossiers ou leur traitement ont évolué depuis cette page.</p>
            <Link href={url()}>Recharger les candidatures</Link>
          </section>
        ) : (
          result.data && (
            <>
              <p>
                {result.data.counts.all} dossier(s) reçu(s) dans la campagne.
                Les essais privés sont exclus.
              </p>
              <nav className="review-views" aria-label="Files de revue">
                {Object.entries(viewLabels).map(([key, label]) => (
                  <Link
                    key={key}
                    href={url(key as keyof typeof viewLabels)}
                    aria-current={key === view ? "page" : undefined}
                  >
                    {label}
                    <span>{result.data!.counts[key] ?? 0}</span>
                  </Link>
                ))}
              </nav>
              <form
                className="review-filters"
                action={`/review/campaigns/${id}/applications`}
                method="get"
              >
                <input type="hidden" name="view" value={view} />
                <div className="ui-field">
                  <label htmlFor="review-decision">Décision humaine</label>
                  <select
                    id="review-decision"
                    name="decision"
                    className="ui-input"
                    defaultValue={decision ?? ""}
                  >
                    <option value="">Toutes les décisions</option>
                    {Object.entries(decisionLabels).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="ui-field">
                  <label htmlFor="review-processing">Traitement</label>
                  <select
                    id="review-processing"
                    name="processing_state"
                    className="ui-input"
                    defaultValue={processingState ?? ""}
                  >
                    <option value="">Tous les états</option>
                    {Object.entries(processingLabels).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
                <Button variant="secondary" type="submit">
                  Appliquer
                </Button>
              </form>
              <RefreshButton />
              {result.data.items.length === 0 ? (
                <section className="empty-state">
                  <h2>
                    {result.data.counts.all === 0
                      ? "Aucun dossier reçu."
                      : "Aucun dossier dans cette vue."}
                  </h2>
                  <p>
                    {result.data.counts.all === 0
                      ? "Les candidatures apparaîtront après leur réception."
                      : "Choisissez une autre file ou ajustez les filtres."}
                  </p>
                </section>
              ) : (
                <ul className="review-list">
                  {result.data.items.map((a) => (
                    <li key={a.id}>
                      <header>
                        <Link href={`/review/applications/${a.id}`}>
                          {a.contact.name}
                        </Link>
                        {a.rank !== null && a.rank !== undefined && (
                          <span>Rang {a.rank}</span>
                        )}
                      </header>
                      {a.evaluation_mode === "preloaded" && (
                        <p className="preloaded-notice">Exemple préchargé</p>
                      )}
                      <dl className="review-row">
                        <div>
                          <dt>Évaluation</dt>
                          <dd>
                            {!a.calculation
                              ? "Évaluation indisponible"
                              : a.calculation.score === null
                                ? "Évaluation partielle"
                                : `${displayDecimal(a.calculation.score, true)} / 100`}
                          </dd>
                          {a.calculation && (
                            <p>
                              Couverture{" "}
                              {displayDecimal(a.calculation.coverage)} %
                            </p>
                          )}
                        </div>
                        <div>
                          <dt>Disponibilité</dt>
                          <dd>
                            {a.eligibility
                              ? eligibilityLabels[a.eligibility]
                              : "En attente de vérification"}
                          </dd>
                        </div>
                        <div>
                          <dt>Décision humaine</dt>
                          <dd>{decisionLabels[a.decision]}</dd>
                        </div>
                        <div>
                          <dt>Traitement</dt>
                          <dd>{processingLabels[a.processing_state]}</dd>
                        </div>
                      </dl>
                    </li>
                  ))}
                </ul>
              )}
              {result.data.next_cursor && (
                <Link href={url(view, result.data.next_cursor)}>
                  Dossiers suivants
                </Link>
              )}
            </>
          )
        )}
      </main>
    </>
  );
}
