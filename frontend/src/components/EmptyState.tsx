import { ReactNode } from 'react';
import { Empty } from 'antd';

interface Props {
  description?: ReactNode;
  children?: ReactNode;
}

export default function EmptyState({ description = '暂无数据', children }: Props) {
  return (
    <Empty description={description} style={{ padding: 32 }}>
      {children}
    </Empty>
  );
}
