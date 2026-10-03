"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, RefreshCw } from "lucide-react";
import { SiteHeader } from "../components/site-header";
import { Button } from "../components/ui/button";
import { api } from "../lib/api";
const checking = "Vérification du service…";
async function checkService() {
  try {
    const { data } = await api.GET("/api/v1/health/ready", { signal: AbortSignal.timeout(5000) });
    return data?.status === "ready" ? "Service disponible" : "Service indisponible. Réessayez dans un instant.";
  } catch { return "Service indisponible. Réessayez dans un instant."; }
}
export default function Home() {
  const [status, setStatus] = useState(checking);
  useEffect(() => {
    let cancelled = false;
    void checkService().then((result) => { if (!cancelled) setStatus(result); });
    return () => { cancelled = true; };
  }, []);
  return <><SiteHeader /><main id="main" className="page-width hero"><p className="eyebrow">Des preuves pour éclairer votre revue</p><h1>Des candidatures compréhensibles.</h1><p className="hero-copy">Reliez chaque appréciation à ses éléments justificatifs. Gardez les informations manquantes visibles et la décision entre vos mains.</p><Button asChild><Link href="/login">Accéder à mon espace<ArrowRight size={18} strokeWidth={2} aria-hidden="true" /></Link></Button><div className="hero-status"><div role="status" aria-live="polite">{status}</div><Button variant="ghost" disabled={status === checking} onClick={() => { setStatus(checking); void checkService().then(setStatus); }}><RefreshCw size={16} strokeWidth={1.5} aria-hidden="true" />Actualiser</Button></div></main></>;
}
