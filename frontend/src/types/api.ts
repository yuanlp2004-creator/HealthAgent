export interface UserOut {
  id: number;
  username: string;
  email: string;
  nickname: string | null;
  gender: 'male' | 'female' | 'other' | null;
  birth_date: string | null;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
}

export interface AuthResponse {
  user: UserOut;
  tokens: TokenPair;
}

export interface OcrFields {
  systolic: number | null;
  diastolic: number | null;
  heart_rate: number | null;
}

export interface OcrBpResponse {
  image_id: string;
  raw_text: string;
  candidates: { label: string; value: number; confidence: number }[];
  fields: OcrFields;
}

export interface BpRecord {
  id: number;
  user_id: number;
  systolic: number;
  diastolic: number;
  heart_rate: number | null;
  measured_at: string;
  source: 'manual' | 'ocr';
  image_id: string | null;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface BpRecordListOut {
  total: number;
  page: number;
  size: number;
  items: BpRecord[];
}

export interface BpRecordStats {
  count: number;
  window_days: number;
  systolic_avg?: number;
  systolic_max?: number;
  systolic_min?: number;
  diastolic_avg?: number;
  diastolic_max?: number;
  diastolic_min?: number;
  heart_rate_avg?: number;
}

export interface BpForecastPoint {
  date: string;
  systolic: number;
  diastolic: number;
}

export interface BpRecordForecast {
  window: number;
  points: BpForecastPoint[];
  trend: 'up' | 'down' | 'stable' | 'unknown';
  message: string | null;
}

export interface BpRecordCreate {
  systolic: number;
  diastolic: number;
  heart_rate?: number | null;
  measured_at: string;
  source?: 'manual' | 'ocr';
  image_id?: string | null;
  note?: string | null;
}

export type BpRecordUpdate = Partial<Pick<BpRecord, 'systolic' | 'diastolic' | 'heart_rate' | 'measured_at' | 'note'>>;

export interface Citation {
  idx: number;
  doc_id: string;
  title: string;
  source: string;
  url: string | null;
  heading_path: string;
  text: string;
}

export interface ChatMessageOut {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant';
  content: string;
  citations: Citation[];
  created_at: string;
}

export interface ConversationOut {
  id: number;
  user_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}
