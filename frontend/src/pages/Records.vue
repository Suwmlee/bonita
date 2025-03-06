<script setup lang="ts">
import { useRecordStore } from "@/stores/record.store"
import { useTaskStore } from "@/stores/task.store"
import { VIcon } from "vuetify/components"

const recordStore = useRecordStore()
const taskStore = useTaskStore()

const searchQuery = ref("")
const selected = ref<number[]>([])
const tagColorMap = {
  中文字幕: "#FF0000",
  破解: "#FFA500",
} as const

// 删除确认对话框
const deleteDialog = ref(false)
const forceDelete = ref(false)

const getTagColor = (tag: string) => {
  return tagColorMap[tag.trim() as keyof typeof tagColorMap] || "grey"
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
    title: "name",
    align: "start" as "start" | "center" | "end",
    key: "transfer_record.srcname",
    width: 250,
  },
  {
    title: "path",
    align: "center" as "start" | "center" | "end",
    key: "transfer_record.srcpath",
    width: 200,
  },
  {
    title: "destpath",
    align: "center" as "start" | "center" | "end",
    key: "transfer_record.destpath",
    width: 200,
  },
  {
    title: "season",
    align: "center" as "start" | "center" | "end",
    key: "transfer_record.season",
    width: 100,
  },
  {
    title: "episode",
    align: "center" as "start" | "center" | "end",
    key: "transfer_record.episode",
    width: 100,
  },
  {
    title: "number",
    align: "center" as "start" | "center" | "end",
    key: "extra_info.number",
    width: 100,
  },
  {
    title: "tag",
    align: "center" as "start" | "center" | "end",
    key: "extra_info.tag",
    width: 100,
  },
  {
    title: "updatetime",
    align: "center" as "start" | "center" | "end",
    key: "transfer_record.updatetime",
    width: 120,
    sortable: true,
  },
  {
    title: "deadtime",
    align: "center" as "start" | "center" | "end",
    key: "transfer_record.deadtime",
    width: 120,
  },
  {
    title: "Actions",
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

async function initial() {
  recordStore.getRecords()
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

const confirmDelete = () => {
  recordStore.deleteRecords(selected.value, forceDelete.value)
  deleteDialog.value = false
  forceDelete.value = false
  // 清空选中项
  selected.value = []
}

watch(searchQuery, (newValue) => {
  // TODO: Implement search functionality
  // recordStore.getRecords({ search: newValue })
})

onMounted(() => {
  initial()
})
</script>

<template>
  <VCard>
    <div class="d-flex align-center mb-4 gap-4">
      <v-text-field v-model="searchQuery" label="搜索" hide-details density="compact" class="max-w-xs"
        prepend-inner-icon="mdi-magnify" clearable />
      <v-btn color="error" :disabled="selected.length === 0" prepend-icon="mdi-delete" @click="handleDelete">
        删除选中项 ({{ selected.length }})
      </v-btn>
    </div>

    <v-data-table v-model="selected" :headers="headers" :items="recordStore.records" item-value="transfer_record.id"
      show-select show-select-all select-strategy="page" :sort-by="sortBy">
      <template v-slot:item="{ item, columns, index }">
        <tr :class="{ 'deleted-row': item.transfer_record.deleted }">
          <td><v-checkbox v-model="selected" :value="item.transfer_record.id" multiple hide-details></v-checkbox></td>
          <td>
            <v-tooltip :text="item.transfer_record.srcname">
              <template v-slot:activator="{ props }">
                <span v-bind="props" class="text-truncate d-inline-block" style="max-width: 230px">
                  {{ item.transfer_record.srcname }}
                </span>
              </template>
            </v-tooltip>
          </td>
          <td>
            <v-tooltip :text="item.transfer_record.srcpath">
              <template v-slot:activator="{ props }">
                <span v-bind="props" class="text-truncate d-inline-block" style="max-width: 180px">
                  {{ item.transfer_record.srcpath }}
                </span>
              </template>
            </v-tooltip>
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
            <div class="d-flex align-center">
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
    </v-data-table>
  </VCard>

  <RecordDetailDialog />

  <!-- 删除确认对话框 -->
  <VDialog v-model="deleteDialog" max-width="500">
    <VCard>
      <VCardTitle class="text-h5">
        确认删除
      </VCardTitle>
      <VCardText>
        您确定要删除选中的 {{ selected.length }} 条记录吗？此操作无法撤销。
        <VCheckbox v-model="forceDelete" label="强制删除（忽略锁定状态）" class="mt-4" />
      </VCardText>
      <VCardActions>
        <VSpacer />
        <VBtn color="primary" variant="text" @click="deleteDialog = false">
          取消
        </VBtn>
        <VBtn color="error" @click="confirmDelete">
          删除
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

.max-w-xs {
  max-width: 300px;
}

.deleted-row {
  color: #9e9e9e;
  opacity: 0.85;
}
</style>
