"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../lib/api";
import type { components } from "../../lib/api.generated";
import { Button } from "../../components/ui/button";
import { Alert } from "../../components/ui/alert";
import { decisionLabels } from "./labels";
export function DecisionEditor({
  application,
}: {
  application: components["schemas"]["ApplicationSummary"];
}) {
  const router = useRouter();
  const [decision, setDecision] = useState(application.decision);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save() {
    setBusy(true);
    setError("");
    try {
      const csrf = await api.GET("/api/v1/access/csrf");
      if (!csrf.data) throw new Error();
      const result = await api.POST(
        "/api/v1/applications/{application_id}/decisions",
        {
          params: { path: { application_id: application.id } },
          headers: { "X-CSRF-Token": csrf.data.csrf_token },
          body: {
            review_revision: application.review_revision,
            effective_evaluation_id:
              application.effective_evaluation_id ?? null,
            decision,
            reason,
          },
        },
      );
      if (result.data) router.refresh();
      else
        setError(
          result.response.status === 409
            ? "Le dossier a changé. Rechargez sa version enregistrée avant de décider."
            : "La décision n’a pas pu être enregistrée. Réessayez.",
        );
    } catch {
      setError("La décision n’a pas pu être enregistrée. Réessayez.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="review-section">
      <h2>Décision humaine</h2>
      <p>
        Décision enregistrée : {decisionLabels[application.decision]}. Les
        appréciations et alertes restent consultables.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <label className="ui-field">
          Nouvelle décision
          <select
            className="ui-input"
            value={decision}
            disabled={busy}
            onChange={(e) => setDecision(e.target.value as typeof decision)}
          >
            {Object.entries(decisionLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="ui-field">
          Motif (facultatif)
          <textarea
            className="ui-input"
            rows={3}
            maxLength={2000}
            value={reason}
            disabled={busy}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
        {error && <Alert tone="danger">{error}</Alert>}
        <div>
          <Button
            type="submit"
            disabled={busy || decision === application.decision}
          >
            {busy ? "Enregistrement…" : "Enregistrer la décision"}
          </Button>
        </div>
      </form>
    </section>
  );
}
