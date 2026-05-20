import { Spin } from 'antd'
import { lazy, Suspense } from 'react'
import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'

import { ROUTE_POLICIES, usePermissions, type PermissionCode } from '../lib/permissions'
import { useAuth } from '../auth'
import { AdminLayout } from '../layouts/AdminLayout'

const LoginPage = lazy(() => import('../pages/LoginPage').then((m) => ({ default: m.LoginPage })))
const DashboardPage = lazy(() => import('../pages/DashboardPage').then((m) => ({ default: m.DashboardPage })))
const ForbiddenPage = lazy(() => import('../pages/ForbiddenPage').then((m) => ({ default: m.ForbiddenPage })))
const NotFoundPage = lazy(() => import('../pages/NotFoundPage').then((m) => ({ default: m.NotFoundPage })))
const UsersPage = lazy(() => import('../pages/UsersPage').then((m) => ({ default: m.UsersPage })))
const RolesPage = lazy(() => import('../pages/RolesPage').then((m) => ({ default: m.RolesPage })))
const PermissionsPage = lazy(() => import('../pages/PermissionsPage').then((m) => ({ default: m.PermissionsPage })))
const CustomersPage = lazy(() => import('../pages/CustomersPage').then((m) => ({ default: m.CustomersPage })))
const MyCustomersPage = lazy(() => import('../pages/MyCustomersPage').then((m) => ({ default: m.MyCustomersPage })))
const LongTermCustomersPage = lazy(() => import('../pages/LongTermCustomersPage').then((m) => ({ default: m.LongTermCustomersPage })))
const ClaimStrategiesPage = lazy(() => import('../pages/ClaimStrategiesPage').then((m) => ({ default: m.ClaimStrategiesPage })))

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
    <Suspense fallback={<FullPageSpinner />}>
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

            <Route element={<PermissionRoute permission={ROUTE_POLICIES['/long-term-customers']} />}>
              <Route path="long-term-customers" element={<LongTermCustomersPage />} />
            </Route>

            <Route element={<PermissionRoute permission={ROUTE_POLICIES['/claim-strategies']} />}>
              <Route path="claim-strategies" element={<ClaimStrategiesPage />} />
            </Route>
          </Route>
        </Route>

        <Route path="home" element={<Navigate to="/" replace />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}
