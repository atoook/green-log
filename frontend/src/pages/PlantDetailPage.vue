<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PlantDetail from '../components/plants/PlantDetail.vue'
import PlantEditForm from '../components/plants/PlantEditForm.vue'
import PlantImageGallery from '../components/plants/PlantImageGallery.vue'
import WateringActionButton from '../components/watering/WateringActionButton.vue'
import WateringHistoryList from '../components/watering/WateringHistoryList.vue'
import WateringStatusPanel from '../components/watering/WateringStatusPanel.vue'
import { usePlantDetail } from '../composables/usePlantDetail'
import { usePlantPhotos } from '../composables/usePlantPhotos'
import { usePlantWatering } from '../composables/usePlantWatering'
import type { PlantUpdateInput } from '../types/plant'

const route = useRoute()
const router = useRouter()
const plantId = computed(() => route.params.plantId)
const {
  plant,
  isLoading,
  isUpdating,
  error,
  updateError,
  successMessage: updateSuccessMessage,
  loadPlant,
  updatePlant,
} = usePlantDetail(plantId)
const numericPlantId = computed(() => (plant.value ? plant.value.id : null))
const {
  gallery,
  isLoading: isGalleryLoading,
  isUploading,
  isSettingCover,
  isDeleting,
  error: galleryError,
  actionError: galleryActionError,
  loadPhotos,
  addPhoto,
  setCoverPhoto,
  deletePhoto,
} = usePlantPhotos(numericPlantId, {
  onCoverImageChange: loadPlant,
})
const {
  watering,
  history,
  hasWateredToday,
  isLoading: isWateringLoading,
  isRecording,
  error: wateringError,
  recordingError,
  successMessage,
  loadWatering,
  recordWatering,
} = usePlantWatering(plantId)
const isEditing = ref(false)

const hasRecordingError = computed(() => recordingError.value !== null)
const wasWateringSuccessful = computed(() => successMessage.value !== null)
const isWateringActionDisabled = computed(() => !plant.value || hasWateredToday.value)

function backToList(): void {
  void router.push({ name: 'plants' })
}

async function recordPlantWatering(): Promise<void> {
  await recordWatering()
}

function retryWatering(): void {
  void loadWatering()
}

function startEditing(): void {
  if (plant.value) {
    isEditing.value = true
  }
}

function cancelEditing(): void {
  isEditing.value = false
}

async function savePlant(input: PlantUpdateInput): Promise<void> {
  const updated = await updatePlant(input)
  if (!updated) {
    return
  }

  isEditing.value = false
  await loadWatering()
}
</script>

<template>
  <main class="mx-auto grid max-w-3xl gap-4 p-4">
    <PlantEditForm
      v-if="plant && isEditing"
      :plant="plant"
      :is-saving="isUpdating"
      :server-error="updateError"
      @submit="savePlant"
      @cancel="cancelEditing"
    />

    <PlantDetail
      v-else
      :plant="plant"
      :is-loading="isLoading"
      :error="error"
      @back="backToList"
      @edit="startEditing"
    />

    <PlantImageGallery
      v-if="plant"
      :gallery="gallery"
      :is-loading="isGalleryLoading"
      :is-uploading="isUploading"
      :is-setting-cover="isSettingCover"
      :is-deleting="isDeleting"
      :error="galleryError"
      :action-error="galleryActionError"
      @add="addPhoto"
      @set-cover="setCoverPhoto"
      @delete="deletePhoto"
      @retry="loadPhotos"
    />

    <section
      v-if="plant"
      class="grid gap-4 rounded-lg border border-stone-200 bg-white p-4"
      aria-labelledby="plant-watering-title"
    >
      <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div class="min-w-0">
          <p class="text-sm font-semibold text-leaf-700">水やりの記録</p>
          <h2 id="plant-watering-title" class="break-words text-2xl font-semibold text-stone-950">
            {{ plant.name }}のお世話
          </h2>
        </div>

        <div class="w-full sm:w-auto sm:min-w-48">
          <WateringActionButton
            :is-recording="isRecording"
            :disabled="isWateringActionDisabled"
            :has-error="hasRecordingError"
            :already-recorded-today="hasWateredToday"
            :was-successful="wasWateringSuccessful"
            @record="recordPlantWatering"
          />
        </div>
      </div>

      <p
        v-if="updateSuccessMessage || successMessage"
        class="rounded-md border border-leaf-100 bg-leaf-50 p-3 text-sm font-semibold text-leaf-700"
        aria-live="polite"
      >
        {{ updateSuccessMessage || successMessage }}
      </p>

      <WateringStatusPanel
        :watering="watering"
        :is-loading="isWateringLoading"
        :error="wateringError"
        :watering-cycle-days="plant.wateringCycleDays"
        @retry="retryWatering"
      />

      <WateringHistoryList
        :history="history"
        :is-loading="isWateringLoading"
        :error="wateringError"
        @retry="retryWatering"
      />
    </section>
  </main>
</template>
