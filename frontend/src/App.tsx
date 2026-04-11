import { App as AntApp, ConfigProvider } from 'antd'
import { BrowserRouter } from 'react-router-dom'

import { AuthProvider } from './auth'
import { AppRoutes } from './router/AppRoutes'

function App() {
  return (
    <ConfigProvider>
      <AntApp>
        <AuthProvider>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </AuthProvider>
      </AntApp>
    </ConfigProvider>
  )
}

export default App
