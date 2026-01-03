<script lang="ts" setup>
import {
  ExtraInfoPublic,
  type RecordPublic,
  RecordService,
  TransferRecordPublic,
} from "@/client"
import { useRecordStore } from "@/stores/record.store"
import { useTaskStore } from "@/stores/task.store"
import { useToastStore } from "@/stores/toast.store"
import { onMounted } from "vue"
import { useI18n } from "vue-i18n"

interface Props {
  updateRecord?: RecordPublic
}
const props = defineProps<Props>()

const recordStore = useRecordStore()
const taskStore = useTaskStore()
const { t } = useI18n()
const toastStore = useToastStore()

const { updateRecord } = props as {
  updateRecord: RecordPublic
}

const currentTransferRecord = ref<any>()
const currentExtraInfo = ref<any>()
const originalTopFolder = ref<string | null | undefined>("")
currentTransferRecord.value = { ...updateRecord.transfer_record }
currentExtraInfo.value = { ...updateRecord.extra_info }
originalTopFolder.value = currentTransferRecord.value.top_folder

onMounted(async () => {
  if (!taskStore.allTasks.length) {
    await taskStore.getAllTasks()
  }
})

async function handleSubmit() {
  const data: RecordPublic = {
    transfer_record: currentTransferRecord.value,
    extra_info: currentExtraInfo.value,
  }
  recordStore.updateRecord(data)
}

async function applyTopFolderToAll() {
  try {
    if (
      currentTransferRecord.value.srcfolder !== undefined &&
      currentTransferRecord.value.top_folder !== undefined
    ) {
      const response = await RecordService.updateTopFolder({
        srcfolder: currentTransferRecord.value.srcfolder,
        oldTopFolder: originalTopFolder.value || "",
        newTopFolder: currentTransferRecord.value.top_folder || "",
      })

      if (response?.success) {
        toastStore.success(t("components.record.form.topFolderUpdateSuccess"))
        originalTopFolder.value = currentTransferRecord.value.top_folder
      } else {
        const errorMessage =
          response?.message || t("components.record.form.topFolderUpdateError")
        toastStore.error(errorMessage)
      }
    } else {
      toastStore.error(t("components.record.form.topFolderMissingData"))
    }
  } catch (error) {
    console.error("Top folder update failed:", error)
    toastStore.error(t("components.record.form.topFolderUpdateError"))
  }
}
</script>

<template>
  <VForm @submit.prevent="handleSubmit">
    <VRow>
      <!-- Transfer Record 部分 -->
      <VCol cols="12">
        <div class="text-h6 mb-4">{{ t('components.record.form.transferRecord') }}</div>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>{{ t('components.record.form.sourceName') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <span>{{ currentTransferRecord.srcname }}</span>
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>{{ t('components.record.form.sourcePath') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <span>{{ currentTransferRecord.srcpath }}</span>
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>{{ t('components.record.form.destinationPath') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <span>{{ currentTransferRecord.destpath }}</span>
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>{{ t('components.record.form.taskId') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VSelect 
              v-model="currentTransferRecord.task_id"
              :items="taskStore.allTasks"
              item-title="name"
              item-value="id"
              :placeholder="t('components.record.form.selectTask')"
              :return-object="false"
              density="comfortable"
            />
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>{{ t('components.record.form.isEpisode') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox v-model="currentTransferRecord.isepisode" :label="t('components.record.form.isEpisode')" />
          </VCol>
        </VRow>

        <template v-if="currentTransferRecord.isepisode">
          <VRow no-gutters class="mb-4">
            <VCol cols="12" md="3" class="row-label">
              <label>{{ t('components.record.form.season') }}</label>
            </VCol>
            <VCol cols="12" md="9">
              <VTextField v-model="currentTransferRecord.season" type="number"
                :rules="[v => v >= -1 || t('components.record.form.seasonRule')]" />
            </VCol>
          </VRow>

          <VRow no-gutters class="mb-4">
            <VCol cols="12" md="3" class="row-label">
              <label>{{ t('components.record.form.episode') }}</label>
            </VCol>
            <VCol cols="12" md="9">
              <VTextField v-model="currentTransferRecord.episode" type="number"
                :rules="[v => v >= -1 || t('components.record.form.episodeRule')]" />
            </VCol>
          </VRow>
        </template>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>{{ t('components.record.form.status') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox v-model="currentTransferRecord.ignored" :label="t('components.record.form.ignored')" />
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>{{ t('components.record.form.topFolder') }}</label>
          </VCol>
          <VCol cols="12" md="9" class="d-flex align-center gap-2">
            <VTextField v-model="currentTransferRecord.top_folder" class="flex-grow-1" />
            <VBtn color="primary" size="small" @click="applyTopFolderToAll">
              {{ t('components.record.form.applyAll') }}
            </VBtn>
          </VCol>
        </VRow>
      </VCol>

      <!-- Extra Info 部分 -->
      <VCol cols="12">
        <div class="text-h6 mb-4">{{ t('components.record.form.extraInfo') }}</div>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>{{ t('components.record.form.number') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentExtraInfo.number" />
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>{{ t('components.record.form.tags') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentExtraInfo.tag" :placeholder="t('components.record.form.tagsPlaceholder')" 
              :hint="t('components.record.form.tagsHint')" persistent-hint />
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>{{ t('components.record.form.partNumber') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentExtraInfo.partNumber" type="number"
              :rules="[v => v >= 0 || t('components.record.form.partNumberRule')]" />
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>{{ t('components.record.form.crop') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox v-model="currentExtraInfo.crop" :label="t('components.record.form.cropPoster')" />
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>{{ t('components.record.form.specifiedSource') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentExtraInfo.specifiedsource" :placeholder="t('components.record.form.specifiedSource')" />
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>{{ t('components.record.form.specifiedUrl') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentExtraInfo.specifiedurl" :placeholder="t('components.record.form.specifiedUrl')" />
          </VCol>
        </VRow>
      </VCol>

      <!-- Submit 按钮 -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" />
          <VCol cols="12" md="9">
            <VBtn type="submit" color="primary" class="me-4">
              {{ t('components.record.form.save') }}
            </VBtn>
            <VBtn color="error" variant="outlined" @click="recordStore.showDialog = false">
              {{ t('components.record.form.cancel') }}
            </VBtn>
          </VCol>
        </VRow>
      </VCol>
    </VRow>
  </VForm>
</template>

<style scoped>
.row-label {
  display: flex;
  align-items: center;
  font-weight: 500;
  padding-right: 1rem;
}

@media (max-width: 960px) {
  .row-label {
    margin-bottom: 0.5rem;
  }
}
</style>
