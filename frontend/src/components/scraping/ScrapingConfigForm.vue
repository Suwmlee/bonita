<script lang="ts" setup>
import type {
  ScrapingConfigCreate,
  ScrapingConfigPublic,
} from "@/client/types.gen"
import { useScrapingStore } from "@/stores/scraping.store"
import { useI18n } from "vue-i18n"

interface Props {
  updateSetting?: ScrapingConfigPublic
}
const props = defineProps<Props>()

const scrapingStore = useScrapingStore()
const { t } = useI18n()

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

if (currentSetting.value.watermark_size == null) {
  currentSetting.value.watermark_size = 9
} else {
  currentSetting.value.watermark_size = Number(currentSetting.value.watermark_size)
}
if (currentSetting.value.watermark_location == null) {
  currentSetting.value.watermark_location = 2
} else {
  currentSetting.value.watermark_location = Number(currentSetting.value.watermark_location)
}

const watermarkLocations = computed(() => [
  { title: t("components.scraping.form.watermarkTopRight"), value: 0 },
  { title: t("components.scraping.form.watermarkTopLeft"), value: 1 },
  { title: t("components.scraping.form.watermarkBottomLeft"), value: 2 },
  { title: t("components.scraping.form.watermarkBottomRight"), value: 3 },
])

const watermarkSizePresets = [
  { value: 12, key: "components.scraping.form.watermarkSizeSmall" },
  { value: 9, key: "components.scraping.form.watermarkSizeMedium" },
  { value: 6, key: "components.scraping.form.watermarkSizeLarge" },
  { value: 4, key: "components.scraping.form.watermarkSizeXLarge" },
]

const watermarkSizes = computed(() => {
  const items = watermarkSizePresets.map((preset) => ({
    title: t(preset.key),
    value: preset.value,
  }))
  const current = Number(currentSetting.value?.watermark_size)
  if (Number.isFinite(current) && current > 0 && !watermarkSizePresets.some((preset) => preset.value === current)) {
    items.push({
      title: t("components.scraping.form.watermarkSizeCustom", { ratio: current }),
      value: current,
    })
  }
  return items
})

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
            <label for="name">{{ t('components.scraping.form.name') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentSetting.name" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="mobile">{{ t('components.scraping.form.description') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentSetting.description" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="mobile">{{ t('components.scraping.form.saveMetadata') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox v-model="currentSetting.save_metadata" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="mobile">{{ t('components.scraping.form.namingRule') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentSetting.naming_rule" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="scraping_sites">{{ t('components.scraping.form.scrapingSites') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentSetting.scraping_sites" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="location_rule">{{ t('components.scraping.form.locationRule') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentSetting.location_rule" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="max_title_len">{{ t('components.scraping.form.maxTitleLength') }}</label>
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
            <label for="morestoryline">{{ t('components.scraping.form.moreStoryline') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox v-model="currentSetting.morestoryline" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="extrafanart_enabled">{{ t('components.scraping.form.extraFanartEnabled') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox v-model="currentSetting.extrafanart_enabled" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="extrafanart_folder">{{ t('components.scraping.form.extraFanartFolder') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentSetting.extrafanart_folder" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="watermark_enabled">{{ t('components.scraping.form.watermarkEnabled') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox v-model="currentSetting.watermark_enabled" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="watermark_size">{{ t('components.scraping.form.watermarkSize') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VSelect
              v-model="currentSetting.watermark_size"
              :items="watermarkSizes"
              :hint="t('components.scraping.form.watermarkSizeHint')"
              persistent-hint
            />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="watermark_location">{{ t('components.scraping.form.watermarkLocation') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VSelect
              v-model="currentSetting.watermark_location"
              :items="watermarkLocations"
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- <VCol cols="12">
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
      </VCol> -->

      <!-- 👉 submit and reset button -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" />
          <VCol cols="12" md="9">
            <VBtn type="submit" class="me-4">
              {{ t('components.scraping.form.submit') }}
            </VBtn>
            <VBtn color="secondary" variant="tonal" type="reset">
              {{ t('components.scraping.form.reset') }}
            </VBtn>
          </VCol>
        </VRow>
      </VCol>
    </VRow>
  </VForm>
</template>
