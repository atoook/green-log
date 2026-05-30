import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { compileScript, parse } from '@vue/compiler-sfc'
import * as ts from 'typescript'

const readSource = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8')

const cloneWatchValue = (value) => (Array.isArray(value) ? [...value] : value)

const watchValueChanged = (next, previous) => {
  if (!Array.isArray(next) || !Array.isArray(previous)) {
    return !Object.is(next, previous)
  }

  return next.length !== previous.length || next.some((value, index) => !Object.is(value, previous[index]))
}

const loadComponentHarness = (source) => {
  const { descriptor } = parse(source)
  const compiled = compileScript(descriptor, { id: 'watering-action-button-test' })
  const output = ts.transpileModule(compiled.content, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText
  const watchers = []
  const vueStubs = {
    computed: (getter) => ({
      get value() {
        return getter()
      },
    }),
    defineComponent: (component) => component,
    nextTick: () => Promise.resolve(),
    ref: (value) => ({ value }),
    watch: (sourceGetter, callback) => {
      watchers.push({
        callback,
        lastValue: cloneWatchValue(sourceGetter()),
        sourceGetter,
      })
    },
  }
  const module = { exports: {} }
  const evaluate = new Function('require', 'module', 'exports', output)

  evaluate(
    (id) => {
      if (id === 'vue') {
        return vueStubs
      }
      throw new Error(`Unexpected import in component harness: ${id}`)
    },
    module,
    module.exports,
  )

  return {
    component: module.exports.default,
    flushWatchers() {
      for (const watcher of watchers) {
        const previous = watcher.lastValue
        const next = cloneWatchValue(watcher.sourceGetter())

        if (!watchValueChanged(next, previous)) {
          continue
        }

        watcher.lastValue = cloneWatchValue(next)
        watcher.callback(next, previous)
      }
    },
  }
}

test('WateringActionButton exposes only presentational record action props and emit', async () => {
  const source = await readSource('src/components/watering/WateringActionButton.vue')

  assert.match(source, /defineProps<\{[\s\S]*isRecording:\s*boolean/)
  assert.match(source, /disabled\?:\s*boolean/)
  assert.match(source, /hasError\?:\s*boolean/)
  assert.match(source, /wasSuccessful\?:\s*boolean/)
  assert.match(source, /defineEmits<\{[\s\S]*record:\s*\[\]/)
  assert.doesNotMatch(source, /fetch\(|createWateringApiClient|useAuthenticatedApi|Clerk|useRouter|useRoute/)
})

test('WateringActionButton guards clicks before emitting a single record event', async () => {
  const source = await readSource('src/components/watering/WateringActionButton.vue')
  const { component, flushWatchers } = loadComponentHarness(source)
  const props = {
    disabled: false,
    hasError: false,
    isRecording: false,
    wasSuccessful: false,
  }
  const emitted = []
  const bindings = component.setup(props, {
    emit: (event) => emitted.push(event),
    expose: () => {},
  })

  bindings.handleClick()
  await Promise.resolve()
  bindings.handleClick()

  assert.deepEqual(emitted, ['record'])
  assert.equal(bindings.localPending.value, true)

  props.isRecording = true
  flushWatchers()

  assert.equal(bindings.localPending.value, false)
  assert.equal(bindings.isButtonDisabled.value, true)

  props.isRecording = false
  flushWatchers()
  bindings.handleClick()
  props.wasSuccessful = true
  flushWatchers()

  assert.match(source, /const\s+localPending\s*=\s*ref\(false\)/)
  assert.match(
    source,
    /const\s+isButtonDisabled\s*=\s*computed\(\(\)\s*=>\s*props\.disabled\s*\|\|\s*props\.isRecording\s*\|\|\s*localPending\.value\s*\)/,
  )
  assert.match(
    source,
    /function\s+handleClick\(\):\s*void\s*\{[\s\S]*if\s*\(isButtonDisabled\.value\)\s*\{[\s\S]*return[\s\S]*localPending\.value\s*=\s*true[\s\S]*emit\(['"]record['"]\)/,
  )
  assert.deepEqual(emitted, ['record', 'record'])
  assert.equal(bindings.localPending.value, false)
  assert.doesNotMatch(source, /nextTick/)
  assert.match(source, /watch\(\s*\(\)\s*=>\s*props\.isRecording[\s\S]*if\s*\(isRecording\)[\s\S]*localPending\.value\s*=\s*false/)
  assert.match(source, /props\.wasSuccessful[\s\S]*props\.hasError[\s\S]*props\.disabled/)
  assert.match(source, /:disabled=["']isButtonDisabled["']/)
  assert.match(source, /@click=["']handleClick["']/)
})

test('WateringActionButton renders normal, pending, success, failure, and disabled states with MVP copy', async () => {
  const source = await readSource('src/components/watering/WateringActionButton.vue')

  assert.match(source, /水やりを記録する/)
  assert.match(source, /記録しています/)
  assert.match(source, /記録しました/)
  assert.match(source, /もう一度記録する/)
  assert.match(source, /記録できませんでした/)
  assert.match(source, /min-h-11/)
  assert.match(source, /aria-live=["']polite["']/)
  assert.doesNotMatch(source, /タスク|管理|通知|スキップ|延期|お世話種別/)
})
