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
const selectedPath = ref('')
const isCurrentFolderSelected = ref(false)

// Computed property to display the current selection
const displaySelection = computed(() => {
  if (isCurrentFolderSelected.value) {
    return currentPath.value + ' ' + t('components.fileBrowser.folderSelected')
  } else if (selectedPath.value) {
    return selectedPath.value
  }
  return ''
})

watch(() => props.initialPath, (newPath) => {
  if (newPath) {
    currentPath.value = newPath
    if (dialog.value) {
      loadFiles()
    }
  }
})

watch(() => props.modelValue, (show) => {
  if (show && currentPath.value) {
    selectedPath.value = ''
    isCurrentFolderSelected.value = false
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
    isCurrentFolderSelected.value = false
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
    selectedPath.value = ''
    isCurrentFolderSelected.value = false
    loadFiles()
  }
}

function navigateTo(path: string) {
  currentPath.value = path
  selectedPath.value = ''
  isCurrentFolderSelected.value = false
  loadFiles()
}

function selectItem(file: FileInfo) {
  if (!file.is_dir) {
    selectedPath.value = file.path
    isCurrentFolderSelected.value = false
  } else {
    navigateTo(file.path)
  }
}

function selectCurrentFolder() {
  isCurrentFolderSelected.value = true
  selectedPath.value = ''
}

function confirmSelection() {
  if (isCurrentFolderSelected.value) {
    emit('select', currentPath.value)
    dialog.value = false
  } else if (selectedPath.value) {
    emit('select', selectedPath.value)
    dialog.value = false
  }
}
</script>

<template>
  <VDialog v-model="dialog" width="800">
    <VCard>
      <VCardTitle class="text-h5 pa-4">
        {{ t('components.fileBrowser.title') }}
      </VCardTitle>

      <VCardText>
        <!-- Current Directory Path -->
        <VTextField
          v-model="currentPath"
          :label="t('components.fileBrowser.currentPath')"
          variant="outlined"
          density="compact"
          class="mb-2"
          readonly
        ></VTextField>
        
        <!-- Selection Display -->
        <VTextField
          v-if="selectedPath || isCurrentFolderSelected"
          v-model="displaySelection"
          :label="t('components.fileBrowser.selectedItem')"
          variant="outlined"
          density="compact"
          class="mb-4"
          readonly
          color="success"
        >
          <template v-slot:prepend-inner>
            <VIcon size="small" :icon="selectedPath ? 'mdi-file-check' : 'mdi-folder-check'" color="success" />
          </template>
        </VTextField>

        <div class="d-flex align-center mb-4">
          <VBtn prepend-icon="mdi-arrow-up" @click="navigateUp" class="mr-4">
            {{ t('components.fileBrowser.upOneLevel') }}
          </VBtn>
          <VBtn prepend-icon="mdi-refresh" @click="loadFiles" color="primary" class="mr-4">
            {{ t('components.fileBrowser.refresh') }}
          </VBtn>
          <VBtn 
            prepend-icon="mdi-folder-check" 
            @click="selectCurrentFolder" 
            color="success"
            :variant="isCurrentFolderSelected ? 'flat' : 'outlined'"
          >
            {{ t('components.fileBrowser.selectCurrentFolder') }}
          </VBtn>
        </div>

        <VAlert v-if="error" type="error" class="mb-4">
          {{ error }}
        </VAlert>

        <VList lines="two">
          <VListItem
            v-for="file in files"
            :key="file.path"
            @click="selectItem(file)"
            :prepend-icon="file.is_dir ? 'mdi-folder' : 'mdi-file'"
            :active="selectedPath === file.path"
            :variant="selectedPath === file.path ? 'elevated' : 'flat'"
          >
            <VListItemTitle>{{ file.name }}</VListItemTitle>
            <VListItemSubtitle>{{ file.path }}</VListItemSubtitle>
          </VListItem>
          
          <VListItem v-if="files.length === 0 && !isLoading">
            <VListItemTitle class="text-center text-grey">
              {{ t('components.fileBrowser.noFiles') }}
            </VListItemTitle>
          </VListItem>
        </VList>

        <VProgressCircular v-if="isLoading" indeterminate color="primary" class="ma-4" />
      </VCardText>

      <VCardActions>
        <VSpacer></VSpacer>
        <VBtn color="primary" variant="text" @click="dialog = false">
          {{ t('components.fileBrowser.cancel') }}
        </VBtn>
        <VBtn 
          color="success" 
          @click="confirmSelection"
          :disabled="!selectedPath && !isCurrentFolderSelected"
        >
          {{ t('components.fileBrowser.confirm') }}
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template> 