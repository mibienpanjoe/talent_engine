"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../lib/api";
import type { components } from "../../lib/api.generated";
import { Button } from "../../components/ui/button";
import { Alert } from "../../components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "../../components/ui/dialog";
export function DeleteApplication({
  application: a,
}: {
  application: components["schemas"]["ApplicationSummary"];
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function remove() {
    setBusy(true);
    setError("");
    try {
      const csrf = await api.GET("/api/v1/access/csrf");
      if (!csrf.data) throw new Error();
      const result = await api.DELETE("/api/v1/applications/{application_id}", {
        params: { path: { application_id: a.id } },
        headers: {
          "X-CSRF-Token": csrf.data.csrf_token,
          "If-Match": `"${a.review_revision}"`,
        },
        body: {
          review_revision: a.review_revision,
          effective_evaluation_id: a.effective_evaluation_id ?? null,
        },
      });
      if (result.data) {
        router.replace(`/review/campaigns/${a.campaign_id}/applications`);
        router.refresh();
      } else
        setError(
          result.response.status === 409
            ? "Le dossier a changé. Rechargez-le avant de le supprimer."
            : "La suppression n’a pas pu être confirmée. Réessayez.",
        );
    } catch {
      setError("La suppression n’a pas pu être confirmée. Réessayez.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="review-section dossier-danger">
      <h2>Supprimer ce dossier</h2>
      <Dialog
        open={open}
        onOpenChange={(next) => {
          if (!busy) setOpen(next);
        }}
      >
        <DialogTrigger asChild>
          <Button variant="secondary" className="dossier-delete-button">Supprimer le dossier</Button>
        </DialogTrigger>
        <DialogContent
          onEscapeKeyDown={(e) => {
            if (busy) e.preventDefault();
          }}
          onPointerDownOutside={(e) => {
            if (busy) e.preventDefault();
          }}
        >
          <DialogTitle className="dialog-title">
            Supprimer le dossier de {a.contact.name} ?
          </DialogTitle>
          <DialogDescription>
            Cette action est irréversible. Le dossier sera immédiatement retiré
            de la revue. Ses documents, analyses et corrections seront ensuite
            effacés. Vous pourrez suivre le nettoyage dans la liste des
            candidatures.
          </DialogDescription>
          {error && <Alert tone="danger">{error}</Alert>}
          <div className="dialog-actions">
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() => setOpen(false)}
            >
              Annuler
            </Button>
            <Button disabled={busy} onClick={() => void remove()}>
              {busy ? "Suppression…" : "Confirmer la suppression"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </section>
  );
}
