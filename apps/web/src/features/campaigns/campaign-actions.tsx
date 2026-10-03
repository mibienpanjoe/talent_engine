"use client";
import { PolicyDetails } from "./policy-details";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
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
import type { Campaign } from "./configuration";
export function CampaignActions({
  campaign,
  dirty,
}: {
  campaign: Campaign;
  dirty: boolean;
}) {
  const router = useRouter();
  const keys = useRef<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function action(
    kind: "publish" | "close" | "duplicate" | "test",
    source: "draft" | "published" = "draft",
  ) {
    setBusy(true);
    setMessage("");
    const key = `${kind}:${source}:${campaign.revision}`;
    keys.current[key] ??= crypto.randomUUID();
    try {
      const csrf = await api.GET("/api/v1/access/csrf");
      if (!csrf.data) throw new Error();
      const headers = {
        "X-CSRF-Token": csrf.data.csrf_token,
        "If-Match": `"${campaign.revision}"`,
        "Idempotency-Key": keys.current[key],
      };
      const params = { path: { campaign_id: campaign.id } };
      if (kind === "publish") {
        const result = await api.POST(
          "/api/v1/campaigns/{campaign_id}/publications",
          { params, headers, body: {} },
        );
        if (!result.data) {
          setMessage(
            result.response.status === 422
              ? "Publication refusée : complétez le besoin, les exigences et leurs questions sources. Vérifiez aussi les familles, les doublons et l’échéance."
              : "Cette campagne a changé ou est figée. Rechargez sa version enregistrée.",
          );
          return;
        }
        setMessage("Version publiée.");
        router.refresh();
      }
      if (kind === "close") {
        const result = await api.POST(
          "/api/v1/campaigns/{campaign_id}/closures",
          { params, headers, body: {} },
        );
        if (!result.data) throw new Error();
        setMessage("Campagne fermée.");
        router.refresh();
      }
      if (kind === "duplicate") {
        const result = await api.POST(
          "/api/v1/campaigns/{campaign_id}/duplicates",
          { params, headers, body: { source } },
        );
        if (!result.data) throw new Error();
        router.push(`/review/campaigns/${result.data.id}`);
      }
      if (kind === "test") {
        const result = await api.POST(
          "/api/v1/campaigns/{campaign_id}/test-snapshots",
          { params, headers, body: { source } },
        );
        if (!result.data) throw new Error();
        router.push(`/review/tests/${result.data.id}`);
      }
    } catch {
      setMessage(
        "L’action n’a pas été confirmée. Rechargez la campagne ; vous pouvez réessayer cette action.",
      );
    } finally {
      setBusy(false);
    }
  }
  const locked =
    !!campaign.configuration_locked_at || campaign.state === "closed";
  return (
    <section
      className="campaign-actions"
      aria-label="Publication et cycle de campagne"
    >
      <p>
        <Link href={`/review/campaigns/${campaign.id}/applications`}>
          Voir les candidatures reçues
        </Link>
      </p>
      <h2>
        {
          {
            draft: "Brouillon",
            published: "Campagne publiée",
            closed: "Campagne fermée",
          }[campaign.state]
        }
      </h2>
      {campaign.has_unpublished_changes && (
        <Alert>
          Des changements enregistrés ne sont pas encore publiés. Le formulaire
          actuel reste inchangé.
        </Alert>
      )}
      {dirty && (
        <p>
          Enregistrez vos modifications avant de publier ou de créer une copie.
        </p>
      )}
      {campaign.public_url && (
        <p>
          <Link href={campaign.public_url}>Ouvrir le formulaire public</Link>
        </p>
      )}
      {campaign.active_snapshot_id && (
        <PolicyDetails snapshotId={campaign.active_snapshot_id} />
      )}
      <div className="inline-actions">
        {!locked && (
          <Button disabled={busy || dirty} onClick={() => action("publish")}>
            {campaign.state === "published"
              ? "Republier la version enregistrée"
              : "Publier la campagne"}
          </Button>
        )}
        <Button
          variant="secondary"
          disabled={busy || dirty}
          onClick={() => action("duplicate", "draft")}
        >
          Dupliquer le brouillon
        </Button>
        {campaign.active_snapshot_id && (
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() => action("duplicate", "published")}
          >
            Dupliquer la version publiée
          </Button>
        )}
        <Button
          variant="secondary"
          disabled={busy || dirty}
          onClick={() => action("test", "draft")}
        >
          Essayer en privé
        </Button>
        {campaign.state === "published" && (
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="secondary" disabled={busy}>
                Fermer la campagne
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogTitle className="dialog-title">
                Fermer cette campagne ?
              </DialogTitle>
              <DialogDescription className="dialog-description">
                Les dossiers reçus restent accessibles. Aucun nouveau dépôt ne
                sera accepté et cette campagne ne pourra pas être rouverte.
              </DialogDescription>
              <Button disabled={busy} onClick={() => action("close")}>
                Confirmer la fermeture
              </Button>
            </DialogContent>
          </Dialog>
        )}
      </div>
      {message && <Alert>{message}</Alert>}
    </section>
  );
}
