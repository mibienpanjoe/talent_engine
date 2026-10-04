"use client";
import { Field } from "../../components/ui/field";
import type { Question } from "./configuration";
export type QuestionAnswer = string | string[] | File[];
export function QuestionRenderer({
  question: q,
  value,
  onChange,
  error,
}: {
  question: Question;
  value: QuestionAnswer | undefined;
  onChange: (value: QuestionAnswer) => void;
  error?: string;
}) {
  const id = `answer-${q.id}`;
  const description =
    [q.help ? `${id}-hint` : null, error ? `${id}-error` : null]
      .filter(Boolean)
      .join(" ") || undefined;
  const label = q.label + (q.required ? " *" : " (facultatif)");
  const text = typeof value === "string" ? value : "";
  if (q.type === "long_text")
    return (
      <div className="ui-field">
        <label htmlFor={id}>{label}</label>
        {q.help && (
          <p id={`${id}-hint`} className="field-hint">
            {q.help}
          </p>
        )}
        <textarea
          id={id}
          className="ui-input"
          rows={5}
          required={q.required}
          minLength={q.constraints.min_length ?? undefined}
          maxLength={q.constraints.max_length ?? 10000}
          value={text}
          onChange={(e) => onChange(e.target.value)}
          aria-describedby={description}
          aria-invalid={Boolean(error)}
        />
        {error && (
          <p id={`${id}-error`} role="alert" className="field-error">
            {error}
          </p>
        )}
      </div>
    );
  if (q.type === "single_choice")
    return (
      <div className="ui-field">
        <label htmlFor={id}>{label}</label>
        {q.help && (
          <p id={`${id}-hint`} className="field-hint">
            {q.help}
          </p>
        )}
        <select
          id={id}
          className="ui-input"
          required={q.required}
          value={text}
          onChange={(e) => onChange(e.target.value)}
          aria-describedby={description}
          aria-invalid={Boolean(error)}
        >
          <option value="">Choisir une réponse</option>
          {q.options?.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </select>
        {error && (
          <p id={`${id}-error`} role="alert" className="field-error">
            {error}
          </p>
        )}
      </div>
    );
  if (q.type === "multiple_choice")
    return (
      <fieldset className="question-choices">
        <legend>{label}</legend>
        {q.help && <p>{q.help}</p>}
        {q.options?.map((o) => (
          <label className="source-choice" key={o.id}>
            <input
              type="checkbox"
              checked={
                Array.isArray(value) && (value as string[]).includes(o.id)
              }
              onChange={(e) => {
                const selected = (
                  Array.isArray(value) ? value : []
                ) as string[];
                onChange(
                  e.target.checked
                    ? [...selected, o.id]
                    : selected.filter((x) => x !== o.id),
                );
              }}
            />
            {o.label}
          </label>
        ))}
        <p className="field-hint">
          {q.constraints.min_items != null
            ? `Minimum : ${q.constraints.min_items}. `
            : ""}
          {q.constraints.max_items != null
            ? `Maximum : ${q.constraints.max_items}.`
            : ""}
        </p>
        {error && (
          <p id={`${id}-error`} role="alert" className="field-error">
            {error}
          </p>
        )}
      </fieldset>
    );
  if (q.type === "file")
    return (
      <div className="ui-field">
        <label htmlFor={id}>{label}</label>
        <p id={`${id}-hint`} className="field-hint">
          {q.help} PDF, PNG ou JPEG. Maximum {q.constraints.max_files ?? 5}{" "}
          fichiers,{" "}
          {Math.floor((q.constraints.max_bytes ?? 10485760) / 1048576)} Mio par
          fichier.
        </p>
        <input
          id={id}
          className="ui-input"
          type="file"
          required={q.required}
          multiple={(q.constraints.max_files ?? 5) > 1}
          accept={(
            q.constraints.allowed_media_types ?? [
              "application/pdf",
              "image/png",
              "image/jpeg",
            ]
          ).join(",")}
          onChange={(e) => onChange([...(e.target.files ?? [])])}
          aria-describedby={[`${id}-hint`, error ? `${id}-error` : ""]
            .filter(Boolean)
            .join(" ")}
          aria-invalid={Boolean(error)}
        />
        {error && (
          <p id={`${id}-error`} role="alert" className="field-error">
            {error}
          </p>
        )}
      </div>
    );
  return (
    <Field
      id={id}
      label={label}
      hint={q.help ?? undefined}
      error={error}
      type={
        {
          short_text: "text",
          email: "email",
          number: "number",
          date: "date",
          url: "url",
        }[q.type] ?? "text"
      }
      required={q.required}
      maxLength={
        q.type === "short_text" ? (q.constraints.max_length ?? 500) : undefined
      }
      minLength={
        q.type === "short_text"
          ? (q.constraints.min_length ?? undefined)
          : undefined
      }
      min={
        q.type === "number" ? (q.constraints.min_value ?? undefined) : undefined
      }
      max={
        q.type === "number" ? (q.constraints.max_value ?? undefined) : undefined
      }
      step={q.type === "number" ? "any" : undefined}
      value={text}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}
