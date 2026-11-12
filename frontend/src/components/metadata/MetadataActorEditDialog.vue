<script setup lang="ts">
import type { ActorPublic, ActorSummary } from "@/client"
import { MetadataService, ResourceService } from "@/client"
import { useToastStore } from "@/stores/toast.store"
import { actorGradient, actorInitial } from "@/utils/actorVisual"
import { resourceImageUrl } from "@/utils/resourceImage"
import { computed, ref, watch } from "vue"
import { useI18n } from "vue-i18n"

const props = defineProps<{
  modelValue: boolean
  actor: ActorSummary | null
}>()

const emit = defineEmits<{
  "update:modelValue": [value: boolean]
  saved: [actor: ActorPublic]
}>()

const { t } = useI18n()
const toastStore = useToastStore()

const open = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit("update:modelValue", value),
})

const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const name = ref("")
const photo = ref("")
const photoStamp = ref(0)
const photoBroken = ref(false)
const aliasInput = ref("")
const aliases = ref<string[]>([])
const editingAlias = ref<string | null>(null)
const editingAliasDraft = ref("")
const errorMessage = ref("")
const fileInput = ref<HTMLInputElement | null>(null)
let loadSeq = 0
let formDirty = false
let seedSnapshot = { name: "", photo: "", aliases: [] as string[] }

const primaryName = computed(() => name.value.trim())
const photoPreviewUrl = computed(() => {
  const path = photo.value.trim()
  if (!path || photoBroken.value) return ""
  const actorName = primaryName.value || props.actor?.name || ""
  const base = resourceImageUrl(path, { actor: actorName || undefined })
  if (!base) return ""
  if (!photoStamp.value) return base
  return `${base}${base.includes("?") ? "&" : "?"}v=${photoStamp.value}`
})

function aliasListWithoutPrimary(list: string[], primary: string) {
  const key = primary.toLowerCase()
  return list.filter((item) => item.trim().toLowerCase() !== key)
}

function sameAliasList(a: string[], b: string[]) {
  if (a.length !== b.length) return false
  return a.every((item, index) => item === b[index])
}

function isFormUnchangedFromSeed() {
  return (
    name.value === seedSnapshot.name
    && photo.value === seedSnapshot.photo
    && sameAliasList(aliases.value, seedSnapshot.aliases)
    && !formDirty
  )
}

function seedFromProps() {
  const actor = props.actor
  name.value = actor?.name || ""
  photo.value = actor?.photo || ""
  photoStamp.value = 0
  photoBroken.value = false
  aliases.value = [...(actor?.aliases ?? [])]
  aliasInput.value = ""
  editingAlias.value = null
  editingAliasDraft.value = ""
  errorMessage.value = ""
  formDirty = false
  seedSnapshot = {
    name: name.value,
    photo: photo.value,
    aliases: [...aliases.value],
  }
}

