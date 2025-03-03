<script setup lang="ts">
import { MetadataPublic, MetadataService } from "@/client"
import { useTheme } from "vuetify"

const { global: globalTheme } = useTheme()

const metadata = ref<MetadataPublic[]>()
const showDialog = ref(false)
const selectedItem = ref<MetadataPublic | null>(null)

async function getMetadata() {
  const response = await MetadataService.getMetadata()
  metadata.value = response.data
}

function showEditDialog(item: MetadataPublic) {
  selectedItem.value = item
  showDialog.value = true
}

getMetadata()
</script>

<template>
  <div>
    <VRow>
      <VCol v-for="item in metadata" :key="item.id" cols="12" md="6" lg="4">
        <VCard height="400" class="d-flex flex-column" @click="showEditDialog(item)">
          <VCardItem>
            <VCardTitle>
              {{ item.number }}
            </VCardTitle>
          </VCardItem>

          <VCardText class="flex-grow-1">
            <p class="mb-2 text-truncate">
              <strong>Title:</strong> {{ item.title }}
            </p>
            <p class="mb-2">
              <strong>Actor:</strong> {{ item.actor }}
            </p>
            <p class="mb-2">
              <strong>Site:</strong> {{ item.site }}
            </p>
            <p class="mb-0 text-truncate">
              <strong>URL:</strong> {{ item.detailurl }}
            </p>
          </VCardText>

          <VCardText v-if="item.cover" class="d-flex justify-center" style="max-height: 200px;">
            <VImg :src="item.cover" height="180" contain />
          </VCardText>
        </VCard>
      </VCol>
    </VRow>

    <!-- Edit Dialog -->
    <VDialog v-model="showDialog" max-width="600px">
      <VCard>
        <VCardTitle>
          Edit Metadata
          <VSpacer></VSpacer>
          <VBtn icon @click="showDialog = false">
            <VIcon>mdi-close</VIcon>
          </VBtn>
        </VCardTitle>
        
        <VCardText v-if="selectedItem">
          <VForm @submit.prevent>
            <VTextField
              v-model="selectedItem.number"
              label="Number"
              class="mb-4"
            />
            <VTextField
              v-model="selectedItem.title"
              label="Title"
              class="mb-4"
            />
            <VTextField
              v-model="selectedItem.actor"
              label="Actor"
              class="mb-4"
            />
            <VTextField
              v-model="selectedItem.site"
              label="Site"
              class="mb-4"
            />
            <VTextField
              v-model="selectedItem.detailurl"
              label="URL"
              class="mb-4"
            />
            <VTextField
              v-model="selectedItem.cover"
              label="Cover URL"
              class="mb-4"
            />
          </VForm>
        </VCardText>

        <VCardActions>
          <VSpacer />
          <VBtn color="primary" @click="showDialog = false">
            Save
          </VBtn>
          <VBtn color="error" @click="showDialog = false">
            Cancel
          </VBtn>
        </VCardActions>
      </VCard>
    </VDialog>
  </div>
</template>

<style scoped>
.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
