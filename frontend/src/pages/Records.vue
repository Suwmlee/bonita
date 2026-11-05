<script setup lang="ts">
import {
  type RecordGroupPublic,
  type RecordPublic,
  type SubtitleDeliverResult,
  SubtitleService,
} from "@/client"
import PosterFrame from "@/components/common/PosterFrame.vue"
import { getPosterUrl } from "@/composables/useMediaPoster"
import imdbLogo from "@/assets/logos/imdb.png"
import tmdbLogo from "@/assets/logos/tmdb.png"
import tvdbLogo from "@/assets/logos/tvdb.png"
import { useRecordStore } from "@/stores/record.store"
import { useTaskStore } from "@/stores/task.store"
import { useToastStore } from "@/stores/toast.store"
import { useI18n } from "vue-i18n"
import { VIcon } from "vuetify/components"

const recordStore = useRecordStore()
const taskStore = useTaskStore()
const toastStore = useToastStore()
const { t } = useI18n() // 导入国际化工具函数

const VIEW_MODE_KEY = "records-view-mode"
const VIEW_STATE_KEY = "records-view-state"

type RecordsViewState = {
  taskId: number | null
}

function loadViewState(): Partial<RecordsViewState> {
  try {
    const raw = localStorage.getItem(VIEW_STATE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as Partial<RecordsViewState>
    if (
      typeof parsed.taskId === "number" &&
      Number.isInteger(parsed.taskId) &&
      parsed.taskId > 0
    ) {
      return { taskId: parsed.taskId }
    }
    return {}
  } catch {
    return {}
  }
}

const savedViewState = loadViewState()
const viewMode = ref(
  localStorage.getItem(VIEW_MODE_KEY) === "group" ? "group" : "list",
)
const posterBroken = ref<Record<string, boolean>>({})
const posterPreview = ref<{ src: string; alt: string } | null>(null)

const searchQuery = ref("")
const taskIdQuery = ref<number | null>(savedViewState.taskId ?? null)
const tasksLoaded = ref(false)

const taskOptions = computed(() => {
  const options = [...taskStore.allTasks]
    .sort((a, b) => a.name.localeCompare(b.name, "zh"))
    .map((task) => ({
      id: task.id,
      title: `${task.name} (#${task.id})`,
    }))
  const selectedId = taskIdQuery.value
  if (selectedId != null && !options.some((item) => item.id === selectedId)) {
    options.unshift({
      id: selectedId,
      title: tasksLoaded.value ? `#${selectedId}` : "",
    })
  }
  return options
})

function persistViewState() {
  const state: RecordsViewState = {
    taskId: taskIdQuery.value,
  }
  localStorage.setItem(VIEW_STATE_KEY, JSON.stringify(state))
}
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
const generateDataHash = () => {
  if (viewMode.value === "group") {
    return JSON.stringify(
      recordStore.groups.map((item) => `${item.key}_${item.latest_updatetime}`),
    )
  }
  return JSON.stringify(
    recordStore.records.map(
      (item) => `${item.transfer_record.id}_${item.transfer_record.updatetime}`,
    ),
  )
}

const pageTotal = computed(() =>
  viewMode.value === "group"
    ? recordStore.totalGroups
    : recordStore.totalRecords,
)

const pageLength = computed(() => {
  const pages = Math.ceil(pageTotal.value / recordStore.itemsPerPage)
  return pages > 0 ? pages : 1
})

function externalLinks(group: RecordGroupPublic) {
  const links: { kind: string, href: string, label: string, logo: string }[] = []
  const imdb = group.imdb_id?.trim()
  if (imdb) {
    const id = imdb.startsWith("tt") ? imdb : `tt${imdb}`
    links.push({ kind: "imdb", href: `https://www.imdb.com/title/${id}/`, label: "IMDb", logo: imdbLogo })
  }
  const tmdb = group.tmdb_id?.trim()
  if (tmdb) {
    const type = group.kind === "series" ? "tv" : "movie"
    links.push({
      kind: "tmdb",
      href: `https://www.themoviedb.org/${type}/${encodeURIComponent(tmdb)}`,
      label: "TMDB",
      logo: tmdbLogo,
    })
  }
  const tvdb = group.tvdb_id?.trim()
  if (tvdb) {
    const type = group.kind === "series" ? "series" : "movie"
    links.push({
      kind: "tvdb",
      href: `https://www.thetvdb.com/dereferrer/${type}/${encodeURIComponent(tvdb)}`,
      label: "TVDB",
      logo: tvdbLogo,
    })
  }
  return links
}

function groupPosterUrl(group: RecordGroupPublic) {
  if (group.number) {
    return getPosterUrl({
      media_type: "number",
      number: group.number,
      title: group.title || "",
    })
  }
  return getPosterUrl({
    media_type: group.kind === "series" ? "tvshow" : "movie",
    title: group.title || "",
    imdb_id: group.imdb_id || "",
    tmdb_id: group.tmdb_id || "",
  })
}

function markPosterBroken(key: string) {
  posterBroken.value = { ...posterBroken.value, [key]: true }
}

function openPosterPreview(group: RecordGroupPublic) {
  if (posterBroken.value[group.key]) return
  posterPreview.value = {
    src: groupPosterUrl(group),
    alt: group.number && group.title ? `${group.number} ${group.title}` : (group.title || group.number || ""),
  }
}

function setRecordSelected(id: number, checked: boolean | null) {
  if (checked) {
    if (!selected.value.includes(id)) selected.value = [...selected.value, id]
    return
  }
  selected.value = selected.value.filter((item) => item !== id)
}

function isDeletedRecord(item: RecordPublic) {
  return Boolean(
    item.transfer_record.deleted || item.transfer_record.srcdeleted,
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

const formatPartNumber = (partNumber?: number | null) => {
  if (partNumber == null || partNumber <= 0) return ""
  return `P${String(partNumber).padStart(2, "0")}`
}

const subtitleCount = (item: RecordPublic) => item.subtitle_count || 0

function apiErrorMessage(error: unknown, fallback: string) {
  const detail = (error as { response?: { data?: { detail?: unknown } } })
    ?.response?.data?.detail
  if (typeof detail === "string" && detail.trim()) return detail
  return fallback
}

function deliverSummary(result: SubtitleDeliverResult) {
  const failed = result.failed || 0
  const hasCount = result.copied || result.skipped || result.missing || failed
  const base = hasCount
    ? t("pages.subtitles.deliverResult", { ...result, failed })
    : t("pages.subtitles.deliverNone")
  const details = (result.details || []).filter(Boolean)
  if (!hasCount && details.length) return details.join("；")
  if (details.length) return `${base}。${details.join("；")}`
  return base
}

async function deliverRecordSubtitle(item: RecordPublic) {
  const mediaId = item.transfer_record.media_item_id
  if (!mediaId) return
  try {
    const { data: result } = await SubtitleService.deliverSubtitles({
      subtitleDeliverRequest: {
        media_item_ids: [mediaId],
        part_number: item.transfer_record.part_number || 0,
      },
    })
    toastStore.success(deliverSummary(result))
  } catch (error) {
    toastStore.error(apiErrorMessage(error, t("pages.subtitles.deliverFailed")))
  }
}

function groupHasSubtitles(group: RecordGroupPublic) {
  return group.records.some((item) => subtitleCount(item) > 0)
}

async function deliverGroupSubtitle(group: RecordGroupPublic) {
  const mediaIds = [
    ...new Set(
      group.records
        .map((item) => item.transfer_record.media_item_id)
        .filter((id): id is number => !!id),
    ),
  ]
  if (!mediaIds.length) return
  try {
    const { data: result } = await SubtitleService.deliverSubtitles({
      subtitleDeliverRequest: {
        media_item_ids: mediaIds,
      },
    })
    toastStore.success(deliverSummary(result))
  } catch (error) {
    toastStore.error(apiErrorMessage(error, t("pages.subtitles.deliverFailed")))
  }
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
    width: "24%",
    minWidth: "220",
    nowrap: true,
    sortable: true,
  },
  {
    title: t("pages.records.seasonEpisode"),
    align: "start" as const,
    key: "transfer_record.season",
    width: "120px",
    minWidth: "120",
    nowrap: true,
    sortable: true,
    cellProps: { class: "records-season-col" },
    headerProps: { class: "records-season-col" },
  },
  {
    title: t("pages.records.partNumber"),
    align: "start" as const,
    key: "transfer_record.part_number",
    width: "96px",
    nowrap: true,
    sortable: true,
  },
  {
    title: t("pages.records.number"),
    align: "start" as const,
    key: "extra_info.number",
    width: "180px",
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
    width: "184px",
    minWidth: "184",
    nowrap: true,
    sortable: true,
    cellProps: { class: "records-datetime-col" },
    headerProps: { class: "records-datetime-col" },
  },
  {
    title: t("pages.records.deadTime"),
    align: "start" as const,
    key: "transfer_record.deadtime",
    width: "184px",
    minWidth: "184",
    nowrap: true,
    sortable: true,
    cellProps: { class: "records-datetime-col" },
    headerProps: { class: "records-datetime-col" },
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

  if (taskIdQuery.value != null) {
    searchParams.taskId = taskIdQuery.value
  }

  // 如果有搜索内容，则添加到搜索参数
  const keyword = searchQuery.value?.trim() ?? ""
  if (keyword) {
    searchParams.search = keyword
  }

  let loaded: unknown
  if (viewMode.value === "group") {
    searchParams.sortBy = "updatetime"
    searchParams.sortDesc = true
    loaded = await recordStore.getRecordGroups(searchParams)
  } else {
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
    loaded = await recordStore.getRecords(searchParams)
  }

  // 已有更新的请求在途或已返回，丢弃这次结果，避免旧搜索覆盖新搜索
  if (loaded == null) return

  // 刷新后处理
  lastRefreshTime.value = new Date()

  // 如果是自动刷新，检查数据是否有变化
  if (isAutoRefresh) {
    const newDataHash = generateDataHash()
    if (lastDataHash.value && newDataHash !== lastDataHash.value) {
      hasNewData.value = true
    }
    lastDataHash.value = newDataHash
  } else {
    // 如果是手动刷新，重置新数据标志
    hasNewData.value = false
    lastDataHash.value = generateDataHash()
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
  const deleted = await recordStore.deleteRecords(
    selected.value,
    forceDelete.value,
  )
  deleteDialog.value = false
  forceDelete.value = false
  selected.value = []
  if (deleted) {
    await loadData(recordStore.currentPage, recordStore.itemsPerPage)
  }
}

watch(viewMode, (mode) => {
  localStorage.setItem(VIEW_MODE_KEY, mode)
  selected.value = []
  posterBroken.value = {}
  loadData(1, recordStore.itemsPerPage)
})

watch(
  () => recordStore.showDialog,
  (open, wasOpen) => {
    if (wasOpen && !open && viewMode.value === "group") {
      loadData(recordStore.currentPage, recordStore.itemsPerPage)
    }
  },
)

watch(taskIdQuery, () => {
  persistViewState()
}, { flush: "sync" })

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

onMounted(async () => {
  try {
    await taskStore.getAllTasks()
  } catch (error) {
    console.error("Failed to load tasks", error)
  } finally {
    tasksLoaded.value = true
  }
  await initial()
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
          <v-text-field v-model="searchQuery" :placeholder="t(viewMode === 'group' ? 'pages.records.searchGroup' : 'pages.records.search')" hide-details density="comfortable"
            class="search-input" prepend-inner-icon="mdi-magnify" clearable
            @click:clear="searchQuery = ''" />

          <v-autocomplete v-model="taskIdQuery" :items="taskOptions" item-title="title" item-value="id"
            :placeholder="t('pages.records.filterTaskId')" hide-details density="comfortable"
            class="task-id-input" prepend-inner-icon="mdi-pound" clearable
            @click:clear="taskIdQuery = null" />
        </div>
        
        <div class="d-flex align-center gap-2">
          <v-btn-toggle v-model="viewMode" mandatory density="comfortable" divided class="view-toggle">
            <v-btn value="list" size="small">{{ t('pages.records.viewList') }}</v-btn>
            <v-btn value="group" size="small">{{ t('pages.records.viewGroup') }}</v-btn>
          </v-btn-toggle>
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

    </div>

    <v-data-table v-if="viewMode === 'list'" v-model="selected" :headers="headers" :items="recordStore.records" item-value="transfer_record.id"
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
                color="warning"
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

      <template #item.transfer_record.part_number="{ item }">
        <span class="nowrap-cell">
          {{ formatPartNumber(item.transfer_record.part_number) }}
        </span>
      </template>

      <template #item.extra_info.number="{ item }">
        <span class="nowrap-cell d-inline-flex align-center">
          <span v-if="item.extra_info?.number" class="record-number">{{ item.extra_info.number }}</span>
          <VBtn
            v-if="subtitleCount(item) > 0"
            size="x-small"
            variant="text"
            class="ms-1"
            :title="t('pages.subtitles.deliver')"
            @click.stop="deliverRecordSubtitle(item)"
          >
            <VIcon icon="bx-captions" size="18" />
          </VBtn>
        </span>
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
              {{ t('pages.records.totalRecords', { count: pageTotal }) }}
            </div>
          </div>

          <v-pagination v-model="recordStore.currentPage"
            :length="pageLength"
            @update:model-value="handlePageChange" :total-visible="5" :show-first-last-page="false" />
        </div>
      </template>
    </v-data-table>

    <div v-else class="record-groups">
      <div v-if="recordStore.loading && recordStore.groups.length === 0" class="d-flex justify-center pa-8">
        <v-progress-circular indeterminate color="primary" />
      </div>
      <div v-else-if="recordStore.groups.length === 0" class="text-medium-emphasis text-center pa-8">
        {{ t('pages.records.noGroups') }}
      </div>
      <article v-for="group in recordStore.groups" :key="group.key" class="record-group">
        <aside class="record-group-entry">
          <PosterFrame tag="button" class="record-poster" :src="groupPosterUrl(group)"
            :alt="group.number || group.title || ''" :crop="group.crop" :broken="!!posterBroken[group.key]"
            :disabled="!!posterBroken[group.key]"
            :title="posterBroken[group.key] ? undefined : t('components.metadata.form.clickToView')"
            @error="markPosterBroken(group.key)" @click="openPosterPreview(group)">
            <template #empty>
              <v-icon icon="mdi-image-off" size="small" />
            </template>
          </PosterFrame>
        </aside>
        <div class="record-group-main">
          <div class="record-group-meta">
            <div v-if="group.number" class="record-number">{{ group.number }}</div>
            <div v-if="externalLinks(group).length" class="record-external-links">
              <a v-for="link in externalLinks(group)" :key="link.kind" class="record-external-link"
                :class="link.kind" :href="link.href" target="_blank" rel="noopener noreferrer" :title="link.label"
                :aria-label="link.label">
                <img :src="link.logo" alt="">
              </a>
            </div>
            <div v-if="group.title" class="record-group-title">{{ group.title }}</div>
            <VBtn
              v-if="groupHasSubtitles(group)"
              class="record-group-subtitle record-group-action"
              :title="t('pages.subtitles.deliver')"
              @click="deliverGroupSubtitle(group)"
            >
              <VIcon icon="bx-captions" size="18" />
            </VBtn>
            <div class="text-caption text-medium-emphasis record-group-count">
              {{ t('pages.records.groupFileCount', { count: group.record_count }) }}
            </div>
          </div>
          <div class="record-group-list">
            <div class="record-group-row record-group-columns">
              <span />
              <span class="record-group-status">{{ t('pages.records.status') }}</span>
              <span>{{ t('pages.records.name') }}</span>
              <span>{{ t('pages.records.destPath') }}</span>
              <span>{{ t('pages.records.seasonEpisode') }}</span>
              <span>{{ t('pages.records.partNumber') }}</span>
              <span>{{ t('pages.records.tag') }}</span>
              <span>{{ t('pages.records.updateTime') }}</span>
              <span>{{ t('pages.records.actions') }}</span>
            </div>
            <div v-for="item in group.records" :key="item.transfer_record.id" class="record-group-row"
              :class="{ 'deleted-row': isDeletedRecord(item) }">
              <v-checkbox :model-value="selected.includes(item.transfer_record.id)" hide-details density="compact"
                class="group-check" @update:model-value="setRecordSelected(item.transfer_record.id, $event)" />
              <div class="record-group-status">
                <v-tooltip v-if="item.transfer_record.success !== null"
                  :text="item.transfer_record.success ? t('pages.records.success') : t('pages.records.failed')">
                  <template #activator="{ props }">
                    <v-icon v-bind="props" size="18"
                      :icon="item.transfer_record.success ? 'bx-check' : 'bx-x'"
                      :color="item.transfer_record.success ? 'success' : 'error'" />
                  </template>
                </v-tooltip>
                <v-tooltip v-if="item.transfer_record.ignored" :text="t('pages.records.ignored')">
                  <template #activator="{ props }">
                    <v-icon v-bind="props" icon="bx-minus-circle" size="18" color="warning" />
                  </template>
                </v-tooltip>
              </div>
              <div class="record-group-cell">
                <v-tooltip :text="item.transfer_record.srcpath">
                  <template #activator="{ props }">
                    <button v-bind="props" type="button" class="record-group-filename"
                      :class="{ 'text-decoration-line-through': isDeletedRecord(item) }"
                      @click="showSelectedRecord(item)">
                      {{ item.transfer_record.srcname }}
                    </button>
                  </template>
                </v-tooltip>
              </div>
              <div class="record-group-cell">
                <v-tooltip :text="item.transfer_record.destpath || ''">
                  <template #activator="{ props }">
                    <span v-bind="props" class="record-group-text"
                      :class="{ 'text-decoration-line-through': item.transfer_record.deleted }">
                      {{ item.transfer_record.destpath || '' }}
                    </span>
                  </template>
                </v-tooltip>
              </div>
              <span class="record-group-cell record-group-fixed">
                {{ formatSeasonEpisode(item.transfer_record.season, item.transfer_record.episode) }}
              </span>
              <span class="record-group-cell record-group-fixed">
                {{ formatPartNumber(item.transfer_record.part_number) }}
              </span>
              <div class="tag-cell">
                <template v-if="item.extra_info?.tag">
                  <v-chip v-for="tag in item.extra_info.tag.split(',')" :key="tag" :color="getTagColor(tag)"
                    variant="flat" class="tag-chip" size="small">
                    {{ tag.trim() }}
                  </v-chip>
                </template>
              </div>
              <div class="record-group-cell">
                <span class="record-group-time">
                  {{ formatDateTime(item.transfer_record.updatetime) }}
                </span>
              </div>
              <div class="actions-cell">
                <VBtn
                  v-if="subtitleCount(item) > 0"
                  class="record-group-action"
                  :title="t('pages.subtitles.deliver')"
                  @click="deliverRecordSubtitle(item)"
                >
                  <VIcon icon="bx-captions" size="18" />
                </VBtn>
                <VBtn class="record-group-action" @click="showSelectedRecord(item)">
                  <VIcon icon="bx-edit-alt" size="18" />
                </VBtn>
                <VBtn class="record-group-action" @click="rerunThisRecord(item)">
                  <VIcon icon="bx-refresh" size="18" />
                </VBtn>
              </div>
            </div>
          </div>
        </div>
      </article>
      <div class="d-flex align-center justify-end px-4 py-3 w-100">
        <div class="d-flex align-center me-4">
          <span class="text-caption text-grey me-2">{{ t('pages.records.itemsPerPage') }}</span>
          <v-select :model-value="recordStore.itemsPerPage" :items="pageSizeOptions" density="compact"
            style="width: 80px" hide-details variant="plain" @update:model-value="handleItemsPerPageChange" />
          <div class="ms-4 text-caption text-grey">
            {{ t('pages.records.totalGroups', { count: pageTotal }) }}
          </div>
        </div>
        <v-pagination v-model="recordStore.currentPage" :length="pageLength" @update:model-value="handlePageChange"
          :total-visible="5" :show-first-last-page="false" />
      </div>
    </div>
  </VCard>

  <RecordDetailDialog />

  <VDialog :model-value="posterPreview !== null" max-width="96vw"
    @update:model-value="(open) => { if (!open) posterPreview = null }">
    <img v-if="posterPreview" class="record-poster-lightbox" :src="posterPreview.src" :alt="posterPreview.alt"
      @click="posterPreview = null">
  </VDialog>

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
  width: max(100%, 1560px) !important;
  min-width: 1560px !important;
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

.records-table :deep(.records-season-col) {
  width: 120px !important;
  min-width: 120px !important;
  max-width: 120px !important;
}

.records-table :deep(.records-datetime-col) {
  width: 184px !important;
  min-width: 184px !important;
  max-width: 184px !important;
  padding-inline: 8px !important;
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

.datetime-cell {
  font-variant-numeric: tabular-nums;
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
  max-width: 320px;
  min-width: 220px;
}

.delete-btn {
  white-space: nowrap;
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

.view-toggle {
  flex: 0 0 auto;
}

.record-groups {
  min-width: 0;
  overflow-x: hidden;
}

.record-group {
  display: flex;
  align-items: stretch;
  min-width: 0;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.record-group-entry {
  flex: 0 0 128px;
  width: 128px;
  display: flex;
  align-items: flex-start;
  padding: 4px;
  background: rgba(var(--v-theme-on-surface), 0.04);
  border-inline-end: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.record-poster {
  border-radius: 4px;
  cursor: zoom-in;
}

.record-poster-lightbox {
  display: block;
  max-width: 96vw;
  max-height: 90vh;
  margin: auto;
  cursor: zoom-out;
}

.record-group-main {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.record-group-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  padding: 12px 16px;
  background: rgba(var(--v-theme-on-surface), 0.06);
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.record-group-list {
  display: grid;
  grid-template-columns:
    32px
    40px
    minmax(0, 0.7fr)
    minmax(0, 1fr)
    72px
    96px
    160px
    184px
    86px;
  column-gap: 10px;
  min-width: 0;
  padding: 0 8px 0 12px;
  overflow: hidden;
}

.record-group-row {
  display: grid;
  grid-column: 1 / -1;
  grid-template-columns: subgrid;
  align-items: center;
  min-width: 0;
  padding: 6px 0;
}

.record-group-row + .record-group-row {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.record-group-columns {
  color: rgba(var(--v-theme-on-surface), 0.55);
  font-size: 12px;
  line-height: 1.2;
}

.record-group-columns span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-group-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  text-align: center;
}

.record-external-links {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 0 0 auto;
}

.record-external-link {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  line-height: 0;
  text-decoration: none;
}

.record-external-link img {
  display: block;
  width: 18px;
  height: 18px;
}

.record-number {
  flex: 0 0 auto;
  padding: 1px 8px;
  border-radius: 4px;
  background: rgb(var(--v-theme-primary-darken-1));
  color: rgb(var(--v-theme-on-primary));
  font-weight: 600;
  font-size: 0.8125rem;
  line-height: 1.7;
  letter-spacing: 0.03em;
}

.record-group-title {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  color: rgba(var(--v-theme-on-surface), 0.72);
  font-size: 0.875rem;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-group-subtitle {
  flex: 0 0 auto;
  margin-inline-start: auto;
}

.record-group-count {
  flex: 0 0 auto;
  margin-inline-start: 4px;
  white-space: nowrap;
}

.record-group-meta:not(:has(.record-group-subtitle)) .record-group-count {
  margin-inline-start: auto;
}

.record-group-cell {
  min-width: 0;
  overflow: hidden;
}

.record-group-filename,
.record-group-text,
.record-group-time {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-group-filename {
  text-align: start;
  background: none;
  border: 0;
  padding: 0;
  color: inherit;
  cursor: pointer;
}

.record-group-time {
  font-variant-numeric: tabular-nums;
  font-size: 0.8125rem;
}

.group-check {
  flex: 0 0 auto;
  width: 32px;
  margin-inline: 0;
  overflow: hidden;
}

.group-check :deep(.v-selection-control) {
  min-height: 32px;
}

.record-group-row .actions-cell {
  gap: 6px;
  justify-content: flex-end;
}

.record-group-action.v-btn {
  --v-btn-height: 24px;
  height: 24px;
  min-width: 40px;
  padding: 0 6px;
}

.record-group-row .tag-cell {
  min-width: 0;
  overflow: hidden;
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

  .record-group-meta {
    flex-wrap: wrap;
  }

  .record-group-title {
    flex-basis: 100%;
    white-space: normal;
  }
}
</style>