async function loadActor() {
  const actorId = props.actor?.id
  if (!actorId) return
  const seq = ++loadSeq
  const hasSeed = Boolean(props.actor?.name)
  // 已有列表数据时不锁表单，仅后台刷新；避免请求挂起时弹窗一直不可用
  loading.value = !hasSeed
  errorMessage.value = ""
  try {
    const { data } = await MetadataService.getActor({ actor_id: actorId })
    if (seq !== loadSeq) return
    // 用户已改过表单时不要用晚到的详情覆盖正在编辑的内容
    if (!isFormUnchangedFromSeed()) return
    name.value = data.name
    photo.value = data.photo || ""
    photoBroken.value = false
    aliases.value = aliasListWithoutPrimary(
      (data.aliases ?? []).map((item) => item.name),
      data.name,
    )
    seedSnapshot = {
      name: name.value,
      photo: photo.value,
      aliases: [...aliases.value],
    }
  } catch (error: unknown) {
    if (seq !== loadSeq) return
    if (!hasSeed) {
      errorMessage.value = extractError(error, t("components.metadata.actorEdit.loadFailed"))
    }
  } finally {
    if (seq === loadSeq) loading.value = false
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

watch(
  () => [props.modelValue, props.actor?.id] as const,
  ([visible]) => {
    if (visible) {
      seedFromProps()
      loadActor()
      return
    }
    loadSeq += 1
    loading.value = false
    saving.value = false
    uploading.value = false
  },
)

watch(photo, () => {
  photoBroken.value = false
})

function markDirty() {
  formDirty = true
}

function addAlias() {
  const text = aliasInput.value.trim()
  if (!text) return
  const key = text.toLowerCase()
  if (key === primaryName.value.toLowerCase()) {
    aliasInput.value = ""
    return
  }
  if (aliases.value.some((item) => item.toLowerCase() === key)) {
    aliasInput.value = ""
    return
  }
  aliases.value = [...aliases.value, text]
  aliasInput.value = ""
  markDirty()
}

function removeAlias(target: string) {
  aliases.value = aliases.value.filter((item) => item !== target)
  markDirty()
  if (editingAlias.value === target) {
    cancelEditAlias()
  }
}

function startEditAlias(target: string) {
  editingAlias.value = target
  editingAliasDraft.value = target
}

function cancelEditAlias() {
  editingAlias.value = null
  editingAliasDraft.value = ""
}

function confirmEditAlias() {
  const original = editingAlias.value
  if (original == null) return
  const text = editingAliasDraft.value.trim()
  if (!text) return
  const key = text.toLowerCase()
  if (key === primaryName.value.toLowerCase()) {
    cancelEditAlias()
    return
  }
  if (
    aliases.value.some(
      (item) => item !== original && item.toLowerCase() === key,
    )
  ) {
    cancelEditAlias()
    return
  }
  aliases.value = aliases.value.map((item) => (item === original ? text : item))
  markDirty()
  cancelEditAlias()
}

function selectPhoto() {
  fileInput.value?.click()
}

async function handlePhotoUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  if (!file.type.startsWith("image/")) {
    errorMessage.value = t("components.metadata.form.imageTypeError")
    target.value = ""
    return
  }

  uploading.value = true
  errorMessage.value = ""
  try {
    const actorName = primaryName.value || props.actor?.name || ""
    const { data: response } = await ResourceService.uploadImage({
      bodyResourceUploadImage: { file },
      actor: actorName || undefined,
    })
    let path = ""
    if (typeof response === "object" && response !== null && "message" in response) {
      path = String(response.message || "")
    }
    if (!path) {
      errorMessage.value = t("components.metadata.form.uploadSuccess")
      return
    }
    photo.value = path
    photoStamp.value = Date.now()
    photoBroken.value = false
    markDirty()
  } catch (error: unknown) {
    errorMessage.value = extractError(error, t("components.metadata.form.uploadError"))
  } finally {
    uploading.value = false
    target.value = ""
  }
}

async function save() {
  const actorId = props.actor?.id
  if (!actorId) return
  if (editingAlias.value != null) {
    confirmEditAlias()
  }
  const nextName = primaryName.value
  if (!nextName) {
    errorMessage.value = t("components.metadata.actorEdit.nameRequired")
    return
  }
  saving.value = true
  errorMessage.value = ""
  try {
    const { data } = await MetadataService.updateActor({
      actor_id: actorId,
      actorUpdate: {
        name: nextName,
        photo: photo.value.trim(),
        aliases: aliases.value,
      },
    })
    toastStore.success(t("components.metadata.actorEdit.saveSuccess"))
    emit("saved", data)
    open.value = false
  } catch (error: unknown) {
    errorMessage.value = extractError(error, t("components.metadata.actorEdit.saveFailed"))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <VDialog v-model="open" max-width="640" persistent>
    <VCard>
      <VCardTitle class="px-6 pt-5">
        {{ t('components.metadata.actorEdit.title') }}
      </VCardTitle>
      <VCardText class="px-6">
        <VProgressLinear v-if="loading" indeterminate class="mb-4" />
        <VAlert
          v-if="errorMessage"
          type="error"
          variant="tonal"
          class="mb-4"
          density="comfortable"
        >
          {{ errorMessage }}
        </VAlert>

        <VForm @submit.prevent="save">
          <VRow>
            <VCol cols="12">
              <VRow no-gutters>
                <VCol cols="12" md="3" class="row-label align-self-start">
                  <label class="pt-2">{{ t('components.metadata.actorEdit.photo') }}</label>
                </VCol>
                <VCol cols="12" md="9">
                  <div class="photo-edit">
                    <div
                      class="photo-preview"
                      :style="{ background: actorGradient(primaryName || props.actor?.name || '') }"
                    >
                      <span>{{ actorInitial(primaryName || props.actor?.name || '') }}</span>
                      <img
                        v-if="photoPreviewUrl"
                        :src="photoPreviewUrl"
                        :alt="primaryName"
                        @error="photoBroken = true"
                      />
                    </div>
                    <div class="photo-fields">
                      <div class="d-flex align-center mb-2">
                        <VTextField
                          v-model="photo"
                          hide-details
                          class="flex-grow-1 mr-2"
                          :placeholder="t('components.metadata.actorEdit.photoPlaceholder')"
                          :disabled="loading || saving || uploading"
                          @update:model-value="markDirty"
                        />
                        <VBtn
                          variant="outlined"
                          size="small"
                          :loading="uploading"
                          :disabled="loading || saving || uploading"
                          @click="selectPhoto"
                        >
                          <VIcon icon="bx-upload" class="mr-1" />
                          {{ t('components.metadata.actorEdit.uploadPhoto') }}
                        </VBtn>
                        <input
                          ref="fileInput"
                          type="file"
                          accept="image/*"
                          class="d-none"
                          @change="handlePhotoUpload"
                        />
                      </div>
                      <p class="photo-hint">{{ t('components.metadata.actorEdit.photoHint') }}</p>
                    </div>
                  </div>
                </VCol>
              </VRow>
            </VCol>

            <VCol cols="12">
              <VRow no-gutters>
                <VCol cols="12" md="3" class="row-label">
                  <label>{{ t('components.metadata.actorEdit.primaryName') }}</label>
                </VCol>
                <VCol cols="12" md="9">
                  <VTextField
                    v-model="name"
                    hide-details
                    :disabled="loading || saving"
                    @update:model-value="markDirty"
                  />
                </VCol>
              </VRow>
            </VCol>

            <VCol cols="12">
              <VRow no-gutters>
                <VCol cols="12" md="3" class="row-label align-self-start">
                  <label class="pt-2">{{ t('components.metadata.actorEdit.aliases') }}</label>
                </VCol>
                <VCol cols="12" md="9">
                  <div v-if="aliases.length" class="alias-list mb-2">
                    <div
                      v-for="alias in aliases"
                      :key="alias"
                      class="alias-row"
                      :class="{ 'alias-row--editing': editingAlias === alias }"
                    >
                      <template v-if="editingAlias === alias">
                        <VTextField
                          v-model="editingAliasDraft"
                          hide-details
                          class="alias-edit-field"
                          :disabled="loading || saving"
                          autofocus
                          @keydown.enter.prevent="confirmEditAlias"
                          @keydown.esc.prevent="cancelEditAlias"
                        >
                          <template #append-inner>
                            <div class="alias-inline-actions">
                              <VBtn
                                icon
                                variant="text"
                                size="x-small"
                                color="primary"
                                :title="t('components.metadata.actorEdit.applyEdit')"
                                :disabled="loading || saving || !editingAliasDraft.trim()"
                                @click.stop="confirmEditAlias"
                              >
                                <VIcon icon="bx-check" size="18" />
                              </VBtn>
                              <VBtn
                                icon
                                variant="text"
                                size="x-small"
                                :title="t('components.metadata.form.cancel')"
                                :disabled="loading || saving"
                                @click.stop="cancelEditAlias"
                              >
                                <VIcon icon="bx-x" size="18" />
                              </VBtn>
                            </div>
                          </template>
                        </VTextField>
                        <div class="alias-actions" aria-hidden="true" />
                      </template>
                      <template v-else>
                        <span class="alias-text">{{ alias }}</span>
                        <div class="alias-actions">
                          <VBtn
                            icon
                            variant="text"
                            size="small"
                            :title="t('components.metadata.actorEdit.editAlias')"
                            :disabled="loading || saving || editingAlias != null"
                            @click="startEditAlias(alias)"
                          >
                            <VIcon icon="bx-edit-alt" size="18" />
                          </VBtn>
                          <VBtn
                            icon
                            variant="text"
                            size="small"
                            color="error"
                            :title="t('components.metadata.actorEdit.removeAlias')"
                            :disabled="loading || saving || editingAlias != null"
                            @click="removeAlias(alias)"
                          >
                            <VIcon icon="bx-trash" size="18" />
                          </VBtn>
                        </div>
                      </template>
                    </div>
                  </div>
                  <div class="d-flex align-center">
                    <VTextField
                      v-model="aliasInput"
                      :placeholder="t('components.metadata.actorEdit.addAlias')"
                      hide-details
                      class="flex-grow-1 mr-2"
                      :disabled="loading || saving || editingAlias != null"
                      @keydown.enter.prevent="addAlias"
                    />
                    <VBtn
                      variant="outlined"
                      size="small"
                      :disabled="loading || saving || editingAlias != null || !aliasInput.trim()"
                      @click="addAlias"
                    >
                      {{ t('components.metadata.actorEdit.add') }}
                    </VBtn>
                  </div>
                </VCol>
              </VRow>
            </VCol>

            <VCol cols="12">
              <VRow no-gutters>
                <VCol cols="12" md="3" />
                <VCol cols="12" md="9">
                  <VBtn
                    type="submit"
                    class="me-4"
                    :loading="saving"
                    :disabled="loading || saving || uploading"
                  >
                    {{ t('components.metadata.form.save') }}
                  </VBtn>
                  <VBtn
                    type="button"
                    color="secondary"
                    variant="tonal"
                    :disabled="saving || uploading"
                    @click="open = false"
                  >
                    {{ t('components.metadata.form.cancel') }}
                  </VBtn>
                </VCol>
              </VRow>
            </VCol>
          </VRow>
        </VForm>
      </VCardText>
    </VCard>
  </VDialog>
</template>

<style scoped>
.photo-edit {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.photo-preview {
  position: relative;
  width: 96px;
  aspect-ratio: 2 / 3;
  flex-shrink: 0;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 600;
  color: #fff;
}

.photo-preview img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top;
}

.photo-fields {
  flex: 1;
  min-width: 0;
}

.photo-hint {
  margin: 0;
  font-size: 0.78rem;
  line-height: 1.4;
  color: rgba(var(--v-theme-on-surface), 0.5);
}

.alias-list {
  max-height: 220px;
  overflow: auto;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
}

.alias-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 40px;
  padding: 0 4px 0 12px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.alias-row:last-child {
  border-bottom: 0;
}

.alias-row--editing {
  padding: 0 4px 0 0;
  gap: 8px;
  background: transparent;
}

.alias-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.alias-edit-field {
  flex: 1;
  width: 100%;
  min-width: 0;
}

.alias-edit-field :deep(.v-field) {
  border-radius: 0;
}

.alias-edit-field :deep(.v-field__input) {
  padding-inline-start: 12px;
}

.alias-inline-actions {
  display: flex;
  align-items: center;
  margin-inline-end: -4px;
}

.alias-actions {
  display: flex;
  flex-shrink: 0;
  width: 72px;
  justify-content: flex-end;
}

@media (max-width: 600px) {
  .photo-edit {
    flex-direction: column;
  }
}
</style>
