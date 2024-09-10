import DashboardPage from "@/pages/Dashboard.vue"
import LoginPage from "@/pages/Login.vue"
import ScrapingSettingsPage from "@/pages/ScrapingSettings.vue"
import TaskSetupPage from "@/pages/TaskSetup.vue"
import TransferTaskPage from "@/pages/TransferTask.vue"
import UserSettingsPage from "@/pages/UserSettings.vue"
import errorpage from "@/pages/[...error].vue"

export const routes = [
  { path: "/", redirect: "/dashboard" },
  {
    path: "/",
    component: () => import("@/layouts/default.vue"),
    children: [
      {
        path: "dashboard",
        meta: { requiresAuth: true },
        component: () => DashboardPage,
      },
    ],
  },
  {
    path: "/tasks/",
    component: () => import("@/layouts/default.vue"),
    children: [
      {
        path: "transfer",
        meta: { requiresAuth: true },
        component: () => TransferTaskPage,
      },
      {
        path: "setup",
        meta: { requiresAuth: true },
        component: () => TaskSetupPage,
      },
    ],
  },
  {
    path: "/settings/",
    component: () => import("@/layouts/default.vue"),
    children: [
      {
        path: "scraping",
        meta: { requiresAuth: true },
        component: () => ScrapingSettingsPage,
      },
      {
        path: "user",
        meta: { requiresAuth: true },
        component: () => UserSettingsPage,
      },
    ],
  },
  {
    path: "/",
    component: () => import("@/layouts/blank.vue"),
    children: [
      {
        path: "login",
        component: () => LoginPage,
      },
      {
        path: "/:pathMatch(.*)*",
        component: () => errorpage,
      },
    ],
  },
]
