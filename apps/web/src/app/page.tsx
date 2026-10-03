"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
export default function Home() {
  const [status, setStatus] = useState("Vérification du service…");
  async function check() {
    setStatus("Vérification du service…");
    try {
      const { data } = await api.GET("/api/v1/health/ready", { signal: AbortSignal.timeout(5000) });
      setStatus(data?.status === "ready" ? "Service disponible" : "Service indisponible. Réessayez dans un instant.");
    } catch { setStatus("Service indisponible. Réessayez dans un instant."); }
  }
  useEffect(() => { void check(); }, []);
  return <main id="main"><p className="eyebrow">TALENT ENGINE</p><h1>Chaque talent mérite<br />une lecture attentive.</h1><p>Des preuves pour éclairer votre évaluation.<br />La décision reste entre vos mains.</p><div role="status" aria-live="polite">{status}</div><button onClick={() => void check()}>Vérifier à nouveau</button></main>;
}
