import React, { useState, useEffect, useCallback } from "react";
import { getPapers, getWords, getSettings, deletePaper, uploadPapers, uploadPersonalVocab, getPersonalWords, clearPersonalVocab, startPreTranslate, getTranslateProgress } from "./api";
import type { Paper, WordEntry, Settings, PersonalWord, TranslateProgress } from "./types";
import PaperList from "./components/PaperList";
import WordTable from "./components/WordTable";
import SettingsPanel from "./components/SettingsPanel";
import WordDetailModal from "./components/WordDetailModal";
import PersonalVocabTable from "./components/PersonalVocabTable";

const API_BASE = "";

export default function App() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [words, setWords] = useState<WordEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [band, setBand] = useState<string>("high");
  const [bands, setBands] = useState({ high: 0, medium: 0, low: 0 });
  const [settings, setSettings] = useState<Settings>({ high_threshold: 0.5, medium_threshold: 0.2, exclude_levels: ["primary", "zhongkao"], exclude_groups: [] });
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("frequency");
  const [sortOrder, setSortOrder] = useState("desc");
  const [selectedWord, setSelectedWord] = useState<WordEntry | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [personalWords, setPersonalWords] = useState<PersonalWord[]>([]);
  const [personalTotal, setPersonalTotal] = useState(0);
  const [personalPage, setPersonalPage] = useState(1);
  const [personalVocabSize, setPersonalVocabSize] = useState(0);
  const [personalMatched, setPersonalMatched] = useState(0);
  const [personalLoading, setPersonalLoading] = useState(false);
  const [personalSearch, setPersonalSearch] = useState("");
  const [vocabUploading, setVocabUploading] = useState(false);
  const [translateProgress, setTranslateProgress] = useState<TranslateProgress>({
    done: 0, total: 0, status: "idle", current: "",
  });
  const [preTranslating, setPreTranslating] = useState(false);

  const pageSize = 50;

  const fetchWords = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getWords({ band, sort_by: sortBy, sort_order: sortOrder, search, page, page_size: pageSize });
      setWords(res.words);
      setTotal(res.total);
      setBands(res.bands ?? { high: 0, medium: 0, low: 0 });
    } finally {
      setLoading(false);
    }
  }, [band, sortBy, sortOrder, search, page]);

  const fetchPapers = useCallback(async () => {
    const p = await getPapers();
    setPapers(p);
  }, []);

  const fetchSettings = useCallback(async () => {
    const s = await getSettings();
    setSettings(s);
  }, []);

  const fetchPersonalWords = useCallback(async () => {
    setPersonalLoading(true);
    try {
      const res = await getPersonalWords({
        search: personalSearch,
        page: personalPage,
        page_size: pageSize,
      });
      setPersonalWords(res.words);
      setPersonalTotal(res.total);
      setPersonalVocabSize(res.vocab_size);
      setPersonalMatched(res.matched_count);
    } finally {
      setPersonalLoading(false);
    }
  }, [personalSearch, personalPage]);

  useEffect(() => { fetchPapers(); fetchSettings(); }, [fetchPapers, fetchSettings]);
  useEffect(() => { if (band !== "personal") fetchWords(); }, [fetchWords, band, page, sortBy, sortOrder]);
  useEffect(() => { fetchPersonalWords(); }, [fetchPersonalWords, personalPage]);

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      await uploadPapers(Array.from(files));
      await fetchPapers();
      await fetchWords();
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (filename: string) => {
    await deletePaper(filename);
    await fetchPapers();
    await fetchWords();
  };

  const handleSettingsChange = async (s: Settings) => {
    setSettings(s);
    await fetchWords();
  };

  const handleSearch = () => {
    setPage(1);
    fetchWords();
  };

  const handleVocabUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setVocabUploading(true);
    try {
      const result = await uploadPersonalVocab(files[0]);
      alert(`已导入 ${result.unique_count} 个生词（原始 ${result.raw_count} 个）`);
      setPersonalPage(1);
      await fetchPersonalWords();
    } catch (e) {
      alert("上传失败，请检查文件格式（.txt，每行一个单词）");
    } finally {
      setVocabUploading(false);
    }
  };

  const handleVocabClear = async () => {
    await clearPersonalVocab();
    setPersonalWords([]);
    setPersonalTotal(0);
    setPersonalVocabSize(0);
    setPersonalMatched(0);
  };

  const handlePersonalSearch = () => {
    setPersonalPage(1);
    fetchPersonalWords();
  };

  const pollProgress = useCallback(async () => {
    const p = await getTranslateProgress();
    setTranslateProgress(p);
    if (p.status === "running") {
      setTimeout(pollProgress, 1000);
    } else {
      setPreTranslating(false);
    }
  }, []);

  useEffect(() => { pollProgress(); }, []);

  const handlePreTranslate = async () => {
    setPreTranslating(true);
    await startPreTranslate();
    pollProgress();
  };

  return (
    <div className="app-layout">
      <header className="app-header">
        <h1 className="app-title">考研单词频率筛选</h1>
        <div className="header-actions">
          <label className="btn btn-primary upload-btn">
            {uploading ? "导入中..." : "导入试卷"}
            <input type="file" multiple accept=".docx,.pdf" hidden onChange={(e) => handleUpload(e.target.files)} />
          </label>
          <label className="btn btn-outline upload-btn">
            {uploading ? "导入中..." : "导入文件夹"}
            <input {...{ webkitdirectory: "", directory: "" } as React.InputHTMLAttributes<HTMLInputElement>} type="file" multiple accept=".docx,.pdf" hidden onChange={(e) => handleUpload(e.target.files)} />
          </label>
          <label className="btn btn-outline upload-btn" style={{ borderColor: "var(--accent)", color: "var(--accent)" }}>
            {vocabUploading ? "导入中..." : personalWords.length > 0 ? `生词本(${personalVocabSize}词)` : "上传生词本"}
            <input type="file" accept=".txt,.xlsx" hidden onChange={(e) => handleVocabUpload(e.target.files)} />
          </label>
          {personalWords.length > 0 && (
            <button className="btn btn-outline" onClick={handleVocabClear} style={{ color: "#c0392b", borderColor: "#c0392b" }}>
              清除生词本
            </button>
          )}
          {translateProgress.status !== "done" && (
            <button
              className="btn btn-outline"
              onClick={handlePreTranslate}
              disabled={preTranslating}
              style={{ borderColor: "var(--success)", color: "var(--success)" }}
            >
              {preTranslating
                ? `翻译中 ${translateProgress.done}/${translateProgress.total}`
                : translateProgress.total > 0
                  ? `继续翻译 (${translateProgress.done}/${translateProgress.total})`
                  : "预翻译全部句子"}
            </button>
          )}
          <a href={`${API_BASE}/api/export/excel?band=${band}`} className="btn btn-outline" target="_blank">导出 Excel</a>
          <a href={`${API_BASE}/api/export/csv?band=${band}`} className="btn btn-outline" target="_blank">导出 CSV</a>
        </div>
      </header>

      <div className="app-body">
        <aside className="sidebar">
          <PaperList papers={papers} onDelete={handleDelete} />
          <SettingsPanel settings={settings} onChange={handleSettingsChange} />
        </aside>

        <main className="main-content">
          <div className="toolbar">
            <div className="band-tabs">
              {[
                ["high", "高频词"],
                ["medium", "中频词"],
                ["low", "低频词"],
                ["all", "全部"],
                ["personal", "生词本"],
              ].map(([key, label]) => (
                <button key={key} className={`tab ${band === key ? "active" : ""}`} onClick={() => { setBand(key); setPage(1); }}>
                  {label}
                  {key === "personal"
                    ? ` (${personalVocabSize > 0 ? personalVocabSize : 0})`
                    : ` (${bands[key as keyof typeof bands] ?? "..."})`}
                </button>
              ))}
            </div>
            {band === "personal" ? (
              <div className="search-bar">
                <input type="text" placeholder="搜索生词..." value={personalSearch}
                  onChange={(e) => setPersonalSearch(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handlePersonalSearch()} />
                <button className="btn btn-sm" onClick={handlePersonalSearch}>搜索</button>
              </div>
            ) : (
              <div className="search-bar">
                <input type="text" placeholder="搜索单词..." value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()} />
                <button className="btn btn-sm" onClick={handleSearch}>搜索</button>
              </div>
            )}
          </div>

          {band === "personal" ? (
            <PersonalVocabTable
              words={personalWords}
              loading={personalLoading}
              total={personalTotal}
              page={personalPage}
              pageSize={pageSize}
              vocabSize={personalVocabSize}
              matchedCount={personalMatched}
              onPageChange={setPersonalPage}
            />
          ) : (
            <WordTable
              words={words}
              loading={loading}
              total={total}
              page={page}
              pageSize={pageSize}
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={(field) => {
                if (sortBy === field) setSortOrder(sortOrder === "desc" ? "asc" : "desc");
                else { setSortBy(field); setSortOrder("desc"); }
              }}
              onPageChange={setPage}
              onWordClick={(lemma) => {
                const w = words.find((x) => x.lemma === lemma) || null;
                setSelectedWord(w);
              }}
            />
          )}
        </main>
      </div>

      {selectedWord && <WordDetailModal word={selectedWord} onClose={() => setSelectedWord(null)} />}
    </div>
  );
}
