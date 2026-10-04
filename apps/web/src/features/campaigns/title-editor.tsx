"use client";
import { useState } from "react";
import { api } from "../../lib/api";
import type { components } from "../../lib/api.generated";
import type { Campaign } from "./configuration";
import { Field } from "../../components/ui/field";
import { Button } from "../../components/ui/button";
import { Alert } from "../../components/ui/alert";
export function TitleEditor({
  campaign,
  saved,
}: {
  campaign: Campaign;
  saved: (campaign: Campaign) => void;
}) {
  const [title, setTitle] = useState(
    campaign.display_title ?? campaign.configuration.title,
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [history, setHistory] =
    useState<components["schemas"]["TitleChange"][]>();
  async function save() {
    setBusy(true);
    setMessage("");
    try {
      const csrf = await api.GET("/api/v1/access/csrf");
      if (!csrf.data) throw new Error();
      const result = await api.PATCH("/api/v1/campaigns/{campaign_id}", {
        params: { path: { campaign_id: campaign.id } },
        headers: {
          "X-CSRF-Token": csrf.data.csrf_token,
          "If-Match": `"${campaign.revision}"`,
        },
        body: { title },
      });
      if (result.data) {
        saved(result.data);
        setMessage("Le titre affiché a été corrigé.");
        setHistory(undefined);
      } else
        setMessage(
          result.response.status === 409
            ? "La campagne a changé. Rechargez sa version enregistrée avant de corriger le titre."
            : "Le titre n’a pas pu être enregistré. Vérifiez-le puis réessayez.",
        );
    } catch {
      setMessage("Le titre n’a pas pu être enregistré. Réessayez.");
    } finally {
      setBusy(false);
    }
  }
  async function showHistory() {
    setBusy(true);
    try {
      const result = await api.GET(
        "/api/v1/campaigns/{campaign_id}/title-history",
        { params: { path: { campaign_id: campaign.id } } },
      );
      if (result.data) setHistory(result.data);
      else setMessage("L’historique est indisponible.");
    } catch {
      setMessage("L’historique est indisponible.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="empty-state" aria-label="Correction du titre affiché">
      <h2>Titre affiché</h2>
      <p>
        Le titre peut être corrigé. Les questions, le besoin et les barèmes
        utilisés pour les candidatures restent figés.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <Field
          id="display-title"
          label="Titre affiché"
          value={title}
          required
          maxLength={200}
          disabled={busy}
          onChange={(e) => setTitle(e.target.value)}
        />
        <div className="inline-actions">
          <Button disabled={busy} type="submit">
            Corriger le titre affiché
          </Button>
          <Button
            type="button"
            variant="secondary"
            disabled={busy}
            onClick={showHistory}
          >
            Voir les corrections du titre
          </Button>
        </div>
      </form>
      {message && <Alert>{message}</Alert>}
      {history &&
        (history.length ? (
          <ul>
            {history.map((item) => (
              <li key={item.id}>
                {item.previous_title} → {item.title} ·{" "}
                {new Date(item.changed_at).toLocaleString("fr-FR", {
                  timeZone: "UTC",
                })}{" "}
                UTC
              </li>
            ))}
          </ul>
        ) : (
          <p>Aucune correction enregistrée.</p>
        ))}
    </section>
  );
}
