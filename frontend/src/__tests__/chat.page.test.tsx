import { act, fireEvent, render, screen, waitFor, cleanup } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ChatPage from '../pages/ChatPage';
import { chatApi, askStream } from '../api/chat';
import type { ChatMessageOut } from '../types/api';

vi.mock('../api/chat', () => ({
  chatApi: { listConversations: vi.fn(), listMessages: vi.fn(), createConversation: vi.fn(), deleteConversation: vi.fn() },
  askStream: vi.fn(),
}));
vi.mock('../components/AppLayout', () => ({ default: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));
vi.mock('../components/PageHeader', () => ({ default: () => null }));
const conv = (id: number) => ({ id, user_id: 1, title: `会话${id}`, created_at: '2026-09-14', updated_at: '2026-09-14' });
const oldMessage: ChatMessageOut = { id: 1, conversation_id: 1, role: 'user', content: '旧会话消息', citations: [], created_at: '2026-09-14' };

beforeEach(() => {
  vi.resetAllMocks();
  Object.defineProperty(window, 'matchMedia', { writable: true, value: vi.fn().mockImplementation(() => ({ matches: false, addListener: vi.fn(), removeListener: vi.fn(), addEventListener: vi.fn(), removeEventListener: vi.fn() })) });
  Element.prototype.scrollTo = vi.fn();
  vi.mocked(chatApi.listConversations).mockResolvedValue([conv(1)]);
  vi.mocked(chatApi.createConversation).mockResolvedValue(conv(2));
  vi.mocked(chatApi.deleteConversation).mockResolvedValue(undefined);
});
afterEach(cleanup);

describe('conversation switching', () => {
  it('ignores old messages that arrive after creating a new conversation', async () => {
    let resolve!: (messages: ChatMessageOut[]) => void;
    vi.mocked(chatApi.listMessages).mockReturnValue(new Promise((r) => { resolve = r; }));
    render(<ChatPage />);
    await waitFor(() => expect(chatApi.listMessages).toHaveBeenCalledWith(1));
    fireEvent.click(screen.getByRole('button', { name: /新建/ }));
    await screen.findByText('会话2');
    await act(async () => resolve([oldMessage]));
    expect(screen.queryByText('旧会话消息')).not.toBeInTheDocument();
  });

  it('cancels a deleted conversation and ignores late stream callbacks after ID reuse', async () => {
    vi.mocked(chatApi.listMessages).mockResolvedValue([oldMessage]);
    vi.mocked(chatApi.createConversation).mockResolvedValue(conv(1));
    const cancel = vi.fn();
    vi.mocked(askStream).mockReturnValue(cancel);
    const { container } = render(<ChatPage />);
    await screen.findByText('旧会话消息');
    fireEvent.change(screen.getByPlaceholderText('请输入你的问题…'), { target: { value: '继续回答' } });
    fireEvent.click(screen.getByRole('button', { name: /发\s*送/ }));
    const callbacks = vi.mocked(askStream).mock.calls[0][2];
    fireEvent.click(container.querySelector('.anticon-delete')!.closest('button')!);
    fireEvent.click(await screen.findByRole('button', { name: /OK|确\s*定/ }));
    await waitFor(() => expect(cancel).toHaveBeenCalled());
    fireEvent.click(screen.getByRole('button', { name: /新建/ }));
    await waitFor(() => expect(chatApi.createConversation).toHaveBeenCalled());
    await act(async () => {
      callbacks.onDelta?.('删除后迟到的回答');
      callbacks.onDone?.(10);
    });
    expect(screen.queryByText('旧会话消息')).not.toBeInTheDocument();
    expect(screen.queryByText('删除后迟到的回答')).not.toBeInTheDocument();
    expect(chatApi.listMessages).toHaveBeenCalledTimes(1);
  });
});
