<!-- MetadataDetailDialog.vue -->
<script setup lang="ts">
import { useMetadataStore } from "@/stores/metadata.store"
import { ref, watch } from "vue"
import { useI18n } from "vue-i18n"

const dialog = useMetadataStore()
const { t } = useI18n()

const activeTab = ref("manual")

// JSON 导入状态
const jsonText = ref("")
const jsonFileInput = ref<HTMLInputElement | null>(null)
const parseError = ref("")
const isImporting = ref(false)
const importResult = ref<{ success: number; failed: number } | null>(null)
const previewCount = ref<number | null>(null)

// 切换到新增模式时重置 tab
watch(
  () => dialog.showDialog,
  (v) => {
    if (!v) {
      activeTab.value = "manual"
      resetImportState()
    }
  },
)

function resetImportState() {
  jsonText.value = ""
  parseError.value = ""
  importResult.value = null
  previewCount.value = null
}

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
    const result = await dialog.importFromJson(parsed)
    importResult.value = result
    if (result.failed === 0) {
      jsonText.value = ""
      previewCount.value = null
      dialog.showDialog = false
    }
  } finally {
    isImporting.value = false
  }
}
</script>

<template>
  <VDialog v-model="dialog.showDialog" max-width="700" scrollable>
    <VCard style="max-height: 90vh; display: flex; flex-direction: column;">
      <VCardTitle class="px-6 pt-5">
        <span v-if="dialog.editMetadata">{{ t('pages.metadata.editMetadata') }}</span>
        <span v-else>{{ t('pages.metadata.addMetadata') }}</span>
      </VCardTitle>

      <!-- 编辑模式 -->
      <template v-if="dialog.editMetadata">
        <VCardText style="flex: 1; overflow-y: auto;">
          <MetadataDetailForm :updateMetadata="dialog.editMetadata" />
        </VCardText>
      </template>

      <!-- 新增模式：标签页切换 -->
      <template v-else>
        <VTabs v-model="activeTab" class="px-4" height="56" style="flex-shrink: 0;">
          <VTab value="manual" prepend-icon="bx-edit">{{ t('pages.metadata.addManual') }}</VTab>
          <VTab value="import" prepend-icon="bx-import">{{ t('pages.metadata.importJson') }}</VTab>
        </VTabs>
        <VDivider style="flex-shrink: 0;" />

        <!-- 手动填写 -->
        <VCardText v-if="activeTab === 'manual'" style="flex: 1; overflow-y: auto;">
          <MetadataDetailForm />
        </VCardText>

        <!-- JSON 导入 -->
        <VCardText v-if="activeTab === 'import'" style="flex: 1; overflow-y: auto;">
          <p class="text-body-2 text-medium-emphasis mb-4">
            {{ t('components.metadata.importDialog.description') }}
          </p>

          <div class="mb-3">
            <VBtn variant="outlined" prepend-icon="bx-file" @click="selectJsonFile" size="small">
              {{ t('components.metadata.importDialog.selectFile') }}
            </VBtn>
            <input
              ref="jsonFileInput"
              type="file"
              accept=".json,application/json"
              class="d-none"
              @change="handleJsonFileChange"
            />
          </div>

          <VTextarea
            v-model="jsonText"
            :label="t('components.metadata.importDialog.jsonLabel')"
            :placeholder="t('components.metadata.importDialog.placeholder')"
            rows="12"
            variant="outlined"
            :error-messages="parseError ? [parseError] : []"
            @input="onJsonTextInput"
            class="json-textarea"
          />

          <div v-if="previewCount !== null && !parseError" class="mt-1 text-caption text-success">
            <VIcon icon="bx-info-circle" size="small" class="mr-1" />
            {{ t('components.metadata.importDialog.previewCount', { count: previewCount }) }}
          </div>

          <VAlert
            v-if="importResult"
            class="mt-3"
            :type="importResult.failed === 0 ? 'success' : 'warning'"
            variant="tonal"
            density="compact"
          >
            {{ t('components.metadata.importDialog.resultSuccess', { count: importResult.success }) }}
            <span v-if="importResult.failed > 0">
              {{ t('components.metadata.importDialog.resultFailed', { count: importResult.failed }) }}
            </span>
          </VAlert>

          <div class="d-flex gap-3 mt-4">
            <VBtn
              color="primary"
              :loading="isImporting"
              :disabled="isImporting || !!parseError || !jsonText.trim()"
              prepend-icon="bx-import"
              @click="handleImport"
            >
              {{ t('components.metadata.importDialog.import') }}
            </VBtn>
            <VBtn variant="tonal" color="secondary" @click="dialog.showDialog = false">
              {{ t('common.cancel') }}
            </VBtn>
          </div>
        </VCardText>
      </template>
    </VCard>
  </VDialog>
</template>

<style lang="scss">
.json-textarea :deep(textarea) {
  font-family: monospace;
  font-size: 12px;
}
</style>
