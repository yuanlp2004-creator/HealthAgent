import { ReactNode, useState } from 'react';
import { Layout, Menu, Button, Space, Typography, Breadcrumb, Avatar, Dropdown } from 'antd';
import {
  DashboardOutlined,
  CameraOutlined,
  DatabaseOutlined,
  MessageOutlined,
  UserOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  LogoutOutlined,
  HeartFilled,
} from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../store/auth';
import { ROUTE_META } from '../theme';
import type { MenuProps } from 'antd';

interface NavItem {
  key: string;
  icon: React.ReactNode;
  label: string;
}

const NAV_ITEMS: NavItem[] = [
  { key: '/bp/dashboard', icon: <DashboardOutlined />, label: '首页看板' },
  { key: '/bp/new', icon: <CameraOutlined />, label: '拍照录入' },
  { key: '/bp/list', icon: <DatabaseOutlined />, label: '健康数据' },
  { key: '/chat', icon: <MessageOutlined />, label: '智能问诊' },
  { key: '/me', icon: <UserOutlined />, label: '个人中心' },
];

export default function AppLayout({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);

  const selectedKey =
    NAV_ITEMS.find((i) => location.pathname.startsWith(i.key))?.key ?? '/bp/dashboard';
  const currentTitle =
    ROUTE_META[selectedKey]?.title ??
    NAV_ITEMS.find((i) => i.key === selectedKey)?.label ??
    '';

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const userMenu = {
    items: [
      {
        key: 'me',
        icon: <UserOutlined />,
        label: '个人中心',
        onClick: () => navigate('/me'),
      },
      {
        key: 'logout',
        icon: <LogoutOutlined />,
        label: '退出登录',
        onClick: handleLogout,
      },
    ],
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Layout.Sider
        collapsible
        collapsed={collapsed}
        trigger={null}
        breakpoint="lg"
        onBreakpoint={(broken) => setCollapsed(broken)}
        width={228}
        style={{
          background: 'linear-gradient(180deg, #f7f9fc 0%, #f0f3f8 40%, #eef1f6 100%)',
          borderRight: '1px solid #e4e9f0',
          boxShadow: '1px 0 8px rgba(0,0,0,0.03)',
          zIndex: 10,
        }}
      >
        {/* Logo 区域 */}
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? 0 : '0 22px',
            gap: 10,
            borderBottom: '1px solid rgba(47,125,255,0.08)',
          }}
        >
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: 10,
              background: 'linear-gradient(135deg, #2f7dff 0%, #5b9eff 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 3px 10px rgba(47,125,255,0.25)',
              flexShrink: 0,
            }}
          >
            <HeartFilled style={{ color: '#fff', fontSize: 17 }} />
          </div>
          {!collapsed && (
            <div>
              <Typography.Text
                strong
                style={{ fontSize: 15, color: '#1a2a3a', lineHeight: '20px', display: 'block' }}
              >
                HealthAgent
              </Typography.Text>
              <Typography.Text style={{ fontSize: 10, color: '#94a3b8', lineHeight: '14px', display: 'block' }}>
                个人健康管理
              </Typography.Text>
            </div>
          )}
        </div>

        {/* 导航菜单 */}
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={NAV_ITEMS as MenuProps['items']}
          onClick={(e) => navigate(e.key)}
          style={{
            background: 'transparent',
            borderInlineEnd: 'none',
            padding: '14px 12px',
            fontSize: 14,
          }}
        />
      </Layout.Sider>

      <Layout>
        <Layout.Header
          style={{
            background: '#ffffff',
            borderBottom: '1px solid #eef1f6',
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: 56,
            lineHeight: '56px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
          }}
        >
          <Space size="middle">
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{ color: '#64748b' }}
            />
            <Breadcrumb
              items={[{ title: 'Home' }, { title: currentTitle }]}
              style={{ fontSize: 13 }}
            />
          </Space>
          <Dropdown menu={userMenu} placement="bottomRight">
            <Space style={{ cursor: 'pointer', padding: '4px 10px', borderRadius: 24, transition: 'background 0.2s' }}>
              <Avatar
                size={30}
                icon={<UserOutlined />}
                style={{ background: 'linear-gradient(135deg, #2f7dff, #52c41a)', flexShrink: 0 }}
              />
              <span style={{ fontSize: 13, fontWeight: 500, color: '#334155' }}>
                {user?.nickname || user?.username}
              </span>
            </Space>
          </Dropdown>
        </Layout.Header>
        <Layout.Content style={{ padding: 24 }}>
          <div style={{ maxWidth: 1200, margin: '0 auto' }}>{children}</div>
        </Layout.Content>
      </Layout>
    </Layout>
  );
}
