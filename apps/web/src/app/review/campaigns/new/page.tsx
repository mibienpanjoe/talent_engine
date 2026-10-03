import { reviewerApi } from "../../../../lib/server-api";
import { SiteHeader } from "../../../../components/site-header";
import { AccountDialog } from "../../../../features/access/account-dialog";
import { DraftEditor } from "../../../../features/campaigns/draft-editor";
export default async function NewCampaign() {
  const { reviewer } = await reviewerApi();
  return (
    <>
      <SiteHeader>
        <AccountDialog login={reviewer.login} expiresAt={reviewer.expires_at} />
      </SiteHeader>
      <main id="main" className="page-width">
        <DraftEditor initial={null} />
      </main>
    </>
  );
}
