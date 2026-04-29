import { useEffect, useRef, useState } from 'react';
import {
  Alert,
  Avatar,
  Button,
  Card,
  Collapse,
  Empty,
  Input,
  List,
  Popconfirm,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  DeleteOutlined,
  PlusOutlined,
  SendOutlined,
  RobotOutlined,
  UserOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import AppLayout from '../components/AppLayout';
import PageHeader from '../components/PageHeader';
import { askStream, chatApi } from '../api/chat';
import { extractError } from '../utils/error';
import type { ChatMessageOut, Citation, ConversationOut } from '../types/api';
import '../chat.css';

const QUICK_QUESTIONS = [
  { emoji: '📊', text: '解读我最近 14 天的血压情况' },
  { emoji: '🏠', text: '高血压在家如何正确测量' },
  { emoji: '🚨', text: '血压突然升高到 170/100 怎么办' },
  { emoji: '📈', text: '怎么看我的血压趋势在改善还是恶化' },
];

type AssistantDraft = {
  content: string;
  citations: Citation[];
  streaming: boolean;
};

export default function ChatPage() {
  const [conversations, setConversations] = useState<ConversationOut[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessageOut[]>([]);
  const [draft, setDraft] = useState<AssistantDraft | null>(null);
  const [input, setInput] = useState('');
  const [loadingList, setLoadingList] = useState(false);
  const [loadingMsgs, setLoadingMsgs] = useState(false);
  const cancelRef = useRef<(() => void) | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const loadConversations = async () => {
    setLoadingList(true);
    try {
      const items = await chatApi.listConversations();
      setConversations(items);
      if (items.length > 0 && activeId == null) setActiveId(items[0].id);
    } catch (err) {
      message.error(extractError(err, '加载会话失败'));
    } finally {
      setLoadingList(false);
    }
  };

  const loadMessages = async (id: number) => {
    setLoadingMsgs(true);
    try {
      const items = await chatApi.listMessages(id);
      setMessages(items);
    } catch (err) {
      message.error(extractError(err, '加载消息失败'));
    } finally {
      setLoadingMsgs(false);
    }
  };

  useEffect(() => {
    void loadConversations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (activeId != null) {
      setDraft(null);
      cancelRef.current?.();
      void loadMessages(activeId);
    }
  }, [activeId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, draft]);

  const handleNewConversation = async () => {
    try {
      const c = await chatApi.createConversation();
      setConversations((cs) => [c, ...cs]);
      setActiveId(c.id);
    } catch (err) {
      message.error(extractError(err, '新建会话失败'));
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await chatApi.deleteConversation(id);
      setConversations((cs) => cs.filter((c) => c.id !== id));
      if (activeId === id) {
        setActiveId(null);
        setMessages([]);
      }
    } catch (err) {
      message.error(extractError(err, '删除失败'));
    }
  };

  const handleSend = async (question?: string) => {
    const q = (question ?? input).trim();
    if (!q) return;
    if (draft?.streaming) {
      message.warning('上一条回复仍在生成，请稍候或取消');
      return;
    }

    let targetId = activeId;
    if (targetId == null) {
      try {
        const c = await chatApi.createConversation();
        setConversations((cs) => [c, ...cs]);
        targetId = c.id;
        setActiveId(c.id);
      } catch (err) {
        message.error(extractError(err, '新建会话失败'));
        return;
      }
    }

    setInput('');
    // optimistically append the user message
    const tempUserMsg: ChatMessageOut = {
      id: -Date.now(),
      conversation_id: targetId,
      role: 'user',
      content: q,
      citations: [],
      created_at: new Date().toISOString(),
    };
    setMessages((m) => [...m, tempUserMsg]);
    setDraft({ content: '', citations: [], streaming: true });

    cancelRef.current = askStream(targetId, q, {
      onCitations: (cits) => setDraft((d) => (d ? { ...d, citations: cits } : d)),
      onDelta: (delta) =>
        setDraft((d) => (d ? { ...d, content: d.content + delta } : d)),
      onDone: async () => {
        setDraft(null);
        if (targetId != null) await loadMessages(targetId);
        // refresh sidebar in case title was updated from the first question
        void loadConversations();
      },
      onError: (detail) => {
        setDraft((d) => (d ? { ...d, streaming: false } : d));
        message.error(`回答失败：${detail}`);
      },
    });
  };

  const handleCancel = () => {
    cancelRef.current?.();
    cancelRef.current = null;
    setDraft((d) => (d ? { ...d, streaming: false } : d));
  };

  return (
    <AppLayout>
      <div className="page-enter">
      <PageHeader
        title="智能问诊"
        subtitle="基于本地知识库 + 你的血压数据的 AI 健康助手"
      />
      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 16, borderRadius: 10 }}
        message="本功能提供的内容仅供参考，不构成医疗诊断；涉及用药请咨询医生。"
      />

      <div
        style={{
          display: 'flex',
          gap: 16,
          height: 'calc(100vh - 220px)',
          minHeight: 480,
        }}
      >
        {/* ---- sidebar ---- */}
        <Card
          size="small"
          style={{
            width: 260,
            flexShrink: 0,
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 2px 12px rgba(47,125,255,0.06)',
            borderRadius: 14,
            border: '1px solid #eef1f6',
          }}
          bodyStyle={{ padding: 10, overflow: 'auto', flex: 1 }}
          title={<span style={{ fontWeight: 600, fontSize: 15 }}>💬 会话</span>}
          extra={
            <Button
              size="small"
              type="primary"
              shape="round"
              icon={<PlusOutlined />}
              onClick={handleNewConversation}
            >
              新建
            </Button>
          }
        >
          <Spin spinning={loadingList}>
            {conversations.length === 0 ? (
              <Empty description="暂无会话" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <List
                dataSource={conversations}
                renderItem={(c) => (
                  <List.Item
                    key={c.id}
                    onClick={() => setActiveId(c.id)}
                    style={{
                      cursor: 'pointer',
                      padding: 8,
                      background: c.id === activeId ? '#e6f4ff' : undefined,
                      borderLeft: c.id === activeId ? '3px solid #2f7dff' : '3px solid transparent',
                      paddingLeft: c.id === activeId ? 5 : 8,
                      borderRadius: 10,
                    }}
                    actions={[
                      <Popconfirm
                        key="del"
                        title="删除该会话？"
                        onConfirm={(e) => {
                          e?.stopPropagation();
                          void handleDelete(c.id);
                        }}
                        onCancel={(e) => e?.stopPropagation()}
                      >
                        <Button
                          type="text"
                          size="small"
                          icon={<DeleteOutlined />}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </Popconfirm>,
                    ]}
                  >
                    <div style={{ overflow: 'hidden' }}>
                      <div style={{ fontWeight: 500 }}>{c.title}</div>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        {new Date(c.updated_at).toLocaleString()}
                      </Typography.Text>
                    </div>
                  </List.Item>
                )}
              />
            )}
          </Spin>
        </Card>

        {/* ---- main ---- */}
        <Card
          size="small"
          style={{
            flex: 1,
            minWidth: 0,
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 2px 16px rgba(47,125,255,0.06)',
            borderRadius: 14,
            border: '1px solid #eef1f6',
          }}
          bodyStyle={{
            padding: 0,
            display: 'flex',
            flexDirection: 'column',
            flex: 1,
            minHeight: 0,
          }}
        >
          <div
            ref={scrollRef}
            className="chat-scroll"
            style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 20 }}
          >
            <Spin spinning={loadingMsgs}>
              {messages.length === 0 && !draft ? (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Typography.Text type="secondary">
                    选择一个快捷问题，或直接输入你的问题：
                  </Typography.Text>
                  <Space wrap>
                    {QUICK_QUESTIONS.map((q) => (
                      <Tag
                        key={q.text}
                        className="quick-tag"
                        style={{
                          cursor: 'pointer',
                          padding: '6px 14px',
                          borderRadius: 22,
                          background: '#f0f5ff',
                          border: '1px solid #d9e8ff',
                          color: '#1f3a5f',
                          fontSize: 13,
                          fontWeight: 500,
                          transition: 'all 0.2s ease',
                        }}
                        onClick={() => void handleSend(q.text)}
                      >
                        {q.emoji} {q.text}
                      </Tag>
                    ))}
                  </Space>
                </Space>
              ) : (
                <Space direction="vertical" style={{ width: '100%' }} size={12}>
                  {messages.map((m) => (
                    <MessageBubble key={m.id} msg={m} />
                  ))}
                  {draft && (
                    <AssistantBubble
                      content={draft.content || (draft.streaming ? '思考中…' : '')}
                      citations={draft.citations}
                      streaming={draft.streaming}
                    />
                  )}
                </Space>
              )}
            </Spin>
          </div>

          <div
            className="chat-input-divider"
            style={{
              padding: '14px 18px',
              display: 'flex',
              gap: 10,
              alignItems: 'flex-end',
              background: 'linear-gradient(180deg, #fafbfd 0%, #ffffff 100%)',
            }}
          >
            <Input.TextArea
              placeholder="请输入你的问题…"
              autoSize={{ minRows: 1, maxRows: 4 }}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  void handleSend();
                }
              }}
              disabled={draft?.streaming}
              style={{
                borderRadius: 24,
                background: '#ffffff',
                resize: 'none',
              }}
            />
            {draft?.streaming ? (
              <Button
                onClick={handleCancel}
                style={{ borderRadius: 20, color: '#ff4d4f' }}
              >
                取消
              </Button>
            ) : (
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={() => void handleSend()}
                disabled={!input.trim()}
                style={{ borderRadius: 24, height: 36 }}
              >
                发送
              </Button>
            )}
          </div>
        </Card>
      </div>
      </div>
    </AppLayout>
  );
}

