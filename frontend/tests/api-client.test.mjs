import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

async function loadApiClientModule() {
  const sourceUrl = new URL('../src/api/client.ts', import.meta.url)
  const source = await readFile(sourceUrl, 'utf8')
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
      verbatimModuleSyntax: true,
    },
    fileName: 'client.ts',
  })

  return import(`data:text/javascript;charset=utf-8,${encodeURIComponent(outputText)}`)
}

function jsonResponse(status, body = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() {
      return body
    },
  }
}

function headerValue(headers, name) {
  if (typeof headers.get === 'function') {
    return headers.get(name)
  }

  const entry = Object.entries(headers).find(([key]) => key.toLowerCase() === name.toLowerCase())
  return entry?.[1]
}

async function captureApiError(action) {
  try {
    await action()
  } catch (error) {
    return error
  }

  assert.fail('Expected ApiError to be thrown')
}

test('gets a Clerk session token for each request and sends it as a bearer token', async () => {
  const { createAuthenticatedApiClient } = await loadApiClientModule()
  const fetchCalls = []
  const tokens = ['first-token', 'second-token']
  const client = createAuthenticatedApiClient({
    baseUrl: 'https://api.example.test',
    getToken: async () => tokens.shift() ?? null,
    fetch: async (url, init) => {
      fetchCalls.push({ url, init })
      return jsonResponse(200, { ok: true })
    },
  })

  await client.request('/plants', { headers: { 'X-Request-Id': 'a' } })
  await client.request('/plants/1')

  assert.equal(fetchCalls.length, 2)
  assert.equal(fetchCalls[0].url, 'https://api.example.test/plants')
  assert.equal(headerValue(fetchCalls[0].init.headers, 'Authorization'), 'Bearer first-token')
  assert.equal(headerValue(fetchCalls[0].init.headers, 'Content-Type'), 'application/json')
  assert.equal(headerValue(fetchCalls[0].init.headers, 'X-Request-Id'), 'a')
  assert.equal(headerValue(fetchCalls[1].init.headers, 'Authorization'), 'Bearer second-token')
})

test('missing token fails as auth without calling fetch', async () => {
  const { createAuthenticatedApiClient } = await loadApiClientModule()
  let fetchCalled = false
  const client = createAuthenticatedApiClient({
    baseUrl: 'https://api.example.test',
    getToken: async () => null,
    fetch: async () => {
      fetchCalled = true
      return jsonResponse(200, {})
    },
  })

  const error = await captureApiError(() => client.request('/plants'))

  assert.equal(fetchCalled, false)
  assert.equal(error.type, 'auth')
  assert.match(error.message, /ログイン|認証|セッション/)
})

test('token provider failures fail closed as sanitized auth errors without calling fetch', async () => {
  const { createAuthenticatedApiClient } = await loadApiClientModule()
  let fetchCalled = false
  const client = createAuthenticatedApiClient({
    baseUrl: 'https://api.example.test',
    getToken: async () => {
      throw new Error('Clerk getToken failed with Bearer stale-token and sk_test_secret')
    },
    fetch: async () => {
      fetchCalled = true
      return jsonResponse(200, {})
    },
  })

  const error = await captureApiError(() => client.request('/plants'))

  assert.equal(fetchCalled, false)
  assert.equal(error.type, 'auth')
  assert.doesNotMatch(error.message, /stale-token/)
  assert.doesNotMatch(error.message, /sk_test_secret/)
  assert.doesNotMatch(error.message, /Clerk getToken/)
})

test('classifies protected API and validation responses as typed errors without leaking details', async () => {
  const { createAuthenticatedApiClient } = await loadApiClientModule()
  const statuses = [
    [401, 'auth'],
    [403, 'forbidden'],
    [404, 'not_found'],
    [422, 'validation'],
  ]

  for (const [status, type] of statuses) {
    const client = createAuthenticatedApiClient({
      baseUrl: 'https://api.example.test',
      getToken: async () => 'valid-token',
      fetch: async () =>
        jsonResponse(status, {
          detail: 'internal verifier failed with sk_test_secret and Bearer leaked-token',
        }),
    })

    const error = await captureApiError(() => client.request('/plants'))

    assert.equal(error.type, type)
    assert.doesNotMatch(error.message, /sk_test_secret/)
    assert.doesNotMatch(error.message, /leaked-token/)
    assert.doesNotMatch(error.message, /internal verifier/i)
  }
})

test('classifies network and server failures without leaking backend details', async () => {
  const { createAuthenticatedApiClient } = await loadApiClientModule()
  const networkClient = createAuthenticatedApiClient({
    baseUrl: 'https://api.example.test',
    getToken: async () => 'valid-token',
    fetch: async () => {
      throw new Error('connect ECONNRESET with Bearer network-token')
    },
  })

  const networkError = await captureApiError(() => networkClient.request('/plants'))
  assert.equal(networkError.type, 'network')
  assert.doesNotMatch(networkError.message, /network-token/)

  const serverClient = createAuthenticatedApiClient({
    baseUrl: 'https://api.example.test',
    getToken: async () => 'valid-token',
    fetch: async () =>
      jsonResponse(500, {
        detail: 'stack trace includes CLERK_SECRET_KEY=sk_live_secret',
      }),
  })

  const serverError = await captureApiError(() => serverClient.request('/plants'))
  assert.equal(serverError.type, 'server')
  assert.doesNotMatch(serverError.message, /sk_live_secret/)
  assert.doesNotMatch(serverError.message, /CLERK_SECRET_KEY/)
})

test('createApiError sanitizes secret-bearing messages', async () => {
  const { createApiError } = await loadApiClientModule()

  const error = createApiError('auth', 'verifier rejected token Bearer abc with sk_test_secret')

  assert.equal(error.type, 'auth')
  assert.doesNotMatch(error.message, /verifier/)
  assert.doesNotMatch(error.message, /Bearer abc/)
  assert.doesNotMatch(error.message, /sk_test_secret/)
})
