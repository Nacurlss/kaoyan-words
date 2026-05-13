import type { WordEntry, SenseDetail, Translation } from "../types";
import { useState, useEffect } from "react";
import { getSenseDetail, fetchTranslations } from "../api";
import TranslateLine from "./TranslateLine";

interface Props {
  words: WordEntry[];
  loading: boolean;
  total: number;
  page: number;
  pageSize: number;
  sortBy: string;
  sortOrder: string;
  onSort: (field: string) => void;
  onPageChange: (p: number) => void;
  onWordClick: (lemma: string) => void;
}

const COLUMNS = [
  { key: "lemma",    label: "单词",     sortable: true },
  { key: "senses",   label: "释义（次数）", sortable: false },
  { key: "example",  label: "常考例句",  sortable: false },
  { key: "frequency", label: "年频率",   sortable: true },
];

function freqClass(freq: number): string {
  if (freq >= 0.5) return "freq-high";
  if (freq >= 0.2) return "freq-medium";
  return "freq-low";
}

function SenseDetailPopover({ lemma, pos, onClose }: { lemma: string; pos: string; onClose: () => void }) {
  const [detail, setDetail] = useState<{ unit_count: number; sentences: SenseDetail[] } | null>(null);
  const [translations, setTranslations] = useState<Record<string, Translation>>({});
  const [translating, setTranslating] = useState(false);

  useState(() => {
    getSenseDetail(lemma, pos).then(setDetail);
  });

  useEffect(() => {
    if (!detail || detail.sentences.length === 0) return;
    setTranslating(true);
    const items = detail.sentences.map((s) => ({
      text: s.text,
      word: s.word,
      lemma: "",
    }));
    fetchTranslations(items).then((t) => {
      setTranslations(t);
      setTranslating(false);
    });
  }, [detail]);

  if (!detail) {
    return (
      <div className="sense-detail-overlay" onClick={onClose}>
        <div className="sense-detail" onClick={(e) => e.stopPropagation()}>
          <p>加载中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="sense-detail-overlay" onClick={onClose}>
      <div className="sense-detail" onClick={(e) => e.stopPropagation()}>
        <div className="sense-detail-header">
          <strong>{lemma}</strong> · {pos}. · {detail.unit_count} 个考试单元
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="sense-detail-body">
          {detail.sentences.length === 0 ? (
            <p style={{ color: "var(--text-secondary)" }}>暂无例句</p>
          ) : (
            detail.sentences.slice(0, 50).map((s, i) => {
              const idx = s.text.toLowerCase().indexOf(s.word.toLowerCase());
              const typeLabel = s.exam_type ? `${s.exam_type} · ` : "";
              return (
                <div key={i} className="sentence-item">
                  <div className="paper-label">{typeLabel}{s.year} · {s.section_label}</div>
                  <div>
                    {idx >= 0 ? (
                      <>
                        {s.text.slice(0, idx)}
                        <span className="highlight">{s.text.slice(idx, idx + s.word.length)}</span>
                        {s.text.slice(idx + s.word.length)}
                      </>
                    ) : (
                      s.text
                    )}
                  </div>
                  <TranslateLine
                    translation={translations[`${s.text}|${s.word}`] || null}
                    loading={translating}
                  />
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

export default function WordTable({ words, loading, total, page, pageSize, sortBy, sortOrder, onSort, onPageChange, onWordClick }: Props) {
  const totalPages = Math.ceil(total / pageSize);
  const [sensePop, setSensePop] = useState<{ lemma: string; pos: string } | null>(null);

  if (!loading && words.length === 0) {
    return (
      <div className="empty-state">
        <h3>暂无数据</h3>
        <p>真题已自动加载。如需添加更多试卷，请使用「导入试卷」按钮。</p>
      </div>
    );
  }

  return (
    <>
      <div className="word-table-wrap">
        <table>
          <thead>
            <tr>
              {COLUMNS.map((col) => (
                <th key={col.key} className={sortBy === col.key ? "sorted" : ""}
                    onClick={() => col.sortable && onSort(col.key)}>
                  {col.label} {sortBy === col.key ? (sortOrder === "desc" ? "↓" : "↑") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={4} className="loading-state">加载中...</td></tr>
            ) : (
              words.map((w) => (
                <tr key={w.lemma} className="word-row" onClick={() => onWordClick(w.lemma)}>
                  <td>
                    <div className="word-lemma">{w.lemma}</div>
                    {w.variants.length > 0 && w.variants[0] !== w.lemma && (
                      <div className="word-variants">{w.variants.slice(0, 4).join(", ")}</div>
                    )}
                  </td>
                  <td>
                    <div className="word-senses">
                      {w.senses && w.senses.length > 0
                        ? w.senses.slice(0, 4).map((s, i) => (
                            <span key={i} className="sense-line">
                              {s.pos}. {s.meaning}{" "}
                              <span
                                className="sense-count"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSensePop({ lemma: w.lemma, pos: s.pos });
                                }}
                              >
                                ({s.count})
                              </span>
                              {i < Math.min(w.senses.length, 4) - 1 ? "；" : ""}
                            </span>
                          ))
                        : "—"}
                    </div>
                  </td>
                  <td>
                    <div className="example-cell">
                      {w.top_example ? (
                        <>
                          <div className="example-text">
                            {w.top_example.text.length > 70
                              ? w.top_example.text.slice(0, 70) + "…"
                              : w.top_example.text}
                          </div>
                          <div className="example-source">
                            {w.top_example.exam_type ? `${w.top_example.exam_type} · ` : ""}
                            {w.top_example.year} · {w.top_example.section_label}
                          </div>
                        </>
                      ) : (
                        "—"
                      )}
                    </div>
                  </td>
                  <td>
                    <span className={`word-freq ${freqClass(w.frequency)}`}>
                      {w.frequency.toFixed(3)}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button disabled={page <= 1} onClick={() => onPageChange(page - 1)}>上一页</button>
          <span>第 {page} / {totalPages} 页（共 {total} 条）</span>
          <button disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>下一页</button>
        </div>
      )}

      {sensePop && (
        <SenseDetailPopover
          lemma={sensePop.lemma}
          pos={sensePop.pos}
          onClose={() => setSensePop(null)}
        />
      )}
    </>
  );
}
