<script setup lang="ts">
import { useRecordStore } from "@/stores/record.store"
import { useTaskStore } from "@/stores/task.store"
import { useI18n } from "vue-i18n"
import { VIcon } from "vuetify/components"

const recordStore = useRecordStore()
const taskStore = useTaskStore()
const { t } = useI18n() // 导入国际化工具函数

const searchQuery = ref("")
const taskIdQuery = ref("")
const searchTimeout = ref<number | null>(null)
const selected = ref<number[]>([])
const tagColorMap = {
  中文字幕: "#FF0000",
  破解: "#FFA500",
} as const

// 刷新相关变量
const autoRefresh = ref(true) // 是否自动刷新
const refreshInterval = ref(10) // 刷新间隔（秒）
const refreshTimer = ref<number | null>(null) // 刷新定时器
const lastRefreshTime = ref<Date | null>(null) // 上次刷新时间
const hasNewData = ref(false) // 是否有新数据
const lastDataHash = ref("") // 上次数据的哈希值，用于检测变化

// 删除确认对话框
const deleteDialog = ref(false)
const forceDelete = ref(false)

// 分页选项
const pageSizeOptions = [10, 15, 25, 50, 100]

// 计算下次刷新时间的倒计时
const refreshCountdown = computed(() => {
  if (!autoRefresh.value || !lastRefreshTime.value) return 0

  const nextRefreshTime = new Date(
    lastRefreshTime.value.getTime() + refreshInterval.value * 1000,
  )
  const now = new Date()
  const remainingSeconds = Math.max(
    0,
    Math.floor((nextRefreshTime.getTime() - now.getTime()) / 1000),
  )

  return remainingSeconds
})

// 一个简单的函数来生成数据哈希，用于检测变化
const generateDataHash = (data: any[]) => {
  return JSON.stringify(
    data.map(
      (item) => `${item.transfer_record.id}_${item.transfer_record.updatetime}`,
    ),
  )
}

const getTagColor = (tag: string) => {
  return tagColorMap[tag.trim() as keyof typeof tagColorMap] || "#9DA8B5"
}

const formatDateTime = (dateStr: string | null | undefined) => {
  if (!dateStr) return ""
  return new Date(dateStr).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  })
}

const formatSeasonEpisode = (
  season?: number | null,
  episode?: number | null,
) => {
  const hasSeason = season != null && season !== -1
  const hasEpisode = episode != null && episode !== -1
  if (!hasSeason && !hasEpisode) return ""
  const seasonPart = hasSeason ? `S${String(season).padStart(2, "0")}` : ""
  const episodePart = hasEpisode ? `E${String(episode).padStart(2, "0")}` : ""
  return `${seasonPart}${episodePart}`
}

const headers = [
  {
    title: t("pages.records.name"),
    align: "start" as const,
    key: "transfer_record.srcname",
    width: "22%",
    minWidth: "200",
    nowrap: true,
    sortable: true,
  },
  {
    title: t("pages.records.status"),
    align: "center" as const,
    key: "transfer_record.success",
    width: "72px",
    nowrap: true,
    sortable: false,
  },
  {
    title: t("pages.records.destPath"),
    align: "start" as const,
    key: "transfer_record.destpath",
    width: "30%",
    minWidth: "260",
    nowrap: true,
    sortable: true,
  },
  {
    title: t("pages.records.seasonEpisode"),
    align: "start" as const,
    key: "transfer_record.season",
    width: "88px",
    nowrap: true,
    sortable: true,
  },
  {
    title: t("pages.records.number"),
    align: "start" as const,
    key: "extra_info.number",
    width: "120px",
    nowrap: true,
    sortable: false,
  },
  {
    title: t("pages.records.tag"),
    align: "start" as const,
    key: "extra_info.tag",
    width: "160px",
    nowrap: true,
    sortable: false,
  },
  {
    title: t("pages.records.updateTime"),
    align: "start" as const,
    key: "transfer_record.updatetime",
    width: "170px",
    nowrap: true,
    sortable: true,
  },
  {
    title: t("pages.records.deadTime"),
    align: "start" as const,
    key: "transfer_record.deadtime",
    width: "170px",
    nowrap: true,
    sortable: true,
  },
  {
    title: t("common.actions"),
    align: "start" as const,
    key: "actions",
    sortable: false,
    width: "146px",
    minWidth: "146",
    nowrap: true,
    cellProps: { class: "records-actions-col" },
    headerProps: { class: "records-actions-col" },
  },
]

const getRowProps = ({ item }: { item: any }) => ({
  class:
    item.transfer_record.deleted || item.transfer_record.srcdeleted
      ? "deleted-row"
      : undefined,
})

