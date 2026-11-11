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
    <div v-if="!loading && !credits.length" class="credit-empty">
      {{ t('components.metadata.credits.empty') }}
    </div>
    <div v-else class="credit-grid">
      <article
        v-for="credit in credits"
        :key="`${credit.actor_id}-${credit.sort}`"
        class="credit-card"
        :class="{ 'credit-card--busy': busyActorId === credit.actor_id }"
      >
        <div
          class="credit-avatar"
          :style="{ background: actorGradient(credit.actor_name || credit.credit_name || '') }"
        >
          <span>{{ actorInitial(credit.actor_name || credit.credit_name || '') }}</span>
          <img
            v-if="showPhoto(credit)"
            :src="resourceImageUrl(credit.photo || '', { actor: credit.actor_name })"
            :alt="credit.actor_name"
            @error="markPhotoBroken(credit.actor_id)"
          />
          <div class="credit-card-actions">
            <VBtn
              v-if="(credit.homonym_count ?? 1) > 1"
              icon
              size="small"
              variant="flat"
              class="credit-action-btn"
              :title="t('components.metadata.credits.rematch')"
              :disabled="busyActorId != null"
              :loading="busyActorId === credit.actor_id && rematchFor?.actor_id === credit.actor_id"
              @click.stop="openRematch(credit)"
            >
              <VIcon icon="bx-transfer-alt" size="20" />
            </VBtn>
            <VBtn
              icon
              size="small"
              variant="flat"
              class="credit-action-btn"
              :title="t('components.metadata.credits.split')"
              :disabled="busyActorId != null"
              :loading="busyActorId === credit.actor_id && rematchFor == null"
              @click.stop="splitCredit(credit)"
            >
              <VIcon icon="bx-user-plus" size="20" />
            </VBtn>
          </div>
        </div>
        <div class="credit-meta">
          <p class="credit-name" :title="credit.actor_name">{{ credit.actor_name }}</p>
          <p
            v-if="credit.credit_name && credit.credit_name !== credit.actor_name"
            class="credit-scraped"
            :title="credit.credit_name"
          >
            {{ credit.credit_name }}
          </p>
          <p
            v-if="(credit.homonym_count ?? 1) > 1"
            class="credit-homonym"
          >
            {{ t('components.metadata.credits.homonymCount', { count: credit.homonym_count }) }}
          </p>
        </div>
      </article>
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
                  :src="resourceImageUrl(item.photo, { actor: item.name })"
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
  border-radius: 10px;
  padding: 12px;
}

.credit-empty {
  color: rgba(var(--v-theme-on-surface), 0.55);
  font-size: 0.875rem;
}

.credit-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(92px, 1fr));
  gap: 12px 10px;
}

.credit-card {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  min-width: 0;
}

.credit-card--busy {
  opacity: 0.72;
}

.credit-avatar {
  position: relative;
  width: 100%;
  aspect-ratio: 2 / 3;
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 600;
  color: #fff;
  background: #2a2a2a;
}

.credit-avatar img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top;
}

.credit-card-actions {
  position: absolute;
  right: 6px;
  bottom: 6px;
  z-index: 1;
  display: flex;
  gap: 4px;
  opacity: 0;
  transform: translateY(2px);
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.credit-card:hover .credit-card-actions,
.credit-card:focus-within .credit-card-actions {
  opacity: 1;
  transform: translateY(0);
}

.credit-action-btn {
  background: rgba(0, 0, 0, 0.68) !important;
  color: #fff !important;
  width: 34px !important;
  height: 34px !important;
}

.credit-meta {
  margin-top: 6px;
  min-width: 0;
  text-align: center;
}

.credit-name,
.credit-scraped {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.credit-name {
  font-size: 0.82rem;
  font-weight: 600;
  line-height: 1.25;
}

.credit-scraped {
  margin-top: 2px;
  color: rgba(var(--v-theme-on-surface), 0.5);
  font-size: 0.72rem;
}

.credit-homonym {
  margin: 3px 0 0;
  color: rgb(var(--v-theme-warning));
  font-size: 0.7rem;
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
  width: 40px;
  aspect-ratio: 2 / 3;
  border-radius: 8px;
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
  object-position: center top;
}

@media (hover: none) {
  .credit-card-actions {
    opacity: 1;
    transform: none;
  }
}
</style>
