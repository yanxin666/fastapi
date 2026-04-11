import { Result } from 'antd'

export function NotFoundPage() {
  return <Result status="404" title="404" subTitle="你访问的页面不存在。" />
}
