<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PlantDetail from '../components/plants/PlantDetail.vue'
import { usePlantDetail } from '../composables/usePlantDetail'

const route = useRoute()
const router = useRouter()
const plantId = computed(() => route.params.plantId)
const { plant, isLoading, error } = usePlantDetail(plantId)

function backToList(): void {
  void router.push({ name: 'plants' })
}
</script>

<template>
  <main class="mx-auto max-w-3xl p-4">
    <PlantDetail :plant="plant" :is-loading="isLoading" :error="error" @back="backToList" />
  </main>
</template>
