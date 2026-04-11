import { describe, expect, it } from 'vitest'

describe('api config', () => {
  it('uses the configured admin API base url when overridden', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000/api/v1/admin/')
    const { getApiBaseUrl } = await import('../config/api')

    expect(getApiBaseUrl()).toBe('http://localhost:8000/api/v1/admin')
  })

  it('uses the default admin API base url when no override is set', async () => {
    const { getApiBaseUrl } = await import('../config/api')

    expect(getApiBaseUrl()).toBe('/api/v1/admin')
  })
})
