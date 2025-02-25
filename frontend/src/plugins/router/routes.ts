import blanklayout from "@/layouts/blank.vue"
import defaultlayout from "@/layouts/default.vue"
import DashboardPage from "@/pages/Dashboard.vue"
import RecordsPage from "@/pages/Records.vue"
import LoginPage from "@/pages/Login.vue"
import ScrapingSettingsPage from "@/pages/ScrapingSettings.vue"
import TaskSetupPage from "@/pages/TaskSetup.vue"
import TransferTaskPage from "@/pages/TransferTask.vue"
import MetadataPage from "@/pages/Metadata.vue"
import ToolsPage from "@/pages/Tools.vue"
import ServiceSettingsPage from "@/pages/ServiceSettings.vue"
import UserSettingsPage from "@/pages/UserSettings.vue"
import errorpage from "@/pages/[...error].vue"

export const routes = [
  { path: "/", redirect: "/dashboard" },
  {
    path: "/",
    component: defaultlayout,
    children: [
      {
        path: "dashboard",
        meta: { requiresAuth: true },
        component: DashboardPage,
      },
      {
        path: "records",
        meta: { requiresAuth: true },
        component: RecordsPage,
      },
      {
        path: "metadata",
        meta: { requiresAuth: true },
        component: MetadataPage,
      },
      {
        path: "tools",
        meta: { requiresAuth: true },
        component: ToolsPage,
      },
    ],
  },
  {
    path: "/tasks",
    redirect: "/tasks/transfer",
    component: defaultlayout,
    children: [
      {
        path: "transfer",
        meta: { requiresAuth: true },
        component: TransferTaskPage,
      },
      {
        path: "setup",
        meta: { requiresAuth: true },
        component: TaskSetupPage,
      },
    ],
  },
  {
    path: "/scraping",
    component: defaultlayout,
    children: [
      {
        path: "settings",
        meta: { requiresAuth: true },
        component: ScrapingSettingsPage,
      },
    ],
  },
  {
    path: "/settings",
    component: defaultlayout,
    children: [
      {
        path: "user",
        meta: { requiresAuth: true },
        component: UserSettingsPage,
      },
      {
        path: "service",
        meta: { requiresAuth: true },
        component: ServiceSettingsPage,
      },
    ],
  },
  {
    path: "/",
    component: blanklayout,
    children: [
      {
        path: "login",
        component: LoginPage,
      },
      {
        path: "/:pathMatch(.*)*",
        component: errorpage,
      },
    ],
  },
]
