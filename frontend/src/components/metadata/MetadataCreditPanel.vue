<script setup lang="ts">
import type { ActorHomonymPublic, MetadataCreditPublic } from "@/client"
import { MetadataService } from "@/client"
import { useToastStore } from "@/stores/toast.store"
import { actorGradient, actorInitial } from "@/utils/actorVisual"
import { resourceImageUrl } from "@/utils/resourceImage"
import { onMounted, ref, watch } from "vue"
import { useI18n } from "vue-i18n"

const brokenPhotos = ref<Record<number, boolean>>({})

function showPhoto(credit: MetadataCreditPublic) {
  return Boolean(credit.photo) && !brokenPhotos.value[credit.actor_id]
}

function markPhotoBroken(actorId: number) {
  brokenPhotos.value = { ...brokenPhotos.value, [actorId]: true }
}

const props = defineProps<{
  metadataId: number
}>()

const emit = defineEmits<{
  changed: [credits: MetadataCreditPublic[]]
}>()

const { t } = useI18n()
const toastStore = useToastStore()

const credits = ref<MetadataCreditPublic[]>([])
const loading = ref(false)
const busyActorId = ref<number | null>(null)
const rematchFor = ref<MetadataCreditPublic | null>(null)
const homonyms = ref<ActorHomonymPublic[]>([])
const loadingHomonyms = ref(false)

async function loadCredits() {
  loading.value = true
  try {
    const { data } = await MetadataService.listMetadataCredits({ id: props.metadataId })
    credits.value = data ?? []
    emit("changed", credits.value)
  } catch (error: unknown) {
    toastStore.error(extractError(error, t("components.metadata.credits.loadFailed")))
  } finally {
    loading.value = false
  }
}

function extractError(error: unknown, fallback: string) {
  const detail =
    (error as any)?.response?.data?.detail
    ?? (error as any)?.body?.detail
    ?? (error as any)?.detail
    ?? (error as any)?.message
  return typeof detail === "string" && detail.trim() ? detail : fallback
}

async function openRematch(credit: MetadataCreditPublic) {
  rematchFor.value = credit
  loadingHomonyms.value = true
  homonyms.value = []
  try {
    const { data } = await MetadataService.listActorHomonyms({
      name: credit.actor_name || credit.credit_name,
    })
    homonyms.value = data ?? []
  } catch (error: unknown) {
    toastStore.error(extractError(error, t("components.metadata.credits.loadHomonymsFailed")))
    rematchFor.value = null
  } finally {
    loadingHomonyms.value = false
  }
}

async function rematchTo(targetId: number) {
  const credit = rematchFor.value
  if (!credit || targetId === credit.actor_id) {
    rematchFor.value = null
    return
  }
  busyActorId.value = credit.actor_id
  try {
    const { data } = await MetadataService.rematchMetadataCredit({
      id: props.metadataId,
      actor_id: credit.actor_id,
      creditRematchRequest: { to_actor_id: targetId },
    })
    credits.value = data ?? []
    emit("changed", credits.value)
    rematchFor.value = null
    toastStore.success(t("components.metadata.credits.rematchSuccess"))
  } catch (error: unknown) {
    toastStore.error(extractError(error, t("components.metadata.credits.rematchFailed")))
  } finally {
    busyActorId.value = null
  }
}

async function splitCredit(credit: MetadataCreditPublic) {
  busyActorId.value = credit.actor_id
  try {
    const { data } = await MetadataService.splitMetadataCredit({
      id: props.metadataId,
      actor_id: credit.actor_id,
      creditSplitRequest: { name: credit.actor_name || credit.credit_name },
    })
    credits.value = data?.credits ?? []
    emit("changed", credits.value)
    toastStore.success(t("components.metadata.credits.splitSuccess"))
  } catch (error: unknown) {
    toastStore.error(extractError(error, t("components.metadata.credits.splitFailed")))
  } finally {
    busyActorId.value = null
  }
}

watch(
  () => props.metadataId,
  () => {
    if (props.metadataId) loadCredits()
  },
)

onMounted(() => {
  if (props.metadataId) loadCredits()
})

defineExpose({ reload: loadCredits })
</script>

