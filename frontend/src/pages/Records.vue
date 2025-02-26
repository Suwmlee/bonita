<script setup lang="ts">
import { useTheme } from "vuetify"
import { useRecordStore } from "@/stores/record.store";

const { global: globalTheme } = useTheme()

const recordStore = useRecordStore()

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
  <div>
    <VTable :theme="globalTheme.name.value" class="rounded-0">
      <thead>
        <tr>
          <th>
            name
          </th>
          <th class="text-uppercase">
            path
          </th>
          <th class="text-uppercase">
            updatetime
          </th>
          <th class="text-uppercase">
            deadtime
          </th>
          <th class="text-uppercase">
            isepisode
          </th>
          <th class="text-uppercase">
            number
          </th>
          <th class="text-uppercase">
            tag
          </th>
          <th class="text-uppercase">
            operation
          </th>
        </tr>
      </thead>

      <tbody>
        <tr v-for="item in recordStore.records" :key="item.transfer_record.id">
          <td>
            {{ item.transfer_record.srcname }}
          </td>
          <td>
            {{ item.transfer_record.destpath }}
          </td>
          <td>
            {{ item.transfer_record.updatetime }}
          </td>
          <td>
            {{ item.transfer_record.deadtime }}
          </td>
          <td>
            {{ item.transfer_record.isepisode }}
          </td>
          <td>
            {{ item.extra_info.number }}
          </td>
          <td>
            {{ item.extra_info.tag }}
          </td>
          <td>
            <VBtn type="submit" class="me-2" @click="showSelectedRecord(item)">
              编辑
            </VBtn>
          </td>
        </tr>
      </tbody>
    </VTable>
  </div>

  <RecordDetailDialog/>
</template>
