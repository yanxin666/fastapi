import { Result } from 'antd'

export function ForbiddenPage() {
  return <Result status="403" title="403" subTitle="你没有权限访问当前页面。" />
}
