"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

async function checkService() {
  try {
    const { data } = await api.GET("/api/v1/health/ready", { signal: AbortSignal.timeout(5000) });
    return data?.status === "ready" ? "Service disponible" : "Service indisponible. Réessayez dans un instant.";
  } catch { return "Service indisponible. Réessayez dans un instant."; }
}

export default function Home() {
  const [status, setStatus] = useState("Vérification du service…");
  useEffect(() => {
    let cancelled = false;
    void checkService().then((result) => { if (!cancelled) setStatus(result); });
    return () => { cancelled = true; };
  }, []);
  return <main id="main"><p className="eyebrow">TALENT ENGINE</p><h1>Chaque talent mérite<br />une lecture attentive.</h1><p>Des preuves pour éclairer votre évaluation.<br />La décision reste entre vos mains.</p><div role="status" aria-live="polite">{status}</div><button onClick={() => { setStatus("Vérification du service…"); void checkService().then(setStatus); }}>Vérifier à nouveau</button></main>;
}
