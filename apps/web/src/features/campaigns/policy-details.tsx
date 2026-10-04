"use client";
import { useState } from "react";
import type { components } from "../../lib/api.generated";
import { api } from "../../lib/api";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "../../components/ui/dialog";
import { Button } from "../../components/ui/button";
import { Alert } from "../../components/ui/alert";
import { families } from "./configuration";
export function PolicyDetails({ snapshotId }: { snapshotId: string }) {
  const [data, setData] =
    useState<components["schemas"]["PolicyExplanation"]>();
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);
  async function load() {
    setLoading(true);
    setError(false);
    try {
      const result = await api.GET("/api/v1/snapshots/{snapshot_id}/policy", {
        params: { path: { snapshot_id: snapshotId } },
      });
      if (result.data) setData(result.data);
      else setError(true);
    } catch {
      setError(true);
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
        <Button variant="secondary">Comprendre les barèmes publiés</Button>
      </DialogTrigger>
      <DialogContent className="form-preview">
        <DialogTitle className="dialog-title">
          Politique de cette version
        </DialogTitle>
        <DialogDescription className="dialog-description">
          Les barèmes et poids sont fixés au moment de la publication.
        </DialogDescription>
        {loading && <p role="status">Chargement…</p>}
        {error && (
          <Alert tone="danger">La politique n’a pas pu être chargée.</Alert>
        )}
        {data && (
          <>
            <p>{data.notice}</p>
            {data.criteria.map((c) => (
              <section key={c.criterion_id}>
                <h3>
                  {(
                    { ...families.training, ...families.recruitment } as Record<
                      string,
                      string
                    >
                  )[c.family] ?? "Condition de disponibilité"}
                </h3>
                {c.weight && (
                  <p>
                    Poids : {c.weight.numerator}/{c.weight.denominator} %
                    {c.required_skill_threshold !== null
                      ? ` · seuil indispensable ${c.required_skill_threshold}/4`
                      : ""}
                  </p>
                )}
                <ol start={0}>
                  {c.levels.map((level, i) => (
                    <li key={i}>{level}</li>
                  ))}
                </ol>
              </section>
            ))}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
