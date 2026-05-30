import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'

const readSource = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8')

test('plant routes are marked as protected routes', async () => {
  const router = await readSource('src/router/index.ts')

  assert.match(router, /path:\s*['"]\/plants['"][\s\S]*meta:\s*\{[^}]*requiresAuth:\s*true/)
  assert.match(router, /path:\s*['"]\/plants\/:plantId['"][\s\S]*meta:\s*\{[^}]*requiresAuth:\s*true/)
})

test('app shell keeps routed content inside AuthGate and exposes auth header controls', async () => {
  const app = await readSource('src/App.vue')

  assert.match(app, /import\s+AuthGate\s+from\s+['"]\.\/components\/auth\/AuthGate\.vue['"]/)
  assert.match(
    app,
    /import\s+AuthHeaderControls\s+from\s+['"]\.\/components\/auth\/AuthHeaderControls\.vue['"]/,
  )
  assert.match(app, /<AuthHeaderControls\s*\/>/)
  assert.match(app, /<AuthGate[\s\S]*<RouterView\s*\/>[\s\S]*<\/AuthGate>/)
})

test('AuthGate fails closed while auth loads or is signed out', async () => {
  const gate = await readSource('src/components/auth/AuthGate.vue')

  assert.match(gate, /useAuth\(/)
  assert.match(gate, /isLoaded/)
  assert.match(gate, /isSignedIn/)
  assert.match(gate, /v-if=["']!isLoaded["']/)
  assert.match(gate, /v-else-if=["']!isSignedIn["']/)
  assert.match(gate, /<slot\s+v-else\s*\/>/)
  assert.match(gate, /<SignInButton/)
  assert.match(gate, /<SignUpButton/)
})

test('AuthHeaderControls exposes signed-out and signed-in Clerk controls', async () => {
  const controls = await readSource('src/components/auth/AuthHeaderControls.vue')

  assert.match(controls, /useAuth\(/)
  assert.match(controls, /isLoaded/)
  assert.match(controls, /isSignedIn/)
  assert.match(controls, /<SignInButton/)
  assert.match(controls, /<SignUpButton/)
  assert.match(controls, /<UserButton/)
  assert.match(controls, /<SignOutButton/)
})
