<script setup lang="ts">
import type { RecordPublic } from "@/client"
import { useRecordStore } from "@/stores/record.store"

const recordStore = useRecordStore()
const searchQuery = ref('')
const selected = ref<RecordPublic[]>([])
const tagColorMap = {
  '中文字幕': '#FF0000',
  '破解': '#FFA500',
} as const

const getTagColor = (tag: string) => {
  return tagColorMap[tag.trim() as keyof typeof tagColorMap] || 'grey'
}

const formatDateTime = (dateStr: string | null | undefined) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
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
    fixed: true,
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

async function initial() {
  recordStore.getRecords()
}

const showSelectedRecord = (item: any) => {
  recordStore.showUpdateRecord(item)
}

const handleDelete = () => {
  if (selected.value.length === 0) return
  // TODO: Implement delete functionality
  console.log('Delete items:', selected.value)
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
      show-select show-select-all select-strategy="page">
      <template v-slot:item.transfer_record.srcname="{ item }">
        <v-tooltip :text="item.transfer_record.srcname">
          <template v-slot:activator="{ props }">
            <span v-bind="props" class="text-truncate d-inline-block" style="max-width: 230px">
              {{ item.transfer_record.srcname }}
            </span>
          </template>
        </v-tooltip>
      </template>
      <template v-slot:item.transfer_record.srcpath="{ item }">
        <v-tooltip :text="item.transfer_record.srcpath">
          <template v-slot:activator="{ props }">
            <span v-bind="props" class="text-truncate d-inline-block" style="max-width: 180px">
              {{ item.transfer_record.srcpath }}
            </span>
          </template>
        </v-tooltip>
      </template>
      <template v-slot:item.transfer_record.season="{ item }">
        {{ item.transfer_record.season === -1 ? '' : item.transfer_record.season }}
      </template>
      <template v-slot:item.transfer_record.episode="{ item }">
        {{ item.transfer_record.episode === -1 ? '' : item.transfer_record.episode }}
      </template>
      <template v-slot:item.extra_info.tag="{ item }">
        <div v-if="item.extra_info?.tag" class="d-flex gap-1 flex-wrap">
          <v-chip v-for="tag in item.extra_info.tag.split(',')" :key="tag" :color="getTagColor(tag)" variant="flat"
            class="tag-chip" size="small">
            {{ tag.trim() }}
          </v-chip>
        </div>
      </template>
      <template v-slot:item.transfer_record.updatetime="{ item }">
        {{ formatDateTime(item.transfer_record.updatetime) }}
      </template>
      <template v-slot:item.transfer_record.deadtime="{ item }">
        {{ formatDateTime(item.transfer_record.deadtime) }}
      </template>
      <template v-slot:item.actions="{ item }">
        <VBtn type="submit" class="me-2" @click="showSelectedRecord(item)">
          编辑
        </VBtn>
      </template>
    </v-data-table>
  </VCard>

  <RecordDetailDialog />
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
</style>
