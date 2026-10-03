import type { components } from "../../lib/api.generated";
export type Configuration = components["schemas"]["DraftConfiguration"];
export type Campaign = components["schemas"]["Campaign"];
export type Question = components["schemas"]["Question"];
export type Requirement = components["schemas"]["Requirement"];
export const families = {
  training: {
    programming_foundations: "Bases de programmation",
    practical_work: "Mise en pratique",
    learning_approach: "Démarche d’apprentissage",
  },
  recruitment: {
    audience_understanding: "Compréhension d’audience",
    results_analysis: "Analyse de résultats",
    content_production: "Production de contenu",
  },
};
export const questionTypes: Record<Question["type"], string> = {
  short_text: "Texte court",
  long_text: "Texte long",
  email: "Email",
  number: "Nombre",
  date: "Date",
  single_choice: "Choix simple",
  multiple_choice: "Choix multiple",
  url: "Lien",
  file: "Document",
};
export function emptyConfiguration(): Configuration {
  return {
    type: "training",
    title: "",
    domain: "",
    description: "",
    target_level: "",
    deadline: null,
    requirements: [],
    questions: [],
  };
}
