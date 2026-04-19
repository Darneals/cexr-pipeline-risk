// Fix 8: API base URL is now environment-controlled.
// Local dev:   create .env in phase9/frontend/ containing VITE_API_BASE=http://127.0.0.1:8000
// Evaluation:  create .env in phase9/frontend/ containing VITE_API_BASE=https://your-ngrok-url
// Fallback:    if no .env exists, defaults to localhost (your normal local dev still works)

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

export async function getRegions() {
  const res = await fetch(`${API_BASE}/regions`);
  return res.json();
}

export async function getManifest(slug) {
  const res = await fetch(`${API_BASE}/regions/${slug}/manifest`);
  return res.json();
}

export async function getLayer(slug, key) {
  const res = await fetch(`${API_BASE}/regions/${slug}/geo/${key}`);
  return res.json();
}
