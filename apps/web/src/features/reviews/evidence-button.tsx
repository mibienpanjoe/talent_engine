"use client";
import { useState } from "react";
import { api } from "../../lib/api";
import type { components } from "../../lib/api.generated";
import { Button } from "../../components/ui/button";
import { Alert } from "../../components/ui/alert";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "../../components/ui/dialog";

export function EvidenceButton({
  id,
  label,
  uploadId,
}: {
  id: string;
  label: string;
  uploadId?: string | null;
}) {
  const [evidence, setEvidence] = useState<components["schemas"]["Evidence"]>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();
  async function load() {
    setLoading(true);
    setError(undefined);
    setEvidence(undefined);
    try {
      const result = await api.GET("/api/v1/evidence/{evidence_id}", {
        params: { path: { evidence_id: id } },
        signal: AbortSignal.timeout(5000),
      });
      if (result.data) setEvidence(result.data);
      else
        setError(
          result.response.status === 401
            ? "La session a expiré. Reconnectez-vous pour consulter la preuve."
            : "Cette preuve n’a pas pu être chargée. Fermez puis réessayez.",
        );
    } catch {
      setError("La preuve n’a pas pu être chargée. Fermez puis réessayez.");
    } finally {
      setLoading(false);
    }
  }
  return (
    <Dialog
      onOpenChange={(open) => {
        if (open) void load();
      }}
    >
      <DialogTrigger asChild>
        <Button variant="secondary">{label}</Button>
      </DialogTrigger>
      <DialogContent className="form-preview">
        <DialogTitle className="dialog-title">Preuve citée</DialogTitle>
        <DialogDescription className="dialog-description">
          Texte effectivement recueilli dans ce dossier.
        </DialogDescription>
        {loading && <p role="status">Chargement de la preuve…</p>}
        {error && <Alert tone="danger">{error}</Alert>}
        {evidence && (
          <>
            <p>
              {evidence.locator.kind === "pdf"
                ? `Document · page ${evidence.locator.page}`
                : "Réponse au formulaire"}{" "}
              ·{" "}
              {evidence.nature === "declaration"
                ? "Déclaration du candidat"
                : "Élément consultable"}
            </p>
            <blockquote className="evidence-quote preserve-lines">
              {evidence.text}
            </blockquote>
            {uploadId && (
              <a href={`/api/v1/uploads/${uploadId}/download`}>
                Ouvrir le document original
              </a>
            )}
            <details className="provenance-details">
              <summary>Vérifier la provenance</summary>
              <p>
                Caractères {evidence.locator.start} à {evidence.locator.end} du
                texte recueilli.
              </p>
              <p className="hash-text">
                Empreinte de l’extrait : {evidence.excerpt_hash}
              </p>
            </details>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
