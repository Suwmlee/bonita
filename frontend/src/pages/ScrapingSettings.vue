<script setup lang="ts">
import ScrapingSettingForm from "@/views/scraping/ScrapingSettingForm.vue"
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
