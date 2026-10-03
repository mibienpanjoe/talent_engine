import type { ComponentProps } from "react";
type FieldProps = ComponentProps<"input"> & { id: string; label: string; hint?: string; error?: string };
export function Field({ id, label, hint, error, className = "", "aria-describedby": describedBy, ...props }: FieldProps) {
  const descriptions = [describedBy, hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(" ");
  return <div className="ui-field"><label htmlFor={id}>{label}</label>
    {hint && <p id={`${id}-hint`} className="field-hint">{hint}</p>}
    <input id={id} className={`ui-input ${className}`} aria-invalid={error ? true : undefined} aria-describedby={descriptions || undefined} {...props} />
    {error && <p id={`${id}-error`} className="field-error" role="alert">{error}</p>}
  </div>;
}
