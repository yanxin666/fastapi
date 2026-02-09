from fastapi import Request, HTTPException

# JWT 校验依赖函数
def jwt_auth_dependency(request: Request):
    """
    用于路由 Depends 的 JWT 校验依赖函数，只在需要的路由上使用。
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = auth_header[7:]
    # 这里可以添加解析和验证 JWT Token 的逻辑
    # 例如：user = parse_and_validate_jwt(token)
    # request.state.user = user
    return token