// 默认排序设置
const sortBy = ref([
  {
    key: "transfer_record.updatetime",
    order: "desc" as const,
  },
])

// 处理分页变化
const handlePageChange = async (newPage: number) => {
  selected.value = [] // 页面切换时清空选中项
  await loadData(newPage, recordStore.itemsPerPage)
}

// 处理每页数量变化
const handleItemsPerPageChange = async (newItemsPerPage: number) => {
  // 这里不使用v-model双向绑定，而是手动更新并重新加载数据
  selected.value = [] // 清空选中项
  // 调用loadData，传递当前页和新的每页数量
  await loadData(1, newItemsPerPage)
}

// 加载数据函数
const loadData = async (
  page = recordStore.currentPage,
  itemsPerPage = recordStore.itemsPerPage,
  isAutoRefresh = false,
) => {
  // 构建搜索参数
  const searchParams: {
    page: number
    itemsPerPage: number
    search?: string
    taskId?: number
    sortBy?: string
    sortDesc?: boolean
  } = {
    page,
    itemsPerPage,
  }

  // 如果有任务ID输入，则添加到搜索参数
  if (taskIdQuery.value.trim()) {
    const taskId = Number.parseInt(taskIdQuery.value.trim())
    if (!Number.isNaN(taskId)) {
      searchParams.taskId = taskId
    }
  }

  // 如果有搜索内容，则添加到搜索参数
  if (searchQuery.value.trim()) {
    searchParams.search = searchQuery.value.trim()
  }

  // 添加排序参数
  if (sortBy.value.length > 0) {
    const sortKey = sortBy.value[0].key
    // 只有 transfer_record 前缀的字段才可以排序
    if (sortKey.startsWith("transfer_record.")) {
      // 去掉 "transfer_record." 前缀，只传入字段名
      searchParams.sortBy = sortKey.replace("transfer_record.", "")
      searchParams.sortDesc = sortBy.value[0].order === "desc"
    }
  }
  await recordStore.getRecords(searchParams)

  // 刷新后处理
  lastRefreshTime.value = new Date()

  // 如果是自动刷新，检查数据是否有变化
  if (isAutoRefresh) {
    const newDataHash = generateDataHash(recordStore.records)
    if (lastDataHash.value && newDataHash !== lastDataHash.value) {
      hasNewData.value = true
    }
    lastDataHash.value = newDataHash
  } else {
    // 如果是手动刷新，重置新数据标志
    hasNewData.value = false
    lastDataHash.value = generateDataHash(recordStore.records)
  }

  // 设置下一次自动刷新
  setupAutoRefresh()
}

// 设置自动刷新定时器
const setupAutoRefresh = () => {
  // 清除现有定时器
  if (refreshTimer.value) {
    clearTimeout(refreshTimer.value)
    refreshTimer.value = null
  }

  // 如果启用了自动刷新，设置新的定时器
  if (autoRefresh.value) {
    refreshTimer.value = setTimeout(() => {
      loadData(recordStore.currentPage, recordStore.itemsPerPage, true)
    }, refreshInterval.value * 1000) as unknown as number
  }
}

// 切换自动刷新状态
const toggleAutoRefresh = () => {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    // 启用自动刷新时，立即设置定时器
    setupAutoRefresh()
  } else {
    // 禁用自动刷新时，清除定时器
    if (refreshTimer.value) {
      clearTimeout(refreshTimer.value)
      refreshTimer.value = null
    }
  }
}

// 手动刷新数据
const manualRefresh = async () => {
  hasNewData.value = false
  await loadData(recordStore.currentPage, recordStore.itemsPerPage)
}

async function initial() {
  await loadData()
}

const showSelectedRecord = (item: any) => {
  recordStore.showUpdateRecord(item)
}

const rerunThisRecord = (item: any) => {
  taskStore.runTaskByIdWithPath(
    item.transfer_record.task_id,
    item.transfer_record.srcpath,
  )
}

const handleDelete = () => {
  if (selected.value.length === 0) return
  deleteDialog.value = true
}

const confirmDelete = async () => {
  await recordStore.deleteRecords(selected.value, forceDelete.value)
  deleteDialog.value = false
  forceDelete.value = false
  // 清空选中项
  selected.value = []
}

// 更新 watch 函数以实现搜索功能，添加防抖
watch([searchQuery, taskIdQuery], () => {
  // 清除之前的定时器
  if (searchTimeout.value) {
    clearTimeout(searchTimeout.value)
  }

  // 设置新的定时器，300ms 后执行搜索
  searchTimeout.value = setTimeout(() => {
    selected.value = [] // 清空选中项
    loadData(1, recordStore.itemsPerPage) // 回到第一页，保持当前每页数量
  }, 300) as unknown as number
})

