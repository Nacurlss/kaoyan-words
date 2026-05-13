import { useState } from "react";
import type { PersonalWord, SenseDetail, Translation } from "../types";
import { getSenseDetail, fetchTranslations } from "../api";
import TranslateLine from "./TranslateLine";

interface Props {
  words: PersonalWord[];
  loading: boolean;
  total: number;
  page: number;
  pageSize: number;
  vocabSize: number;
  matchedCount: number;
  onPageChange: (page: number) => void;
}

function SenseDetailPopover({ lemma, pos, onClose }: { lemma: string; pos: string; onClose: () => void }) {
  const [detail, setDetail] = useState<{ unit_count: number; sentences: SenseDetail[] } | null>(null);
  const [translations, setTranslations] = useState<Record<string, Translation>>({});
  const [translating, setTranslating] = useState(false);

  useState(() => {
    getSenseDetail(lemma, pos).then(setDetail);
  });

  useState(() => {
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
  });

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
                  <div className="paper-label">
                    {typeLabel}{s.year} · {s.section_label}
                  </div>
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

export default function PersonalVocabTable({
  words, loading, total, page, pageSize,
  vocabSize, matchedCount, onPageChange,
}: Props) {
  const totalPages = Math.ceil(total / pageSize);
  const [sensePop, setSensePop] = useState<{ lemma: string; pos: string } | null>(null);

  return (
    <div className="word-table-container">
      <div style={{ marginBottom: 12, fontSize: 13, color: "var(--text-secondary)" }}>
        生词本共 <strong>{vocabSize}</strong> 词，
        在真题中匹配到 <strong style={{ color: "var(--accent)" }}>{matchedCount}</strong> 个
        {matchedCount < vocabSize && (
          <span>（{vocabSize - matchedCount} 个未在真题中出现）</span>
        )}
      </div>

      {loading ? (
        <div className="loading">加载中……</div>
      ) : words.length === 0 ? (
        <div className="empty">生词本为空，请先上传生词本文件</div>
      ) : (
        <table className="word-table">
          <thead>
            <tr>
              <th style={{ width: 120 }}>单词</th>
              <th style={{ width: 80 }}>词频</th>
              <th style={{ width: 200 }}>释义</th>
              <th>真题例句</th>
            </tr>
          </thead>
          <tbody>
            {words.map((w) => (
              <tr key={w.lemma} className={!w.in_exam_papers ? "not-in-exam" : ""}>
                <td className="lemma-cell">
                  <strong>{w.lemma}</strong>
                  {!w.in_exam_papers && (
                    <span style={{ fontSize: 10, color: "#999", marginLeft: 6 }}>
                      未在真题中出现
                    </span>
                  )}
                </td>
                <td className="freq-cell">
                  <span className="freq-badge" style={{
                    background: w.frequency >= 0.1 ? "var(--accent)" : w.frequency > 0 ? "var(--text-secondary)" : "transparent",
                    color: w.frequency > 0 ? "#fff" : "#999",
                    padding: "2px 8px", borderRadius: 10, fontSize: 12,
                  }}>
                    {w.frequency > 0 ? (w.frequency * 100).toFixed(1) + "%" : "无数据"}
                  </span>
                </td>
                <td className="sense-cell">
                  {w.senses.length > 0 ? (
                    <div className="senses">
                      {w.senses.map((s, i) => (
                        <div key={i} className="sense-line">
                          <span className="pos-tag">{s.pos}</span>
                          <span className="meaning">{s.meaning}</span>
                          {s.count > 0 ? (
                            <span
                              className="count-tag"
                              style={{ cursor: "pointer", textDecoration: "underline" }}
                              onClick={() => setSensePop({ lemma: w.lemma, pos: s.pos })}
                            >
                              {s.count}次
                            </span>
                          ) : (
                            <span className="count-tag" style={{ opacity: 0.4 }}>{s.count}次</span>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <span style={{ color: "#999", fontSize: 12 }}>无释义</span>
                  )}
                </td>
                <td className="example-cell">
                  {w.exam_example ? (
                    <div className="example-block">
                      <div className="example-text">{w.exam_example.text}</div>
                      <div className="example-source">
                        {w.exam_example.exam_type ? `${w.exam_example.exam_type} · ` : ""}
                        {w.exam_example.year} · {w.exam_example.section_label}
                      </div>
                    </div>
                  ) : w.momo_example ? (
                    <div className="example-block momo-example">
                      <div className="example-text">{w.momo_example}</div>
                      <div className="example-source">墨墨原版例句</div>
                    </div>
                  ) : (
                    <span style={{ color: "#999", fontSize: 12 }}>无例句</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {totalPages > 1 && (
        <div className="pagination">
          <button disabled={page <= 1} onClick={() => onPageChange(page - 1)}>上一页</button>
          <span>第 {page} / {totalPages} 页（共 {total} 词）</span>
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
    </div>
  );
}
