from .client import _get_client
from .schemas import DeleteFileSchema, InitClientSchema, UploadFileSchema


# COSService 类封装了与腾讯云对象存储服务（COS）的交互，提供了上传文件的功能。
class COSService:

    # 初始化 COS 客户端
    def __init__(self, params: InitClientSchema):
        self.client = _get_client(
            params.region,
            params.secret_id,
            params.secret_key,
            params.token,
            params.scheme,
        )

    # 上传文件到 COS
    def upload_file(self, params: UploadFileSchema):
        try:
            response = self.client.upload_file(
                Bucket=params.bucket_name,
                Key=params.object_name,
                LocalFilePath=params.file_path,
                PartSize=1,
                MAXThread=3,
                EnableMD5=False,
            )
            return response
        except Exception as e:
            print(f"Error uploading file to COS: {e}")
            raise e

    # 删除 COS 上的文件
    def delete_file(self, params: DeleteFileSchema):
        try:
            response = self.client.delete_object(
                Bucket=params.bucket_name,
                Key=params.object_name,
            )
            return response
        except Exception as e:
            print(f"Error deleting file from COS: {e}")
            raise e
