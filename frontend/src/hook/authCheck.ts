import { OpenAPI } from "@/client/core/OpenAPI"
import { useAuthStore } from "@/stores/auth.store"

// hook auth check
const authCheck = () => {
  OpenAPI.interceptors.response.use(async (response) => {
    // Determine if it is an authentication error
    if (response.status === 401) {
      const errDetail = (response as any)?.data?.detail
      if (errDetail === "Could not validate credentials") {
        const authStore = useAuthStore()
        authStore.logout()
      }
    }

    return response // <-- must return response
  })
}

export default authCheck
