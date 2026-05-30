<script setup lang="ts">
import { SignInButton, SignUpButton, useAuth } from '@clerk/vue'

defineProps<{
  requiresAuth?: boolean
}>()

const { isLoaded, isSignedIn } = useAuth()
</script>

<template>
  <slot v-if="!requiresAuth" />
  <template v-else>
    <section
      v-if="!isLoaded"
      class="mx-auto flex min-h-[60vh] max-w-5xl items-center justify-center px-4 py-16"
      aria-live="polite"
    >
      <div class="max-w-md rounded-lg border border-leaf-100 bg-white p-6 text-center shadow-sm">
        <p class="text-sm font-medium text-leaf-700">認証状態を確認しています</p>
        <p class="mt-2 text-sm text-stone-600">植物の記録は確認が終わるまで表示しません。</p>
      </div>
    </section>

    <section
      v-else-if="!isSignedIn"
      class="mx-auto flex min-h-[60vh] max-w-5xl items-center justify-center px-4 py-16"
    >
      <div class="max-w-lg rounded-lg border border-leaf-100 bg-white p-6 text-center shadow-sm">
        <p class="text-lg font-semibold text-stone-900">植物の記録を見るにはログインしてください</p>
        <p class="mt-2 text-sm leading-6 text-stone-600">
          Green Mate はあなたの植物記録をアカウントごとに分けて保管します。
        </p>
        <div class="mt-6 flex flex-wrap justify-center gap-3">
          <SignInButton mode="modal">
            <button
              class="rounded-md bg-leaf-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-leaf-700 focus:outline-none focus:ring-2 focus:ring-leaf-500 focus:ring-offset-2"
              type="button"
            >
              ログイン
            </button>
          </SignInButton>
          <SignUpButton mode="modal">
            <button
              class="rounded-md border border-leaf-200 bg-white px-4 py-2 text-sm font-semibold text-leaf-700 hover:bg-leaf-50 focus:outline-none focus:ring-2 focus:ring-leaf-500 focus:ring-offset-2"
              type="button"
            >
              登録
            </button>
          </SignUpButton>
        </div>
      </div>
    </section>

    <slot v-else />
  </template>
</template>
