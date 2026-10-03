"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Alert } from "../../components/ui/alert";
import { Button } from "../../components/ui/button";
import { api } from "../../lib/api";
export function LogoutButton() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  async function logout() {
    setPending(true); setError("");
    try {
      const { data, response: sessionResponse } = await api.GET("/api/v1/access/csrf", { signal: AbortSignal.timeout(5000) });
      if (sessionResponse.status === 401) { router.replace("/login"); router.refresh(); return; }
      if (!data) throw new Error("CSRF unavailable");
      const { response } = await api.DELETE("/api/v1/access/session", {
        headers: { "X-CSRF-Token": data.csrf_token }, signal: AbortSignal.timeout(5000),
      });
      if (response.status !== 204 && response.status !== 401) throw new Error("Logout unavailable");
      router.replace("/login"); router.refresh();
    } catch { setError("Déconnexion impossible. Réessayez dans un instant."); }
    finally { setPending(false); }
  }
  return <div className="logout-controls">{error && <Alert>{error}</Alert>}<Button disabled={pending} onClick={() => void logout()}>{pending ? "Déconnexion…" : "Se déconnecter"}</Button></div>;
}
