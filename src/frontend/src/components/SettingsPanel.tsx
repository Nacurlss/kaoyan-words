import { useState, useEffect } from "react";
import { updateSettings } from "../api";
import type { Settings } from "../types";

interface Props {
  settings: Settings;
  onChange: (s: Settings) => void;
}

const LEVELS = [
  { key: "primary", label: "小学词汇" },
  { key: "zhongkao", label: "中考词汇" },
  { key: "gaokao", label: "高考词汇" },
  { key: "cet4", label: "四级词汇" },
  { key: "custom", label: "自定义词表" },
];

const MOMO_GROUPS = [
  { key: "basic", label: "基础词" },
  { key: "low_syllabus", label: "低频大纲词" },
  { key: "zero_syllabus", label: "零频大纲词" },
  { key: "low_extra", label: "低频超纲词" },
];

export default function SettingsPanel({ settings, onChange }: Props) {
  const [highThreshold, setHighThreshold] = useState(settings.high_threshold);
  const [mediumThreshold, setMediumThreshold] = useState(settings.medium_threshold);
  const [excludeLevels, setExcludeLevels] = useState(settings.exclude_levels);
  const [excludeGroups, setExcludeGroups] = useState<string[]>(settings.exclude_groups || []);

  useEffect(() => {
    setHighThreshold(settings.high_threshold);
    setMediumThreshold(settings.medium_threshold);
    setExcludeLevels(settings.exclude_levels);
    setExcludeGroups(settings.exclude_groups || []);
  }, [settings]);

  const applyThresholds = async () => {
    const ns = { ...settings, high_threshold: highThreshold, medium_threshold: mediumThreshold };
    await updateSettings(ns);
    onChange(ns);
  };

  const toggleLevel = async (key: string) => {
    const next = excludeLevels.includes(key)
      ? excludeLevels.filter((l: string) => l !== key)
      : [...excludeLevels, key];
    setExcludeLevels(next);
    const ns = { ...settings, high_threshold: highThreshold, medium_threshold: mediumThreshold, exclude_levels: next };
    await updateSettings(ns);
    onChange(ns);
  };

  const toggleGroup = async (key: string) => {
    const next = excludeGroups.includes(key)
      ? excludeGroups.filter((g: string) => g !== key)
      : [...excludeGroups, key];
    setExcludeGroups(next);
    const ns = { ...settings, high_threshold: highThreshold, medium_threshold: mediumThreshold, exclude_groups: next };
    await updateSettings(ns);
    onChange(ns);
  };

  const groupSizes = settings.group_sizes || {};

  return (
    <div className="settings-panel">
      <h3>频率设置</h3>
      <label>
        高频线
        <span className="threshold-val">{highThreshold.toFixed(2)}</span>
      </label>
      <input
        type="range" min="0" max="2" step="0.05" value={highThreshold}
        onChange={(e) => setHighThreshold(parseFloat(e.target.value))}
        onMouseUp={applyThresholds}
      />

      <label>
        中频线
        <span className="threshold-val">{mediumThreshold.toFixed(2)}</span>
      </label>
      <input
        type="range" min="0" max="2" step="0.05" value={mediumThreshold}
        onChange={(e) => setMediumThreshold(parseFloat(e.target.value))}
        onMouseUp={applyThresholds}
      />

      <h3 style={{ marginTop: 16 }}>墨墨分组筛选</h3>
      <p style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 8 }}>
        主词条始终保留。勾选要排除的附录分组：
      </p>
      <div className="level-checkboxes">
        {MOMO_GROUPS.map(({ key, label }) => (
          <label key={key}>
            <input
              type="checkbox"
              checked={excludeGroups.includes(key)}
              onChange={() => toggleGroup(key)}
            />
            {label}
            {groupSizes[key] && <span style={{ color: "var(--text-secondary)", fontSize: 10 }}>（{groupSizes[key]}词）</span>}
          </label>
        ))}
      </div>

      <h3 style={{ marginTop: 16 }}>常考例句来源</h3>
      <div className="level-checkboxes">
        <label>
          <input
            type="checkbox"
            checked={settings.use_momo_examples || false}
            onChange={async () => {
              const next = !(settings.use_momo_examples || false);
              const ns = { ...settings, use_momo_examples: next };
              await updateSettings(ns);
              onChange(ns);
            }}
          />
          使用墨墨原版例句（不勾选则显示真题例句）
        </label>
      </div>

      <h3 style={{ marginTop: 16 }}>基础词过滤</h3>
      <p style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 8 }}>
        进一步筛去基础词汇（叠加生效）
      </p>
      <div className="level-checkboxes">
        {LEVELS.map(({ key, label }) => (
          <label key={key}>
            <input
              type="checkbox"
              checked={excludeLevels.includes(key)}
              onChange={() => toggleLevel(key)}
            />
            {label}
          </label>
        ))}
      </div>
    </div>
  );
}
