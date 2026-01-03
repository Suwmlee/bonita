<script setup lang="ts">
import { useScrapingStore } from "@/stores/scraping.store"

const scrapingStore = useScrapingStore()

async function initial() {
  scrapingStore.getAllSetting()
}

function addNewSetting() {
  console.log("add new")
  scrapingStore.showAddSetting()
}

function deleteConfig(id: number) {
  scrapingStore.deleteSetting(id)
}

const showSelectedSetting = (item: any) => {
  scrapingStore.showUpdateSetting(item)
}

onMounted(() => {
  initial()
})
</script>

<template>
  <div>

    <p class="text-xl mb-6">
      {{ $t('pages.scraping.title') }}
    </p>

    <VRow>
      <VCol v-for="data in scrapingStore.allSettings" :key="data.id" cols="12" sm="6" md="4" lg="3" xl="2"
        @click="showSelectedSetting(data)">
        <VCard>
          <VCardItem>
            <VCardTitle>
              {{ data.name }}
            </VCardTitle>
          </VCardItem>

          <VCardText>
            <p class="clamp-text mb-0">
              {{ data.description }}
            </p>
          </VCardText>

          <VCardText class="d-flex justify-space-between align-center flex-wrap">
            <div class="text-no-wrap">
              <span class="ms-2">{{ data.location_rule }}</span>
            </div>
          </VCardText>
          <VCardActions class="justify-space-between">
            <VBtn type="submit" class="me-4" @click.stop="deleteConfig(data.id)">
              <VIcon style="color: firebrick;" icon="bx-trash" size="22" />
            </VBtn>
          </VCardActions>
        </VCard>
      </VCol>

      <VCol cols="12" sm="6" md="4" lg="3" xl="2" @click="addNewSetting">
        <VCard style="height: 100%;">
          <VCardText class="d-flex flex-column align-center justify-center" style="height: 100%;">
            <VIcon icon="bx-plus" size="140" color="primary" />
          </VCardText>
        </VCard>
      </VCol>
    </VRow>
  </div>

  <ScrapingConfigDialog />
</template>
