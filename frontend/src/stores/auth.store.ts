// Utilities
import { LoginService } from "@/client"
import type { Body_login_login_access_token as AccessToken } from "@/client"
import router from "@/router"
import { defineStore } from "pinia"

export const useAuthStore = defineStore("auth", {
  state: () => ({
    returnUrl: "",
  }),
  actions: {
    isLoggedIn() {
      return localStorage.getItem("access_token") !== null
    },
    async login(email: string, pwd: string) {
      const data: AccessToken = {
        username: email,
        password: pwd,
      }
      const response = await LoginService.loginAccessToken({ formData: data })
      localStorage.setItem("access_token", response.access_token)
      // redirect to previous url or default to home page
      router.push(this.returnUrl || "/dashboard")
    },
    logout() {
      localStorage.removeItem("access_token")
      router.push("/login")
    },
  },
})
