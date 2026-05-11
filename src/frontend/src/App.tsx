import React, { useState, useEffect, useCallback } from "react";
import { getPapers, getWords, getSettings, deletePaper, uploadPapers } from "./api";
import type { Paper, WordEntry, Settings } from "./types";
import PaperList from "./components/PaperList";
import WordTable from "./components/WordTable";
import SettingsPanel from "./components/SettingsPanel";
import WordDetailModal from "./components/WordDetailModal";

const API_BASE = "http://localhost:8000";

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

  useEffect(() => { fetchPapers(); fetchSettings(); }, [fetchPapers, fetchSettings]);
  useEffect(() => { fetchWords(); }, [fetchWords, band, page, sortBy, sortOrder]);

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
              ].map(([key, label]) => (
                <button key={key} className={`tab ${band === key ? "active" : ""}`} onClick={() => { setBand(key); setPage(1); }}>
                  {label} ({bands[key as keyof typeof bands] ?? "..."})
                </button>
              ))}
            </div>
            <div className="search-bar">
              <input type="text" placeholder="搜索单词..." value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleSearch()} />
              <button className="btn btn-sm" onClick={handleSearch}>搜索</button>
            </div>
          </div>

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
        </main>
      </div>

      {selectedWord && <WordDetailModal word={selectedWord} onClose={() => setSelectedWord(null)} />}
    </div>
  );
}
