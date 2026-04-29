import { useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Row,
  Space,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd';
import type { UploadFile } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import PageHeader from '../components/PageHeader';
import { bpRecordsApi, ocrApi } from '../api/bpRecords';
import { extractError } from '../utils/error';
import type { OcrBpResponse } from '../types/api';

interface FormValues {
  systolic: number;
  diastolic: number;
  heart_rate?: number;
  measured_at: Dayjs;
  note?: string;
}

export default function BpRecordForm() {
  const navigate = useNavigate();
  const [form] = Form.useForm<FormValues>();
  const [ocrLoading, setOcrLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [ocrResult, setOcrResult] = useState<OcrBpResponse | null>(null);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [imageId, setImageId] = useState<string | null>(null);
  const [source, setSource] = useState<'manual' | 'ocr'>('manual');

  const runOcr = async (file: File) => {
    setOcrLoading(true);
    try {
      const result = await ocrApi.bp(file);
      setOcrResult(result);
      setImageId(result.image_id);
      const { systolic, diastolic, heart_rate } = result.fields;
      const patch: Partial<FormValues> = {};
      if (systolic != null) patch.systolic = systolic;
      if (diastolic != null) patch.diastolic = diastolic;
      if (heart_rate != null) patch.heart_rate = heart_rate;
      form.setFieldsValue(patch);
      setSource('ocr');
      const filled = [systolic, diastolic, heart_rate].filter((v) => v != null).length;
      if (filled === 3) message.success('识别成功，已回填三个字段，如有误请手动修改');
      else if (filled > 0) message.warning(`仅识别到 ${filled}/3 个字段，请手动补齐`);
      else message.error('未能识别到任何字段，请手动录入');
    } catch (err) {
      message.error(extractError(err, 'OCR 识别失败'));
    } finally {
      setOcrLoading(false);
    }
  };

  const onSubmit = async (values: FormValues) => {
    setSaving(true);
    try {
      await bpRecordsApi.create({
        systolic: values.systolic,
        diastolic: values.diastolic,
        heart_rate: values.heart_rate ?? null,
        measured_at: values.measured_at.toISOString(),
        source,
        image_id: imageId,
        note: values.note ?? null,
      });
      message.success('记录已保存');
      navigate('/bp/list');
    } catch (err) {
      message.error(extractError(err, '保存失败'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppLayout>
      <PageHeader
        title="拍照录入"
        subtitle="上传血压计照片自动识别，或直接手动录入"
      />
      <Row gutter={16}>
        <Col xs={24} md={10}>
          <Card
            title={<span style={{ fontWeight: 600 }}>📷 拍照识别（可选）</span>}
            size="small"
            style={{ borderRadius: 14, border: '1px solid #eef1f6' }}
          >
            <Upload.Dragger
              accept="image/jpeg,image/png,image/webp"
              fileList={fileList}
              maxCount={1}
              beforeUpload={(file) => {
                setFileList([
                  { uid: file.uid, name: file.name, status: 'done', originFileObj: file as any },
                ]);
                void runOcr(file);
                return false;
              }}
              onRemove={() => {
                setFileList([]);
                setOcrResult(null);
                setImageId(null);
                setSource('manual');
              }}
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽血压计照片到此处</p>
              <p className="ant-upload-hint">JPG/PNG/WebP，≤8MB</p>
            </Upload.Dragger>

            {ocrLoading && (
              <Alert style={{ marginTop: 12 }} type="info" message="识别中，请稍候…" />
            )}
            {ocrResult && !ocrLoading && (
              <Space direction="vertical" style={{ marginTop: 12, width: '100%' }}>
                <div>识别结果：</div>
                <Space wrap>
                  <Tag color="blue">
                    收缩压：{ocrResult.fields.systolic ?? '—'}
                  </Tag>
                  <Tag color="green">
                    舒张压：{ocrResult.fields.diastolic ?? '—'}
                  </Tag>
                  <Tag color="orange">
                    心率：{ocrResult.fields.heart_rate ?? '—'}
                  </Tag>
                </Space>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  结果已回填到右侧表单，识别有误时可直接修改后再保存。
                </Typography.Text>
              </Space>
            )}
          </Card>
        </Col>

        <Col xs={24} md={14}>
          <Card
            title={<span style={{ fontWeight: 600 }}>✏️ 确认并保存</span>}
            size="small"
            style={{ borderRadius: 14, border: '1px solid #eef1f6' }}
          >
            <Form<FormValues>
              form={form}
              layout="vertical"
              initialValues={{ measured_at: dayjs() }}
              onFinish={onSubmit}
              onValuesChange={(_, all) => {
                if (source === 'ocr') {
                  // 用户动过任何字段后，保留 ocr 作为 source（表示来源仍是拍照）
                  // 这里无需切换，source 仅在无拍照时才是 manual
                }
                void all;
              }}
            >
              <Row gutter={12}>
                <Col span={8}>
                  <Form.Item
                    label="收缩压 (mmHg)"
                    name="systolic"
                    rules={[{ required: true, message: '必填' }]}
                  >
                    <InputNumber min={60} max={260} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="舒张压 (mmHg)"
                    name="diastolic"
                    rules={[{ required: true, message: '必填' }]}
                  >
                    <InputNumber min={30} max={200} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item label="心率 (bpm)" name="heart_rate">
                    <InputNumber min={30} max={220} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>
              <Form.Item
                label="测量时间"
                name="measured_at"
                rules={[{ required: true, message: '请选择测量时间' }]}
              >
                <DatePicker showTime style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label="备注" name="note">
                <Input.TextArea rows={2} maxLength={500} />
              </Form.Item>
              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit" loading={saving} shape="round">
                    保存记录
                  </Button>
                  <Button onClick={() => navigate('/bp/list')} shape="round">取消</Button>
                  <Typography.Text type="secondary">
                    来源：{source === 'ocr' ? '拍照识别' : '手动录入'}
                  </Typography.Text>
                </Space>
              </Form.Item>
            </Form>
          </Card>
        </Col>
      </Row>
    </AppLayout>
  );
}
