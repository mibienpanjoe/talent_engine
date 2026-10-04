import Link from "next/link";
import { reviewerApi } from "../../lib/server-api";
import { SiteHeader } from "../../components/site-header";
import { Button } from "../../components/ui/button";
import { AccountDialog } from "../../features/access/account-dialog";
export default async function ReviewPage({
  searchParams,
}: {
  searchParams: Promise<{ cursor?: string }>;
}) {
  const { client, reviewer } = await reviewerApi();
  const { cursor } = await searchParams;
  const result = await client.GET("/api/v1/campaigns", {
    params: { query: { limit: 25, ...(cursor ? { cursor } : {}) } },
    signal: AbortSignal.timeout(5000),
  });
  if (!result.data) throw new Error("Campaigns unavailable");
  return (
    <>
      <SiteHeader>
        <AccountDialog login={reviewer.login} expiresAt={reviewer.expires_at} />
      </SiteHeader>
      <main id="main" className="page-width workspace">
        <p className="eyebrow">Espace responsable</p>
        <h1>Mes campagnes</h1>
        <Button asChild>
          <Link href="/review/campaigns/new">Créer une campagne</Link>
        </Button>
        {result.data.items.length === 0 ? (
          <section className="empty-state">
            <h2>Votre première campagne commence ici.</h2>
            <p>Décrivez le besoin et les questions à poser aux candidats.</p>
          </section>
        ) : (
          <ul className="campaign-list">
            {result.data.items.map((c) => (
              <li key={c.id}>
                <Link href={`/review/campaigns/${c.id}`}>
                  {c.display_title ||
                    c.configuration.title ||
                    "Brouillon sans titre"}
                </Link>
                <span>
                  {
                    {
                      draft: "Brouillon",
                      published: "Publiée",
                      closed: "Fermée",
                    }[c.state]
                  }
                </span>
              </li>
            ))}
          </ul>
        )}
        {result.data.next_cursor && (
          <Link href={`/review?cursor=${result.data.next_cursor}`}>
            Campagnes suivantes
          </Link>
        )}
      </main>
    </>
  );
}
