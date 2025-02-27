import { type RecordPublic, TransRecordsService } from "@/client"

import { defineStore } from "pinia"

export const useRecordStore = defineStore("record-store", {
  state: () => ({
    records: [] as RecordPublic[],
    showDialog: false,
    editRecord: undefined as RecordPublic | undefined,
  }),
  actions: {
    async getRecords() {
      const all = await TransRecordsService.getRecords()
      this.records = all.data
      return this.records
    },
    showUpdateRecord(data: RecordPublic) {
      this.editRecord = data
      this.showDialog = true
    },
    async updateRecord(data: RecordPublic) {
      const record = await TransRecordsService.updateRecord({
        requestBody: data,
      })
      if (this.showDialog) {
        this.updateRecordById(data.transfer_record.id, data)
        this.showDialog = false
      }
    },
    async deleteRecord(idToRemove: number) {},
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
