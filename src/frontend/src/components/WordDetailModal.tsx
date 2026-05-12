import { useEffect, useState } from "react";
import { getWordDetail } from "../api";
import type { WordEntry } from "../types";

interface Props {
  word: WordEntry;
  onClose: () => void;
}

export default function WordDetailModal({ word, onClose }: Props) {
  const [detail, setDetail] = useState<WordEntry>(word);

  useEffect(() => {
    getWordDetail(word.lemma).then(setDetail);
  }, [word.lemma]);

  const totalUnits = Object.values(detail.pos_counts || {}).reduce((a, b) => a + b, 0);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{detail.lemma}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-stats">
          <span>频率 <strong>{detail.frequency.toFixed(4)}</strong></span>
          <span>覆盖 <strong>{totalUnits}</strong> 个考试单元</span>
        </div>

        {detail.variants.length > 0 && (
          <div className="modal-section">
            <h4>词形变体</h4>
            <div className="meanings-list">
              {detail.variants.map((v) => (
                <span key={v} className="meaning-tag">{v}</span>
              ))}
            </div>
          </div>
        )}

        {detail.senses && detail.senses.length > 0 && (
          <div className="modal-section">
            <h4>释义（墨墨词库 · 按词性）</h4>
            <div className="senses-list">
              {detail.senses.map((s, i) => (
                <div key={i} className="sense-item">
                  <span className="sense-pos">{s.pos}.</span>
                  <span className="sense-meaning">{s.meaning}</span>
                  <span className="sense-badge">{s.count}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Sentences grouped by POS */}
        {detail.sentences_by_pos && Object.keys(detail.sentences_by_pos).length > 0 && (
          <div className="modal-section">
            <h4>真题例句（按词性分组）</h4>
            {Object.entries(detail.sentences_by_pos).map(([pos, sents]) => (
              <div key={pos} className="pos-sentence-group">
                <h5 className="pos-label">{pos}. ({sents.length} 句)</h5>
                {sents.slice(0, 10).map((s, i) => {
                  const idx = s.text.toLowerCase().indexOf(s.word.toLowerCase());
                  return (
                    <div key={i} className="sentence-item">
                      <div className="paper-label">{s.exam_type ? `${s.exam_type} · ` : ""}{s.year} · {s.section_label}</div>
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
                  );
                })}
              </div>
            ))}
          </div>
        )}

        {(!detail.sentences_by_pos || Object.keys(detail.sentences_by_pos).length === 0) && (
          <div className="modal-section">
            <h4>真题例句</h4>
            <p style={{ color: "var(--text-secondary)", fontSize: 13 }}>暂无收录例句</p>
          </div>
        )}
      </div>
    </div>
  );
}
