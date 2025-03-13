<template>
  <IconBtn @click="changeLanguage">
    <VIcon :icon="languages[currentLanguageIndex].icon" />
    <VTooltip
      activator="parent"
      open-delay="1000"
      scroll-strategy="close"
    >
      <span class="text-capitalize">{{ t(`language.${currentLanguageCode}`) }}</span>
    </VTooltip>
  </IconBtn>
</template>

<script setup lang="ts">
import { watch } from "vue"
import { useI18n } from "vue-i18n"

// 语言配置
const languages = [
  { code: "zh", name: "中文", icon: "mdi-translate" },
  { code: "en", name: "English", icon: "mdi-translate" },
]

const { locale: i18nLocale, t } = useI18n()

// 使用 useCycleList 循环遍历语言列表
const {
  state: currentLanguageCode,
  next: getNextLanguageCode,
  index: currentLanguageIndex,
} = useCycleList(
  languages.map((lang) => lang.code),
  { initialValue: i18nLocale.value },
)

// 切换语言
const changeLanguage = () => {
  const nextLang = getNextLanguageCode()
  i18nLocale.value = nextLang
  localStorage.setItem("language", nextLang)
}

// 监听语言变化（可能从其他地方修改）
watch(
  () => i18nLocale.value,
  (val) => {
    currentLanguageCode.value = val
  },
)
</script> 