// 清除搜索并重新加载数据
const handleClearSearch = () => {
  searchQuery.value = ""
  taskIdQuery.value = ""
  loadData(1, recordStore.itemsPerPage)
}

// 处理排序变化
const handleSortChange = (newSortBy: any) => {
  sortBy.value = newSortBy
  loadData(recordStore.currentPage, recordStore.itemsPerPage)
}

// 组件卸载时清除定时器
onBeforeUnmount(() => {
  if (refreshTimer.value) {
    clearTimeout(refreshTimer.value)
    refreshTimer.value = null
  }
})

onMounted(() => {
  initial()
})
</script>

<template>
  <p class="text-xl mb-6">
    {{ t('pages.records.title') }}
  </p>
  <VCard>
    <div class="search-toolbar px-4 py-4">
      <div class="d-flex align-center justify-space-between flex-wrap gap-4">
        <div class="search-fields d-flex gap-4 align-center flex-grow-1 flex-wrap">
          <v-text-field v-model="searchQuery" :placeholder="t('pages.records.search')" hide-details density="comfortable"
            class="search-input" prepend-inner-icon="mdi-magnify" clearable
            @click:clear="searchQuery = ''; loadData(1, recordStore.itemsPerPage)" />

          <v-text-field v-model="taskIdQuery" :placeholder="t('pages.records.filterTaskId')" hide-details density="comfortable"
            class="task-id-input" prepend-inner-icon="mdi-pound" clearable type="number"
            @click:clear="taskIdQuery = ''; loadData(1, recordStore.itemsPerPage)" />
        </div>
        
        <div class="d-flex align-center gap-2">
          <!-- 刷新状态和控件 -->
          <div class="refresh-controls d-flex align-center">
            <v-tooltip :text="autoRefresh ? t('pages.records.refreshOn') : t('pages.records.refreshOff')">
              <template v-slot:activator="{ props }">
                <v-btn icon v-bind="props" :color="autoRefresh ? 'success' : 'grey'" @click="toggleAutoRefresh" size="small">
                  <v-icon>{{ autoRefresh ? 'mdi-sync' : 'mdi-sync-off' }}</v-icon>
                </v-btn>
              </template>
            </v-tooltip>
            
            <v-tooltip :text="t('pages.records.manualRefresh')">
              <template v-slot:activator="{ props }">
                <v-btn icon v-bind="props" color="primary" @click="manualRefresh" size="small" class="ml-1" 
                  :disabled="recordStore.loading" :loading="recordStore.loading">
                  <v-icon>mdi-refresh</v-icon>
                </v-btn>
              </template>
            </v-tooltip>
            
            <v-chip v-if="hasNewData" color="warning" size="small" class="ml-2" @click="manualRefresh">
              <v-icon start size="x-small" class="mr-1">mdi-alert</v-icon>
              {{ t('pages.records.newData') }}
            </v-chip>
            
            <div v-if="autoRefresh && lastRefreshTime && !hasNewData" class="refresh-counter text-grey text-caption ml-2">
              {{ t('pages.records.nextRefresh', { seconds: refreshCountdown }) }}
            </div>
          </div>
          
          <v-btn color="error" :disabled="selected.length === 0" prepend-icon="mdi-delete" @click="handleDelete"
            size="default" class="delete-btn">
            {{ t('pages.records.deleteSelected', { count: selected.length }) }}
          </v-btn>
        </div>
      </div>

      <div class="search-filters mt-2 mb-1 d-flex flex-wrap align-center gap-2" v-if="searchQuery || taskIdQuery">
        <v-chip v-if="searchQuery" color="primary" size="default" variant="elevated" class="search-chip">
          <v-icon start size="small" class="mr-1">mdi-magnify</v-icon>
          {{ t('pages.records.nameFilter') }}: {{ searchQuery }}
          <template v-slot:append>
            <v-icon size="small" @click="searchQuery = ''; loadData(1, recordStore.itemsPerPage)">mdi-close</v-icon>
          </template>
        </v-chip>

        <v-chip v-if="taskIdQuery" color="info" size="default" variant="elevated" class="search-chip">
          <v-icon start size="small" class="mr-1">mdi-pound</v-icon>
          {{ t('pages.records.taskIdFilter') }}: {{ taskIdQuery }}
          <template v-slot:append>
            <v-icon size="small" @click="taskIdQuery = ''; loadData(1, recordStore.itemsPerPage)">mdi-close</v-icon>
          </template>
        </v-chip>

        <v-btn v-if="searchQuery || taskIdQuery" icon="mdi-close-circle" size="small" color="error" variant="text"
          @click="handleClearSearch" class="ml-1 clear-all-btn">
          <v-tooltip activator="parent" location="top">{{ t('pages.records.clearFilters') }}</v-tooltip>
        </v-btn>
      </div>
    </div>

    <v-data-table v-model="selected" :headers="headers" :items="recordStore.records" item-value="transfer_record.id"
      show-select :loading="recordStore.loading" :sort-by="sortBy" height="auto" :items-per-page="-1"
      :row-props="getRowProps" class="records-table" @update:sort-by="handleSortChange">
      <template #item.transfer_record.srcname="{ item }">
        <v-tooltip :text="item.transfer_record.srcpath">
          <template #activator="{ props }">
            <div v-bind="props" class="cell-truncate">
              {{ item.transfer_record.srcname }}
            </div>
          </template>
        </v-tooltip>
      </template>

      <template #item.transfer_record.success="{ item }">
        <div class="d-flex align-center justify-center gap-1">
          <v-tooltip
            v-if="item.transfer_record.success !== null"
            :text="item.transfer_record.success ? t('pages.records.success') : t('pages.records.failed')"
          >
            <template #activator="{ props }">
              <v-chip
                v-bind="props"
                :color="item.transfer_record.success ? 'success' : 'error'"
                variant="flat"
                size="small"
                class="status-chip"
              >
                <v-icon
                  :icon="item.transfer_record.success ? 'bx-check' : 'bx-x'"
                  size="small"
                />
              </v-chip>
            </template>
          </v-tooltip>
          <v-tooltip v-if="item.transfer_record.ignored" :text="t('pages.records.ignored')">
            <template #activator="{ props }">
              <v-chip
                v-bind="props"
                color="grey"
                variant="flat"
                size="small"
                class="status-chip"
              >
                <v-icon icon="bx-minus-circle" size="small" />
              </v-chip>
            </template>
          </v-tooltip>
        </div>
      </template>

      <template #item.transfer_record.destpath="{ item }">
        <v-tooltip :text="item.transfer_record.destpath || ''">
          <template #activator="{ props }">
            <div
              v-bind="props"
              class="cell-truncate"
              :class="{ 'text-decoration-line-through': item.transfer_record.deleted }"
            >
              {{ item.transfer_record.destpath || '' }}
            </div>
          </template>
        </v-tooltip>
      </template>

      <template #item.transfer_record.season="{ item }">
        <span class="nowrap-cell">
          {{ formatSeasonEpisode(item.transfer_record.season, item.transfer_record.episode) }}
        </span>
      </template>

      <template #item.extra_info.number="{ item }">
        <span class="nowrap-cell">{{ item.extra_info?.number || '' }}</span>
      </template>

      <template #item.extra_info.tag="{ item }">
        <div v-if="item.extra_info?.tag" class="tag-cell">
          <v-chip v-for="tag in item.extra_info.tag.split(',')" :key="tag" :color="getTagColor(tag)" variant="flat"
            class="tag-chip" size="small">
            {{ tag.trim() }}
          </v-chip>
        </div>
      </template>

      <template #item.transfer_record.updatetime="{ item }">
        <span class="datetime-cell">{{ formatDateTime(item.transfer_record.updatetime) }}</span>
      </template>

      <template #item.transfer_record.deadtime="{ item }">
        <span class="datetime-cell">{{ formatDateTime(item.transfer_record.deadtime) }}</span>
      </template>

      <template #item.actions="{ item }">
        <div class="actions-cell">
          <VBtn size="small" @click="showSelectedRecord(item)">
            <VIcon icon="bx-edit-alt" />
          </VBtn>
          <VBtn size="small" @click="rerunThisRecord(item)">
            <VIcon icon="bx-refresh" />
          </VBtn>
        </div>
      </template>

      <!-- 自定义底部分页 -->
      <template v-slot:bottom>
        <div class="d-flex align-center justify-end px-4 py-3 w-100">
          <div class="d-flex align-center me-4">
            <span class="text-caption text-grey me-2">{{ t('pages.records.itemsPerPage') }}</span>
            <v-select :model-value="recordStore.itemsPerPage" :items="pageSizeOptions" density="compact"
              style="width: 80px" hide-details variant="plain" @update:model-value="handleItemsPerPageChange" />
            <div class="ms-4 text-caption text-grey">
              {{ t('pages.records.totalRecords', { count: recordStore.totalRecords }) }}
            </div>
          </div>

          <v-pagination v-model="recordStore.currentPage"
            :length="Math.ceil(recordStore.totalRecords / recordStore.itemsPerPage)"
            @update:model-value="handlePageChange" :total-visible="5" :show-first-last-page="false" />
        </div>
      </template>
    </v-data-table>
  </VCard>

  <RecordDetailDialog />

  <!-- 删除确认对话框 -->
  <VDialog v-model="deleteDialog" max-width="500">
    <VCard>
      <VCardTitle class="text-h5">
        {{ t('pages.records.deleteDialog.title') }}
      </VCardTitle>
      <VCardText>
        {{ t('pages.records.deleteDialog.message', { count: selected.length }) }}
        <VCheckbox v-model="forceDelete" :label="t('pages.records.deleteDialog.forceDelete')" class="mt-4" />
      </VCardText>
      <VCardActions>
        <VSpacer />
        <VBtn color="primary" variant="text" @click="deleteDialog = false">
          {{ t('pages.records.deleteDialog.cancel') }}
        </VBtn>
        <VBtn color="error" @click="confirmDelete">
          {{ t('pages.records.deleteDialog.confirm') }}
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>

