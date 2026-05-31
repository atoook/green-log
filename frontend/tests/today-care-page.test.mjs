import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'

const readSource = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8')

const outOfScopeCareUi =
  /通知|スキップ|延期|カレンダー|ダッシュボード|タスク|管理|Notification|permission|skip|defer|calendar|dashboard/i

test('TodayCarePage composes useUpcomingCare and UpcomingCareList for the in-page watering flow', async () => {
  const source = await readSource('src/pages/TodayCarePage.vue')

  assert.match(source, /import\s+\{\s*ref\s*\}\s+from\s+['"]vue['"]/)
  assert.match(
    source,
    /import\s+UpcomingCareList\s+from\s+['"]\.\.\/components\/watering\/UpcomingCareList\.vue['"]/,
  )
  assert.match(source, /import\s+\{\s*useUpcomingCare\s*\}\s+from\s+['"]\.\.\/composables\/useUpcomingCare['"]/)
  assert.match(
    source,
    /const\s+\{[\s\S]*sections[\s\S]*isLoading[\s\S]*error[\s\S]*recordingError[\s\S]*isRecordingByPlantId[\s\S]*successMessage[\s\S]*loadUpcomingCare[\s\S]*recordWatering[\s\S]*\}\s*=\s*useUpcomingCare\(\)/,
  )
  assert.match(source, /const\s+successfulPlantId\s*=\s*ref<number\s*\|\s*null>\(null\)/)
  assert.match(
    source,
    /async\s+function\s+recordUpcomingCare\(plantId:\s*number\):\s*Promise<void>\s*\{[\s\S]*const\s+result\s*=\s*await\s+recordWatering\(plantId\)[\s\S]*successfulPlantId\.value\s*=\s*result\?\.record\.plantId\s*\?\?\s*null/,
  )
  assert.match(
    source,
    /function\s+retryUpcomingCare\(\):\s*void\s*\{[\s\S]*successfulPlantId\.value\s*=\s*null[\s\S]*void\s+loadUpcomingCare\(\)/,
  )
  assert.match(
    source,
    /<UpcomingCareList[\s\S]*:sections=["']sections["'][\s\S]*:is-loading=["']isLoading["'][\s\S]*:error=["']error["'][\s\S]*:recording-error=["']recordingError["'][\s\S]*:is-recording-by-plant-id=["']isRecordingByPlantId["'][\s\S]*:successful-plant-id=["']successfulPlantId["'][\s\S]*@record=["']recordUpcomingCare["'][\s\S]*@retry=["']retryUpcomingCare["']/,
  )
})

test('TodayCarePage stays presentational and uses MVP wording without direct auth or API access', async () => {
  const source = await readSource('src/pages/TodayCarePage.vue')

  assert.match(source, /<main\s+class=["']mx-auto grid max-w-5xl gap-4 p-4/)
  assert.match(source, /<h1[\s\S]*今日のお世話/)
  assert.match(source, /successMessage/)
  assert.match(source, /aria-live=["']polite["']/)
  assert.doesNotMatch(source, /fetch\(|createWateringApiClient|useAuthenticatedApi|Clerk|Authorization|Bearer/)
  assert.doesNotMatch(source, outOfScopeCareUi)
})

test('today care route is protected and reachable from the compact app header navigation', async () => {
  const [router, app] = await Promise.all([
    readSource('src/router/index.ts'),
    readSource('src/App.vue'),
  ])

  assert.match(router, /import\s+TodayCarePage\s+from\s+['"]\.\.\/pages\/TodayCarePage\.vue['"]/)
  assert.match(
    router,
    /path:\s*['"]\/care\/today['"][\s\S]*name:\s*['"]today-care['"][\s\S]*component:\s*TodayCarePage[\s\S]*meta:\s*\{[^}]*requiresAuth:\s*true/,
  )

  assert.match(app, /<nav[\s\S]*aria-label=["']主要ナビゲーション["'][\s\S]*<\/nav>/)
  assert.match(app, /<RouterLink[\s\S]*to=["']\/care\/today["'][\s\S]*今日のお世話[\s\S]*<\/RouterLink>/)
  assert.match(app, /<RouterLink[\s\S]*to=["']\/plants["'][\s\S]*植物一覧[\s\S]*<\/RouterLink>/)
  assert.match(app, /<AuthGate[\s\S]*<RouterView\s*\/>[\s\S]*<\/AuthGate>/)
  assert.doesNotMatch(app, outOfScopeCareUi)
})
