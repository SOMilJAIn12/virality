// Thin client around the Express API described in
// backend/src/routes/simulations.js. The response envelope is always
// { success, data } or { success: false, error: { message } }.

export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:4000/api";

export const TERMINAL_STATUSES = new Set(["COMPLETED", "FAILED"]);

export const PERSONA_LABELS = {
  ai_ml_student: "AI/ML Student",
  software_developer: "Software Developer",
  college_student: "College Student",
  entrepreneur: "Entrepreneur",
  gamer: "Gamer",
  meme_entertainment_user: "Meme/Entertainment User",
  fitness_enthusiast: "Fitness Enthusiast",
  productivity_enthusiast: "Productivity Enthusiast",
  finance_business_user: "Finance/Business User",
  fashion_lifestyle_user: "Fashion/Lifestyle User",
  general_social_media_user: "General Social Media User",
  tech_professional: "Tech Professional",
  creator_influencer: "Creator/Influencer",
  parent: "Parent",
  educator: "Educator",
  surprise_curiosity_viewer: "Surprise/Curiosity Viewer",
  short_form_entertainment_viewer: "Short-Form Entertainment Viewer",
  mainstream_casual_viewer: "Mainstream Casual Viewer",
};

export async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, options);
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.error?.message || "Request failed.");
  }

  return payload.data;
}

export function getPersonaName(personaId) {
  return PERSONA_LABELS[personaId] || personaId.replace(/_/g, " ");
}

export function formatDate(value) {
  return new Date(value).toLocaleString();
}

export function downloadReport(simulation, result) {
  if (!result || !simulation) return;

  const payload = {
    simulationId: simulation.simulationId,
    status: simulation.status,
    result,
  };

  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  });

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `virality-report-${simulation.simulationId}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

export async function createSimulation(file, seed) {
  const formData = new FormData();
  formData.append("video", file);

  if (seed !== undefined && seed !== null && seed !== "") {
    formData.append("seed", String(seed));
  }

  return request("/simulations", { method: "POST", body: formData });
}

export async function fetchSimulation(id) {
  return request(`/simulations/${id}`);
}

export async function fetchHistory() {
  return request("/simulations");
}
