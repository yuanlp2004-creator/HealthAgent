import { ReactNode } from 'react';
import { Typography, Space } from 'antd';

interface Props {
  title: string;
  subtitle?: ReactNode;
  extra?: ReactNode;
}

export default function PageHeader({ title, subtitle, extra }: Props) {
  return (
    <div
      className="page-enter"
      style={{
        marginBottom: 20,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: 16,
        flexWrap: 'wrap',
      }}
    >
      <div>
        <Typography.Title level={3} style={{ margin: 0 }}>
          {title}
        </Typography.Title>
        {subtitle && (
          <Typography.Text type="secondary" style={{ fontSize: 13 }}>
            {subtitle}
          </Typography.Text>
        )}
      </div>
      {extra && <Space wrap>{extra}</Space>}
    </div>
  );
}
