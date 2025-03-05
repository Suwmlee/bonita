<script lang="ts" setup>
import type {
  ScrapingConfigCreate,
  ScrapingConfigPublic,
} from "@/client/types.gen"
import { useScrapingStore } from "@/stores/scraping.store"

interface Props {
  updateSetting?: ScrapingConfigPublic
}
const props = defineProps<Props>()

const scrapingStore = useScrapingStore()

const { updateSetting } = props as {
  updateSetting: ScrapingConfigPublic
}
const currentSetting = ref<any>()

if (updateSetting) {
  currentSetting.value = { ...updateSetting }
} else {
  const createSetting: ScrapingConfigCreate = {
    name: "name",
    description: "descrip",
  }
  currentSetting.value = createSetting
}

async function handleSubmit() {
  console.log(currentSetting)
  if (updateSetting) {
    scrapingStore.updateSetting(currentSetting.value)
  } else {
    scrapingStore.addSetting(currentSetting.value)
  }
}
</script>

<template>
  <VForm @submit.prevent="handleSubmit">
    <VRow>
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="name">Name</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentSetting.name" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="mobile">description</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentSetting.description" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="mobile">save metadata</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox v-model="currentSetting.save_metadata" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="mobile">naming_rule</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentSetting.naming_rule" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="scraping_sites">Scraping Sites</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentSetting.scraping_sites" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="location_rule">Location Rule</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentSetting.location_rule" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="max_title_len">Max Title Length</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField 
              v-model="currentSetting.max_title_len" 
              type="number"
            />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="morestoryline">More Storyline</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox v-model="currentSetting.morestoryline" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="extrafanart_enabled">Extra Fanart Enabled</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox v-model="currentSetting.extrafanart_enabled" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="extrafanart_folder">Extra Fanart Folder</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentSetting.extrafanart_folder" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="watermark_enabled">Watermark Enabled</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox v-model="currentSetting.watermark_enabled" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="watermark_size">Watermark Size</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField 
              v-model="currentSetting.watermark_size" 
              type="number"
            />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="watermark_location">Watermark Location</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField 
              v-model="currentSetting.watermark_location" 
              type="number"
            />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="transalte_enabled">Translate Enabled</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox v-model="currentSetting.transalte_enabled" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="transalte_to_sc">Translate to SC</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox v-model="currentSetting.transalte_to_sc" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="transalte_values">Translate Values</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentSetting.transalte_values" />
          </VCol>
        </VRow>
      </VCol>

      <!-- 👉 submit and reset button -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" />
          <VCol cols="12" md="9">
            <VBtn type="submit" class="me-4">
              Submit
            </VBtn>
            <VBtn color="secondary" variant="tonal" type="reset">
              Reset
            </VBtn>
          </VCol>
        </VRow>
      </VCol>
    </VRow>
  </VForm>
</template>
