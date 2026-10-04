import Link from "next/link";
import { notFound } from "next/navigation";
import { reviewerApi } from "../../../../../lib/server-api";
import { SiteHeader } from "../../../../../components/site-header";
import { AccountDialog } from "../../../../../features/access/account-dialog";
import { RefreshButton } from "../../../../../features/campaigns/refresh-button";
export default async function ApplicationsPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ cursor?: string }>;
}) {
  const { id } = await params;
  const { cursor } = await searchParams;
  const { client, reviewer } = await reviewerApi();
  const result = await client.GET(
    "/api/v1/campaigns/{campaign_id}/applications",
    {
      params: {
        path: { campaign_id: id },
        query: { limit: 25, ...(cursor ? { cursor } : {}) },
      },
      signal: AbortSignal.timeout(5000),
    },
  );
  if (result.response.status === 404 || result.response.status === 422)
    notFound();
  if (result.error?.error.code === "cursor_invalidated")
    return (
      <>
        <SiteHeader>
          <AccountDialog
            login={reviewer.login}
            expiresAt={reviewer.expires_at}
          />
        </SiteHeader>
        <main id="main" className="page-width campaign-editor">
          <h1>La liste a changé.</h1>
          <p>De nouvelles candidatures ont été reçues depuis cette page.</p>
          <Link href={`/review/campaigns/${id}/applications`}>
            Recharger les candidatures
          </Link>
        </main>
      </>
    );
  if (!result.data) throw new Error("Applications unavailable");
  return (
    <>
      <SiteHeader>
        <AccountDialog login={reviewer.login} expiresAt={reviewer.expires_at} />
      </SiteHeader>
      <main id="main" className="page-width">
        <Link href={`/review/campaigns/${id}`}>← La campagne</Link>
        <h1>Candidatures reçues</h1>
        <p>
          {result.data.counts.all} dossier(s) réel(s). Les essais privés sont
          exclus.
        </p>
        <RefreshButton />
        {result.data.items.length === 0 ? (
          <section className="empty-state">
            <h2>Aucun dossier reçu.</h2>
            <p>Les candidatures apparaîtront après leur réception.</p>
          </section>
        ) : (
          <ul className="campaign-list">
            {result.data.items.map((a) => (
              <li key={a.id}>
                <Link href={`/review/applications/${a.id}`}>
                  {a.contact.name}
                </Link>
                <span>
                  {
                    {
                      queued: "En attente d’analyse",
                      collecting: "Collecte en cours",
                      evaluating: "Évaluation en cours",
                      completed: "Analyse disponible",
                      completed_partial: "Analyse partielle",
                      failed: "Incident de traitement",
                    }[a.processing_state]
                  }
                </span>
              </li>
            ))}
          </ul>
        )}
        {result.data.next_cursor && (
          <Link
            href={`/review/campaigns/${id}/applications?cursor=${result.data.next_cursor}`}
          >
            Dossiers suivants
          </Link>
        )}
      </main>
    </>
  );
}
