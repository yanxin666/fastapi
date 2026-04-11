import type { ReactNode } from 'react'
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import {
  ApiError,
  type AdminUser,
  getCurrentAdminUser,
  loginAdmin,
  logoutAdmin,
  refreshAdminToken,
} from './lib/api-client'

type StoredSession = {
  accessToken: string
  refreshToken: string
  user: AdminUser | null
}

type LoginCredentials = {
  username: string
  password: string
}

type AuthContextValue = {
  accessToken: string | null
  user: AdminUser | null
  permissions: string[]
  isLoading: boolean
  login: (credentials: LoginCredentials) => Promise<AdminUser>
  logout: () => Promise<void>
}

const STORAGE_KEY = 'admin.auth.session'

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

function readStoredSession(): StoredSession | null {
  const rawValue = localStorage.getItem(STORAGE_KEY)

  if (!rawValue) {
    return null
  }

  try {
    const parsedValue = JSON.parse(rawValue) as Partial<StoredSession>

    if (
      typeof parsedValue.accessToken !== 'string' ||
      typeof parsedValue.refreshToken !== 'string'
    ) {
      localStorage.removeItem(STORAGE_KEY)
      return null
    }

    return {
      accessToken: parsedValue.accessToken,
      refreshToken: parsedValue.refreshToken,
      user: parsedValue.user ?? null,
    }
  } catch {
    localStorage.removeItem(STORAGE_KEY)
    return null
  }
}

function writeStoredSession(session: StoredSession | null) {
  if (session) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
    return
  }

  localStorage.removeItem(STORAGE_KEY)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<StoredSession | null>(readStoredSession)
  const [isLoading, setIsLoading] = useState(() => readStoredSession() !== null)

  const applySession = useCallback((nextSession: StoredSession | null) => {
    setSession(nextSession)
    writeStoredSession(nextSession)
  }, [])

  useEffect(() => {
    const storedSession = readStoredSession()

    if (!storedSession) {
      setIsLoading(false)
      return
    }

    let active = true

    const bootstrapSession = async () => {
      try {
        const user = await getCurrentAdminUser(storedSession.accessToken)

        if (!active) {
          return
        }

        applySession({ ...storedSession, user })
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          try {
            const refreshedTokens = await refreshAdminToken(storedSession.refreshToken)
            const refreshedSession = {
              accessToken: refreshedTokens.accessToken,
              refreshToken: refreshedTokens.refreshToken,
              user: storedSession.user,
            }
            const user = await getCurrentAdminUser(refreshedSession.accessToken)

            if (!active) {
              return
            }

            applySession({ ...refreshedSession, user })
          } catch {
            if (active) {
              applySession(null)
            }
          }
        }
      } finally {
        if (active) {
          setIsLoading(false)
        }
      }
    }

    void bootstrapSession()

    return () => {
      active = false
    }
  }, [applySession])

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      const result = await loginAdmin(credentials)
      const nextSession = {
        accessToken: result.accessToken,
        refreshToken: result.refreshToken,
        user: result.user,
      }

      applySession(nextSession)
      return result.user
    },
    [applySession],
  )

  const logout = useCallback(async () => {
    const refreshToken = session?.refreshToken

    if (refreshToken) {
      try {
        await logoutAdmin(refreshToken)
      } catch {
        applySession(null)
        return
      }
    }

    applySession(null)
  }, [applySession, session?.refreshToken])

  const value = useMemo<AuthContextValue>(
    () => ({
      accessToken: session?.accessToken ?? null,
      user: session?.user ?? null,
      permissions: session?.user?.permissions ?? [],
      isLoading,
      login,
      logout,
    }),
    [isLoading, login, logout, session],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }

  return context
}
