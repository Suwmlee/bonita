<script setup lang="ts">
import { useAuthStore } from "@/stores/auth.store"
import logo from "@images/logo.png"
import { useI18n } from "vue-i18n"

const form = ref({
  email: "",
  password: "",
  remember: false,
})

const { t } = useI18n() // 导入国际化工具函数

const isPasswordVisible = ref(false)

const login = () => {
  const authStore = useAuthStore()
  const { email, password } = form.value
  if (email && password) {
    authStore.login(email, password)
  }
}
</script>

<template>
  <div class="auth-wrapper d-flex align-center justify-center pa-4">
    <VCard class="auth-card pa-4 pt-7" max-width="448" min-width="320">
      <VCardItem class="justify-center">
        <template #prepend>
          <div class="d-flex">
            <VImg style="width: 38px;" :src="logo"></VImg>
          </div>
        </template>

        <VCardTitle class="text-2xl font-weight-bold">
          {{ t('app.title') }}
        </VCardTitle>
      </VCardItem>

      <VCardText class="pt-2">
        <!-- <h5 class="text-h5 mb-1">
          Welcome to Bonita! 👋🏻
        </h5> -->
        <p class="mb-0">
          {{ t('auth.welcomeMessage') }}
        </p>
      </VCardText>

      <VCardText>
        <VForm @submit.prevent="login">
          <VRow>
            <!-- email -->
            <VCol cols="12">
              <VTextField v-model="form.email" autofocus :placeholder="t('auth.enterEmail')" type="email" />
            </VCol>

            <!-- password -->
            <VCol cols="12">
              <VTextField v-model="form.password" :placeholder="t('auth.enterPassword')" :type="isPasswordVisible ? 'text' : 'password'"
                :append-inner-icon="isPasswordVisible ? 'bx-hide' : 'bx-show'"
                @click:append-inner="isPasswordVisible = !isPasswordVisible" />

              <!-- remember me checkbox -->
              <div class="d-flex align-center justify-space-between flex-wrap mt-1 mb-4">
                <VCheckbox v-model="form.remember" :label="t('auth.rememberMe')" />
              </div>

              <!-- login button -->
              <VBtn block type="submit">
                {{ t('auth.login') }}
              </VBtn>
            </VCol>

          </VRow>
        </VForm>
      </VCardText>
    </VCard>
  </div>
</template>

<style lang="scss">
@use "@core/scss/template/pages/page-auth.scss";
</style>