function MessageBubble({ msg }: { msg: ChatMessageOut }) {
  const isUser = msg.role === 'user';
  return (
    <div style={{ marginBottom: 16 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: isUser ? 'flex-end' : 'flex-start',
          alignItems: 'flex-end',
          gap: 8,
        }}
      >
        {!isUser && (
          <Avatar
            size={32}
            icon={<RobotOutlined />}
            style={{ background: '#52c41a', flexShrink: 0 }}
          />
        )}
        <div
          style={{
            background: isUser ? '#2f7dff' : '#f5f8ff',
            color: isUser ? '#ffffff' : '#1f1f1f',
            padding: '12px 16px',
            borderRadius: isUser ? '18px 18px 6px 18px' : '18px 18px 18px 6px',
            border: isUser ? 'none' : '1px solid #e4ecf7',
            maxWidth: isUser ? '70%' : '80%',
            wordBreak: 'break-word',
            overflowWrap: 'break-word',
            lineHeight: 1.65,
            boxShadow: isUser ? '0 2px 8px rgba(47,125,255,0.20)' : '0 1px 3px rgba(0,0,0,0.04)',
          }}
          className={isUser ? undefined : 'markdown-body'}
        >
          {isUser ? msg.content : <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>}
        </div>
        {isUser && (
          <Avatar
            size={32}
            icon={<UserOutlined />}
            style={{ background: '#2f7dff', flexShrink: 0 }}
          />
        )}
      </div>
      <div
        style={{
          fontSize: 11,
          color: 'rgba(0,0,0,0.40)',
          marginTop: 4,
          paddingLeft: isUser ? 0 : 40,
          paddingRight: isUser ? 8 : 0,
          textAlign: isUser ? 'right' : 'left',
        }}
      >
        {new Date(msg.created_at).toLocaleString()}
      </div>
      {msg.citations && msg.citations.length > 0 && (
        <Collapse
          ghost
          size="small"
          style={{ marginTop: 4, marginLeft: 40 }}
          items={[
            {
              key: 'c',
              label: `引用 ${msg.citations.length} 条`,
              children: (
                <Space direction="vertical" style={{ width: '100%' }} size={8}>
                  {msg.citations.map((c) => (
                    <Card
                      key={c.idx}
                      size="small"
                      className="citation-card"
                      title={
                        <span>
                          <Tag color="success">[{c.idx}]</Tag>
                          {c.title}
                          {c.heading_path && (
                            <Typography.Text type="secondary" style={{ marginLeft: 6 }}>
                              · {c.heading_path}
                            </Typography.Text>
                          )}
                        </span>
                      }
                      extra={
                        c.url ? (
                          <a href={c.url} target="_blank" rel="noreferrer">
                            原文
                          </a>
                        ) : (
                          <Typography.Text type="secondary">{c.source}</Typography.Text>
                        )
                      }
                    >
                      <Typography.Paragraph style={{ margin: 0, fontSize: 13 }}>
                        {c.text}
                      </Typography.Paragraph>
                    </Card>
                  ))}
                </Space>
              ),
            },
          ]}
        />
      )}
    </div>
  );
}

