import type { Paper } from "../types";

interface Props {
  papers: Paper[];
  onDelete: (filename: string) => void;
}

export default function PaperList({ papers, onDelete }: Props) {
  return (
    <div className="paper-list">
      <h3>已导入试卷 ({papers.length})</h3>
      {papers.length === 0 ? (
        <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>
          尚未导入试卷，请点击上方"导入试卷"按钮上传 docx 或 pdf 文件。
        </p>
      ) : (
        <ul>
          {papers.map((p) => (
            <li key={p.filename} className="paper-item">
              <span className="year">{p.year}</span>
              <span className="filename" title={p.filename}>{p.filename}</span>
              <button className="del-btn" onClick={() => onDelete(p.filename)} title="删除">×</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
