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
  className,
}: {
  id: string;
  label: string;
  uploadId?: string | null;
  className?: string;
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
        <Button variant="secondary" className={className}>{label}</Button>
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
                ? `${evidence.locator.method === "ocr" ? "Texte OCR" : "Document"} · page ${evidence.locator.page}`
                : evidence.locator.kind === "web"
                  ? "Page de portfolio"
                  : evidence.locator.kind === "github"
                    ? `Dépôt GitHub · ${evidence.locator.path}`
                    : evidence.locator.kind === "human"
                      ? "Note de vérification humaine"
                      : "Réponse au formulaire"}{" "}
              ·{" "}
              {evidence.nature === "declaration"
                ? "Déclaration du candidat"
                : evidence.nature === "contextual_explanation"
                  ? "Explication fournie"
                  : evidence.nature === "human_verification"
                    ? "Vérification du responsable"
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
            {evidence.locator.kind === "web" && (
              <a
                href={evidence.locator.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Ouvrir la page d’origine
              </a>
            )}
            {evidence.locator.kind === "github" && (
              <>
                <p>
                  Le dépôt ne suffit pas à établir la contribution personnelle.
                </p>
                <a
                  href={`${evidence.locator.repository}/blob/${evidence.locator.commit}/${evidence.locator.path.split("/").map(encodeURIComponent).join("/")}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Ouvrir le fichier au commit recueilli
                </a>
                <p className="hash-text">Commit : {evidence.locator.commit}</p>
              </>
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
