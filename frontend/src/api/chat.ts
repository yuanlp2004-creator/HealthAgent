import { api } from './client';
import { tokenStore } from './client';
import type { ChatMessageOut, Citation, ConversationOut } from '../types/api';

const BASE = import.meta.env.VITE_API_BASE ?? '/api/v1';

export const chatApi = {
  createConversation: (title?: string) =>
    api.post<ConversationOut>('/chat/conversations', { title }).then((r) => r.data),

  listConversations: () =>
    api
      .get<{ items: ConversationOut[] }>('/chat/conversations')
      .then((r) => r.data.items),

  deleteConversation: (id: number) =>
    api.delete<void>(`/chat/conversations/${id}`).then((r) => r.data),

  listMessages: (id: number) =>
    api
      .get<{ items: ChatMessageOut[] }>(`/chat/conversations/${id}/messages`)
      .then((r) => r.data.items),
};

export type SseCallbacks = {
  onCitations?: (cits: Citation[]) => void;
  onDelta?: (delta: string) => void;
  onDone?: (messageId: number) => void;
  onError?: (detail: string) => void;
};

/**
 * Send a question to a conversation and stream the answer via fetch + SSE.
 * Returns a cancel() function.
 */
export function askStream(
  conversationId: number,
  question: string,
  cb: SseCallbacks,
): () => void {
  const controller = new AbortController();
  const token = tokenStore.getAccess();

  (async () => {
    let resp: Response;
    try {
      resp = await fetch(`${BASE}/chat/conversations/${conversationId}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: token ? `Bearer ${token}` : '',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({ question }),
        signal: controller.signal,
      });
    } catch (err) {
      if (!controller.signal.aborted) cb.onError?.(String(err));
      return;
    }

    if (!resp.ok || !resp.body) {
      const text = await resp.text().catch(() => '');
      cb.onError?.(`HTTP ${resp.status}: ${text || resp.statusText}`);
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let sepIdx: number;
        while ((sepIdx = buffer.indexOf('\n\n')) !== -1) {
          const raw = buffer.slice(0, sepIdx);
          buffer = buffer.slice(sepIdx + 2);
          dispatch(raw, cb);
        }
      }
    } catch (err) {
      if (!controller.signal.aborted) cb.onError?.(String(err));
    }
  })();

  return () => controller.abort();
}

function dispatch(raw: string, cb: SseCallbacks): void {
  let event = 'message';
  const dataLines: string[] = [];
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
  }
  const data = dataLines.join('\n');
  if (event === 'delta') {
    cb.onDelta?.(data);
  } else if (event === 'citations') {
    try {
      cb.onCitations?.(JSON.parse(data) as Citation[]);
    } catch {
      /* ignore */
    }
  } else if (event === 'done') {
    try {
      const parsed = JSON.parse(data) as { message_id: number };
      cb.onDone?.(parsed.message_id);
    } catch {
      cb.onDone?.(-1);
    }
  } else if (event === 'error') {
    try {
      const parsed = JSON.parse(data) as { detail: string };
      cb.onError?.(parsed.detail);
    } catch {
      cb.onError?.(data);
    }
  }
}
