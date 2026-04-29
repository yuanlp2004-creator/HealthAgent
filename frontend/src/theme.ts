import type { ThemeConfig } from 'antd';

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
} as const;

export const fontSize = {
  xs: 12,
  sm: 14,
  md: 16,
  lg: 20,
  xl: 24,
} as const;

export const theme: ThemeConfig = {
  token: {
    colorPrimary: '#2f7dff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    borderRadius: 10,
    borderRadiusLG: 14,
    fontSize: 14,
    colorBgContainer: '#ffffff',
    colorBorderSecondary: '#f0f2f5',
    boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
    boxShadowSecondary: '0 4px 20px rgba(0,0,0,0.08)',
  },
  components: {
    Layout: {
      headerBg: '#ffffff',
      headerColor: '#1f1f1f',
      siderBg: '#001529',
      headerPadding: '0 24px',
      bodyBg: '#f6f8fc',
    },
    Card: {
      borderRadiusLG: 14,
      paddingLG: 20,
    },
    Button: {
      borderRadius: 8,
      controlHeight: 36,
      paddingContentHorizontal: 18,
    },
    Input: {
      borderRadius: 8,
    },
    Menu: {
      itemBorderRadius: 8,
      subMenuItemBg: 'transparent',
      darkItemBg: 'transparent',
      darkItemSelectedBg: 'rgba(47,125,255,0.20)',
      darkItemSelectedColor: '#ffffff',
    },
    Table: {
      borderRadius: 10,
      headerBg: '#fafbfc',
    },
    Statistic: {
      contentFontSize: 28,
      titleFontSize: 13,
    },
    Tag: {
      borderRadiusSM: 6,
    },
  },
};

export interface RouteMeta {
  title: string;
}

export const ROUTE_META: Record<string, RouteMeta> = {
  '/bp/dashboard': { title: '首页看板' },
  '/bp/new': { title: '拍照录入' },
  '/bp/list': { title: '健康数据' },
  '/chat': { title: '智能问诊' },
  '/me': { title: '个人中心' },
};
