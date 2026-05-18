import type { Translation } from "../types";

interface Props {
  translation: Translation | null;
  loading?: boolean;
}

export default function TranslateLine({ translation, loading }: Props) {
  if (loading) {
    return (
      <div className="translate-line translate-loading">翻译中...</div>
    );
  }

  if (!translation) {
    return null;
  }

  const { translation: text, highlight_start, highlight_end } = translation;

  return (
    <div className="translate-line">
      {highlight_start < highlight_end ? (
        <>
          <span className="translate-normal">{text.slice(0, highlight_start)}</span>
          <span className="translate-highlight">{text.slice(highlight_start, highlight_end)}</span>
          <span className="translate-normal">{text.slice(highlight_end)}</span>
        </>
      ) : (
        <span className="translate-normal">{text}</span>
      )}
    </div>
  );
}
