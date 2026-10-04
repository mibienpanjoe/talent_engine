"use client";
import { useState } from "react";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "../../components/ui/dialog";
import { Button } from "../../components/ui/button";
import { Alert } from "../../components/ui/alert";
import { QuestionRenderer, type QuestionAnswer } from "./question-renderer";
import type { Configuration } from "./configuration";
export function FormPreview({
  configuration,
}: {
  configuration: Configuration;
}) {
  const [answers, setAnswers] = useState<Record<string, QuestionAnswer>>({});
  const [feedback, setFeedback] = useState("");
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="secondary">Prévisualiser le formulaire</Button>
      </DialogTrigger>
      <DialogContent className="form-preview">
        <DialogTitle className="dialog-title">Aperçu du brouillon</DialogTitle>
        <DialogDescription className="dialog-description">
          Cet aperçu utilise vos modifications actuelles. Il n’enregistre aucune
          candidature.
        </DialogDescription>
        <h2>{configuration.title || "Campagne sans titre"}</h2>
        <p className="preserve-lines">{configuration.description}</p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const invalid = configuration.questions
              .filter((q) => q.type === "multiple_choice")
              .some((q) => {
                const count = Array.isArray(answers[q.id])
                  ? answers[q.id].length
                  : 0;
                return (
                  (q.required && count === 0) ||
                  (count > 0 && count < (q.constraints.min_items ?? 0)) ||
                  count > (q.constraints.max_items ?? 20)
                );
              });
            setFeedback(
              invalid
                ? "Vérifiez le nombre de choix demandé."
                : "Réponses de prévisualisation vérifiées. Aucune candidature enregistrée.",
            );
          }}
        >
          {[...configuration.questions]
            .sort((a, b) => a.position - b.position)
            .map((q) => (
              <QuestionRenderer
                key={q.id}
                question={q}
                value={answers[q.id]}
                onChange={(value) =>
                  setAnswers((previous) => ({ ...previous, [q.id]: value }))
                }
              />
            ))}
          <Button type="submit">Vérifier cet aperçu</Button>
          {feedback && <Alert>{feedback}</Alert>}
        </form>
      </DialogContent>
    </Dialog>
  );
}
