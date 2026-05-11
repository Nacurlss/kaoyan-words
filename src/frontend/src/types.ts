export interface Paper {
  year: string;
  type: string;
  sections: PaperSection[];
  section_count: number;
}

export interface PaperSection {
  section: string;
  section_label: string;
  sentence_count: number;
  enabled: boolean;
}

export interface SenseDetail {
  text: string;
  word: string;
  year: string;
  section: string;
  section_label: string;
}

export interface Sense {
  pos: string;
  meaning: string;
  count: number;
}

export interface TopExample {
  text: string;
  word: string;
  year: string;
  section: string;
  section_label: string;
}

export interface WordEntry {
  lemma: string;
  variants: string[];
  frequency: number;
  senses: Sense[];
  pos_counts: Record<string, number>;
  top_example: TopExample | null;
  sentences_by_pos: Record<string, SenseDetail[]>;
}

export interface WordListResponse {
  words: WordEntry[];
  total: number;
  page: number;
  page_size: number;
  bands: {
    high: number;
    medium: number;
    low: number;
  };
}

export interface SenseDetailResponse {
  lemma: string;
  pos: string;
  unit_count: number;
  sentences: SenseDetail[];
}

export interface Settings {
  high_threshold: number;
  medium_threshold: number;
  exclude_levels: string[];
  exclude_groups: string[];
  use_momo_examples?: boolean;
  available_groups?: string[];
  group_sizes?: Record<string, number>;
}
