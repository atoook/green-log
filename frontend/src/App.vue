<template>
  <div class="min-h-svh bg-leaf-50 text-stone-900">
    <header class="border-b border-leaf-100 bg-white/80 px-4 py-3">
      <div class="mx-auto flex max-w-5xl items-center justify-between">
        <RouterLink class="text-lg font-semibold text-leaf-700" to="/plants">Green Mate</RouterLink>
        <span class="text-sm text-stone-600">植物との生活記録</span>
      </div>
    </header>
    <RouterView />
  </div>
</template>
