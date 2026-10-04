import type { components } from "../../lib/api.generated";
import { EvidenceButton } from "./evidence-button";
import { assessmentLabels } from "./labels";
type Event = components["schemas"]["ReviewEvent"];
type Detail = components["schemas"]["ApplicationDetail"];
type Evaluation = components["schemas"]["Evaluation"];
export type ReapplyChoice = {
  selected: boolean;
  value: string;
  proof: string;
  note: string;
  zero: string;
};
export function activeCorrections(
  history: Event[],
  evaluationId?: string | null,
) {
  const latest = new Map<string, Event>();
  for (const item of history)
    if (
      item.evaluation_id === evaluationId &&
      ["assessment", "condition"].includes(item.kind)
    )
      latest.set(`${item.kind}:${item.criterion_id}`, item);
  return [...latest.values()].filter((item) => item.action === "set");
}
export function initialChoice(
  event: Event,
  dossier: Detail,
  base: Evaluation,
): ReapplyChoice {
  const oldIds = Array.isArray(event.value.evidence_ids)
    ? event.value.evidence_ids.map(String)
    : [];
  return {
    selected: false,
    value:
      typeof event.value.level === "number"
        ? String(event.value.level)
        : String(event.value.status),
    proof:
      oldIds.find(
        (id) =>
          base.provenance.evidence_ids.includes(id) ||
          dossier.evidence?.some(
            (e) => e.id === id && e.nature === "human_verification",
          ),
      ) ?? "",
    note: "",
    zero: String(event.value.zero_evidence_quote ?? ""),
  };
}
export function ReapplicationFields({
  event,
  choice,
  change,
  dossier,
  base,
  disabled,
}: {
  event: Event;
  choice: ReapplyChoice;
  change: (choice: ReapplyChoice) => void;
  dossier: Detail;
  base: Evaluation;
  disabled: boolean;
}) {
  const title =
    dossier.snapshot.configuration.requirements.find(
      (r) => r.id === event.criterion_id,
    )?.expectation ?? "Correction";
  const notes =
    dossier.evidence
      ?.filter((e) => e.nature === "human_verification")
      .map((e) => e.id) ?? [];
  const proofs = [...new Set([...base.provenance.evidence_ids, ...notes])];
  return (
    <fieldset className="question-choices">
      <legend>{title}</legend>
      <label className="source-choice">
        <input
          type="checkbox"
          checked={choice.selected}
          disabled={disabled}
          onChange={(e) => change({ ...choice, selected: e.target.checked })}
        />
        Reporter cette correction après vérification
      </label>
      {choice.selected && (
        <div className="ui-field">
          <label className="ui-field">
            Nouvelle appréciation
            <select
              className="ui-input"
              value={choice.value}
              disabled={disabled}
              onChange={(e) => change({ ...choice, value: e.target.value })}
            >
              {event.kind === "assessment" ? (
                <>
                  {[0, 1, 2, 3, 4].map((level) => (
                    <option key={level} value={level}>
                      Niveau {level} / 4
                    </option>
                  ))}
                  {Object.entries(assessmentLabels)
                    .filter(([key]) => key !== "evaluated")
                    .map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                </>
              ) : (
                <>
                  <option value="met">Satisfaite</option>
                  <option value="unmet">Non satisfaite</option>
                  <option value="unknown">À vérifier</option>
                </>
              )}
            </select>
          </label>
          <label className="ui-field">
            Preuve à reciter
            <select
              className="ui-input"
              value={choice.proof}
              disabled={disabled}
              onChange={(e) => change({ ...choice, proof: e.target.value })}
            >
              <option value="">Ajouter une nouvelle observation humaine</option>
              {proofs.map((id, i) => (
                <option key={id} value={id}>
                  {notes.includes(id)
                    ? "Note humaine"
                    : "Passage de la nouvelle analyse"}{" "}
                  {i + 1}
                </option>
              ))}
            </select>
          </label>
          {choice.proof && (
            <EvidenceButton id={choice.proof} label="Vérifier cette preuve" />
          )}
          <label className="ui-field">
            Nouvelle observation humaine{choice.proof ? " (facultative)" : ""}
            <textarea
              className="ui-input"
              rows={3}
              required={!choice.proof}
              maxLength={2000}
              value={choice.note}
              disabled={disabled}
              onChange={(e) => change({ ...choice, note: e.target.value })}
            />
          </label>
          {event.kind === "assessment" && choice.value === "0" && (
            <label className="ui-field">
              Passage justifiant le niveau zéro
              <input
                className="ui-input"
                required
                maxLength={1000}
                value={choice.zero}
                disabled={disabled}
                onChange={(e) => change({ ...choice, zero: e.target.value })}
              />
            </label>
          )}
        </div>
      )}
    </fieldset>
  );
}
