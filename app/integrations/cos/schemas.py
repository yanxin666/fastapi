from pydantic import BaseModel


# 定义初始化客户端请求的数据模型
# region: COS 所在的地域，例如 'ap-beijing'
# secret_id: 用户的 SecretId，建议使用子账号密钥，授权遵循最小权限指引，降低使用风险。子账号密钥获取可参见 https://cloud.tencent.com/document/product/598/37140
# secret_key: 用户的 SecretKey，建议使用子账号密钥，授权遵循最小权限指引，降低使用风险。子账号密钥获取可参见 https://cloud.tencent.com/document/product/598/
# token: 如果使用永久密钥不需要填入 token，如果使用临时密钥需要填入，临时密钥生成和使用指引参见 https://cloud.tencent.com/document/product/436/14048
# scheme: 指定使用 http/https 协议来访问 COS，默认为 https，可不填
class InitClientSchema(BaseModel):
    # 必填字段：region、secret_id、secret_key
    region: str
    ''' COS 所在的地域，例如 'ap-beijing '''

    secret_id: str
    ''' 用户的 SecretId '''

    secret_key: str
    ''' 用户的 SecretKey '''

    # 可选字段：token、scheme，scheme 默认为 'https'
    token: str = None
    ''' 如果使用永久密钥不需要填入 token，如果使用临时密钥需要填入 '''

    scheme: str = 'https'
    ''' 指定使用 http/https 协议来访问 COS，默认为 https '''


# 定义上传文件请求的数据模型
# bucket_name: 存储桶名称，格式为 BucketName-Appid，例如 mybucket-1250000000
# object_name: 存储在 COS 中的对象键（即文件路径），例如 folder/subfolder/file.txt
# file_path: 本地文件路径，例如 /path/to/local/file.txt
class UploadFileSchema(BaseModel):
    bucket_name: str
    ''' 存储桶名称，格式为 BucketName-Appid，例如 mybucket-1250000000 '''

    object_name: str
    ''' 存储在 COS 中的对象键（即文件路径），例如 folder/subfolder/file.txt '''

    file_path: str
    ''' 本地文件路径，例如 /path/to/local/file.txt '''
