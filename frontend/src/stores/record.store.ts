import {
  type RecordGroupPublic,
  type RecordPublic,
  RecordService,
} from "@/client"

import { defineStore } from "pinia"

const ITEMS_PER_PAGE_KEY = "records-items-per-page"
const ITEMS_PER_PAGE_OPTIONS = [10, 15, 25, 50, 100]

function loadItemsPerPage(): number {
  const parsed = Number.parseInt(
    localStorage.getItem(ITEMS_PER_PAGE_KEY) ?? "",
    10,
  )
  return ITEMS_PER_PAGE_OPTIONS.includes(parsed) ? parsed : 10
}

// 列表和词条共用序号，后发出的请求作废仍在途的上一次。
let recordListRequestId = 0

export const useRecordStore = defineStore("record-store", {
  state: () => ({
    records: [] as RecordPublic[],
    groups: [] as RecordGroupPublic[],
    totalGroups: 0,
    showDialog: false,
    editRecord: undefined as RecordPublic | undefined,
    totalRecords: 0,
    currentPage: 1,
    itemsPerPage: loadItemsPerPage(),
    loading: false,
  }),
  actions: {
    async getRecords(
      options: {
        page: number
        itemsPerPage: number
        search?: string
        taskId?: number
        sortBy?: string
        sortDesc?: boolean
      } = {
        page: 1,
        itemsPerPage: loadItemsPerPage(),
      },
    ) {
      const requestId = ++recordListRequestId
      this.loading = true
      try {
        const skip = (options.page - 1) * options.itemsPerPage
        const limit = options.itemsPerPage
        const { data: response } = await RecordService.getRecords({
          skip,
          limit,
          search: options.search,
          task_id: options.taskId,
          sort_by: options.sortBy,
          sort_desc: options.sortDesc,
        })

        if (requestId !== recordListRequestId) return null

        this.records = response.data
        this.totalRecords = response.count
        this.currentPage = options.page
        this.itemsPerPage = options.itemsPerPage
        if (ITEMS_PER_PAGE_OPTIONS.includes(options.itemsPerPage)) {
          localStorage.setItem(ITEMS_PER_PAGE_KEY, String(options.itemsPerPage))
        }

        return this.records
      } catch (error) {
        if (requestId !== recordListRequestId) return null
        console.error("获取记录失败:", error)
        return []
      } finally {
        if (requestId === recordListRequestId) {
          this.loading = false
        }
      }
    },
    async getRecordGroups(
      options: {
        page: number
        itemsPerPage: number
        search?: string
        taskId?: number
        sortBy?: string
        sortDesc?: boolean
      } = {
        page: 1,
        itemsPerPage: loadItemsPerPage(),
      },
    ) {
      const requestId = ++recordListRequestId
      this.loading = true
      try {
        const skip = (options.page - 1) * options.itemsPerPage
        const limit = options.itemsPerPage
        const { data: response } = await RecordService.getRecordGroups({
          skip,
          limit,
          search: options.search,
          task_id: options.taskId,
          sort_by: options.sortBy,
          sort_desc: options.sortDesc,
        })

        if (requestId !== recordListRequestId) return null

        this.groups = response.data
        this.totalGroups = response.count
        this.currentPage = options.page
        this.itemsPerPage = options.itemsPerPage
        if (ITEMS_PER_PAGE_OPTIONS.includes(options.itemsPerPage)) {
          localStorage.setItem(ITEMS_PER_PAGE_KEY, String(options.itemsPerPage))
        }

        return this.groups
      } catch (error) {
        if (requestId !== recordListRequestId) return null
        console.error("获取番号词条失败:", error)
        return []
      } finally {
        if (requestId === recordListRequestId) {
          this.loading = false
        }
      }
    },
    showUpdateRecord(data: RecordPublic) {
      this.editRecord = data
      this.showDialog = true
    },
    async updateRecord(data: RecordPublic) {
      const { data: updated } = await RecordService.updateRecord({
        recordPublic: data,
      })
      if (this.showDialog) {
        this.updateRecordById(data.transfer_record.id, updated ?? data)
        this.showDialog = false
      }
    },
    async deleteRecords(ids: number[], force = false) {
      const { data: response } = await RecordService.deleteRecords({
        body: ids,
        force: force,
      })
      return Boolean(response.success)
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
      }

      let foundInGroup = index !== -1
      for (const group of this.groups) {
        const groupIndex = group.records.findIndex(
          (record) => record.transfer_record.id === id,
        )
        if (groupIndex === -1) continue
        group.records[groupIndex] = {
          ...group.records[groupIndex],
          ...newValue,
        }
        foundInGroup = true
      }

      if (!foundInGroup) {
        console.error(`Record with id ${id} not found.`)
      }
    },
  },
})
