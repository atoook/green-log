<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AuthGate from './components/auth/AuthGate.vue'
import AuthHeaderControls from './components/auth/AuthHeaderControls.vue'

const route = useRoute()
const requiresAuth = computed(() => route.meta.requiresAuth === true)
</script>

<template>
  <div class="min-h-svh bg-leaf-50 text-stone-900">
    <header class="border-b border-leaf-100 bg-white/80 px-4 py-3">
      <div class="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3">
        <div class="flex min-w-0 flex-wrap items-center gap-3">
          <RouterLink class="shrink-0 text-lg font-semibold text-leaf-700" to="/plants">
            Green Mate
          </RouterLink>
          <nav aria-label="主要ナビゲーション" class="flex items-center gap-1 text-sm font-semibold">
            <RouterLink
              class="rounded-md px-2.5 py-2 text-stone-600 hover:bg-leaf-50 hover:text-leaf-700"
              active-class="bg-leaf-50 text-leaf-700"
              to="/care/today"
            >
              今日のお世話
            </RouterLink>
            <RouterLink
              class="rounded-md px-2.5 py-2 text-stone-600 hover:bg-leaf-50 hover:text-leaf-700"
              active-class="bg-leaf-50 text-leaf-700"
              to="/plants"
            >
              植物一覧
            </RouterLink>
          </nav>
        </div>
        <div class="flex items-center gap-3">
          <span class="hidden text-sm text-stone-600 sm:inline">植物との生活記録</span>
          <AuthHeaderControls />
        </div>
      </div>
    </header>
    <AuthGate :requires-auth="requiresAuth">
      <RouterView />
    </AuthGate>
  </div>
</template>
