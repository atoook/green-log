import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'

const readProjectFile = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8')

test('frontend auth and api TypeScript contract explicitly rejects implicit any', async () => {
  const tsconfig = await readProjectFile('tsconfig.app.json')

  assert.match(tsconfig, /"noImplicitAny"\s*:\s*true/)
})

test('frontend auth and api source do not introduce explicit any', async () => {
  const sourcePaths = [
    'src/api/client.ts',
    'src/api/plants.ts',
    'src/api/watering.ts',
    'src/composables/useAuthenticatedApi.ts',
    'src/composables/usePlants.ts',
    'src/composables/usePlantDetail.ts',
    'src/composables/useTodayCare.ts',
    'src/composables/usePlantWatering.ts',
    'src/types/api.ts',
    'src/types/plant.ts',
    'src/types/watering.ts',
  ]

  const explicitAnyPattern = /(?<![A-Za-z0-9_$])any(?![A-Za-z0-9_$])/

  for (const sourcePath of sourcePaths) {
    const source = await readProjectFile(sourcePath)
    assert.doesNotMatch(source, explicitAnyPattern, `${sourcePath} must not contain explicit any`)
  }
})

test('signed-in plant create keeps the existing detail navigation contract', async () => {
  const page = await readProjectFile('src/pages/PlantsPage.vue')

  assert.match(page, /const\s+created\s*=\s*await\s+addPlant\(input\)/)
  assert.match(
    page,
    /if\s*\(\s*created\s*\)\s*\{[\s\S]*router\.push\(\s*\{\s*name:\s*['"]plant-detail['"][\s\S]*plantId:\s*String\(created\.id\)/,
  )
  assert.match(
    page,
    /<PlantList[\s\S]*:plants="plants"[\s\S]*:error="error\?\.type\s*===\s*'validation'\s*\?\s*null\s*:\s*error"[\s\S]*@select="selectPlant"/,
  )
})

test('frontend PlantCreateInput mirrors backend public create schema without owner fields', async () => {
  const [frontendTypes, backendSchema] = await Promise.all([
    readProjectFile('src/types/plant.ts'),
    readFile(new URL('../../backend/app/schemas/plant.py', import.meta.url), 'utf8'),
  ])

  const backendCreateFields = extractBackendCreateFields(backendSchema)
  const frontendCreateFields = extractTypescriptInterfaceFields(frontendTypes, 'PlantCreateInput')
  const backendReadFields = new Set([
    ...backendCreateFields.keys(),
    ...extractBackendReadFields(backendSchema).keys(),
  ])
  const frontendReadFields = extractTypescriptInterfaceFields(frontendTypes, 'Plant')
  const forbiddenFields = /\b(owner|ownerUserId|owner_user_id|userId|clerkUserId)\b/

  assert.deepEqual([...frontendCreateFields.keys()], [...backendCreateFields.keys()])
  assert.deepEqual([...frontendReadFields.keys()].sort(), [...backendReadFields].sort())
  assert.doesNotMatch(frontendTypes, forbiddenFields)
  assert.doesNotMatch(backendSchema, /class Plant(Create|Read)[\s\S]*owner_user_id/)

  for (const [fieldName, backendField] of backendCreateFields) {
    assert.equal(
      frontendCreateFields.get(fieldName)?.required,
      backendField.required,
      `${fieldName} requiredness must match backend PlantCreate`,
    )
  }
})

function extractBackendCreateFields(source) {
  const block = source.match(/class PlantCreate\(SQLModel\):(?<body>[\s\S]*?)\n\nclass PlantRead/)
    ?.groups.body
  assert.ok(block, 'PlantCreate schema block must be present')

  const fields = new Map()
  for (const line of block.split('\n')) {
    const match = line.match(/^\s{4}(?<name>[a-z_]+):(?<definition>.+)$/)
    if (!match || match.groups.name === 'model_config') {
      continue
    }

    fields.set(toCamel(match.groups.name), {
      required: !match.groups.definition.includes('='),
    })
  }
  return fields
}

function extractBackendReadFields(source) {
  const block = source.match(/class PlantRead\(PlantCreate\):(?<body>[\s\S]*?)(\n\n|$)/)
    ?.groups.body
  assert.ok(block, 'PlantRead schema block must be present')

  const fields = new Map()
  for (const line of block.split('\n')) {
    const match = line.match(/^\s{4}(?<name>[a-z_]+):/)
    if (!match) {
      continue
    }

    fields.set(toCamel(match.groups.name), { required: true })
  }
  return fields
}

function extractTypescriptInterfaceFields(source, interfaceName) {
  const block = source.match(
    new RegExp(`export interface ${interfaceName} \\{(?<body>[\\s\\S]*?)\\n\\}`),
  )?.groups.body
  assert.ok(block, `${interfaceName} interface must be present`)

  const fields = new Map()
  for (const line of block.split('\n')) {
    const match = line.match(/^\s{2}(?<name>[A-Za-z][A-Za-z0-9]*)(?<optional>\?)?:/)
    if (!match) {
      continue
    }

    fields.set(match.groups.name, {
      required: match.groups.optional !== '?',
    })
  }
  return fields
}

function toCamel(value) {
  return value.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())
}
