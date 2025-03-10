import { createI18n } from 'vue-i18n'
import type { App } from 'vue'

// 导入语言包
import zh from './locales/zh'
import en from './locales/en'

// 获取浏览器语言
const getBrowserLanguage = () => {
  const browserLang = navigator.language.toLowerCase()
  return browserLang.startsWith('zh') ? 'zh' : 'en'
}

// 从本地存储中获取保存的语言设置，如果没有则使用浏览器语言
const getStoredLanguage = () => {
  return localStorage.getItem('language') || getBrowserLanguage()
}

// 创建 i18n 实例
const i18n = createI18n({
  legacy: false, // 使用 Composition API 模式
  locale: getStoredLanguage(),
  fallbackLocale: 'zh', // 默认语言为中文
  messages: {
    zh,
    en
  }
})

// 导出 i18n 实例供组件内使用
export { i18n }

// 默认导出插件安装函数
export default function (app: App) {
  app.use(i18n)
} 