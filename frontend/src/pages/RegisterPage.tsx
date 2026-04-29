import { Button, Card, Form, Input, Typography, message } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined, HeartFilled } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../store/auth';
import { extractError } from '../utils/error';

interface FormValues {
  username: string;
  email: string;
  password: string;
  nickname?: string;
}

export default function RegisterPage() {
  const [form] = Form.useForm<FormValues>();
  const { register, loading } = useAuth();
  const navigate = useNavigate();

  const onFinish = async (values: FormValues) => {
    try {
      await register(values.username, values.email, values.password, values.nickname);
      message.success('注册成功');
      navigate('/bp/dashboard', { replace: true });
    } catch (err) {
      message.error(extractError(err, '注册失败'));
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
      <div className="auth-bg-orb" style={{ width: 280, height: 280, top: -40, right: -20 }} />
      <div className="auth-bg-orb" style={{ width: 200, height: 200, bottom: -30, left: -20, animationDelay: '4s' }} />

      <Card
        className="glass-card"
        style={{ width: 400, borderRadius: 18, boxShadow: '0 8px 32px rgba(0,0,0,0.07)' }}
        bodyStyle={{ padding: '32px 28px' }}
      >
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <HeartFilled className="breathe" style={{ color: '#2f7dff', fontSize: 40 }} />
          <Typography.Title level={3} style={{ margin: '10px 0 4px', fontWeight: 600 }}>
            注册新账号
          </Typography.Title>
        </div>
        <Form form={form} layout="vertical" onFinish={onFinish} size="large">
          <Form.Item
            name="username"
            rules={[
              { required: true, message: '请输入用户名' },
              { pattern: /^[A-Za-z0-9_]+$/, message: '仅允许字母/数字/下划线' },
              { min: 3, max: 32, message: '长度 3-32' },
            ]}
          >
            <Input prefix={<UserOutlined />} placeholder="3-32 位用户名" autoFocus />
          </Form.Item>
          <Form.Item
            name="email"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '邮箱格式不正确' },
            ]}
          >
            <Input prefix={<MailOutlined />} placeholder="you@example.com" />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, max: 128, message: '长度 6-128' },
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="至少 6 位密码" />
          </Form.Item>
          <Form.Item name="nickname">
            <Input prefix={<UserOutlined />} placeholder="昵称（可选）" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 8 }}>
            <Button type="primary" htmlType="submit" block loading={loading} shape="round">
              注册
            </Button>
          </Form.Item>
          <div style={{ textAlign: 'center' }}>
            <Typography.Text type="secondary">
              已有账号？<Link to="/login">返回登录</Link>
            </Typography.Text>
          </div>
        </Form>
      </Card>
    </div>
  );
}
