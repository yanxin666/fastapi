import { Spin } from 'antd'
import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'

import { useAuth } from '../auth'
import { AdminLayout } from '../layouts/AdminLayout'
import { DashboardPage } from '../pages/DashboardPage'
import { ForbiddenPage } from '../pages/ForbiddenPage'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { PermissionsPage } from '../pages/PermissionsPage'
import { RolesPage } from '../pages/RolesPage'
import { UsersPage } from '../pages/UsersPage'

function FullPageSpinner() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Spin size="large" />
    </div>
  )
}

function PublicOnlyRoute() {
  const { isLoading, user } = useAuth()

  if (isLoading) {
    return <FullPageSpinner />
  }

  if (user) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}

function ProtectedRoute() {
  const { isLoading, user } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <FullPageSpinner />
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <Outlet />
}

function PermissionRoute({ permission }: { permission: string }) {
  const { permissions } = useAuth()

  if (!permissions.includes(permission)) {
    return <Navigate to="/403" replace />
  }

  return <Outlet />
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicOnlyRoute />}>
        <Route path="login" element={<LoginPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AdminLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="403" element={<ForbiddenPage />} />

          <Route element={<PermissionRoute permission="user:view" />}>
            <Route path="users" element={<UsersPage />} />
          </Route>

          <Route element={<PermissionRoute permission="role:view" />}>
            <Route path="roles" element={<RolesPage />} />
          </Route>

          <Route element={<PermissionRoute permission="permission:view" />}>
            <Route path="permissions" element={<PermissionsPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="home" element={<Navigate to="/" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
