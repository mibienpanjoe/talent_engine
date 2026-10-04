import { notFound } from "next/navigation";
import { reviewerApi } from "../../../../lib/server-api";
import { SiteHeader } from "../../../../components/site-header";
import { AccountDialog } from "../../../../features/access/account-dialog";
import { DraftEditor } from "../../../../features/campaigns/draft-editor";
export default async function CampaignPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { client, reviewer } = await reviewerApi();
  const { id } = await params;
  const result = await client.GET("/api/v1/campaigns/{campaign_id}", {
    params: { path: { campaign_id: id } },
    signal: AbortSignal.timeout(5000),
  });
  if (result.response.status === 404 || result.response.status === 422)
    notFound();
  if (!result.data) throw new Error("Campaign unavailable");
  return (
    <>
      <SiteHeader>
        <AccountDialog login={reviewer.login} expiresAt={reviewer.expires_at} />
      </SiteHeader>
      <main id="main" className="page-width">
        <DraftEditor key={result.data.revision} initial={result.data} />
      </main>
    </>
  );
}
