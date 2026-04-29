import { Button, Card, Form, Input, Typography, message } from 'antd';
import { UserOutlined, LockOutlined, HeartFilled } from '@ant-design/icons';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../store/auth';
import { extractError } from '../utils/error';

interface FormValues {
  username: string;
  password: string;
}

export default function LoginPage() {
  const [form] = Form.useForm<FormValues>();
  const { login, loading } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();

  const onFinish = async (values: FormValues) => {
    try {
      await login(values.username, values.password);
      message.success('登录成功');
      const redirect = params.get('redirect');
      navigate(redirect ? decodeURIComponent(redirect) : '/bp/dashboard', { replace: true });
    } catch (err) {
      message.error(extractError(err, '登录失败'));
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(150deg, #e8f4ff 0%, #f0f5ff 30%, #fafbfd 60%, #f5f7fa 100%)',
        padding: 16,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Background orbs */}
      <div className="auth-bg-orb" style={{ width: 320, height: 320, top: -60, left: -40 }} />
      <div className="auth-bg-orb" style={{ width: 240, height: 240, bottom: -40, right: -30, animationDelay: '4s' }} />
      <div className="auth-bg-orb" style={{ width: 120, height: 120, top: '40%', right: '15%', animationDelay: '2s', opacity: 0.05 }} />

      <Card
        className="glass-card"
        style={{ width: 400, borderRadius: 18, boxShadow: '0 8px 32px rgba(0,0,0,0.07)' }}
        bodyStyle={{ padding: '32px 28px' }}
      >
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <HeartFilled className="breathe" style={{ color: '#2f7dff', fontSize: 40 }} />
          <Typography.Title level={3} style={{ margin: '10px 0 4px', fontWeight: 600 }}>
            HealthAgent
          </Typography.Title>
          <Typography.Text type="secondary">个人健康管理平台</Typography.Text>
        </div>
        <Form form={form} layout="vertical" onFinish={onFinish} autoComplete="on" size="large">
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="用户名" autoFocus />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 8 }}>
            <Button type="primary" htmlType="submit" block loading={loading} shape="round">
              登录
            </Button>
          </Form.Item>
          <div style={{ textAlign: 'center' }}>
            <Typography.Text type="secondary">
              没有账号？<Link to="/register">立即注册</Link>
            </Typography.Text>
          </div>
        </Form>
      </Card>
    </div>
  );
}
