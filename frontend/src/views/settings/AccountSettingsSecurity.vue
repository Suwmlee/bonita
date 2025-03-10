<script lang="ts" setup>
import { UserService } from "@/client"
import type { UpdatePassword } from "@/client/types.gen"
import { useI18n } from "vue-i18n"

const { t } = useI18n() // 导入国际化工具函数

const isCurrentPasswordVisible = ref(false)
const isNewPasswordVisible = ref(false)
const isConfirmPasswordVisible = ref(false)
const currentPassword = ref("")
const newPassword = ref("")
const confirmPassword = ref("")

const passwordRequirements = [
  t('auth.passwordMinLength'),
]

const changePasswd = async () => {
  const data: UpdatePassword = {
    current_password: currentPassword.value,
    new_password: newPassword.value,
  }
  const response = await UserService.updatePasswordMe({ requestBody: data })
  console.log(response)
}
</script>

<template>
  <VRow>
    <!-- SECTION: Change Password -->
    <VCol cols="12">
      <VCard :title="t('auth.changePassword')">
        <VForm>
          <VCardText>
            <!-- 👉 Current Password -->
            <VRow>
              <VCol cols="12" md="6">
                <!-- 👉 current password -->
                <VTextField v-model="currentPassword" :type="isCurrentPasswordVisible ? 'text' : 'password'"
                  :append-inner-icon="isCurrentPasswordVisible ? 'bx-hide' : 'bx-show'" :placeholder="t('auth.currentPassword')"
                  @click:append-inner="isCurrentPasswordVisible = !isCurrentPasswordVisible" />
              </VCol>
            </VRow>

            <!-- 👉 New Password -->
            <VRow>
              <VCol cols="12" md="6">
                <!-- 👉 new password -->
                <VTextField v-model="newPassword" :type="isNewPasswordVisible ? 'text' : 'password'"
                  :append-inner-icon="isNewPasswordVisible ? 'bx-hide' : 'bx-show'" autocomplete="on"
                  :placeholder="t('auth.newPassword')" @click:append-inner="isNewPasswordVisible = !isNewPasswordVisible" />
              </VCol>

              <VCol cols="12" md="6">
                <!-- 👉 confirm password -->
                <VTextField v-model="confirmPassword" :type="isConfirmPasswordVisible ? 'text' : 'password'"
                  :append-inner-icon="isConfirmPasswordVisible ? 'bx-hide' : 'bx-show'"
                  :placeholder="t('auth.confirmPassword')"
                  @click:append-inner="isConfirmPasswordVisible = !isConfirmPasswordVisible" />
              </VCol>
            </VRow>
          </VCardText>

          <!-- 👉 Password Requirements -->
          <VCardText>
            <p class="text-base font-weight-medium mt-2">
              {{ t('auth.passwordRequirements') }}
            </p>

            <ul class="d-flex flex-column gap-y-3">
              <li v-for="item in passwordRequirements" :key="item" class="d-flex">
                <div>
                  <VIcon size="7" icon="bxs-circle" class="me-3" />
                </div>
                <span class="font-weight-medium">{{ item }}</span>
              </li>
            </ul>
          </VCardText>

          <!-- 👉 Action Buttons -->
          <VCardText class="d-flex flex-wrap gap-4">
            <VBtn @click="changePasswd">{{ t('common.saveChanges') }}</VBtn>

            <VBtn type="reset" color="secondary" variant="tonal">
              {{ t('common.reset') }}
            </VBtn>
          </VCardText>
        </VForm>
      </VCard>
    </VCol>
    <!-- !SECTION -->
  </VRow>
</template>
