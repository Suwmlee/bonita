<script setup lang="ts">
import type { RecordPublic } from "@/client"
import { useRecordStore } from "@/stores/record.store"

const recordStore = useRecordStore()

const selected: RecordPublic[] = []
const headers = [
  {
    title: "name",
    align: "start",
    sortable: false,
    key: "transfer_record.srcname",
  },
  { title: "path", align: "end", key: "transfer_record.srcpath" },
  { title: "updatetime", align: "end", key: "transfer_record.updatetime" },
  { title: "deadtime", align: "end", key: "transfer_record.deadtime" },
  { title: "isepisode", align: "end", key: "transfer_record.isepisode" },
  { title: "number", align: "end", key: "extra_info.number" },
  { title: "tag", align: "end", key: "extra_info.tag" },
  { title: "Actions", key: "actions", sortable: false },
]

async function initial() {
  recordStore.getRecords()
}

const showSelectedRecord = (item: any) => {
  recordStore.showUpdateRecord(item)
}

onMounted(() => {
  initial()
})
</script>

<template>
  <v-data-table
    v-model="selected"
    :headers="headers"
    :items="recordStore.records"
    item-value="name"
    show-select>
    <template v-slot:item.actions="{ item }">
      <VBtn type="submit" class="me-2" @click="showSelectedRecord(item)">
        编辑
      </VBtn>
    </template>
  </v-data-table>

  <RecordDetailDialog />
</template>