<style scoped>
.records-table :deep(.v-table__wrapper),
.records-table :deep(.v-data-table__wrapper) {
  overflow-x: auto !important;
}

.records-table :deep(table) {
  table-layout: fixed;
  width: max(100%, 1400px) !important;
  min-width: 1400px !important;
}

.records-table :deep(th:not(.records-actions-col)),
.records-table :deep(td:not(.records-actions-col)) {
  overflow: hidden;
  vertical-align: middle;
}

.records-table :deep(th) {
  white-space: nowrap;
}

.records-table :deep(th:first-child),
.records-table :deep(td:first-child) {
  width: 48px;
  min-width: 48px;
  position: sticky;
  left: 0;
  z-index: 2;
  background-color: rgb(var(--v-theme-surface));
}

.records-table :deep(.records-actions-col) {
  width: 146px !important;
  min-width: 146px !important;
  max-width: 146px !important;
  overflow: visible !important;
  position: sticky;
  right: 0;
  z-index: 2;
  background-color: rgb(var(--v-theme-surface));
  box-shadow: -6px 0 8px -6px rgba(0, 0, 0, 0.35);
  white-space: nowrap;
  padding-inline-end: 10px !important;
}

.records-table :deep(thead th:first-child),
.records-table :deep(thead .records-actions-col) {
  z-index: 3;
}

