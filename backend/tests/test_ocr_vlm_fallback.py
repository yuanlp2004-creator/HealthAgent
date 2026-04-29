from app.services import ocr_service
from app.services.ocr.extractor import OCRFields, OCRResult


def _mock_primary(monkeypatch, fields: OCRFields):
    def fake_primary(_image_bytes: bytes):
        return "mocked", []
    monkeypatch.setattr(ocr_service, "_recognize_baidu", fake_primary)
    monkeypatch.setattr(ocr_service, "_recognize_paddle", fake_primary)

    def fake_extract(_tokens):
        return fields, []
    monkeypatch.setattr(ocr_service, "extract_fields", fake_extract)


def test_vlm_fallback_triggered_when_missing(monkeypatch):
    from app.core.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test")
    monkeypatch.setenv("OCR_VLM_FALLBACK", "true")
    monkeypatch.setenv("OCR_ENGINE", "baidu")
    get_settings.cache_clear()

    _mock_primary(monkeypatch, OCRFields(systolic=None, diastolic=None, heart_rate=None))

    called = {"n": 0}
    def fake_vlm(_data: bytes):
        called["n"] += 1
        return {"systolic": 138, "diastolic": 91, "heart_rate": 102}
    import app.services.ocr.qwen_vl_client as qwen_mod
    monkeypatch.setattr(qwen_mod, "recognize_bp", fake_vlm)

    result = ocr_service.recognize(b"imgbytes")
    assert called["n"] == 1
    assert result.fields.to_dict() == {"systolic": 138, "diastolic": 91, "heart_rate": 102}
    assert len(result.candidates) == 3
    get_settings.cache_clear()


def test_vlm_fallback_skipped_when_complete(monkeypatch):
    from app.core.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test")
    monkeypatch.setenv("OCR_VLM_FALLBACK", "true")
    monkeypatch.setenv("OCR_ENGINE", "baidu")
    get_settings.cache_clear()

    _mock_primary(monkeypatch, OCRFields(systolic=120, diastolic=80, heart_rate=70))

    called = {"n": 0}
    def fake_vlm(_data: bytes):
        called["n"] += 1
        return {"systolic": 999, "diastolic": 999, "heart_rate": 999}
    import app.services.ocr.qwen_vl_client as qwen_mod
    monkeypatch.setattr(qwen_mod, "recognize_bp", fake_vlm)

    result = ocr_service.recognize(b"imgbytes")
    assert called["n"] == 0
    assert result.fields.to_dict() == {"systolic": 120, "diastolic": 80, "heart_rate": 70}
    get_settings.cache_clear()


def test_vlm_fallback_disabled_without_api_key(monkeypatch):
    from app.core.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("DASHSCOPE_API_KEY", "")
    monkeypatch.setenv("OCR_VLM_FALLBACK", "true")
    monkeypatch.setenv("OCR_ENGINE", "baidu")
    get_settings.cache_clear()

    _mock_primary(monkeypatch, OCRFields(systolic=None, diastolic=None, heart_rate=None))

    import app.services.ocr.qwen_vl_client as qwen_mod
    def boom(_):
        raise AssertionError("should not be called")
    monkeypatch.setattr(qwen_mod, "recognize_bp", boom)

    result = ocr_service.recognize(b"imgbytes")
    assert result.fields.to_dict() == {"systolic": None, "diastolic": None, "heart_rate": None}
    get_settings.cache_clear()


def test_vlm_fallback_swallows_errors(monkeypatch):
    from app.core.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test")
    monkeypatch.setenv("OCR_VLM_FALLBACK", "true")
    monkeypatch.setenv("OCR_ENGINE", "baidu")
    get_settings.cache_clear()

    _mock_primary(monkeypatch, OCRFields(systolic=120, diastolic=None, heart_rate=None))

    import app.services.ocr.qwen_vl_client as qwen_mod
    def fake_vlm(_):
        raise RuntimeError("network down")
    monkeypatch.setattr(qwen_mod, "recognize_bp", fake_vlm)

    result = ocr_service.recognize(b"imgbytes")
    assert result.fields.systolic == 120
    assert result.fields.diastolic is None
    get_settings.cache_clear()