function AssistantBubble({
  content,
  citations,
  streaming,
}: {
  content: string;
  citations: Citation[];
  streaming: boolean;
}) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'flex-start',
          alignItems: 'flex-end',
          gap: 8,
        }}
      >
        <Avatar
          size={32}
          icon={<RobotOutlined />}
          style={{ background: '#52c41a', flexShrink: 0 }}
        />
        <div
          style={{
            background: '#f5f8ff',
            color: '#1f1f1f',
            padding: '12px 16px',
            borderRadius: '18px 18px 18px 6px',
            border: '1px solid #e4ecf7',
            maxWidth: '80%',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            overflowWrap: 'break-word',
            lineHeight: 1.65,
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}
          className="markdown-body"
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          {streaming && (
            <span className="chat-streaming-dot" aria-label="正在输出" />
          )}
        </div>
      </div>
      {citations.length > 0 && (
        <Collapse
          ghost
          size="small"
          style={{ marginTop: 4, marginLeft: 40 }}
          items={[
            {
              key: 'c',
              label: `引用 ${citations.length} 条`,
              children: (
                <Space direction="vertical" style={{ width: '100%' }} size={8}>
                  {citations.map((c) => (
                    <Card
                      key={c.idx}
                      size="small"
                      className="citation-card"
                      title={
                        <span>
                          <Tag color="success">[{c.idx}]</Tag>
                          {c.title}
                          {c.heading_path && (
                            <Typography.Text type="secondary" style={{ marginLeft: 6 }}>
                              · {c.heading_path}
                            </Typography.Text>
                          )}
                        </span>
                      }
                      extra={
                        c.url ? (
                          <a href={c.url} target="_blank" rel="noreferrer">
                            原文
                          </a>
                        ) : (
                          <Typography.Text type="secondary">{c.source}</Typography.Text>
                        )
                      }
                    >
                      <Typography.Paragraph style={{ margin: 0, fontSize: 13 }}>
                        {c.text}
                      </Typography.Paragraph>
                    </Card>
                  ))}
                </Space>
              ),
            },
          ]}
        />
      )}
    </div>
  );
}
