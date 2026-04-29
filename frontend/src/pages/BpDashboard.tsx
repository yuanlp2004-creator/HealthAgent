import { useEffect, useState } from 'react';
import { Card, Col, Row, Segmented, Tag, Spin, Tooltip, Typography } from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  LineOutlined,
  ThunderboltOutlined,
  HeartOutlined,
  DashboardOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import ReactEChartsRaw from 'echarts-for-react';
const ReactECharts = ReactEChartsRaw as unknown as React.FC<{ option: unknown; style?: React.CSSProperties }>;
import AppLayout from '../components/AppLayout';
import EmptyState from '../components/EmptyState';
import { bpRecordsApi } from '../api/bpRecords';
import { useAuth } from '../store/auth';
import type { BpRecord, BpRecordForecast, BpRecordStats } from '../types/api';

function greeting(): string {
  const h = new Date().getHours();
  if (h < 6) return '夜深了';
  if (h < 12) return '早上好';
  if (h < 14) return '中午好';
  if (h < 18) return '下午好';
  return '晚上好';
}

const trendColor: Record<string, string> = {
  up: 'red',
  down: 'green',
  stable: 'blue',
  unknown: 'default',
};
const trendLabel: Record<string, string> = {
  up: '↑ 上升趋势',
  down: '↓ 下降趋势',
  stable: '→ 保持平稳',
  unknown: '数据不足',
};
const trendIcon: Record<string, React.ReactNode> = {
  up: <ArrowUpOutlined />,
  down: <ArrowDownOutlined />,
  stable: <LineOutlined />,
  unknown: null,
};

interface StatCardProps {
  label: string;
  value: string | number;
  suffix: string;
  icon: React.ReactNode;
  accent: 'systolic' | 'diastolic' | 'heart' | 'records';
  valueStyle?: React.CSSProperties;
}

function StatCard({ label, value, suffix, icon, accent, valueStyle }: StatCardProps) {
  return (
    <Card className={`stat-card ${accent}`} bodyStyle={{ padding: '18px 20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <Typography.Text type="secondary" style={{ fontSize: 13, marginBottom: 4, display: 'block' }}>
            {label}
          </Typography.Text>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginTop: 4 }}>
            <span style={{ fontSize: 30, fontWeight: 700, lineHeight: 1, ...valueStyle }}>
              {value}
            </span>
            <Typography.Text type="secondary" style={{ fontSize: 13 }}>
              {suffix}
            </Typography.Text>
          </div>
        </div>
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 20,
            flexShrink: 0,
            ...(accent === 'systolic' && { background: '#e6f0ff', color: '#2f7dff' }),
            ...(accent === 'diastolic' && { background: '#e6fff0', color: '#52c41a' }),
            ...(accent === 'heart' && { background: '#fff3e0', color: '#fa8c16' }),
            ...(accent === 'records' && { background: '#f3e8ff', color: '#722ed1' }),
          }}
        >
          {icon}
        </div>
      </div>
    </Card>
  );
}

