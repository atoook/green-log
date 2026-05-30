<script setup lang="ts">
import { SignInButton, SignOutButton, SignUpButton, UserButton, useAuth } from '@clerk/vue'

const { isLoaded, isSignedIn } = useAuth()
</script>

<template>
  <div class="flex min-h-10 items-center justify-end gap-2">
    <div v-if="!isLoaded" class="h-8 w-28 rounded-md bg-leaf-100" aria-hidden="true" />

    <template v-else-if="!isSignedIn">
      <SignInButton mode="modal">
        <button
          class="rounded-md px-3 py-2 text-sm font-semibold text-leaf-700 hover:bg-leaf-50 focus:outline-none focus:ring-2 focus:ring-leaf-500 focus:ring-offset-2"
          type="button"
        >
          ログイン
        </button>
      </SignInButton>
      <SignUpButton mode="modal">
        <button
          class="rounded-md bg-leaf-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-leaf-700 focus:outline-none focus:ring-2 focus:ring-leaf-500 focus:ring-offset-2"
          type="button"
        >
          登録
        </button>
      </SignUpButton>
    </template>

    <template v-else>
      <UserButton />
      <SignOutButton redirect-url="/plants">
        <button
          class="rounded-md border border-leaf-200 bg-white px-3 py-2 text-sm font-semibold text-leaf-700 hover:bg-leaf-50 focus:outline-none focus:ring-2 focus:ring-leaf-500 focus:ring-offset-2"
          type="button"
        >
          ログアウト
        </button>
      </SignOutButton>
    </template>
  </div>
</template>
