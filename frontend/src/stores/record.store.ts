import { type RecordPublic, RecordService } from "@/client"

import { defineStore } from "pinia"

export const useRecordStore = defineStore("record-store", {
  state: () => ({
    records: [] as RecordPublic[],
    showDialog: false,
    editRecord: undefined as RecordPublic | undefined,
    totalRecords: 0,
    currentPage: 1,
    itemsPerPage: 10,
    loading: false,
  }),
  actions: {
    async getRecords(
      options: {
        page: number
        itemsPerPage: number
        search?: string
        taskId?: number
      } = {
        page: 1,
        itemsPerPage: 10,
      },
    ) {
      this.loading = true
      try {
        const skip = (options.page - 1) * options.itemsPerPage
        const limit = options.itemsPerPage
        const response = await RecordService.getRecords({
          skip,
          limit,
          search: options.search,
          taskId: options.taskId,
        })

        this.records = response.data
        this.totalRecords = response.count
        this.currentPage = options.page
        this.itemsPerPage = options.itemsPerPage

        return this.records
      } catch (error) {
        console.error("获取记录失败:", error)
        return []
      } finally {
        this.loading = false
      }
    },
    showUpdateRecord(data: RecordPublic) {
      this.editRecord = data
      this.showDialog = true
    },
    async updateRecord(data: RecordPublic) {
      const record = await RecordService.updateRecord({
        requestBody: data,
      })
      if (this.showDialog) {
        this.updateRecordById(data.transfer_record.id, data)
        this.showDialog = false
      }
    },
    async deleteRecords(ids: number[], force = false) {
      const response = await RecordService.deleteRecords({
        requestBody: ids,
        force: force,
      })
      if (response.success) {
        if (force) {
          // 如果force为true，直接从列表中移除这些记录
          this.records = this.records.filter(
            (record) => !ids.includes(record.transfer_record.id),
          )
        } else {
          // 如果force为false，只将记录标记为已删除
          // Use map instead of forEach for better performance with large arrays
          this.records = this.records.map((record) => {
            if (ids.includes(record.transfer_record.id)) {
              return {
                ...record,
                transfer_record: {
                  ...record.transfer_record,
                  deleted: true,
                },
              }
            }
            return record
          })
        }

        // 删除记录后刷新当前页，以保持页面数据完整
        await this.getRecords({
          page: this.currentPage,
          itemsPerPage: this.itemsPerPage,
        })
      }
    },
    updateRecordById(id: number, newValue: Partial<RecordPublic>) {
      const index = this.records.findIndex(
        (task) => task.transfer_record.id === id,
      )

      if (index !== -1) {
        this.records[index] = {
          ...this.records[index],
          ...newValue,
        }
      } else {
        console.error(`Record with id ${id} not found.`)
      }
    },
  },
})
