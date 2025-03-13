<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { FilesService } from '@/client'
import { useI18n } from "vue-i18n"
import type { FileInfo } from '@/client/types.gen'

const { t } = useI18n()
const props = defineProps<{
  modelValue: boolean
  initialPath: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'select', path: string): void
}>()

const dialog = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value)
})

const currentPath = ref(props.initialPath || '')
const files = ref<FileInfo[]>([])
const isLoading = ref(false)
const error = ref('')
const isSelected = ref(false)

watch(() => props.initialPath, (newPath) => {
  if (newPath) {
    currentPath.value = newPath
    isSelected.value = false
    if (dialog.value) {
      loadFiles()
    }
  }
})

watch(() => props.modelValue, (show) => {
  if (show && currentPath.value) {
    isSelected.value = false
    loadFiles()
  }
})

async function loadFiles() {
  if (!currentPath.value) return
  
  isLoading.value = true
  error.value = ''
  
  try {
    const response = await FilesService.listDirectory({
      directoryPath: currentPath.value
    })
    
    files.value = response.data || []
    currentPath.value = response.current_path || currentPath.value
    isSelected.value = false
  } catch (err) {
    console.error("Error loading files:", err)
    error.value = t('components.fileBrowser.loadError')
  } finally {
    isLoading.value = false
  }
}

function navigateUp() {
  if (currentPath.value.includes('/') || currentPath.value.includes('\\')) {
    const parts = currentPath.value.split(/[/\\]/)
    parts.pop()
    currentPath.value = parts.join('/')
    isSelected.value = false
    loadFiles()
  }
}

function navigateTo(path: string) {
  currentPath.value = path
  isSelected.value = false
  loadFiles()
}

function selectItem(file: FileInfo) {
  currentPath.value = file.path
  isSelected.value = true
}

function confirmSelection() {
  if (isSelected.value) {
    emit('select', currentPath.value)
    dialog.value = false
  }
}
</script>

<template>
  <VDialog v-model="dialog" width="800">
    <VCard>
      <VCardTitle class="text-h5 pa-4 d-flex align-center justify-space-between">
        {{ t('components.fileBrowser.title') }}
        <VBtn 
          color="success" 
          @click="confirmSelection"
          :disabled="!isSelected"
        >
          {{ t('components.fileBrowser.confirm') }}
        </VBtn>
      </VCardTitle>

      <VCardText>
        <!-- Path Input -->
        <VRow no-gutters class="mb-4">
          <VCol cols="12">
            <VTextField
              v-model="currentPath"
              variant="outlined"
              density="compact"
              hide-details
              class="mb-2"
              @keyup.enter="loadFiles"
              :color="isSelected ? 'success' : undefined"
            >
              <template v-slot:prepend-inner v-if="isSelected">
                <VIcon size="small" icon="bx-check" color="success" />
              </template>
              <template v-slot:append>
                <VBtn icon="bx-refresh" size="small" @click="loadFiles" color="primary"></VBtn>
              </template>
            </VTextField>
          </VCol>
        </VRow>

        <div class="d-flex align-center mb-4">
          <VBtn prepend-icon="bx-up-arrow-alt" @click="navigateUp" class="mr-4">
            {{ t('components.fileBrowser.upOneLevel') }}
          </VBtn>
        </div>

        <VAlert v-if="error" type="error" class="mb-4">
          {{ error }}
        </VAlert>

        <VCard class="file-list-card">
          <VList lines="one" bg-color="grey-lighten-5">
            <template v-for="(file, index) in files" :key="file.path">
              <VDivider v-if="index > 0" />
              <VListItem
                @click="selectItem(file)"
                :active="isSelected && currentPath === file.path"
                :variant="isSelected && currentPath === file.path ? 'elevated' : 'flat'"
                class="py-2"
              >
                <template v-slot:prepend>
                  <VIcon :icon="file.is_dir ? 'bx-folder' : 'bx-file'" />
                </template>
                
                <VListItemTitle>{{ file.name }}</VListItemTitle>
                
                <template v-slot:append v-if="file.is_dir">
                  <VBtn 
                    icon="bx-folder-open" 
                    size="small" 
                    color="primary" 
                    @click.stop="navigateTo(file.path)"
                  ></VBtn>
                </template>
              </VListItem>
            </template>
            
            <VListItem v-if="files.length === 0 && !isLoading">
              <VListItemTitle class="text-center text-grey">
                {{ t('components.fileBrowser.noFiles') }}
              </VListItemTitle>
            </VListItem>
          </VList>
          
          <div v-if="isLoading" class="d-flex justify-center pa-4">
            <VProgressCircular indeterminate color="primary" />
          </div>
        </VCard>
      </VCardText>
    </VCard>
  </VDialog>
</template>

<style scoped>
.row-label {
  display: flex;
  align-items: center;
  font-weight: 500;
  padding-right: 1rem;
}

@media (max-width: 960px) {
  .row-label {
    margin-bottom: 0.5rem;
  }
}

.file-list-card {
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 4px;
  overflow: hidden;
}
</style> 