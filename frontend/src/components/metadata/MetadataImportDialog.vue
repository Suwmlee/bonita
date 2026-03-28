<script setup lang="ts">
import { useMetadataStore } from "@/stores/metadata.store"
import { ref } from "vue"
import { useI18n } from "vue-i18n"

const metadataStore = useMetadataStore()
const { t } = useI18n()

const jsonText = ref("")
const jsonFileInput = ref<HTMLInputElement | null>(null)
const parseError = ref("")
const isImporting = ref(false)
const importResult = ref<{ success: number; failed: number } | null>(null)
const previewCount = ref<number | null>(null)

function onJsonTextInput() {
  parseError.value = ""
  importResult.value = null
  previewCount.value = null

  if (!jsonText.value.trim()) return

  try {
    const parsed = JSON.parse(jsonText.value)
    previewCount.value = Array.isArray(parsed) ? parsed.length : 1
  } catch {
    parseError.value = t("components.metadata.importDialog.invalidJson")
  }
}

function selectJsonFile() {
  jsonFileInput.value?.click()
}

function handleJsonFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files || target.files.length === 0) return

  const file = target.files[0]
  const reader = new FileReader()
  reader.onload = (e) => {
    jsonText.value = (e.target?.result as string) || ""
    onJsonTextInput()
  }
  reader.readAsText(file)

  if (jsonFileInput.value) jsonFileInput.value.value = ""
}

async function handleImport() {
  parseError.value = ""
  importResult.value = null

  if (!jsonText.value.trim()) {
    parseError.value = t("components.metadata.importDialog.emptyInput")
    return
  }

  let parsed: any
  try {
    parsed = JSON.parse(jsonText.value)
  } catch {
    parseError.value = t("components.metadata.importDialog.invalidJson")
    return
  }

  isImporting.value = true
  try {
    const result = await metadataStore.importFromJson(parsed)
    importResult.value = result
    if (result.failed === 0) {
      jsonText.value = ""
      previewCount.value = null
    }
  } finally {
    isImporting.value = false
  }
}

function handleClose() {
  metadataStore.showImportDialog = false
  jsonText.value = ""
  parseError.value = ""
  importResult.value = null
  previewCount.value = null
}
</script>

<template>
  <VDialog v-model="metadataStore.showImportDialog" max-width="700" scrollable @update:model-value="(v) => { if (!v) handleClose() }">
    <VCard class="pa-2">
      <VCardTitle class="ms-2">
        {{ t('components.metadata.importDialog.title') }}
      </VCardTitle>

      <VCardText>
        <p class="text-body-2 text-medium-emphasis mb-4">
          {{ t('components.metadata.importDialog.description') }}
        </p>

        <!-- File upload button -->
        <div class="mb-3">
          <VBtn variant="outlined" prepend-icon="bx-file" @click="selectJsonFile" size="small">
            {{ t('components.metadata.importDialog.selectFile') }}
          </VBtn>
          <input ref="jsonFileInput" type="file" accept=".json,application/json" class="d-none" @change="handleJsonFileChange" />
        </div>

        <!-- JSON textarea -->
        <VTextarea
          v-model="jsonText"
          :label="t('components.metadata.importDialog.jsonLabel')"
          :placeholder="t('components.metadata.importDialog.placeholder')"
          rows="12"
          variant="outlined"
          font-family="monospace"
          :error-messages="parseError ? [parseError] : []"
          @input="onJsonTextInput"
          class="json-textarea"
        />

        <!-- Preview count -->
        <div v-if="previewCount !== null && !parseError" class="mt-1 text-caption text-success">
          <VIcon icon="bx-info-circle" size="small" class="mr-1" />
          {{ t('components.metadata.importDialog.previewCount', { count: previewCount }) }}
        </div>

        <!-- Import result -->
        <VAlert v-if="importResult" class="mt-3" :type="importResult.failed === 0 ? 'success' : 'warning'" variant="tonal" density="compact">
          {{ t('components.metadata.importDialog.resultSuccess', { count: importResult.success }) }}
          <span v-if="importResult.failed > 0">
            {{ t('components.metadata.importDialog.resultFailed', { count: importResult.failed }) }}
          </span>
        </VAlert>
      </VCardText>

      <VCardActions class="px-6 pb-4">
        <VBtn
          color="primary"
          :loading="isImporting"
          :disabled="isImporting || !!parseError || !jsonText.trim()"
          prepend-icon="bx-import"
          @click="handleImport"
        >
          {{ t('components.metadata.importDialog.import') }}
        </VBtn>
        <VBtn variant="tonal" color="secondary" @click="handleClose">
          {{ t('common.cancel') }}
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>

<style scoped>
.json-textarea :deep(textarea) {
  font-family: monospace;
  font-size: 12px;
}
</style>
