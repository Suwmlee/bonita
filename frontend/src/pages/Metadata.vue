<script setup lang="ts">
import { MetadataService } from "@/client"
import { useTheme } from "vuetify"

const { global: globalTheme } = useTheme()

const metadata = ref()

async function getMetadata() {
  const response = await MetadataService.getMetadata()
  metadata.value = response.data
}

getMetadata()
</script>

<template>
  <div>
    <VTable :theme="globalTheme.name.value" class="rounded-0">
      <thead>
        <tr>
          <th>
            Number
          </th>
          <th class="text-uppercase">
            Title
          </th>
          <th class="text-uppercase">
            Actor
          </th>
          <th class="text-uppercase">
            Cover
          </th>
          <th class="text-uppercase">
            Site
          </th>
          <th class="text-uppercase">
            URL
          </th>
        </tr>
      </thead>

      <tbody>
        <tr v-for="item in metadata" :key="item.id">
          <td>
            {{ item.number }}
          </td>
          <td>
            {{ item.title }}
          </td>
          <td>
            {{ item.actor }}
          </td>
          <td>
            {{ item.cover }}
          </td>
          <td>
            {{ item.site }}
          </td>
          <td>
            {{ item.detailurl }}
          </td>
        </tr>
      </tbody>
    </VTable>
  </div>
</template>
