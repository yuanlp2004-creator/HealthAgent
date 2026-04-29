import { useEffect, useState } from 'react';
import {
  Button,
  Card,
  DatePicker,
  Popconfirm,
  Table,
  Tag,
  message,
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import type { TableProps } from 'antd';
import { useNavigate } from 'react-router-dom';
import dayjs, { Dayjs } from 'dayjs';
import AppLayout from '../components/AppLayout';
import PageHeader from '../components/PageHeader';
import EmptyState from '../components/EmptyState';
import { bpRecordsApi } from '../api/bpRecords';
import { extractError } from '../utils/error';
import type { BpRecord } from '../types/api';

export default function BpRecordList() {
  const navigate = useNavigate();
  const [items, setItems] = useState<BpRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const resp = await bpRecordsApi.list({
        page,
        size,
        start: range?.[0].toISOString(),
        end: range?.[1].toISOString(),
      });
      setItems(resp.items);
      setTotal(resp.total);
    } catch (err) {
      message.error(extractError(err, '加载失败'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, size, range]);

  const handleDelete = async (id: number) => {
    try {
      await bpRecordsApi.remove(id);
      message.success('已删除');
      if (items.length === 1 && page > 1) setPage(page - 1);
      else void load();
    } catch (err) {
      message.error(extractError(err, '删除失败'));
    }
  };

  function bpColor(value: number, type: 'systolic' | 'diastolic'): string {
    if (type === 'systolic') {
      if (value < 120) return '#52c41a';
      if (value < 140) return '#faad14';
      return '#ff4d4f';
    }
    if (value < 80) return '#52c41a';
    if (value < 90) return '#faad14';
    return '#ff4d4f';
  }

  const columns: TableProps<BpRecord>['columns'] = [
    {
      title: '测量时间',
      dataIndex: 'measured_at',
      render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm'),
      width: 170,
    },
    {
      title: '收缩压',
      dataIndex: 'systolic',
      width: 90,
      render: (v: number) => (
        <span style={{ fontWeight: 600, color: bpColor(v, 'systolic') }}>{v}</span>
      ),
    },
    {
      title: '舒张压',
      dataIndex: 'diastolic',
      width: 90,
      render: (v: number) => (
        <span style={{ fontWeight: 600, color: bpColor(v, 'diastolic') }}>{v}</span>
      ),
    },
    {
      title: '心率',
      dataIndex: 'heart_rate',
      width: 80,
      render: (v) => v ?? '—',
    },
    {
      title: '来源',
      dataIndex: 'source',
      width: 90,
      render: (v: string) =>
        v === 'ocr' ? <Tag color="blue">拍照</Tag> : <Tag>手动</Tag>,
    },
    {
      title: '备注',
      dataIndex: 'note',
      ellipsis: true,
      render: (v) => v ?? '—',
    },
    {
      title: '操作',
      width: 100,
      render: (_: unknown, rec: BpRecord) => (
        <Popconfirm
          title="确认删除这条记录？"
          onConfirm={() => handleDelete(rec.id)}
          okText="删除"
          cancelText="取消"
        >
          <Button size="small" danger type="link">
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <AppLayout>
      <PageHeader
        title="健康数据"
        subtitle="所有血压/心率记录，可按时间筛选并维护"
        extra={
          <>
            <DatePicker.RangePicker
              showTime
              value={range}
              onChange={(v) => {
                setRange(v as [Dayjs, Dayjs] | null);
                setPage(1);
              }}
            />
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/bp/new')}>
              新增记录
            </Button>
          </>
        }
      />
      <Card style={{ borderRadius: 14 }}>
        <Table<BpRecord>
          rowKey="id"
          columns={columns}
          dataSource={items}
          loading={loading}
          locale={{
            emptyText: <EmptyState description="暂无记录，去『拍照录入』添加一条吧" />,
          }}
          pagination={{
            current: page,
            pageSize: size,
            total,
            onChange: (p, s) => {
              setPage(p);
              setSize(s);
            },
            showSizeChanger: true,
          }}
        />
      </Card>
    </AppLayout>
  );
}
