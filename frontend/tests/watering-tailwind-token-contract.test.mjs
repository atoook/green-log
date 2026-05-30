import assert from 'node:assert/strict'
import { readdir, readFile } from 'node:fs/promises'
import { test } from 'node:test'
import tailwindConfig from '../tailwind.config.js'

const wateringComponentsUrl = new URL('../src/components/watering/', import.meta.url)
const customPalettes = ['leaf', 'soil']

async function readWateringComponentSources() {
  const files = await readdir(wateringComponentsUrl)
  return Promise.all(
    files
      .filter((file) => file.endsWith('.vue'))
      .map(async (file) => ({
        file,
        source: await readFile(new URL(file, wateringComponentsUrl), 'utf8'),
      })),
  )
}

test('watering components only use configured custom Tailwind color tokens', async () => {
  const colors = tailwindConfig.theme?.extend?.colors ?? {}
  const configuredShades = Object.fromEntries(
    customPalettes.map((palette) => [palette, new Set(Object.keys(colors[palette] ?? {}))]),
  )
  const sources = await readWateringComponentSources()

  const violations = sources.flatMap(({ file, source }) => {
    return Array.from(source.matchAll(/\b(leaf|soil)-(\d+)\b/g))
      .filter((match) => !configuredShades[match[1]].has(match[2]))
      .map((match) => `${file}: ${match[0]}`)
  })

  assert.deepEqual(violations, [])
})
