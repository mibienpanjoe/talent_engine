import "server-only";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import createClient from "openapi-fetch";
import type { paths } from "./api.generated";
export async function reviewerApi() {
  const client = createClient<paths>({
    baseUrl: process.env.TALENT_API_ORIGIN ?? "http://127.0.0.1:8000",
    headers: { Cookie: (await cookies()).toString() },
    cache: "no-store",
  });
  const { data, response } = await client.GET("/api/v1/access/session", {
    signal: AbortSignal.timeout(5000),
  });
  if (response.status === 401) redirect("/login");
  if (!data) throw new Error("Private space unavailable");
  return { client, reviewer: data };
}
