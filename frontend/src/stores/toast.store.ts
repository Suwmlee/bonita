import { defineStore } from 'pinia'

interface ToastState {
    /** 通知内容 */
    msg: string;
    /** 通知颜色 */
    color: string;
    /** 显示 */
    visible?: boolean;
    /** 是否显示关闭按钮 */
    showClose?:boolean;
    /** 超时时间 */
    timeout?: number;
    /** 防抖计时器 */
    debounceTimer?: NodeJS.Timeout | null
}


export const useToastStore = defineStore('toastStore', {
  state: ():ToastState => {
    return {
      msg: '',
      color: 'info',
      visible: false,
      showClose: true,
      timeout: 3000,
      debounceTimer: null
    }
  },
  actions: {
    /**
     * 显示通知
     * @param options 参数
     */
    open (options:ToastState) {
      this.msg = options.msg
      if (options?.color) {
        this.color = options.color
      }
      if (options?.timeout) {
        this.timeout = options.timeout
      }
      this.visible = true
      // 防抖
      if (this.debounceTimer) {
        clearTimeout(this.debounceTimer)
      }
      this.debounceTimer = setTimeout(() => {
        this.visible = false
      }, this.timeout)
    },
    /**
     * 成功通知
     * @param msg 消息
     */
    success (msg:string) {
      this.open({
        msg,
        color: 'success'
      })
    },
    /**
     * 错误通知
     * @param msg 消息
     */
    error (msg:string) {
      this.open({
        msg,
        color: 'error'
      })
    },
    /**
     * info通知
     * @param msg 消息
     */
    info (msg:string) {
      this.open({
        msg,
        color: 'info'
      })
    },
    /**
     * 警告通知
     * @param msg 消息
     */
    warning (msg:string) {
      this.open({
        msg,
        color: 'warning'
      })
    }
  }
})
