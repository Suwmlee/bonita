<script lang="ts" setup>
import type {
  ScrapingSettingCreate,
  ScrapingSettingPublic,
} from "@/client/types.gen"
import { useScrapingStore } from "@/stores/scraping.store"

interface Props {
  updateSetting?: ScrapingSettingPublic
}
const props = defineProps<Props>()

const scrapingStore = useScrapingStore()

const { updateSetting } = props as {
  updateSetting: ScrapingSettingPublic
}
const currentSetting = ref<any>()

if (updateSetting) {
  currentSetting.value = updateSetting
} else {
  const createSetting: ScrapingSettingCreate = {
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
