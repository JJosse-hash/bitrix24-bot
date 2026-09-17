export type Evidence = {
  value: string;
  source: string;
  confidence: number;
  status: "unknown" | "detected" | "hypothesis" | "confirmed" | "rejected";
  alternatives: string[];
};

export type ParsedAddress = {
  raw_text: string;
  normalized_text: string;
  state?: Evidence | null;
  municipality?: Evidence | null;
  locality?: Evidence | null;
  neighborhood?: Evidence | null;
  postal_code?: Evidence | null;
  streets: Evidence[];
  intersections: Evidence[];
  house_number?: Evidence | null;
  block?: Evidence | null;
  lot?: Evidence | null;
  references: Evidence[];
  poi_categories: Evidence[];
  ambiguities: string[];
  contradictions: string[];
};

export type RankedCandidate = {
  candidate: {
    id: string;
    label: string;
    normalized_address: string;
    point: { lat: number; lon: number };
    state: string;
    municipality: string;
    neighborhood?: string | null;
    postal_code?: string | null;
    streets: string[];
    house_number?: string | null;
    poi_categories: string[];
    source: string;
  };
  score: number;
  confidence_label: "alta" | "media" | "baja" | "insuficiente";
  breakdown: { signal: string; points: number; reason: string }[];
};

export type SearchResponse = {
  parsed: ParsedAddress;
  candidates: RankedCandidate[];
  recommended_question?: string | null;
  warnings: string[];
};
