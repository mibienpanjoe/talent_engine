import { notFound } from "next/navigation";
import createClient from "openapi-fetch";
import type { paths } from "../../../lib/api.generated";
import { SiteHeader } from "../../../components/site-header";
import { PublicFormView } from "../../../features/campaigns/public-form-view";
export default async function ApplyPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  const client = createClient<paths>({
    baseUrl: process.env.TALENT_API_ORIGIN ?? "http://127.0.0.1:8000",
  });
  const result = await client.GET("/api/v1/public/campaigns/{public_token}", {
    params: { path: { public_token: token } },
    cache: "no-store",
    signal: AbortSignal.timeout(5000),
  });
  if (result.response.status === 404) notFound();
  if (!result.data) throw new Error("Form unavailable");
  return (
    <>
      <SiteHeader />
      <main id="main" className="page-width campaign-editor">
        <PublicFormView key={result.data.snapshot_id} form={result.data} />
      </main>
    </>
  );
}
