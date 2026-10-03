"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../lib/api";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    setPending(true); setError("");
    const form = new FormData(event.currentTarget);
    try {
      const { data, response } = await api.POST("/api/v1/access/session", {
        body: { login: String(form.get("login")), password: String(form.get("password")) },
        signal: AbortSignal.timeout(10000),
      });
      if (data) { router.replace("/review"); router.refresh(); return; }
      setError(response.status === 429 ? "Trop de tentatives. Réessayez dans quelques minutes." : "Connexion impossible. Vérifiez vos identifiants.");
    } catch { setError("Le service est indisponible. Réessayez dans un instant."); }
    finally { setPending(false); }
  }
  return <form onSubmit={submit} aria-busy={pending}>
    <label htmlFor="login">Identifiant</label>
    <input id="login" name="login" autoComplete="username" required maxLength={200} />
    <label htmlFor="password">Mot de passe</label>
    <input id="password" name="password" type="password" autoComplete="current-password" required maxLength={1024} />
    {error && <p role="alert">{error}</p>}
    <button type="submit" disabled={pending}>{pending ? "Connexion…" : "Se connecter"}</button>
  </form>;
}
