<script setup lang="ts">
import { ScrapingSettingService } from "@/client"
import ScrapingSettingForm from "@/views/scraping/ScrapingSettingForm.vue"

async function getAllSettings() {
  const allSettings = await ScrapingSettingService.getAllSettings()
  console.log(allSettings)
}

onMounted(() => {
  getAllSettings()
})
</script>

<template>
  <div>
    <VRow>
      <VCol cols="12" md="6">
        <!-- 👉 Horizontal Form -->
        <VCard title="Scraping Setting">
          <VCardText>
            <ScrapingSettingForm />
          </VCardText>
        </VCard>
      </VCol>
    </VRow>
  </div>
</template>
