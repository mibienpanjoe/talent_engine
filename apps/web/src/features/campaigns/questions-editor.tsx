"use client";
import { Button } from "../../components/ui/button";
import { Field } from "../../components/ui/field";
import {
  questionTypes,
  type Configuration,
  type Question,
} from "./configuration";
export function QuestionsEditor({
  config,
  disabled,
  change,
  question,
  removeQuestion,
  moveQuestion,
}: {
  config: Configuration;
  disabled: boolean;
  change: (next: Configuration) => void;
  question: (id: string, patch: Partial<Question>) => void;
  removeQuestion: (id: string) => void;
  moveQuestion: (index: number, offset: number) => void;
}) {
  return (
    <fieldset disabled={disabled} className="editor-fields">
      <legend>Les questions</legend>
      {config.questions.map((q, i) => (
        <section
          className="editor-card"
          key={q.id}
          aria-label={`Question ${i + 1}`}
        >
          <Field
            id={`label-${q.id}`}
            label={`Question ${i + 1}`}
            maxLength={200}
            value={q.label}
            onChange={(e) => question(q.id, { label: e.target.value })}
          />
          <label className="ui-field">
            Type de réponse
            <select
              className="ui-input"
              value={q.type}
              onChange={(e) =>
                question(q.id, {
                  type: e.target.value as Question["type"],
                  options: [],
                  constraints: {},
                })
              }
            >
              {Object.entries(questionTypes).map(([value, label]) => (
                <option value={value} key={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <Field
            id={`help-${q.id}`}
            label="Aide (facultative)"
            maxLength={1000}
            value={q.help ?? ""}
            onChange={(e) => question(q.id, { help: e.target.value || null })}
          />
          <label>
            <input
              type="checkbox"
              checked={q.required}
              onChange={(e) => question(q.id, { required: e.target.checked })}
            />{" "}
            Réponse obligatoire
          </label>
          {(q.type === "single_choice" || q.type === "multiple_choice") && (
            <div>
              {(q.options ?? []).map((option, j) => (
                <div className="inline-actions" key={option.id}>
                  <Field
                    id={option.id}
                    label={`Option ${j + 1}`}
                    value={option.label}
                    maxLength={200}
                    onChange={(e) =>
                      question(q.id, {
                        options: q.options?.map((o) =>
                          o.id === option.id
                            ? { ...o, label: e.target.value }
                            : o,
                        ),
                      })
                    }
                  />
                  <Button
                    variant="ghost"
                    onClick={() =>
                      question(q.id, {
                        options: q.options?.filter((o) => o.id !== option.id),
                      })
                    }
                  >
                    Retirer l’option {j + 1}
                  </Button>
                </div>
              ))}
              <Button
                variant="secondary"
                disabled={(q.options?.length ?? 0) >= 20}
                onClick={() =>
                  question(q.id, {
                    options: [
                      ...(q.options ?? []),
                      { id: crypto.randomUUID(), label: "Nouvelle option" },
                    ],
                  })
                }
              >
                Ajouter une option
              </Button>
            </div>
          )}
          {(["short_text", "long_text"].includes(q.type)
            ? ["min_length", "max_length"]
            : q.type === "number"
              ? ["min_value", "max_value"]
              : q.type === "multiple_choice"
                ? ["min_items", "max_items"]
                : q.type === "file"
                  ? ["max_files", "max_bytes"]
                  : []
          ).map((bound) => (
            <Field
              key={bound}
              id={`${q.id}-${bound}`}
              label={
                {
                  min_length: "Longueur minimale",
                  max_length: "Longueur maximale",
                  min_value: "Valeur minimale",
                  max_value: "Valeur maximale",
                  min_items: "Choix minimum",
                  max_items: "Choix maximum",
                  max_files: "Nombre maximum de fichiers",
                  max_bytes: "Taille maximale par fichier (octets)",
                }[bound] ?? bound
              }
              type="number"
              value={
                (q.constraints[
                  bound as keyof Question["constraints"]
                ] as number) ?? ""
              }
              onChange={(e) =>
                question(q.id, {
                  constraints: {
                    ...q.constraints,
                    [bound]:
                      e.target.value === "" ? null : Number(e.target.value),
                  },
                })
              }
            />
          ))}
          <div className="inline-actions">
            <Button
              variant="secondary"
              disabled={i === 0}
              onClick={() => moveQuestion(i, -1)}
            >
              Monter
            </Button>
            <Button
              variant="secondary"
              disabled={i === config.questions.length - 1}
              onClick={() => moveQuestion(i, 1)}
            >
              Descendre
            </Button>
            <Button variant="ghost" onClick={() => removeQuestion(q.id)}>
              Supprimer la question {i + 1}
            </Button>
          </div>
        </section>
      ))}
      <Button
        variant="secondary"
        disabled={config.questions.length >= 50}
        onClick={() =>
          change({
            ...config,
            questions: [
              ...config.questions,
              {
                id: crypto.randomUUID(),
                type: "long_text",
                label: "",
                help: null,
                required: false,
                position: config.questions.length,
                options: [],
                constraints: {},
              },
            ],
          })
        }
      >
        Ajouter une question
      </Button>
    </fieldset>
  );
}
