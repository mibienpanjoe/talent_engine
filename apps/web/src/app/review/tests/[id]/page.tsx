import { notFound } from "next/navigation";
import { reviewerApi } from "../../../../lib/server-api";
import { SiteHeader } from "../../../../components/site-header";
import { PublicFormView } from "../../../../features/campaigns/public-form-view";
export default async function TestPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { client } = await reviewerApi();
  const result = await client.GET("/api/v1/test-snapshots/{snapshot_id}", {
    params: { path: { snapshot_id: id } },
    signal: AbortSignal.timeout(5000),
  });
  if (result.response.status === 404) notFound();
  if (!result.data) throw new Error("Test unavailable");
  return (
    <>
      <SiteHeader />
      <main id="main" className="page-width campaign-editor">
        <PublicFormView key={result.data.snapshot_id} form={result.data} test />
      </main>
    </>
  );
}
