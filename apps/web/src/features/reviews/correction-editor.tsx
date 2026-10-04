"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useActionKey } from "./use-action-key";
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

type Detail = components["schemas"]["ApplicationDetail"];
export function CorrectionEditor({
  dossier,
  criterionId,
  kind,
  initialValue,
}: {
  dossier: Detail;
  criterionId: string;
  kind: "assessment" | "condition";
  initialValue: string;
}) {
  const router = useRouter();
  const actionKey = useActionKey();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [action, setAction] = useState<"set" | "restore_base">("set");
  const [value, setValue] = useState(initialValue);
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [zero, setZero] = useState("");
  const label = dossier.snapshot.configuration.requirements.find(
    (r) => r.id === criterionId,
  )?.expectation;
  async function save() {
    setBusy(true);
    setMessage("");
    try {
      const csrf = await api.GET("/api/v1/access/csrf");
      if (!csrf.data) throw new Error();
      const level =
        kind === "assessment" && /^\d$/.test(value) ? Number(value) : null;
      const body: components["schemas"]["CorrectionInput"] = {
        review_revision: dossier.application.review_revision,
        effective_evaluation_id:
          dossier.application.effective_evaluation_id ?? null,
        criterion_id: criterionId,
        target_kind: kind,
        action,
        reason,
        ...(action === "set"
          ? {
              status: (level !== null
                ? "evaluated"
                : value) as components["schemas"]["CorrectionInput"]["status"],
              level,
              human_note: note,
              zero_evidence_quote: level === 0 ? zero : null,
            }
          : {}),
      };
      const result = await api.POST(
        "/api/v1/applications/{application_id}/corrections",
        {
          params: { path: { application_id: dossier.application.id } },
          headers: {
            "X-CSRF-Token": csrf.data.csrf_token,
            "If-Match": `"${dossier.application.review_revision}"`,
            "Idempotency-Key": actionKey(body),
          },
          body,
        },
      );
      if (result.data) {
        setOpen(false);
        setReason("");
        setNote("");
        router.refresh();
      } else
        setMessage(
          result.response.status === 409
            ? "Le dossier a changé. Fermez puis rechargez la fiche avant de corriger."
            : "Correction refusée. Vérifiez le motif, l’observation et le niveau.",
        );
    } catch {
      setMessage("La correction n’a pas pu être enregistrée. Réessayez.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!busy) {
          setOpen(next);
          setMessage("");
        }
      }}
    >
      <DialogTrigger asChild>
        <Button variant="ghost" className="criterion-correction-button">{kind === "condition" ? "Corriger la condition" : "Corriger l’appréciation"}</Button>
      </DialogTrigger>
      <DialogContent className="form-preview">
        <DialogTitle>Correction humaine</DialogTitle>
        <DialogDescription>{label}</DialogDescription>
        <p>
          Le résultat sera recalculé et cette correction restera dans l’historique.
        </p>
        <form
          className="form-stack"
          onSubmit={(e) => {
            e.preventDefault();
            void save();
          }}
        >
          <label className="ui-field">
            Action
            <select
              className="ui-input"
              value={action}
              disabled={busy}
              onChange={(e) => setAction(e.target.value as typeof action)}
            >
              <option value="set">Enregistrer une correction</option>
              <option value="restore_base">
                Revenir à l’appréciation automatique
              </option>
            </select>
          </label>
          {action === "set" && (
            <>
              <label className="ui-field">
                {kind === "assessment"
                  ? "Niveau ou information manquante"
                  : "Condition vérifiée"}
                <select
                  className="ui-input"
                  value={value}
                  disabled={busy}
                  onChange={(e) => setValue(e.target.value)}
                >
                  {kind === "assessment" ? (
                    <>
                      {[0, 1, 2, 3, 4].map((n) => (
                        <option key={n} value={n}>
                          Niveau {n} / 4
                        </option>
                      ))}
                      <option value="insufficient_information">
                        Information insuffisante
                      </option>
                      <option value="conflicting_information">
                        Informations contradictoires
                      </option>
                      <option value="source_unavailable">
                        Source indisponible
                      </option>
                    </>
                  ) : (
                    <>
                      <option value="met">Satisfaite</option>
                      <option value="unmet">Non satisfaite</option>
                      <option value="unknown">À vérifier</option>
                    </>
                  )}
                </select>
              </label>
              <label className="ui-field">
                Observation humaine
                <textarea
                  className="ui-input"
                  rows={4}
                  required
                  maxLength={2000}
                  value={note}
                  disabled={busy}
                  onChange={(e) => setNote(e.target.value)}
                />
              </label>
              {kind === "assessment" && value === "0" && (
                <label className="ui-field">
                  Passage de l’observation justifiant le niveau zéro
                  <input
                    className="ui-input"
                    required
                    maxLength={1000}
                    value={zero}
                    disabled={busy}
                    onChange={(e) => setZero(e.target.value)}
                  />
                </label>
              )}
            </>
          )}
          <label className="ui-field">
            Motif de la correction
            <textarea
              className="ui-input"
              rows={4}
              required
              maxLength={2000}
              value={reason}
              disabled={busy}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
          {message && <Alert tone="danger">{message}</Alert>}
          <Button
            type="submit"
            disabled={
              busy || !reason.trim() || (action === "set" && !note.trim())
            }
          >
            {busy ? "Enregistrement…" : "Enregistrer la correction"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
