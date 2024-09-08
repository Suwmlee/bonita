// Utilities
import { LoginService } from "@/client"
import type { Body_login_login_access_token as AccessToken, Token } from "@/client"
import { router } from "@/plugins/router"
import { handleError } from "@/utils"
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
      await LoginService.loginAccessToken({ formData: data })
        .then((response: Token) => {
          localStorage.setItem("access_token", response.access_token)
          // redirect to previous url or default to home page
          router.push(this.returnUrl || "/dashboard")
        })
        .catch((error) => {
          handleError(error)
        });
    },
    logout() {
      localStorage.removeItem("access_token")
      router.push("/login")
    },
  },
})
