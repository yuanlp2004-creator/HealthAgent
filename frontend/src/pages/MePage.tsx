import { useState } from 'react';
import {
  Button,
  Card,
  DatePicker,
  Descriptions,
  Form,
  Input,
  Modal,
  Radio,
  message,
} from 'antd';
import { KeyOutlined, LogoutOutlined } from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import { useAuth } from '../store/auth';
import { userApi } from '../api/endpoints';
import { extractError } from '../utils/error';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import PageHeader from '../components/PageHeader';

interface ProfileForm {
  nickname?: string | null;
  gender?: 'male' | 'female' | 'other' | null;
  birth_date?: Dayjs | null;
}

interface PasswordForm {
  old_password: string;
  new_password: string;
  confirm: string;
}

export default function MePage() {
  const { user, setUser, logout } = useAuth();
  const navigate = useNavigate();
  const [form] = Form.useForm<ProfileForm>();
  const [pwdForm] = Form.useForm<PasswordForm>();
  const [saving, setSaving] = useState(false);
  const [pwdOpen, setPwdOpen] = useState(false);
  const [pwdSaving, setPwdSaving] = useState(false);

  if (!user) return null;

  const onSubmit = async (values: ProfileForm) => {
    setSaving(true);
    try {
      const payload = {
        nickname: values.nickname ?? null,
        gender: values.gender ?? null,
        birth_date: values.birth_date ? values.birth_date.format('YYYY-MM-DD') : null,
      };
      const updated = await userApi.updateProfile(payload);
      setUser(updated);
      message.success('已保存');
    } catch (err) {
      message.error(extractError(err, '保存失败'));
    } finally {
      setSaving(false);
    }
  };

  const onChangePassword = async (values: PasswordForm) => {
    if (values.new_password !== values.confirm) {
      message.error('两次新密码不一致');
      return;
    }
    setPwdSaving(true);
    try {
      await userApi.changePassword({
        old_password: values.old_password,
        new_password: values.new_password,
      });
      message.success('密码已修改，请重新登录');
      setPwdOpen(false);
      pwdForm.resetFields();
      logout();
      navigate('/login', { replace: true });
    } catch (err) {
      message.error(extractError(err, '修改失败'));
    } finally {
      setPwdSaving(false);
    }
  };

  return (
    <AppLayout>
      <div style={{ maxWidth: 720, margin: '0 auto' }}>
        <PageHeader
          title="个人中心"
          subtitle="查看与维护你的账号资料与安全设置"
          extra={
            <>
              <Button icon={<KeyOutlined />} onClick={() => setPwdOpen(true)}>
                修改密码
              </Button>
              <Button
                danger
                icon={<LogoutOutlined />}
                onClick={() => {
                  logout();
                  navigate('/login', { replace: true });
                }}
              >
                退出登录
              </Button>
            </>
          }
        />

        <Card
          title={<span style={{ fontWeight: 600 }}>📋 账号信息</span>}
          style={{ marginBottom: 16, borderRadius: 14, border: '1px solid #eef1f6' }}
        >
          <Descriptions column={1} size="small">
            <Descriptions.Item label="头像">
              <div
                style={{
                  width: 48,
                  height: 48,
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #2f7dff 0%, #52c41a 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                  fontWeight: 700,
                  fontSize: 18,
                }}
              >
                {(user.nickname || user.username)[0].toUpperCase()}
              </div>
            </Descriptions.Item>
            <Descriptions.Item label="用户名">{user.username}</Descriptions.Item>
            <Descriptions.Item label="邮箱">{user.email}</Descriptions.Item>
            <Descriptions.Item label="注册时间">{user.created_at}</Descriptions.Item>
          </Descriptions>
        </Card>

        <Card
          title={<span style={{ fontWeight: 600 }}>👤 基础资料</span>}
          style={{ borderRadius: 14, border: '1px solid #eef1f6' }}
        >
          <Form<ProfileForm>
            form={form}
            layout="vertical"
            initialValues={{
              nickname: user.nickname ?? undefined,
              gender: user.gender ?? undefined,
              birth_date: user.birth_date ? dayjs(user.birth_date) : undefined,
            }}
            onFinish={onSubmit}
          >
            <Form.Item label="昵称" name="nickname">
              <Input placeholder="昵称" />
            </Form.Item>
            <Form.Item label="性别" name="gender">
              <Radio.Group>
                <Radio value="male">男</Radio>
                <Radio value="female">女</Radio>
                <Radio value="other">其他</Radio>
              </Radio.Group>
            </Form.Item>
            <Form.Item label="生日" name="birth_date">
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={saving} shape="round">
                保存资料
              </Button>
            </Form.Item>
          </Form>
        </Card>

      <Modal
        title="修改密码"
        open={pwdOpen}
        onCancel={() => setPwdOpen(false)}
        onOk={() => pwdForm.submit()}
        confirmLoading={pwdSaving}
        destroyOnClose
      >
        <Form<PasswordForm> form={pwdForm} layout="vertical" onFinish={onChangePassword}>
          <Form.Item
            label="旧密码"
            name="old_password"
            rules={[{ required: true, message: '请输入旧密码' }]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item
            label="新密码"
            name="new_password"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, max: 128, message: '长度 6-128' },
            ]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item
            label="确认新密码"
            name="confirm"
            rules={[{ required: true, message: '请再次输入新密码' }]}
          >
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>
      </div>
    </AppLayout>
  );
}
