import { Spin } from 'antd'
import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'

import { ROUTE_POLICIES, usePermissions, type PermissionCode } from '../lib/permissions'
import { useAuth } from '../auth'
import { AdminLayout } from '../layouts/AdminLayout'
import { ClaimStrategiesPage } from '../pages/ClaimStrategiesPage'
import { CustomersPage } from '../pages/CustomersPage'
import { DashboardPage } from '../pages/DashboardPage'
import { ForbiddenPage } from '../pages/ForbiddenPage'
import { LoginPage } from '../pages/LoginPage'
import { MyCustomersPage } from '../pages/MyCustomersPage'
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

function PermissionRoute({ permission }: { permission: PermissionCode }) {
  const perms = usePermissions()

  if (!perms.has(permission)) {
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

          <Route element={<PermissionRoute permission={ROUTE_POLICIES['/users']} />}>
            <Route path="users" element={<UsersPage />} />
          </Route>

          <Route element={<PermissionRoute permission={ROUTE_POLICIES['/roles']} />}>
            <Route path="roles" element={<RolesPage />} />
          </Route>

          <Route element={<PermissionRoute permission={ROUTE_POLICIES['/permissions']} />}>
            <Route path="permissions" element={<PermissionsPage />} />
          </Route>

          <Route element={<PermissionRoute permission={ROUTE_POLICIES['/customers']} />}>
            <Route path="customers" element={<CustomersPage />} />
          </Route>

          <Route element={<PermissionRoute permission={ROUTE_POLICIES['/my-customers']} />}>
            <Route path="my-customers" element={<MyCustomersPage />} />
          </Route>

          <Route element={<PermissionRoute permission={ROUTE_POLICIES['/claim-strategies']} />}>
            <Route path="claim-strategies" element={<ClaimStrategiesPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="home" element={<Navigate to="/" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
