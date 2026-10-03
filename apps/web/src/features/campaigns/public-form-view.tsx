"use client";
import { useState } from "react";
import type { components } from "../../lib/api.generated";
import { Alert } from "../../components/ui/alert";
import { QuestionRenderer, type QuestionAnswer } from "./question-renderer";
export function PublicFormView({
  form,
  test = false,
}: {
  form: components["schemas"]["PublicForm"];
  test?: boolean;
}) {
  const [answers, setAnswers] = useState<Record<string, QuestionAnswer>>({});
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
        <div className="public-form">
          {form.questions.map((q) => (
            <QuestionRenderer
              key={q.id}
              question={q}
              value={answers[q.id]}
              onChange={(value) =>
                setAnswers((previous) => ({ ...previous, [q.id]: value }))
              }
            />
          ))}
          <Alert>
            La réception des candidatures n’est pas encore ouverte.
          </Alert>
        </div>
      )}
    </>
  );
}
