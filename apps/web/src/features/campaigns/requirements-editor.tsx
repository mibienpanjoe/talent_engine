"use client";
import { Button } from "../../components/ui/button";
import { Field } from "../../components/ui/field";
import { Alert } from "../../components/ui/alert";
import {
  families,
  type Configuration,
  type Requirement,
} from "./configuration";
export function RequirementsEditor({
  config,
  disabled,
  change,
  requirement,
}: {
  config: Configuration;
  disabled: boolean;
  change: (next: Configuration) => void;
  requirement: (id: string, patch: Partial<Requirement>) => void;
}) {
  return (
    <fieldset disabled={disabled} className="editor-fields">
      <legend>Les exigences</legend>
      {config.requirements.map((r, i) => (
        <section
          className="editor-card"
          key={r.id}
          aria-label={`Exigence ${i + 1}`}
        >
          <label className="ui-field">
            Mode d’exigence
            <select
              className="ui-input"
              value={r.evaluation_mode}
              onChange={(e) =>
                requirement(r.id, {
                  evaluation_mode: e.target
                    .value as Requirement["evaluation_mode"],
                  family:
                    e.target.value === "deterministic"
                      ? "available_by_date"
                      : Object.keys(families[config.type])[0],
                  assessment_mode:
                    e.target.value === "deterministic" ? null : "automatic",
                  condition_rule: null,
                  source_question_ids: [],
                })
              }
            >
              <option value="qualitative">Compétence à apprécier</option>
              <option value="deterministic">Condition de disponibilité</option>
            </select>
          </label>
          {r.evaluation_mode === "qualitative" ? (
            <>
              <label className="ui-field">
                Famille d’évaluation
                <select
                  className="ui-input"
                  value={r.family in families[config.type] ? r.family : "other"}
                  onChange={(e) =>
                    requirement(r.id, {
                      family: e.target.value === "other" ? "" : e.target.value,
                    })
                  }
                >
                  {Object.entries(families[config.type]).map(
                    ([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ),
                  )}
                  <option value="other">Autre, à préciser</option>
                </select>
              </label>
              {!(r.family in families[config.type]) && (
                <>
                  <Field
                    id={`family-${r.id}`}
                    label="Famille à préciser"
                    value={r.family}
                    maxLength={100}
                    onChange={(e) =>
                      requirement(r.id, { family: e.target.value })
                    }
                  />
                  <Alert>
                    Cette famille n’est pas prise en charge. Précisez ou
                    reformulez l’exigence avant publication.
                  </Alert>
                </>
              )}
              <label className="ui-field">
                Attente concrète
                <textarea
                  className="ui-input"
                  rows={3}
                  value={r.expectation}
                  maxLength={2000}
                  onChange={(e) =>
                    requirement(r.id, { expectation: e.target.value })
                  }
                />
              </label>
              <label className="ui-field">
                Importance
                <select
                  className="ui-input"
                  value={r.importance}
                  onChange={(e) =>
                    requirement(r.id, {
                      importance: e.target.value as Requirement["importance"],
                    })
                  }
                >
                  <option value="desired">Souhaitée</option>
                  <option value="required">Indispensable</option>
                </select>
              </label>
              <label className="ui-field">
                Appréciation
                <select
                  className="ui-input"
                  value={r.assessment_mode ?? "automatic"}
                  onChange={(e) =>
                    requirement(r.id, {
                      assessment_mode: e.target.value as "automatic" | "manual",
                    })
                  }
                >
                  <option value="automatic">
                    Automatique, selon les preuves
                  </option>
                  <option value="manual">Manuelle, à vérifier</option>
                </select>
              </label>
            </>
          ) : (
            <>
              <label className="ui-field">
                Condition
                <select
                  className="ui-input"
                  value={r.family}
                  onChange={(e) =>
                    requirement(r.id, {
                      family: e.target.value,
                      source_question_ids: [],
                      condition_rule: null,
                    })
                  }
                >
                  <option value="available_by_date">
                    Disponible avant une date
                  </option>
                  <option value="available_slots">
                    Disponible sur des créneaux
                  </option>
                </select>
              </label>
              <label className="ui-field">
                Question structurée
                <select
                  className="ui-input"
                  value={r.source_question_ids[0] ?? ""}
                  onChange={(e) =>
                    requirement(r.id, {
                      source_question_ids: e.target.value
                        ? [e.target.value]
                        : [],
                      condition_rule: null,
                    })
                  }
                >
                  <option value="">Choisir une question compatible</option>
                  {config.questions
                    .filter(
                      (q) =>
                        q.type ===
                        (r.family === "available_by_date"
                          ? "date"
                          : "multiple_choice"),
                    )
                    .map((q) => (
                      <option key={q.id} value={q.id}>
                        {q.label || "Question sans libellé"}
                      </option>
                    ))}
                </select>
              </label>
              {r.family === "available_by_date" && (
                <Field
                  id={`condition-${r.id}`}
                  label="Date attendue"
                  type="date"
                  disabled={!r.source_question_ids[0]}
                  value={
                    r.condition_rule?.kind === "available_by_date"
                      ? r.condition_rule.date
                      : ""
                  }
                  onChange={(e) =>
                    requirement(r.id, {
                      condition_rule: e.target.value
                        ? {
                            kind: "available_by_date",
                            question_id: r.source_question_ids[0],
                            date: e.target.value,
                          }
                        : null,
                    })
                  }
                />
              )}{" "}
              {r.family === "available_slots" && (
                <fieldset>
                  <legend>Créneaux attendus</legend>
                  {config.questions
                    .find((q) => q.id === r.source_question_ids[0])
                    ?.options?.map((o) => (
                      <label className="source-choice" key={o.id}>
                        <input
                          type="checkbox"
                          checked={
                            r.condition_rule?.kind === "available_slots" &&
                            r.condition_rule.option_ids.includes(o.id)
                          }
                          onChange={(e) => {
                            const previous =
                              r.condition_rule?.kind === "available_slots"
                                ? r.condition_rule.option_ids
                                : [];
                            const selected = e.target.checked
                              ? [...previous, o.id]
                              : previous.filter((x) => x !== o.id);
                            requirement(r.id, {
                              condition_rule: selected.length
                                ? {
                                    kind: "available_slots",
                                    question_id: r.source_question_ids[0],
                                    option_ids: selected,
                                  }
                                : null,
                            });
                          }}
                        />
                        {o.label}
                      </label>
                    ))}
                </fieldset>
              )}
            </>
          )}
          {r.source_question_ids.length === 0 && (
            <Alert>
              <div>
                Cette exigence n’a plus de question source. Associez une
                question compatible, reformulez l’exigence ou ajoutez une
                question.
                <Button
                  variant="secondary"
                  onClick={() => {
                    const id = crypto.randomUUID();
                    change({
                      ...config,
                      questions: [
                        ...config.questions,
                        {
                          id,
                          type:
                            r.evaluation_mode === "qualitative"
                              ? "long_text"
                              : r.family === "available_by_date"
                                ? "date"
                                : "multiple_choice",
                          label: r.expectation || "Question à préciser",
                          help: null,
                          required: false,
                          position: config.questions.length,
                          options: [],
                          constraints: {},
                        },
                      ],
                      requirements: config.requirements.map((x) =>
                        x.id === r.id ? { ...x, source_question_ids: [id] } : x,
                      ),
                    });
                  }}
                  disabled={config.questions.length >= 50}
                >
                  Ajouter une question source
                </Button>
              </div>
            </Alert>
          )}
          <fieldset>
            <legend>Questions sources</legend>
            {config.questions.map((q, j) => (
              <label className="source-choice" key={q.id}>
                <input
                  type="checkbox"
                  checked={r.source_question_ids.includes(q.id)}
                  onChange={(e) =>
                    requirement(r.id, {
                      source_question_ids: e.target.checked
                        ? [...r.source_question_ids, q.id]
                        : r.source_question_ids.filter((x) => x !== q.id),
                    })
                  }
                />{" "}
                {q.label || `Question ${j + 1}`}
              </label>
            ))}
          </fieldset>
          <Button
            variant="ghost"
            onClick={() =>
              change({
                ...config,
                requirements: config.requirements.filter((x) => x.id !== r.id),
              })
            }
          >
            Supprimer l’exigence {i + 1}
          </Button>
        </section>
      ))}
      <Button
        variant="secondary"
        disabled={config.requirements.length >= 20}
        onClick={() =>
          change({
            ...config,
            requirements: [
              ...config.requirements,
              {
                id: crypto.randomUUID(),
                family: Object.keys(families[config.type])[0],
                expectation: "",
                importance: "desired",
                evaluation_mode: "qualitative",
                assessment_mode: "automatic",
                source_question_ids: [],
                condition_rule: null,
              },
            ],
          })
        }
      >
        Ajouter une exigence
      </Button>
    </fieldset>
  );
}
