<script setup lang="ts">
import FileBrowserDialog from "@/components/FileBrowserDialog.vue"
import { useScrapingStore } from "@/stores/scraping.store"
import { useTaskStore } from "@/stores/task.store"
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import { useI18n } from "vue-i18n"
import { VCardActions } from "vuetify/components"

const taskStore = useTaskStore()
const scrapingStore = useScrapingStore()
const { t } = useI18n() // 导入国际化工具函数

// Store selected files for each task
const selectedFiles = ref(new Map<number, string>())

// File browser dialog control
const showFileBrowser = ref(false)
const currentTaskId = ref<number | null>(null)

// Get selected file for a task
function getSelectedFile(taskId: number): string {
  return selectedFiles.value.get(taskId) || ""
}

// Set selected file for a task
function setSelectedFile(taskId: number, value: string): void {
  if (value && taskStore.allTasks) {
    const task = taskStore.allTasks.find((t) => t.id === taskId)
    if (task) {
      // Store the selected path regardless of whether it's a file or folder
      selectedFiles.value.set(taskId, value)
    }
  } else {
    // If value is empty, clear it
    selectedFiles.value.delete(taskId)
  }
}

// Get the display value (selected file or source folder)
function getSourceFolderDisplay(taskId: number, sourceFolder: string): string {
  const selectedFile = getSelectedFile(taskId)
  return selectedFile || sourceFolder
}

// Open file browser for a specific task
function openFileBrowser(taskId: number, sourcePath: string): void {
  currentTaskId.value = taskId
  showFileBrowser.value = true
}

// Handle file selection from the file browser
function handleFileSelected(path: string): void {
  if (currentTaskId.value !== null) {
    setSelectedFile(currentTaskId.value, path)
    currentTaskId.value = null
  }
}

// Reactive method to check if a task is running
const isTaskRunning = computed(() => {
  return (taskId: number) => taskStore.isTaskRunning(taskId)
})

async function initial() {
  await taskStore.getAllTasks()
  await scrapingStore.getAllSetting()
  taskStore.startPollingTasks(3000)
}

function addNewTask() {
  console.log("add new")
  taskStore.showAddTask()
}

function runTask(id: number) {
  // Get the selected file for this task
  const selectedFile = getSelectedFile(id)

  // Use the appropriate method based on whether a file is selected
  if (selectedFile) {
    // If a file is selected, use that
    taskStore.runTaskByIdWithPath(id, selectedFile)
  } else {
    // Otherwise, just run with the default source folder
    taskStore.runTaskById(id)
  }
}

const showSelectedTask = (item: any) => {
  taskStore.showUpdateTask(item)
}

function deleteTask(id: number) {
  taskStore.deleteTaskById(id)
}

// Prevent event propagation for input field
function handleInputClick(event: Event) {
  event.stopPropagation()
}

onMounted(() => {
  initial()
})

onBeforeUnmount(() => {
  taskStore.stopPollingTasks()
})
</script>

<template>
  <div>
    <p class="text-xl mb-6">
      {{ t('pages.task.title') }}
    </p>

    <VRow>
      <VCol v-for="data in taskStore.allTasks" :key="data.id" cols="12" sm="6" md="4" lg="3" xl="2" @click="showSelectedTask(data)">
        <VCard>
          <VCardItem>
            <VCardTitle>
              {{ data.name }} <span class="text-caption text-grey">#{{ data.id }}</span>
            </VCardTitle>
          </VCardItem>

          <VCardText>
            <p class="clamp-text mb-0">
              {{ data.description }}
            </p>
          </VCardText>

          <!-- File path display with file browser button -->
          <VCardText>
            <div class="d-flex align-center">
              <div 
                class="file-path-display d-flex align-center flex-grow-1 pa-2 rounded border"
                v-tooltip="getSourceFolderDisplay(data.id, data.source_folder)"
              >
                <span class="text-truncate">{{ getSourceFolderDisplay(data.id, data.source_folder) }}</span>
              </div>
              <VBtn
                icon
                variant="text"
                density="compact"
                color="primary"
                class="ml-2"
                @click.stop="openFileBrowser(data.id, data.source_folder)"
              >
                <VIcon>bx-folder-open</VIcon>
              </VBtn>
            </div>
          </VCardText>

          <VCardActions class="justify-space-between">
            <VBtn v-if="!isTaskRunning(data.id)" type="submit" class="me-4" @click.stop="runTask(data.id)">
              {{ t('pages.task.runNow') }}
            </VBtn>
            <VBtn v-else color="primary" class="me-4" :loading="true" variant="tonal">
              <template #loader>
                <span>{{ t('pages.task.running') }}</span>
              </template>
            </VBtn>
            <VBtn type="submit" class="me-4" @click.stop="deleteTask(data.id)">
              <VIcon style="color: firebrick;" icon="bx-trash" size="22" />
            </VBtn>
          </VCardActions>
        </VCard>
      </VCol>

      <VCol cols="12" sm="6" md="4" lg="3" xl="2" @click="addNewTask">
        <VCard style="height: 100%;">
          <VCardText class="d-flex flex-column align-center justify-center" style="height: 100%;">
            <VIcon icon="bx-plus" size="140" color="primary" />
          </VCardText>
        </VCard>
      </VCol>
    </VRow>

    <!-- File Browser Dialog -->
    <FileBrowserDialog
      v-model="showFileBrowser"
      :initial-path="currentTaskId !== null && taskStore.allTasks ? 
        (taskStore.allTasks.find(t => t.id === currentTaskId)?.source_folder || '') : ''"
      @select="handleFileSelected"
    />
  </div>

  <TransferConfigDetailDialog />
</template>

<style scoped>
.file-path-display {
  min-height: 40px;
  background-color: var(--v-theme-surface);
  border-color: rgba(var(--v-theme-on-surface), 0.38);
  transition: border-color 0.2s ease;
  overflow: hidden;
}

.file-path-display:hover {
  border-color: rgba(var(--v-theme-on-surface), 0.86);
}

.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.clamp-text {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