.actions-cell {
  display: flex;
  flex-shrink: 0;
  flex-wrap: nowrap;
  align-items: center;
  gap: 8px;
}

.cell-truncate {
  width: 100%;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nowrap-cell,
.datetime-cell {
  white-space: nowrap;
}

.tag-cell {
  display: flex;
  flex-wrap: nowrap;
  gap: 4px;
  overflow: hidden;
}

.tag-chip {
  font-size: 12px;
  height: 20px;
  padding: 0 4px;
  min-width: 0;
  min-height: 0;
  flex: 0 0 auto;
}

.v-chip.tag-chip .v-chip__content {
  padding: 0;
  line-height: 20px;
}

.status-chip {
  min-width: 32px;
  width: 32px;
  height: 24px;
  justify-content: center;
  padding-inline: 0;
}

.max-w-xs {
  max-width: 300px;
}

.records-table :deep(.deleted-row) {
  color: #9e9e9e;
  opacity: 0.85;
}

.max-w-taskid {
  max-width: 150px;
}

.search-toolbar {
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.search-fields {
  flex-wrap: wrap;
  min-width: 0;
}

.search-input {
  max-width: 350px;
  min-width: 250px;
}

.task-id-input {
  max-width: 180px;
  min-width: 150px;
}

.delete-btn {
  white-space: nowrap;
}

.search-filters {
  min-height: 36px;
}

.search-chip {
  height: 32px;
  font-size: 14px;
}

.clear-all-btn {
  margin-left: 4px;
}

@media (max-width: 768px) {
  .search-input, .task-id-input {
    min-width: 0;
    width: 100%;
  }
  
  .delete-btn {
    margin-top: 8px;
    width: 100%;
  }
}

/* ... existing responsive adjustments ... */

.refresh-controls {
  white-space: nowrap;
}

.refresh-counter {
  min-width: 100px;
}

@media (max-width: 768px) {
  /* ... existing responsive styles ... */
  
  .refresh-controls {
    width: 100%;
    justify-content: space-between;
    margin-bottom: 8px;
  }
  
  .refresh-counter {
    text-align: right;
  }
}
</style>