<template>
  <div class="credit-panel">
    <VProgressLinear v-if="loading" indeterminate class="mb-2" />
    <div v-if="!loading && !credits.length" class="text-medium-emphasis text-body-2">
      {{ t('components.metadata.credits.empty') }}
    </div>
    <div
      v-for="credit in credits"
      :key="`${credit.actor_id}-${credit.sort}`"
      class="credit-row"
    >
      <div class="credit-main">
        <div
          class="credit-avatar"
          :style="{ background: actorGradient(credit.actor_name || credit.credit_name || '') }"
        >
          <span>{{ actorInitial(credit.actor_name || credit.credit_name || '') }}</span>
          <img
            v-if="showPhoto(credit)"
            :src="resourceImageUrl(credit.photo || '')"
            :alt="credit.actor_name"
            @error="markPhotoBroken(credit.actor_id)"
          />
        </div>
        <div class="credit-text">
          <span class="credit-name">{{ credit.actor_name }}</span>
          <span
            v-if="credit.credit_name && credit.credit_name !== credit.actor_name"
            class="credit-scraped"
          >
            {{ credit.credit_name }}
          </span>
          <span
            v-if="(credit.homonym_count ?? 1) > 1"
            class="credit-homonym"
          >
            {{ t('components.metadata.credits.homonymCount', { count: credit.homonym_count }) }}
          </span>
        </div>
      </div>
      <div class="credit-actions">
        <VBtn
          v-if="(credit.homonym_count ?? 1) > 1"
          size="small"
          variant="text"
          :disabled="busyActorId != null"
          :loading="busyActorId === credit.actor_id && rematchFor?.actor_id === credit.actor_id"
          @click="openRematch(credit)"
        >
          {{ t('components.metadata.credits.rematch') }}
        </VBtn>
        <VBtn
          size="small"
          variant="text"
          :disabled="busyActorId != null"
          :loading="busyActorId === credit.actor_id && rematchFor == null"
          @click="splitCredit(credit)"
        >
          {{ t('components.metadata.credits.split') }}
        </VBtn>
      </div>
    </div>

    <VDialog :model-value="rematchFor != null" max-width="420" @update:model-value="(v) => { if (!v) rematchFor = null }">
      <VCard v-if="rematchFor">
        <VCardTitle>{{ t('components.metadata.credits.rematchTitle') }}</VCardTitle>
        <VCardText>
          <VProgressLinear v-if="loadingHomonyms" indeterminate class="mb-3" />
          <div
            v-for="item in homonyms"
            :key="item.id"
            class="homonym-row"
            :class="{ 'homonym-row--current': item.id === rematchFor.actor_id }"
          >
            <div class="homonym-info">
              <div
                class="homonym-photo"
                :style="{ background: actorGradient(item.name) }"
              >
                <span>{{ actorInitial(item.name) }}</span>
                <img
                  v-if="item.photo && !brokenPhotos[item.id]"
                  :src="resourceImageUrl(item.photo)"
                  alt=""
                  @error="markPhotoBroken(item.id)"
                />
              </div>
              <div>
                <div>{{ item.name }}</div>
                <div class="text-caption text-medium-emphasis">
                  #{{ item.id }} · {{ t('components.metadata.credits.workCount', { count: item.count ?? 0 }) }}
                </div>
              </div>
            </div>
            <VBtn
              size="small"
              variant="tonal"
              :disabled="item.id === rematchFor.actor_id || busyActorId != null"
              @click="rematchTo(item.id)"
            >
              {{ item.id === rematchFor.actor_id
                ? t('components.metadata.credits.current')
                : t('components.metadata.credits.select') }}
            </VBtn>
          </div>
        </VCardText>
        <VCardActions>
          <VSpacer />
          <VBtn variant="text" @click="rematchFor = null">
            {{ t('components.metadata.form.cancel') }}
          </VBtn>
        </VCardActions>
      </VCard>
    </VDialog>
  </div>
</template>

<style scoped>
.credit-panel {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  padding: 4px 0;
}

.credit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 40px;
  padding: 4px 8px 4px 12px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.credit-row:last-child {
  border-bottom: 0;
}

.credit-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.credit-avatar {
  position: relative;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}

.credit-avatar img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.credit-text {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.credit-name {
  font-weight: 500;
}

.credit-scraped {
  color: rgba(var(--v-theme-on-surface), 0.55);
  font-size: 0.85rem;
}

.credit-homonym {
  color: rgb(var(--v-theme-warning));
  font-size: 0.8rem;
}

.credit-actions {
  display: flex;
  flex-shrink: 0;
  gap: 2px;
}

.homonym-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.homonym-row:last-child {
  border-bottom: 0;
}

.homonym-row--current {
  opacity: 0.72;
}

.homonym-info {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.homonym-photo {
  position: relative;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  flex-shrink: 0;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.homonym-photo img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
