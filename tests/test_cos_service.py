import logging
from pathlib import Path

from app.core.config import get_settings
from app.integrations.cos.service import COSService
from app.integrations.cos.schemas import InitClientSchema, UploadFileSchema


# 这个测试函数验证了 COSService 的文件上传功能。
def test_upload_file():
    settings = get_settings()
    init_params = InitClientSchema(
        region="ap-beijing",
        secret_id=settings.tencent_cos_secret_id,
        secret_key=settings.tencent_cos_secret_key,
        token=None,
        scheme="https",
    )

    service = COSService(init_params)

    file_path = Path(__file__).resolve().parents[1] / "tmp" / "customer.xlsx"
    response = service.upload_file(
        UploadFileSchema(
            bucket_name="crm-1256276789",
            object_name="dbBack/customer.xlsx",
            file_path=str(file_path),
        )
    )

    logging.info("Upload response: %s", response)

    # SDK 上传成功通常会返回 ETag 等字段，至少保证返回结果非空。
    assert response is not None
