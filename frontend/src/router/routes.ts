export const routes = [
  { path: "/", redirect: "/dashboard" },
  {
    path: "/",
    component: () => import("@/layouts/default.vue"),
    children: [
      {
        path: "dashboard",
        meta: { requiresAuth: true },
        component: () => import("@/pages/dashboard.vue"),
      },
      {
        path: "settings",
        meta: { requiresAuth: true },
        component: () => import("@/pages/settings.vue"),
      },
    ],
  },
  {
    path: "/",
    component: () => import("@/layouts/blank.vue"),
    children: [
      {
        path: "login",
        component: () => import("@/pages/login.vue"),
      },
      {
        path: "/:pathMatch(.*)*",
        component: () => import("@/pages/[...error].vue"),
      },
    ],
  },
]
