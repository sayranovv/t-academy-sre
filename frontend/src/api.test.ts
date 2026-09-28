import { afterEach, expect, it, vi } from 'vitest'
import { getJson } from './api'

afterEach(() => vi.unstubAllGlobals())

it('does not treat HTTP failure as successful JSON', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response('{}', { status: 503 }))
  vi.stubGlobal('fetch', fetch)
  await expect(getJson('/health/ready')).rejects.toThrow('HTTP 503')
  expect(fetch).toHaveBeenCalledTimes(1)
})

it('propagates network failures without automatic retries', async () => {
  const fetch = vi.fn().mockRejectedValue(new TypeError('Network error'))
  vi.stubGlobal('fetch', fetch)
  await expect(getJson('/api/v1/status')).rejects.toThrow('Network error')
  expect(fetch).toHaveBeenCalledTimes(1)
})
