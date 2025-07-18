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
const pageSizeOptions = [10, 25, 50, 100]

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

const headers = [
  {
    title: t("pages.records.name"),
    align: "start" as "start" | "center" | "end",
    key: "transfer_record.srcname",
    width: 250,
    sortable: true,
  },
  {
    title: t("pages.records.status"),
    align: "center" as "start" | "center" | "end",
    key: "transfer_record.success",
    width: 100,
    sortable: false,
  },
  {
    title: t("pages.records.destPath"),
    align: "center" as "start" | "center" | "end",
    key: "transfer_record.destpath",
    width: 200,
    sortable: true,
  },
  {
    title: t("pages.records.season"),
    align: "center" as "start" | "center" | "end",
    key: "transfer_record.season",
    width: 100,
    sortable: true,
  },
  {
    title: t("pages.records.episode"),
    align: "center" as "start" | "center" | "end",
    key: "transfer_record.episode",
    width: 100,
    sortable: true,
  },
  {
    title: t("pages.records.number"),
    align: "center" as "start" | "center" | "end",
    key: "extra_info.number",
    width: 100,
    sortable: false,
  },
  {
    title: t("pages.records.tag"),
    align: "center" as "start" | "center" | "end",
    key: "extra_info.tag",
    width: 100,
    sortable: false,
  },
  {
    title: t("pages.records.updateTime"),
    align: "center" as "start" | "center" | "end",
    key: "transfer_record.updatetime",
    width: 120,
    sortable: true,
  },
  {
    title: t("pages.records.deadTime"),
    align: "center" as "start" | "center" | "end",
    key: "transfer_record.deadtime",
    width: 120,
    sortable: true,
  },
  {
    title: t("common.actions"),
    key: "actions",
    sortable: false,
    width: 100,
  },
]

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
      @update:sort-by="handleSortChange">
      <!-- 自定义表格行 -->
      <template v-slot:item="{ item, columns, index }">
        <tr :class="{ 'deleted-row': item.transfer_record.deleted || item.transfer_record.srcdeleted }">
          <td><v-checkbox v-model="selected" :value="item.transfer_record.id" multiple hide-details></v-checkbox></td>
          <td>
            <v-tooltip :text="item.transfer_record.srcpath">
              <template v-slot:activator="{ props }">
                <span v-bind="props" class="text-truncate d-inline-block" style="max-width: 230px">
                  {{ item.transfer_record.srcname }}
                </span>
              </template>
            </v-tooltip>
          </td>
          <td>
            <v-chip 
              v-if="item.transfer_record.success !== null"
              :color="item.transfer_record.success ? 'success' : 'error'" 
              variant="flat" 
              size="small"
              class="status-chip">
              <v-icon 
                :icon="item.transfer_record.success ? 'bx-check' : 'bx-x'" 
                size="small">
              </v-icon>
            </v-chip>
          </td>
          <td>
            <v-tooltip :text="item.transfer_record.destpath || ''">
              <template v-slot:activator="{ props }">
                <span v-bind="props" class="text-truncate d-inline-block" style="max-width: 180px"
                  :class="{ 'text-decoration-line-through': item.transfer_record.deleted }">
                  {{ item.transfer_record.destpath || '' }}
                </span>
              </template>
            </v-tooltip>
          </td>
          <td>{{ item.transfer_record.season === -1 ? '' : item.transfer_record.season }}</td>
          <td>{{ item.transfer_record.episode === -1 ? '' : item.transfer_record.episode }}</td>
          <td>{{ item.extra_info?.number || '' }}</td>
          <td>
            <div v-if="item.extra_info?.tag" class="d-flex gap-1 flex-wrap">
              <v-chip v-for="tag in item.extra_info.tag.split(',')" :key="tag" :color="getTagColor(tag)" variant="flat"
                class="tag-chip" size="small">
                {{ tag.trim() }}
              </v-chip>
            </div>
          </td>
          <td>{{ formatDateTime(item.transfer_record.updatetime) }}</td>
          <td>{{ formatDateTime(item.transfer_record.deadtime) }}</td>
          <td>
            <div class="d-flex align-center gap-2">
              <VBtn type="submit" size="small" @click="showSelectedRecord(item)">
                <VIcon icon="bx-edit-alt" />
              </VBtn>
              <VBtn type="submit" size="small" @click="rerunThisRecord(item)">
                <VIcon icon="bx-refresh" />
              </VBtn>
            </div>
          </td>
        </tr>
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
.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tag-chip {
  font-size: 12px;
  height: 20px;
  padding: 0 4px;
  min-width: 0;
  min-height: 0;
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
}

.max-w-xs {
  max-width: 300px;
}

.deleted-row {
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
