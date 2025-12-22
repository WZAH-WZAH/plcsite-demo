# Frontend Architecture（内容站通用，不照抄任何站点）

目标：在不复制任何具体站点 UI 的前提下，搭一个“内容/社区站”常见的可扩展架构，后续可平滑加入视频区、推荐流、创作中心、通知等。

## 分层原则

- **app**：应用组装层（路由、全局布局、启动初始化）
- **layouts**：页面布局容器（Topbar/Sidebar/主内容区）
- **components**：可复用 UI 组件（不含业务）
- **views**：页面级组件（与路由一一对应，尽量薄）
- **services**：与后端交互（api 客户端、鉴权、错误格式化）
- **features（可选）**：按业务域拆分（auth/forum/resources/admin…），复杂后再引入

## 现在的工程（Vue + Vite）推荐目录

```
src/
  app/
    bootstrap.js            # 启动初始化（loadMe 等）
  layouts/
    MainLayout.vue          # 顶部 + 侧边 + 主内容
    TopBar.vue
    SideBar.vue
  services/
    api.js                  # axios 实例（统一 token / 401 清理）
    auth.js                 # 登录/注册/退出/me
  router/
    index.js                # 路由与守卫
  views/                    # 页面
  components/               # 复用 UI
  style.css
  main.js
  App.vue
```

> 说明：当前项目已存在 src/api.js、src/auth.js、src/router、src/views。可以逐步迁移到 services/ 与 layouts/，不需要一次性大改。

## 路由信息架构（参考内容站的“信息结构”，不是外观）

- 发现/内容：板块列表、板块帖子流、帖子详情
- 资源：资源列表、资源详情（后续可拆）
- 个人：我的（配额/等级/封禁提示）
- 管理：审核队列、用户封禁、审计日志

后续可扩展（先预留，不必马上做）：
- 首页：推荐流（latest/hot/following）
- 媒体：视频区（按分区/标签）
- 创作中心：投稿/草稿箱/数据

## 状态管理

当前使用 src/auth.js 的 reactive 状态即可。
当页面/功能更多时，再考虑 Pinia，把 auth、ui（sidebar 状态）、feed 分开。

## 交互与安全

- 所有“最终判断”以**后端**为准（比如密码强度、权限、配额）
- 前端只做辅助提示与友好错误展示

