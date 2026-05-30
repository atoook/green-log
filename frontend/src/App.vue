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
      <div class="mx-auto flex max-w-5xl items-center justify-between gap-4">
        <RouterLink class="shrink-0 text-lg font-semibold text-leaf-700" to="/plants">
          Green Mate
        </RouterLink>
        <div class="flex items-center gap-4">
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
