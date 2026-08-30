import { client } from "@/client/client.gen"
import { useAuthStore } from "@/stores/auth.store"

// hook auth check
const authCheck = () => {
  client.instance.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        const errDetail = error.response?.data?.detail
        if (errDetail === "Could not validate credentials") {
          const authStore = useAuthStore()
          authStore.logout()
        }
      }
      return Promise.reject(error)
    },
  )
}

export default authCheck
