"use client";
import { useRef, useState } from "react";
import type { components } from "../../lib/api.generated";
import { api } from "../../lib/api";
import { Alert } from "../../components/ui/alert";
import { Field } from "../../components/ui/field";
import { Button } from "../../components/ui/button";
import { QuestionRenderer, type QuestionAnswer } from "./question-renderer";
type Form = components["schemas"]["PublicForm"];
type Answer = components["schemas"]["SubmissionInput"]["answers"][number];
export function PublicFormView({
  form: initial,
  test = false,
  publicToken,
  campaignId,
}: {
  form: Form;
  test?: boolean;
  publicToken?: string;
  campaignId?: string;
}) {
  const [form, setForm] = useState(initial);
  const [answers, setAnswers] = useState<Record<string, QuestionAnswer>>({});
  const [contact, setContact] = useState({ name: "", email: "" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [errorCode, setErrorCode] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [receipt, setReceipt] = useState<components["schemas"]["Receipt"]>();
  const key = useRef<string | null>(null);
  async function reloadForm() {
    if (!publicToken) return;
    setBusy(true);
    try {
      const result = await api.GET("/api/v1/public/campaigns/{public_token}", {
        params: { path: { public_token: publicToken } },
      });
      if (result.data) {
        setForm(result.data);
        setMessage(
          "Le formulaire a été actualisé. Vos réponses sont conservées : vérifiez les questions avant de confirmer l’envoi.",
        );
        setErrorCode("");
      } else setMessage("Le formulaire n’a pas pu être actualisé.");
    } catch {
      setMessage("Le formulaire n’a pas pu être actualisé.");
    } finally {
      setBusy(false);
    }
  }
  async function submit() {
    setBusy(true);
    setMessage("");
    setErrors({});
    setErrorCode("");
    key.current ??= crypto.randomUUID();
    try {
      const typed: Answer[] = [];
      for (const q of form.questions) {
        const value = answers[q.id];
        if (value === undefined || value === "") continue;
        if (q.type === "file") {
          if (Array.isArray(value) && value.length)
            throw new Error("documents");
          continue;
        }
        if (q.type === "multiple_choice") {
          typed.push({
            question_id: q.id,
            kind: q.type,
            value: value as string[],
          });
          continue;
        }
        if (q.type === "number") {
          typed.push({ question_id: q.id, kind: q.type, value: Number(value) });
          continue;
        }
        typed.push({
          question_id: q.id,
          kind: q.type,
          value: value as string,
        } as Answer);
      }
      const body = { snapshot_id: form.snapshot_id, contact, answers: typed };
      const result =
        test && campaignId
          ? await (async () => {
              const csrf = await api.GET("/api/v1/access/csrf");
              if (!csrf.data) throw new Error();
              return api.POST(
                "/api/v1/campaigns/{campaign_id}/test-applications",
                {
                  params: { path: { campaign_id: campaignId } },
                  headers: {
                    "Idempotency-Key": key.current!,
                    "X-CSRF-Token": csrf.data.csrf_token,
                  },
                  body,
                },
              );
            })()
          : publicToken
            ? await api.POST(
                "/api/v1/public/campaigns/{public_token}/applications",
                {
                  params: { path: { public_token: publicToken } },
                  headers: { "Idempotency-Key": key.current },
                  body,
                },
              )
            : null;
      if (result?.data) {
        setReceipt(result.data);
        return;
      }
      const code = result?.error?.error.code ?? "network";
      setErrorCode(code);
      const messages: Record<string, string> = {
        snapshot_conflict:
          "Le formulaire a changé. Actualisez-le et vérifiez vos réponses avant de les envoyer.",
        campaign_closed: "Cette campagne n’accepte plus de candidatures.",
        idempotency_conflict:
          "Un dépôt est déjà enregistré avec d’autres réponses. Réessayez avec vos réponses précédentes ou préparez un nouveau dépôt.",
        validation_error: "Vérifiez les coordonnées et les réponses indiquées.",
        payload_too_large: "Vos réponses dépassent la taille autorisée.",
        submission_deleted:
          "Ce dépôt a été supprimé. Il ne peut pas être recréé par un nouvel essai.",
      };
      setMessage(
        messages[code] ??
          "L’enregistrement n’a pas été confirmé. Conservez vos réponses et réessayez le même envoi.",
      );
      const localized: Record<string, string> = {};
      for (const detail of result?.error?.error.details ?? []) {
        const parts = detail.path.replace(/^body\./, "").split(".");
        let questionId: string | undefined;
        if (parts[0] === "answers")
          questionId = typed[Number(parts[1])]?.question_id;
        if (parts[0] === "questions") questionId = parts[1];
        if (questionId)
          localized[questionId] = "Vérifiez cette réponse et ses contraintes.";
        if (parts[0] === "contact")
          localized[parts[1]] = "Vérifiez cette coordonnée.";
      }
      setErrors(localized);
    } catch (error) {
      setMessage(
        error instanceof Error && error.message === "documents"
          ? "Les documents doivent être préparés avant le dépôt."
          : "L’enregistrement n’a pas été confirmé. Réessayez le même envoi avec les mêmes réponses.",
      );
    } finally {
      setBusy(false);
    }
  }
  if (receipt)
    return (
      <>
        <p className="eyebrow">{test ? "Essai privé" : "Candidature"}</p>
        <h1>{test ? "Essai enregistré." : "Candidature reçue."}</h1>
        <Alert tone="success">
          {test
            ? "Cet essai reste privé et ne verrouille pas la campagne."
            : "Vos réponses ont été enregistrées. Leur analyse est indépendante de cette confirmation."}
        </Alert>
        <p>Référence : {receipt.receipt_ref}</p>
        <p>
          Reçue le{" "}
          {new Date(receipt.received_at).toLocaleString("fr-FR", {
            timeZone: "UTC",
          })}{" "}
          UTC.
        </p>
      </>
    );
  return (
    <>
      <p className="eyebrow">{test ? "Essai privé" : "Candidature"}</p>
      <h1>{form.title}</h1>
      <p className="preserve-lines">{form.description}</p>
      <p>
        {form.domain} · {form.target_level}
      </p>
      {form.deadline && (
        <p>
          Échéance :{" "}
          {new Date(form.deadline).toLocaleString("fr-FR", {
            timeZone: "UTC",
            dateStyle: "long",
            timeStyle: "short",
          })}{" "}
          UTC.
        </p>
      )}
      <Alert>
        {test
          ? "Cet essai privé ne compte pas comme candidature réelle et ne verrouille pas la campagne."
          : form.processing_notice}
      </Alert>
      {form.state === "closed" ? (
        <Alert>Cette campagne n’accepte plus de candidatures.</Alert>
      ) : (
        <form
          className="public-form"
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <fieldset disabled={busy} className="submission-fields">
            <legend>Vos coordonnées</legend>
            <Field
              id="candidate-name"
              label="Nom"
              required
              maxLength={200}
              value={contact.name}
              error={errors.name}
              onChange={(e) => setContact({ ...contact, name: e.target.value })}
            />
            <Field
              id="candidate-email"
              label="Email"
              type="email"
              required
              maxLength={320}
              value={contact.email}
              error={errors.email}
              onChange={(e) =>
                setContact({ ...contact, email: e.target.value })
              }
            />
            {form.questions.map((q) => (
              <QuestionRenderer
                key={q.id}
                question={q}
                value={answers[q.id]}
                error={errors[q.id]}
                onChange={(value) =>
                  setAnswers((previous) => ({ ...previous, [q.id]: value }))
                }
              />
            ))}
          </fieldset>
          {message && <Alert tone="danger">{message}</Alert>}
          <div className="inline-actions">
            <Button type="submit" disabled={busy}>
              {busy
                ? "Enregistrement…"
                : test
                  ? "Envoyer l’essai privé"
                  : "Envoyer ma candidature"}
            </Button>
            {errorCode === "snapshot_conflict" && (
              <Button
                type="button"
                variant="secondary"
                disabled={busy}
                onClick={reloadForm}
              >
                Actualiser le formulaire
              </Button>
            )}
            {errorCode === "idempotency_conflict" && (
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  key.current = crypto.randomUUID();
                  setErrorCode("");
                  setMessage(
                    "Nouveau dépôt préparé. Vérifiez vos réponses puis confirmez l’envoi.",
                  );
                }}
              >
                Préparer un nouveau dépôt
              </Button>
            )}
          </div>
        </form>
      )}
    </>
  );
}
