import axios from "axios"

export const handleError = (err: unknown, showToast: any) => {
  const data = axios.isAxiosError(err) ? err.response?.data : undefined
  const errDetail = (data as any)?.detail
  let errorMessage = errDetail || "Something went wrong."
  if (Array.isArray(errDetail) && errDetail.length > 0) {
    errorMessage = errDetail[0].msg
  }
  showToast.error(errorMessage)
}
