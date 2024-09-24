<script setup lang="ts">
import { useTaskStore } from "@/stores/task.store"
import { VCardActions } from "vuetify/components"

const taskStore = useTaskStore()

async function updateTasks() {
  taskStore.getAllTasks()
}

function addNewTask() {
  console.log("add new")
  taskStore.showAddTask()
}

function runTask(id: number) {
  taskStore.runTaskById(id)
}

const showSelectedTask = (item: any) => {
  taskStore.showUpdateTask(item)
}

onMounted(() => {
  updateTasks()
})
</script>

<template>
  <div>

    <p class="text-xl mb-6">
      Transfer Task
    </p>

    <VRow>
      <VCol v-for="data in taskStore.allTasks" :key="data.id" cols="12" md="6" lg="4" @click="showSelectedTask(data)">
        <VCard>
          <VCardItem>
            <VCardTitle>
              {{ data.name }}
            </VCardTitle>
          </VCardItem>

          <VCardText>
            <p class="clamp-text mb-0">
              {{ data.description }}
            </p>
          </VCardText>

          <VCardText class="d-flex justify-space-between align-center flex-wrap">
            <div class="text-no-wrap">
              <span class="ms-2">{{ data.source_folder }}</span>
            </div>
          </VCardText>
          <VCardActions class="justify-space-between">
            <VBtn type="submit" class="me-4" @click.stop="runTask(data.id)">
              立即执行
            </VBtn>
          </VCardActions>
        </VCard>
      </VCol>

      <VCol cols="12" md="6" lg="4" @click="addNewTask">
        <VCard>
          <VCardItem>
            <VCardTitle>
              Add Task
            </VCardTitle>
          </VCardItem>

          <VCardText>
            <p class="clamp-text mb-0">
              Add Task
            </p>
          </VCardText>

          <VCardText class="d-flex justify-space-between align-center flex-wrap">
            <div class="text-no-wrap">
              <span class="ms-2">+</span>
            </div>
          </VCardText>
        </VCard>
      </VCol>
    </VRow>
  </div>

  <TransferTaskDetailDialog />
</template>
