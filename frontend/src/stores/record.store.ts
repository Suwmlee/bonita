import { type RecordPublic, RecordService } from "@/client"

import { defineStore } from "pinia"

export const useRecordStore = defineStore("record-store", {
  state: () => ({
    records: [] as RecordPublic[],
    showDialog: false,
    editRecord: undefined as RecordPublic | undefined,
  }),
  actions: {
    async getRecords() {
      const all = await RecordService.getRecords()
      this.records = all.data
      return this.records
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
