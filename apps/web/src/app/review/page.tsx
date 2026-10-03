import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import createClient from "openapi-fetch";
import type { paths } from "../../lib/api.generated";
import { LogoutButton } from "../../features/access/logout-button";

export default async function ReviewPage() {
  const client = createClient<paths>({ baseUrl: process.env.TALENT_API_ORIGIN ?? "http://127.0.0.1:8000" });
  const { data, response } = await client.GET("/api/v1/access/session", {
    headers: { Cookie: (await cookies()).toString() }, cache: "no-store", signal: AbortSignal.timeout(5000),
  });
  if (response.status === 401) redirect("/login");
  if (!data) throw new Error("Private space unavailable");
  return <main id="main"><p className="eyebrow">TALENT ENGINE</p><h1>Bienvenue dans votre espace.</h1><p>Connecté en tant que {data.login}.</p><p>Vos campagnes et vos dossiers seront regroupés ici.</p><LogoutButton /></main>;
}
