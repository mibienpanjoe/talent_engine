import { families, questionTypes, type Configuration } from "./configuration";

const constraintLabels: Record<string, string> = {
  min_length: "Longueur minimale", max_length: "Longueur maximale",
  min_value: "Valeur minimale", max_value: "Valeur maximale",
  min_items: "Choix minimum", max_items: "Choix maximum",
  max_files: "Nombre de fichiers maximum", max_bytes: "Taille maximale (octets)",
  allowed_media_types: "Formats acceptés",
};

export function ConfigurationSummary({ config }: { config: Configuration }) {
  const familyLabels: Record<string, string> = families[config.type];
  return (
    <section className="configuration-summary" aria-label="Configuration figée">
      <h2>Configuration figée</h2>
      <details>
        <summary>Le besoin</summary>
        <dl className="configuration-facts">
          <div><dt>Type</dt><dd>{config.type === "training" ? "Formation" : "Recrutement"}</dd></div>
          <div><dt>Titre initial</dt><dd>{config.title}</dd></div>
          <div><dt>Domaine</dt><dd>{config.domain}</dd></div>
          <div><dt>Description du besoin</dt><dd className="preserve-lines">{config.description}</dd></div>
          <div><dt>Niveau visé</dt><dd>{config.target_level}</dd></div>
          <div><dt>Échéance</dt><dd>{config.deadline ? `${new Date(config.deadline).toLocaleString("fr-FR", { timeZone: "UTC" })} UTC` : "Aucune échéance"}</dd></div>
        </dl>
      </details>
      <details>
        <summary>Les questions · {config.questions.length}</summary>
        {config.questions.map((q, i) => (
          <article className="configuration-item" key={q.id}>
            <h3>{i + 1}. {q.label}</h3>
            <p>{questionTypes[q.type]} · {q.required ? "Obligatoire" : "Facultative"}</p>
            {q.help && <p className="preserve-lines">{q.help}</p>}
            {!!q.options?.length && <ul>{q.options.map(o => <li key={o.id}>{o.label}</li>)}</ul>}
            <dl className="configuration-facts">
              {Object.entries(q.constraints).filter(([, value]) => value !== null && value !== undefined).map(([key, value]) => (
                <div key={key}><dt>{constraintLabels[key] ?? key}</dt><dd>{Array.isArray(value) ? value.join(", ") : value}</dd></div>
              ))}
            </dl>
          </article>
        ))}
      </details>
      <details>
        <summary>Les exigences · {config.requirements.length}</summary>
        {config.requirements.map((r, i) => (
          <article className="configuration-item" key={r.id}>
            <h3>{i + 1}. {r.expectation}</h3>
            <p>{r.importance === "required" ? "Indispensable" : "Souhaitée"} · {r.evaluation_mode === "deterministic" ? "Condition de disponibilité" : familyLabels[r.family] ?? "Autre compétence"}</p>
            {r.evaluation_mode === "qualitative" && <p>{r.assessment_mode === "manual" ? "Appréciation humaine" : "Appréciation automatique"}</p>}
            {r.condition_rule?.kind === "available_by_date" && <p>Date attendue : {new Date(`${r.condition_rule.date}T00:00:00Z`).toLocaleDateString("fr-FR", { timeZone: "UTC" })}</p>}
            {r.condition_rule?.kind === "available_slots" && <p>Créneaux attendus : {r.condition_rule.option_ids.map(id => config.questions.find(q => q.id === r.condition_rule?.question_id)?.options?.find(o => o.id === id)?.label ?? "Option inconnue").join(", ")}</p>}
            <h4>Questions sources</h4>
            <ul>{r.source_question_ids.map(id => <li key={id}>{config.questions.find(q => q.id === id)?.label ?? "Question inconnue"}</li>)}</ul>
          </article>
        ))}
      </details>
    </section>
  );
}