export default function BpDashboard() {
  const { user } = useAuth();
  const [days, setDays] = useState(30);
  const [stats, setStats] = useState<BpRecordStats | null>(null);
  const [forecast, setForecast] = useState<BpRecordForecast | null>(null);
  const [series, setSeries] = useState<BpRecord[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [s, f, listResp] = await Promise.all([
          bpRecordsApi.stats(days),
          bpRecordsApi.forecast(7),
          bpRecordsApi.list({ page: 1, size: 200 }),
        ]);
        setStats(s);
        setForecast(f);
        setSeries([...listResp.items].reverse());
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [days]);

  const lineOption = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#fff',
      borderColor: '#e8e8e8',
      textStyle: { color: '#1f1f1f', fontSize: 13 },
      boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
    },
    legend: {
      data: ['收缩压', '舒张压', '心率'],
      bottom: 0,
      itemGap: 20,
      textStyle: { fontSize: 13 },
    },
    xAxis: {
      type: 'category',
      data: series.map((r) => r.measured_at.slice(0, 16).replace('T', ' ')),
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: { color: '#8c8c8c', fontSize: 11 },
    },
    yAxis: [
      {
        type: 'value',
        name: 'mmHg',
        nameTextStyle: { color: '#8c8c8c', fontSize: 12 },
        axisLabel: { fontSize: 11 },
        splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
      },
      {
        type: 'value',
        name: 'bpm',
        nameTextStyle: { color: '#8c8c8c', fontSize: 12 },
        axisLabel: { fontSize: 11 },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '收缩压', type: 'line', data: series.map((r) => r.systolic),
        smooth: true, symbol: 'circle', symbolSize: 4,
        lineStyle: { width: 2.5, color: '#2f7dff' },
        itemStyle: { color: '#2f7dff' },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(47,125,255,0.12)' }, { offset: 1, color: 'rgba(47,125,255,0.0)' }] } },
      },
      {
        name: '舒张压', type: 'line', data: series.map((r) => r.diastolic),
        smooth: true, symbol: 'circle', symbolSize: 4,
        lineStyle: { width: 2.5, color: '#52c41a' },
        itemStyle: { color: '#52c41a' },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(82,196,26,0.10)' }, { offset: 1, color: 'rgba(82,196,26,0.0)' }] } },
      },
      {
        name: '心率', type: 'line', yAxisIndex: 1, data: series.map((r) => r.heart_rate),
        smooth: true, symbol: 'diamond', symbolSize: 4,
        lineStyle: { width: 2, color: '#fa8c16' },
        itemStyle: { color: '#fa8c16' },
      },
    ],
    grid: { left: 45, right: 50, top: 30, bottom: 55, containLabel: true },
  };

  const forecastOption = forecast && forecast.points.length > 0 && {
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#fff',
      borderColor: '#e8e8e8',
    },
    legend: { data: ['收缩压 MA', '舒张压 MA'], bottom: 0, itemGap: 20 },
    xAxis: {
      type: 'category',
      data: forecast.points.map((p) => p.date),
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: 'mmHg',
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
    },
    series: [
      {
        name: '收缩压 MA', type: 'line', data: forecast.points.map((p) => p.systolic),
        smooth: true, lineStyle: { width: 2, color: '#2f7dff', type: 'dashed' },
        itemStyle: { color: '#2f7dff' },
      },
      {
        name: '舒张压 MA', type: 'line', data: forecast.points.map((p) => p.diastolic),
        smooth: true, lineStyle: { width: 2, color: '#52c41a', type: 'dashed' },
        itemStyle: { color: '#52c41a' },
      },
    ],
    grid: { left: 45, right: 30, top: 30, bottom: 55, containLabel: true },
  };

  return (
    <AppLayout>
      {/* Hero banner */}
      <Card
        className="hero-card page-enter"
        bodyStyle={{ padding: '24px 28px' }}
        style={{ marginBottom: 20 }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <Typography.Title level={4} style={{ margin: 0, fontWeight: 600 }}>
              {greeting()}，{user?.nickname || user?.username || ''} 👋
            </Typography.Title>
            <Typography.Text type="secondary" style={{ marginTop: 4, display: 'block' }}>
              这里是你的健康数据一览 · 近 {days} 天数据
            </Typography.Text>
          </div>
          <Segmented
            options={[
              { label: '近 7 天', value: 7 },
              { label: '近 30 天', value: 30 },
              { label: '近 90 天', value: 90 },
            ]}
            value={days}
            onChange={(v) => setDays(v as number)}
          />
        </div>
      </Card>

      <Spin spinning={loading}>
        <Row gutter={[16, 16]}>
          {/* Stat cards */}
          <Col xs={12} md={6}>
            <StatCard
              label="收缩压均值" value={stats?.systolic_avg ?? '—'} suffix="mmHg"
              icon={<ThunderboltOutlined />} accent="systolic"
            />
          </Col>
          <Col xs={12} md={6}>
            <StatCard
              label="舒张压均值" value={stats?.diastolic_avg ?? '—'} suffix="mmHg"
              icon={<HeartOutlined />} accent="diastolic"
            />
          </Col>
          <Col xs={12} md={6}>
            <StatCard
              label="心率均值" value={stats?.heart_rate_avg ?? '—'} suffix="bpm"
              icon={<DashboardOutlined />} accent="heart"
            />
          </Col>
          <Col xs={12} md={6}>
            <StatCard
              label="记录数" value={stats?.count ?? 0} suffix="条"
              icon={<FileTextOutlined />} accent="records"
            />
          </Col>

          {/* Trend alert */}
          <Col span={24}>
            <Card
              bodyStyle={{ padding: '16px 24px' }}
              style={{ borderRadius: 14 }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                {forecast && (
                  <Tag
                    color={trendColor[forecast.trend]}
                    icon={trendIcon[forecast.trend]}
                    style={{ fontSize: 14, padding: '2px 12px', borderRadius: 20, lineHeight: '24px' }}
                  >
                    {trendLabel[forecast.trend]}
                  </Tag>
                )}
                <Typography.Text style={{ fontSize: 14, color: '#4a4a4a' }}>
                  {forecast?.message ?? '暂无趋势分析数据'}
                </Typography.Text>
              </div>
            </Card>
          </Col>

          {/* Main chart */}
          <Col span={24}>
            <Card
              title={<span style={{ fontWeight: 600, fontSize: 15 }}>血压/心率时序</span>}
              style={{ borderRadius: 14 }}
              bodyStyle={{ padding: '16px 12px 8px' }}
            >
              {series.length === 0 ? (
                <EmptyState description="暂无数据，先去录入一条吧" />
              ) : (
                <ReactECharts option={lineOption} style={{ height: 380 }} />
              )}
            </Card>
          </Col>

          {/* Forecast chart */}
          {forecastOption && (
            <Col span={24}>
              <Card
                title={
                  <span style={{ fontWeight: 600, fontSize: 15 }}>
                    7 天滑动平均预测
                    <Tooltip title="基于历史数据的滑动平均，仅供参考，不构成医疗建议">
                      <Typography.Text type="secondary" style={{ marginLeft: 8, fontSize: 12, cursor: 'help' }}>
                        ⓘ
                      </Typography.Text>
                    </Tooltip>
                  </span>
                }
                style={{ borderRadius: 14 }}
                bodyStyle={{ padding: '16px 12px 8px' }}
              >
                <ReactECharts option={forecastOption} style={{ height: 300 }} />
              </Card>
            </Col>
          )}
        </Row>
      </Spin>
    </AppLayout>
  );
}
