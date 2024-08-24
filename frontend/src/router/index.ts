import { useAuthStore } from "@/stores/auth.store"
// Composables
import { createRouter, createWebHistory } from "vue-router"
import { routes } from "./routes"

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (to.matched.some((record) => record.meta.requiresAuth)) {
    if (!authStore.isLoggedIn()) {
      authStore.returnUrl = to.fullPath
      next({ path: "/login" })
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
