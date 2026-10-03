"use client";
import { QuestionsEditor } from "./questions-editor";
import { RequirementsEditor } from "./requirements-editor";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Field } from "../../components/ui/field";
import { Alert } from "../../components/ui/alert";
import {
  emptyConfiguration,
  type Campaign,
  type Configuration,
  type Question,
  type Requirement,
} from "./configuration";

export function DraftEditor({ initial }: { initial: Campaign | null }) {
  const router = useRouter();
  const [campaign, setCampaign] = useState(initial);
  const [config, setConfig] = useState<Configuration>(
    initial?.configuration ?? emptyConfiguration(),
  );
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [failed, setFailed] = useState(false);
  const [creationKey] = useState(() => crypto.randomUUID());
  const [issues, setIssues] = useState<{ path: string; code: string }[]>([]);
  const [dirty, setDirty] = useState(!initial);
  function change(next: Configuration) {
    setConfig(next);
    setDirty(true);
    setFeedback("");
  }
  function question(id: string, patch: Partial<Question>) {
    change({
      ...config,
      questions: config.questions.map((q) =>
        q.id === id ? { ...q, ...patch } : q,
      ),
    });
  }
  function requirement(id: string, patch: Partial<Requirement>) {
    change({
      ...config,
      requirements: config.requirements.map((r) =>
        r.id === id ? { ...r, ...patch } : r,
      ),
    });
  }
  function removeQuestion(id: string) {
    change({
      ...config,
      questions: config.questions
        .filter((q) => q.id !== id)
        .map((q, position) => ({ ...q, position })),
      requirements: config.requirements.map((r) => ({
        ...r,
        source_question_ids: r.source_question_ids.filter((x) => x !== id),
        condition_rule:
          r.condition_rule?.question_id === id ? null : r.condition_rule,
      })),
    });
  }
  function moveQuestion(index: number, offset: number) {
    const questions = [...config.questions];
    [questions[index], questions[index + offset]] = [
      questions[index + offset],
      questions[index],
    ];
    change({
      ...config,
      questions: questions.map((q, position) => ({ ...q, position })),
    });
  }
  async function save() {
    setBusy(true);
    setFeedback("");
    setFailed(false);
    try {
      const csrf = await api.GET("/api/v1/access/csrf");
      if (!csrf.data) {
        if (csrf.response.status === 401) router.replace("/login");
        throw new Error();
      }
      const headers = { "X-CSRF-Token": csrf.data.csrf_token };
      const result = campaign
        ? await api.PATCH("/api/v1/campaigns/{campaign_id}", {
            params: { path: { campaign_id: campaign.id } },
            headers: { ...headers, "If-Match": `"${campaign.revision}"` },
            body: { configuration: config },
          })
        : await api.POST("/api/v1/campaigns", {
            headers: { ...headers, "Idempotency-Key": creationKey },
            body: { configuration: config },
          });
      if (!result.data) {
        setFailed(true);
        setFeedback(
          result.response.status === 409
            ? "Cette campagne a changé. Vos modifications sont conservées : rechargez la version enregistrée avant de les réappliquer."
            : "Sauvegarde refusée. Vérifiez les champs et réessayez.",
        );
        return;
      }
      setCampaign(result.data);
      setDirty(false);
      setFeedback("Brouillon enregistré.");
      const check = await api.GET(
        "/api/v1/campaigns/{campaign_id}/preparation",
        { params: { path: { campaign_id: result.data.id } } },
      );
      if (check.data) setIssues(check.data.issues);
      if (!campaign) router.replace(`/review/campaigns/${result.data.id}`);
    } catch {
      setFailed(true);
      setFeedback(
        "La sauvegarde n’a pas été confirmée. Vos modifications sont conservées.",
      );
    } finally {
      setBusy(false);
    }
  }
  const locked =
    campaign?.state === "closed" || !!campaign?.configuration_locked_at;
  return (
    <div className="campaign-editor">
      <Link href="/review">← Mes campagnes</Link>
      <h1>{campaign ? "Configurer la campagne" : "Nouvelle campagne"}</h1>
      <p>
        Décrivez le besoin, puis les éléments que vous souhaitez examiner. Les
        barèmes sont définis par les familles d’évaluation.
      </p>
      {locked && (
        <Alert>
          Cette configuration est figée. Dupliquez la campagne pour la modifier.
        </Alert>
      )}
      <fieldset disabled={busy || locked} className="editor-fields">
        <legend>Le besoin</legend>
        <label className="ui-field">
          Type
          <select
            className="ui-input"
            value={config.type}
            onChange={(e) =>
              change({
                ...config,
                type: e.target.value as Configuration["type"],
              })
            }
          >
            <option value="training">Formation</option>
            <option value="recruitment">Recrutement</option>
          </select>
        </label>
        <Field
          id="campaign-title"
          label="Titre"
          maxLength={200}
          value={config.title}
          onChange={(e) => change({ ...config, title: e.target.value })}
        />
        <Field
          id="campaign-domain"
          label="Domaine"
          maxLength={200}
          value={config.domain}
          onChange={(e) => change({ ...config, domain: e.target.value })}
        />
        <label className="ui-field">
          Description du besoin
          <textarea
            className="ui-input"
            rows={4}
            maxLength={10000}
            value={config.description}
            onChange={(e) => change({ ...config, description: e.target.value })}
          />
        </label>
        <Field
          id="target-level"
          label="Niveau visé"
          maxLength={500}
          value={config.target_level}
          onChange={(e) => change({ ...config, target_level: e.target.value })}
        />
        <Field
          id="deadline"
          label="Échéance (UTC, facultative)"
          type="datetime-local"
          value={config.deadline?.slice(0, 16) ?? ""}
          onChange={(e) =>
            change({
              ...config,
              deadline: e.target.value ? `${e.target.value}:00Z` : null,
            })
          }
        />
      </fieldset>
      <QuestionsEditor
        config={config}
        disabled={!!(busy || locked)}
        change={change}
        question={question}
        removeQuestion={removeQuestion}
        moveQuestion={moveQuestion}
      />
      <RequirementsEditor
        config={config}
        disabled={!!(busy || locked)}
        change={change}
        requirement={requirement}
      />
      {issues.length > 0 && (
        <Alert>
          <div>
            Le brouillon est sauvegardé. À compléter avant publication :
            <ul>
              {issues.map((x, i) => (
                <li key={i}>
                  {x.path} :{" "}
                  {(
                    {
                      required: "champ à compléter",
                      missing_source: "associez une question source",
                      unsupported_family: "famille non prise en charge",
                      qualitative_required: "ajoutez une exigence qualitative",
                      incompatible_source: "source incompatible",
                    } as Record<string, string>
                  )[x.code] ?? x.code}
                </li>
              ))}
            </ul>
          </div>
        </Alert>
      )}
      {feedback && (
        <Alert tone={failed ? "danger" : "success"}>{feedback}</Alert>
      )}
      <div className="save-actions">
        <Button disabled={busy || locked} onClick={save}>
          {busy ? "Enregistrement…" : "Enregistrer le brouillon"}
        </Button>
        <span role="status">
          {dirty ? "Modifications non enregistrées" : "Version enregistrée"}
        </span>
        {failed && campaign && (
          <Button variant="secondary" onClick={() => location.reload()}>
            Recharger la version enregistrée
          </Button>
        )}
      </div>
    </div>
  );
}
