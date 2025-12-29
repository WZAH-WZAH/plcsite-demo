import { createRouter, createWebHistory } from 'vue-router'
import { auth } from '../auth'

import AdminHomeView from '../views/AdminHomeView.vue'
import AdminAuditView from '../views/AdminAuditView.vue'
import AdminModerationView from '../views/AdminModerationView.vue'
import AdminUsersView from '../views/AdminUsersView.vue'
import BoardPostsView from '../views/BoardPostsView.vue'
import BoardsView from '../views/BoardsView.vue'
import HomeView from '../views/HomeView.vue'
import HotView from '../views/HotView.vue'
import LatestView from '../views/LatestView.vue'
import LoginView from '../views/LoginView.vue'
import MeView from '../views/MeView.vue'
import PostDetailView from '../views/PostDetailView.vue'
import PostNewView from '../views/PostNewView.vue'
import RegisterView from '../views/RegisterView.vue'
import SearchPostsView from '../views/SearchPostsView.vue'
import PostEditView from '../views/PostEditView.vue'
import NotificationsView from '../views/NotificationsView.vue'
import UserProfileView from '../views/UserProfileView.vue'
import TopicDetailView from '../views/TopicDetailView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // Home page: recommendation + board rows
    { path: '/', name: 'home', component: HomeView },

    // Hot rankings
    { path: '/hot', name: 'hot', component: HotView },

    // Latest updates feed
    { path: '/latest', name: 'latest', component: LatestView },

    // Boards list
    { path: '/boards', name: 'boards', component: BoardsView },
    { path: '/b/:slug', name: 'board-posts', component: BoardPostsView },

    { path: '/search', name: 'search', component: SearchPostsView },

    { path: '/topic/:name', name: 'topic-detail', component: TopicDetailView },

    { path: '/posts/new', name: 'post-new', component: PostNewView, meta: { requiresAuth: true } },
    { path: '/posts/:id/edit', name: 'post-edit', component: PostEditView, meta: { requiresAuth: true } },
    { path: '/posts/:id', name: 'post-detail', component: PostDetailView },

    { path: '/notifications', name: 'notifications', component: NotificationsView, meta: { requiresAuth: true } },

    { path: '/me', name: 'me', component: MeView, meta: { requiresAuth: true } },
    { path: '/u/:pid', name: 'user-profile', component: UserProfileView },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/register', name: 'register', component: RegisterView },

    { path: '/admin', name: 'admin', component: AdminHomeView, meta: { requiresAuth: true } },
    { path: '/admin/moderation', name: 'admin-moderation', component: AdminModerationView, meta: { requiresAuth: true } },
    { path: '/admin/users', name: 'admin-users', component: AdminUsersView, meta: { requiresAuth: true } },
    { path: '/admin/audit', name: 'admin-audit', component: AdminAuditView, meta: { requiresAuth: true } },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  if (to.meta.requiresAuth && !auth.isAuthed()) {
    return { name: 'login', query: { next: to.fullPath } }
  }

  // 懒加载 me：用于判断是否管理员
  if (auth.isAuthed() && !auth.state.me && !auth.state.loading) {
    await auth.loadMe()
  }

  if (to.path.startsWith('/admin')) {
    const me = auth.state.me
    if (!me || !me.is_staff) {
      return { name: 'home' }
    }
  }
})

export default router
