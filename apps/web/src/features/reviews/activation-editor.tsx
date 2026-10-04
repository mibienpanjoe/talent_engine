"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import type { components } from "../../lib/api.generated";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Alert } from "../../components/ui/alert";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "../../components/ui/dialog";
import { useActionKey } from "./use-action-key";
import {
  activeCorrections,
  initialChoice,
  ReapplicationFields,
  type ReapplyChoice,
} from "./reapplication-fields";
type Detail = components["schemas"]["ApplicationDetail"];
type Version = components["schemas"]["EvaluationVersion"];
type Event = components["schemas"]["ReviewEvent"];
export function ActivationEditor({
  dossier,
  version,
  history,
}: {
  dossier: Detail;
  version: Version;
  history: Event[];
}) {
  const router = useRouter();
  const actionKey = useActionKey();
  const candidates = activeCorrections(
    history,
    dossier.application.effective_evaluation_id,
  );
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<"use_new_base" | "reapply_selected">(
    "use_new_base",
  );
  const [confirmed, setConfirmed] = useState(false);
  const [reason, setReason] = useState("");
  const [choices, setChoices] = useState<Record<string, ReapplyChoice>>(() =>
    Object.fromEntries(
      candidates.map((item) => [
        item.id,
        initialChoice(item, dossier, version.base),
      ]),
    ),
  );
  const discardsCorrections = candidates.some(
    (item) => mode === "use_new_base" || !choices[item.id].selected,
  );
  async function activate() {
    setBusy(true);
    setError("");
    const expectation = {
      review_revision: dossier.application.review_revision,
      effective_evaluation_id:
        dossier.application.effective_evaluation_id ?? null,
    };
    const body: components["schemas"]["ActivationInput"] = {
      ...expectation,
      evaluation_id: version.base.id,
      mode,
      reason,
      confirm_discard_corrections: confirmed,
      corrections:
        mode === "reapply_selected"
          ? candidates
              .filter((item) => choices[item.id].selected)
              .map((item) => {
                const choice = choices[item.id];
                const level =
                  item.kind === "assessment" && /^\d$/.test(choice.value)
                    ? Number(choice.value)
                    : null;
                return {
                  origin_event_id: item.id,
                  correction: {
                    ...expectation,
                    target_kind: item.kind as "assessment" | "condition",
                    criterion_id: item.criterion_id!,
                    action: "set",
                    status: (level !== null
                      ? "evaluated"
                      : choice.value) as components["schemas"]["CorrectionInput"]["status"],
                    level,
                    reason,
                    evidence_ids: choice.proof ? [choice.proof] : [],
                    human_note: choice.note.trim() ? choice.note : null,
                    zero_evidence_quote: level === 0 ? choice.zero : null,
                  },
                };
              })
          : [],
    };
    try {
      const csrf = await api.GET("/api/v1/access/csrf");
      if (!csrf.data) throw new Error();
      const result = await api.POST(
        "/api/v1/applications/{application_id}/activations",
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
        router.refresh();
      } else
        setError(
          result.response.status === 409
            ? "La revue a changé. Rechargez la fiche."
            : "Activation refusée. Vérifiez les corrections, les preuves de cette version et la confirmation.",
        );
    } catch {
      setError(
        "La réponse est incertaine. Réessayez la même activation ou actualisez la fiche.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!busy) setOpen(next);
      }}
    >
      <DialogTrigger asChild>
        <Button variant="secondary">Activer cette analyse</Button>
      </DialogTrigger>
      <DialogContent className="form-preview">
        <DialogTitle>Activer la nouvelle analyse</DialogTitle>
        <DialogDescription>
          Le résultat effectif sera remplacé. La décision humaine et les
          historiques seront conservés.
        </DialogDescription>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void activate();
          }}
        >
          <label className="ui-field">
            Corrections humaines
            <select
              className="ui-input"
              value={mode}
              disabled={busy}
              onChange={(e) => {
                setMode(e.target.value as typeof mode);
                setConfirmed(false);
              }}
            >
              <option value="use_new_base">Utiliser la nouvelle base</option>
              {candidates.length > 0 && (
                <option value="reapply_selected">
                  Reporter des corrections vérifiées
                </option>
              )}
            </select>
          </label>
          {discardsCorrections && (
            <label className="source-choice">
              <input
                type="checkbox"
                required
                disabled={busy}
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
              />
              Je confirme que les corrections non reportées ne feront plus
              partie du résultat effectif. Leur historique restera consultable.
            </label>
          )}
          {mode === "reapply_selected" && (
            <>
              <p>
                Vérifiez chaque appréciation et sa preuve dans la nouvelle
                version avant de la sélectionner.
              </p>
              {candidates.map((item) => (
                <ReapplicationFields
                  key={item.id}
                  event={item}
                  choice={choices[item.id]}
                  change={(choice) => {
                    setChoices((current) => ({
                      ...current,
                      [item.id]: choice,
                    }));
                    setConfirmed(false);
                  }}
                  dossier={dossier}
                  base={version.base}
                  disabled={busy}
                />
              ))}
            </>
          )}
          <label className="ui-field">
            Motif de l’activation et des reports
            <textarea
              className="ui-input"
              rows={3}
              required
              maxLength={2000}
              value={reason}
              disabled={busy}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
          {error && <Alert tone="danger">{error}</Alert>}
          <Button
            type="submit"
            disabled={
              busy ||
              !reason.trim() ||
              (discardsCorrections && !confirmed) ||
              (mode === "reapply_selected" &&
                !Object.values(choices).some((c) => c.selected))
            }
          >
            {busy ? "Activation…" : "Confirmer l’activation"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
