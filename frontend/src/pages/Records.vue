<script setup lang="ts">
import { TransRecordsService } from "@/client";
import { useTheme } from "vuetify"

const { global: globalTheme } = useTheme()

const AllRecords = ref()

async function getAllRecords() {
  let response = await TransRecordsService.getRecords()
  AllRecords.value = response.data
}

getAllRecords()

</script>

<template>
  <div>
    <VTable :theme="globalTheme.name.value" class="rounded-0">
      <thead>
        <tr>
          <th>
            srcpath
          </th>
          <th class="text-uppercase">
            destpath
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
        </tr>
      </thead>

      <tbody>
        <tr v-for="item in AllRecords" :key="item.transfer_record.id">
          <td>
            {{ item.transfer_record.srcpath }}
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
        </tr>
      </tbody>
    </VTable>
  </div>
</template>
