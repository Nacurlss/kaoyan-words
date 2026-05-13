import type { Paper, WordListResponse, WordEntry, Settings, SenseDetailResponse, PersonalWordsResponse, PersonalVocabUploadResult, Translation, TranslateProgress } from "./types";

const API_BASE = "";

export async function uploadPapers(files: File[]): Promise<{ uploaded: number; total_units: number }> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  const res = await fetch(`${API_BASE}/api/upload`, { method: "POST", body: formData });
  return res.json();
}

export async function getPapers(): Promise<Paper[]> {
  const res = await fetch(`${API_BASE}/api/papers`);
  return res.json();
}

export async function deletePaper(year: string): Promise<void> {
  await fetch(`${API_BASE}/api/papers/${encodeURIComponent(year)}`, { method: "DELETE" });
}

export async function getWords(params: {
  band?: string;
  sort_by?: string;
  sort_order?: string;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<WordListResponse> {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== "") sp.set(k, String(v)); });
  const res = await fetch(`${API_BASE}/api/words?${sp.toString()}`);
  return res.json();
}

export async function getWordDetail(lemma: string): Promise<WordEntry> {
  const res = await fetch(`${API_BASE}/api/word/${encodeURIComponent(lemma)}`);
  return res.json();
}

export async function getSenseDetail(lemma: string, pos: string): Promise<SenseDetailResponse> {
  const sp = new URLSearchParams({ lemma, pos });
  const res = await fetch(`${API_BASE}/api/sense_detail?${sp.toString()}`);
  return res.json();
}

export async function getSettings(): Promise<Settings> {
  const res = await fetch(`${API_BASE}/api/settings`);
  return res.json();
}

export async function updateSettings(settings: Partial<Settings>): Promise<Settings> {
  const res = await fetch(`${API_BASE}/api/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  return res.json();
}

export function exportUrl(band: string, format: "csv" | "excel"): string {
  return `${API_BASE}/api/export/${format}?band=${band}`;
}

export async function uploadPersonalVocab(file: File): Promise<PersonalVocabUploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/personal_vocab/upload`, { method: "POST", body: formData });
  return res.json();
}

export async function getPersonalWords(params: {
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<PersonalWordsResponse> {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== "") sp.set(k, String(v)); });
  const res = await fetch(`${API_BASE}/api/personal_words?${sp.toString()}`);
  return res.json();
}

export async function clearPersonalVocab(): Promise<void> {
  await fetch(`${API_BASE}/api/personal_vocab`, { method: "DELETE" });
}

export async function startPreTranslate(): Promise<{ started: boolean; total: number }> {
  const res = await fetch(`${API_BASE}/api/translate/start`, { method: "POST" });
  return res.json();
}

export async function getTranslateProgress(): Promise<TranslateProgress> {
  const res = await fetch(`${API_BASE}/api/translate/progress`);
  return res.json();
}

export async function fetchTranslations(
  items: { text: string; word: string; lemma: string }[]
): Promise<Record<string, Translation>> {
  const res = await fetch(`${API_BASE}/api/translate/sentences`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(items),
  });
  const data = await res.json();
  return data.translations || {};
}
