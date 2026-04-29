import { api } from './client';
import type {
  BpRecord,
  BpRecordCreate,
  BpRecordForecast,
  BpRecordListOut,
  BpRecordStats,
  BpRecordUpdate,
  OcrBpResponse,
} from '../types/api';

export const bpRecordsApi = {
  create: (data: BpRecordCreate) =>
    api.post<BpRecord>('/bp-records', data).then((r) => r.data),

  list: (params: { start?: string; end?: string; page?: number; size?: number } = {}) =>
    api.get<BpRecordListOut>('/bp-records', { params }).then((r) => r.data),

  get: (id: number) =>
    api.get<BpRecord>(`/bp-records/${id}`).then((r) => r.data),

  update: (id: number, data: BpRecordUpdate) =>
    api.patch<BpRecord>(`/bp-records/${id}`, data).then((r) => r.data),

  remove: (id: number) =>
    api.delete<void>(`/bp-records/${id}`).then((r) => r.data),

  stats: (days = 30) =>
    api.get<BpRecordStats>('/bp-records/stats', { params: { days } }).then((r) => r.data),

  forecast: (days = 7) =>
    api.get<BpRecordForecast>('/bp-records/forecast', { params: { days } }).then((r) => r.data),
};

export const ocrApi = {
  bp: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return api
      .post<OcrBpResponse>('/ocr/bp', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      .then((r) => r.data);
  },
};
