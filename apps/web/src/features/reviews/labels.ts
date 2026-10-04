export const viewLabels = {
  all: "Tous les dossiers",
  ready: "Prêts à examiner",
  needs_review: "À vérifier",
  condition_unmet: "Conditions non satisfaites",
} as const;
export const processingLabels = {
  queued: "En attente d’analyse",
  collecting: "Collecte en cours",
  evaluating: "Évaluation en cours",
  completed: "Analyse disponible",
  completed_partial: "Analyse partielle",
  failed: "Incident de traitement",
} as const;
export const decisionLabels = {
  to_review: "À examiner",
  shortlisted: "Présélectionné",
  not_selected: "Non retenu",
} as const;
export const eligibilityLabels = {
  eligible: "Conditions satisfaites",
  condition_unmet: "Condition indispensable non satisfaite",
  needs_review: "Disponibilité à vérifier",
  not_applicable: "Aucune condition indispensable",
} as const;
export const assessmentLabels = {
  evaluated: "Apprécié",
  insufficient_information: "Informations insuffisantes",
  conflicting_information: "Informations contradictoires",
  source_unavailable: "Source indisponible",
} as const;
export function displayDecimal(value: string, score = false) {
  return new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: score ? 1 : 0,
    maximumFractionDigits: 1,
  }).format(Number(value));
}
