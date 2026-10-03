import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import createClient from "openapi-fetch";
import { FolderOpen } from "lucide-react";
import type { paths } from "../../lib/api.generated";
import { AccountDialog } from "../../features/access/account-dialog";
import { SiteHeader } from "../../components/site-header";
export default async function ReviewPage() {
  const client = createClient<paths>({ baseUrl: process.env.TALENT_API_ORIGIN ?? "http://127.0.0.1:8000" });
  const { data, response } = await client.GET("/api/v1/access/session", {
    headers: { Cookie: (await cookies()).toString() }, cache: "no-store", signal: AbortSignal.timeout(5000),
  });
  if (response.status === 401) redirect("/login");
  if (!data) throw new Error("Private space unavailable");
  return <><SiteHeader><AccountDialog login={data.login} expiresAt={data.expires_at} /></SiteHeader><main id="main" className="page-width workspace"><p className="eyebrow">Espace responsable</p><h1>Bienvenue dans votre espace.</h1><section className="empty-state" aria-labelledby="space-title"><FolderOpen size={32} strokeWidth={1.5} aria-hidden="true" /><h2 id="space-title">Une vue d’ensemble pour votre revue.</h2><p>Vos campagnes et vos dossiers seront regroupés ici.</p></section></main></>;
}
