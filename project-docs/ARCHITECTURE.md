# coding-log-web 架构说明

> 面向后续开发/迭代的维护者与 AI agent。
> 核对时间：2026-10-26；核对基线：`master` @ `c3874ef`（接手时两端一致；本轮文档/构建修复提交尚未部署到 Mac mini）。
> 本次核对范围：`docs/.vuepress/config.ts`、`enhanceApp.js`、`components/`、`backend/travel_assistant/`、`nginx/server/*.conf`、两端运行进程与监听端口。

## 1. 项目定位

个人技术博客 + 结构化知识库（站点标题「三木 vlog」）。站点本身是纯静态的：内容全部是 `docs/` 下的 Markdown，没有内容数据库。

完整运行环境由三部分组成：

1. **静态站点**：VuePress 1 + vdoing 主题，当前线上以 `vuepress dev` 常驻运行。
2. **评论服务**：自建 Artalk（Go 二进制 + SQLite），与站点同源，通过 nginx `/api/` 与 `/sidebar/` 反代。
3. **旅行助手**：`backend/travel_assistant` 的 FastAPI 服务，提供行程规划与高德 JS API 安全密钥代理。

> 历史迁移说明：评论早期使用 `vuepress-plugin-comment` + Gitalk（GitHub Issues），2026-10 已迁移到自建 Artalk；旧配置与账号信息仅保留在 git 历史中，当前代码不再加载 Gitalk。

## 2. 技术栈

| 层 | 选型 | 版本/位置 | 说明 |
| --- | --- | --- | --- |
| 站点框架 | VuePress | 1.8.3（Vue 2） | 经典 VuePress 1.x，Webpack 4 |
| 主题 | vuepress-theme-vdoing | 1.12.9（npm 包） | 知识库 + 博客双形态 |
| 配置 | TypeScript | `docs/.vuepress/config.ts` | 主题支持 TS 配置 |
| 运行时 | Node.js | 要求 >=18；实测 v24.22.1 / npm 11.19.1 | 脚本强制 `NODE_OPTIONS=--openssl-legacy-provider` |
| 评论前端 | Artalk | `artalk@^2.10.1`（package.json） | `enhanceApp.js` 动态挂载 `#artalk-comments` |
| 评论后端 | Artalk Server | `/Users/mac/artalk/artalk`（Mac mini） | `127.0.0.1:23366`，SQLite |
| 旅行助手 | FastAPI + uvicorn | `backend/travel_assistant/` | `127.0.0.1:8090`，规则版规划器 |
| 搜索 | vuepress-plugin-thirdparty-search | 已启用 | 不加载全文索引，只跳转外部搜索 |
| SEO/统计 | sitemap、百度自动推送、百度统计 | 已启用 | 依赖 `WEB_SITE` 与 hm 码 |
| 部署 | nginx + frp + 常驻 dev server | Mac mini | 见第 3、7 节 |

常用插件：`one-click-copy`（代码复制）、`demo-block`（可运行示例）、`zooming`（图片放大）、`@vuepress/last-updated`（git 时间）。评论插件 `vuepress-plugin-comment` 已不再启用。

## 3. 仓库与运行拓扑

### 3.1 副本与仓库

| 角色 | 位置 | 说明 |
| --- | --- | --- |
| 开发副本 | MacBook 用户目录下的 `coding-log-web`（实际路径含用户名） | 当前主要编辑副本，`master` |
| 线上副本 | `/Users/mac/coding-log-web`（Mac mini） | nginx 反代目标，独立 clone；只读运行，不直接编辑 |
| 远端仓库 | `git@github.com:pyeden/coding-log-web.git` | 分支 `master` |

**固定分工（2026-10-25 确定，长期有效）：所有开发只在 MacBook 上进行；Mac mini 仅负责部署与运行，不在 Mac mini 上编辑代码或内容。**

### 3.2 公网到服务

```
浏览器 https://seres-ai.com
  → DNS 解析 8.137.118.223
  → frps :443
  → frpc tcp :8888（transport.proxyProtocolVersion = "v2"）
  → nginx :8888（TLS 终止，ssl + proxy_protocol，还原真实 IP）
  → 按 location 分发：
       /            → 127.0.0.1:8080  vuepress dev
       /api/travel/ → 127.0.0.1:8090  旅行助手 FastAPI
       /_AMapService/ → 127.0.0.1:8090 高德代理
       /api/        → 127.0.0.1:23366 Artalk
       /sidebar/    → 127.0.0.1:23366 Artalk 管理面板
       /openclaw、/__openclaw__/ → 127.0.0.1:18789 OpenClaw Gateway

浏览器 http://seres-ai.com
  → frps :80 → frpc tcp :8887 → nginx :8887 → 301 https
```

- frpc 配置在 Mac mini：`/Users/mac/frp_0.68.0_darwin_amd64/frpc.toml`；本机进程为 `frpc -c .../frpc.toml`。
- nginx 主配置 `/usr/local/etc/nginx/nginx.conf` 通过 `include /Users/mac/coding-log-web/nginx/server/*;` 加载仓库内配置。
- `www.seres-ai.com` 另有 `openclaw-sandbox.conf`：`/mcp-app-sandbox` → `127.0.0.1:18790`，其余路径仍回落 8080。

### 3.3 nginx location 与优先级（`nginx/server/https.conf`）

nginx 的前缀 location 采用**最长匹配优先**，与书写顺序无关；正则 location 在前缀匹配之后再评估。因此 `/api/travel/` 天然优先于 `/api/`，但**必须保留这条更长的 location**，否则旅行助手请求会被 Artalk 的 `/api/` 接管。

| location | 上游 | 作用 | 备注 |
| --- | --- | --- | --- |
| `/sidebar/` | `127.0.0.1:23366` | Artalk 管理面板 | 需要 Artalk 管理员账号 |
| `/_AMapService/` | `127.0.0.1:8090` | 高德 JS API 安全密钥代理 | 由 FastAPI 转发到 `restapi.amap.com` |
| `/api/travel/` | `127.0.0.1:8090` | 旅行助手 API | 最长前缀，优先级高于 `/api/` |
| `/api/` | `127.0.0.1:23366` | Artalk API | 同源评论的关键 |
| `/sockjs-node/` | `127.0.0.1:8080` | webpack-dev-server HMR WebSocket | 改成静态托管后可删除 |
| `~* \.hot-update\.(js\|json)$` | `127.0.0.1:8080` | HMR 增量包 | 正则；`Cache-Control: no-store` |
| `/` | `127.0.0.1:8080` | 博客主站 | 静态托管后改为 `root` + `try_files` |
| `/openclaw` | `127.0.0.1:18789` | OpenClaw Gateway | 前缀匹配，长于 `/` |
| `/__openclaw__/` | `127.0.0.1:18789` | 组件 iframe / Canvas 绝对路径 | 不转发会白屏 |

`listen 8888 ssl proxy_protocol` 要求连接方先发送 PROXY protocol 头，所以**不能直接用 `curl https://127.0.0.1:8888` 自测**（会握手失败）；应通过 `https://seres-ai.com` 或经 frpc 验证。

### 3.4 配套服务运行方式

**Artalk（23366）**

- 工作目录：`/Users/mac/artalk`；二进制 `./artalk`；配置 `config.yml`。
- 数据库：`/Users/mac/artalk/data/artalk.db`（SQLite）。
- 关键配置：`host: 127.0.0.1`、`port: 23366`、`site_default: 三木 vlog`、`site_url: https://seres-ai.com`、`locale: zh-CN`、`timezone: Asia/Shanghai`。
- 启动方式：launchctl 作业 `ai.openclaw.artalk`，命令等价于 `cd /Users/mac/artalk && ./artalk server -c config.yml >> server.log 2>&1`。该作业当前是 `launchctl submit` 的临时注册（`type = Submitted`），**未找到持久化 plist**，注销/重启后需要重新提交（见风险清单）。
- 验证码：`captcha.enabled: true`，类型 `image`，`action_limit: 3`（同一会话约 3 次操作后要求验证码）。
- 管理员账号/密码：**不在仓库内，存放位置待确认**；不要写入代码或文档。

**旅行助手（8090）**

- 代码：`backend/travel_assistant/`；入口 `app.py`；依赖 `requirements.txt`（fastapi / uvicorn / pydantic）。
- 虚拟环境：Mac mini 上为 `backend/travel_assistant/.venv`（gitignore）。
- 路由：
  - `GET /api/travel/health` → `{"status":"ok","service":"travel-assistant","version":"1.0.0"}`
  - `GET /api/travel/` → 服务信息
  - `POST /api/travel/plan` → 行程规划
  - `GET|POST /_AMapService/{path:path}` → 高德 Web 服务代理（仅允许 `v3/`、`v4/`、`v5/`、`ws/` 前缀）
- 启动/守护：LaunchAgent `ai.openclaw.travel-api`（`~/Library/LaunchAgents/ai.openclaw.travel-api.plist`），`RunAtLoad` + `KeepAlive`，日志 `backend/travel_assistant/server.log`。
- 环境变量：读取仓库根 `.env`（不提交）：`AMAP_WEB_KEY`、`AMAP_WEB_SECRET`、`AMAP_JS_KEY`、`AMAP_SECURITY_CODE`。
- 前端：`docs/.vuepress/components/TravelAssistant.vue`，在 `docs/08.项目/01.旅行助手.md` 中以 `<TravelAssistant />` 使用。

## 4. 目录结构

```
coding-log-web/
├── docs/                      # VuePress sourceDir，站点全部内容
│   ├── .vuepress/
│   │   ├── config.ts          # 主配置：站点、导航、主题、插件、devServer 代理
│   │   ├── enhanceApp.js      # Artalk 挂载、按钮修复、评论兜底、卡片倾斜
│   │   ├── components/        # TravelAssistant.vue、ProjectShowcase.vue
│   │   ├── config/            # sidebar.js（示例/未使用）、htmlModules.ts、baiduCode.ts
│   │   ├── public/            # 原样拷贝的静态资源（img、CNAME）
│   │   ├── styles/            # palette.styl、index.styl、design-system.styl
│   │   ├── plugins/love-me/   # 本地插件（当前未在 config 中启用）
│   │   └── dist/              # 构建产物，gitignore
│   ├── index.md               # 首页
│   ├── 00.目录页/             # Catalogue 目录页（/web/、/ui/、/projects/ 等）
│   ├── 01.前端/ … 06.收藏夹/   # 结构化知识库栏目
│   ├── 07.hello_agents/       # 《Hello-Agents》书籍（当前均为编号 md，无 docsify 残留）
│   ├── 08.项目/               # 项目页，01.旅行助手.md
│   ├── @pages/                # archives/categories/tags 索引页（构建时自动维护）
│   ├── _posts/                # 碎片化博客文章（sidebar: auto）
│   └── 《…》笔记/             # 成体系的学习笔记栏目
├── backend/
│   └── travel_assistant/      # FastAPI 旅行助手（app.py、planner.py、data.py、models.py、requirements.txt）
├── vdoing/                    # 主题源码副本 1.12.9 —— 当前未启用
├── utils/                     # check.js、editFrontmatter.js、baiduPush.js、config.yml
├── nginx/
│   ├── nginx.conf             # 参考用主配置
│   ├── server/                # default.conf、https.conf、openclaw-sandbox.conf（线上 include）
│   ├── cert/                  # 证书，gitignore
│   └── acme/                  # ACME 相关
├── .github/workflows/         # ci.yml（gh-pages 部署）、baiduPush.yml
├── deploy.sh                  # 本地 build 后强推 gh-pages（模板遗留）
├── package.json
├── .env                       # 高德 Key（gitignore，不提交）
└── project-docs/              # 本套维护文档（不参与站点构建）
```

**`vdoing/` 不是生效代码。** `config.ts` 写的是 `theme: 'vdoing'`，VuePress 从 `node_modules/vuepress-theme-vdoing` 加载主题；本地 `vdoing/` 只是源码参考。只有把配置改成 `theme: resolve(__dirname, '../../vdoing')` 才会生效。

## 5. 内容模型与路由

### 5.1 侧边栏（structured sidebar）

主题开启 `sidebar: 'structuring'`，构建时由主题包内的侧边栏生成器扫描：

- 只扫描 `docs/` 的**一级目录**（排除 `.vuepress`、`@pages`），目录名即 sidebar 的 key。
- 目录和文件必须以「数字.」开头：数字决定排序（同级唯一，重复会覆盖并告警），非数字项会被跳过并输出 warning。
- 显示标题优先取 frontmatter `title`，否则取去掉数字前缀后的文件名/目录名。
- `_posts/` 不生成结构化侧边栏，由文章内的 `sidebar: auto` 接管。
- 目录页（`pageComponent.name: Catalogue`）会登记 `catalogueData`，供面包屑使用。

改动目录结构或新增栏目后，需要重启 dev server 才会重新生成侧边栏。

### 5.2 分类、标签、归档

- 非 `_posts` 文章：未显式写 `categories` 时，按 `docs/` 之后的目录层级自动生成（去掉「数字.」前缀）。
- `_posts` 文章：取 `_posts/<分类>/` 作为分类，没有子目录时用 `categoryText`（默认「随笔」）。
- `@pages/` 下的分类/标签/归档页由主题在启动/构建时自动创建或删除，不要手写。
- 只有 `article !== false` 的页面才参与分类、标签、归档。

### 5.3 永久链接（permalink）

- frontmatter 的 `permalink` 优先，URL 与文件路径解耦。
- 缺失时主题自动生成 `/pages/<6位十六进制>/`（随机，不保证可读）。
- 现有约定：文章多为 `/pages/xxxxxx/`；栏目落地页用语义化路径（`/web/`、`/note/git/`、`/about/`、`/archives/`、`/categories/`、`/tags/`、`/projects/`、`/ai/`）。
- **permalink 一经发布不要修改**：外链会断；Artalk 按页面 path 关联评论，改了 path 后旧评论不会出现在新地址。

### 5.4 页面类型

| 类型 | 位置 | 关键 frontmatter |
| --- | --- | --- |
| 首页 | `docs/index.md` | `home: true`、`heroText`、`features` |
| 栏目目录页 | `docs/00.目录页/*.md` | `pageComponent: {name: Catalogue, data: {path, imgUrl, description}}`、`article: false` |
| 索引页 | `docs/@pages/*.md` | `archivesPage/tagsPage/categoriesPage: true`（自动生成） |
| 博客文章 | 任意栏目下 | `title/date/permalink/categories/tags` |
| 碎片文章 | `docs/_posts/<分类>/*.md` | `sidebar: auto`、`<!-- more -->` |
| 独立页 | 如 `05.关于/01.关于.md` | `sidebar: false`、`article: false` |
| 项目页 | `00.目录页/06.项目.md`（`/projects/`） | 渲染 `<ProjectShowcase />` |
| 旅行助手 | `08.项目/01.旅行助手.md` | 渲染 `<TravelAssistant />` |

评论挂载条件（`enhanceApp.js`）：页面不是首页、`article !== false`、`comment !== false` 且 `comments !== false`。

## 6. 构建流水线

```
npm run dev
├─ predev: node utils/check.js dev   # 平台/脚本检查
├─ predev: vdoing                    # 检查 Node >= 18
└─ node --max_old_space_size=4096 ./node_modules/vuepress/cli.js dev docs
   → http://localhost:8080

npm run build
├─ prebuild: 同上
└─ vuepress build docs
   → docs/.vuepress/dist（gitignore）
```

启动/构建时主题钩子依次执行：

1. `setFrontmatter`：补齐 `title/date/permalink/categories/tags`，并合并 `extendFrontmatter`（当前注入 `author: xugaoyi`）。
2. `getSidebarData`：生成结构化侧边栏与目录页元数据。
3. `createPage/deletePage`：按 `category/tag/archive` 开关维护 `@pages/`。

Markdown 配置：`lineNumbers: true`；`extractHeaders: h2–h6`（侧边栏可显示到 h6，但 `sidebarDepth: 2`）。

`config.ts` 的 `devServer.proxy` 把 `/api/travel`、`/_AMapService` 转发到 8090，把 `/api`、`/sidebar` 转发到 23366——本地 `npm run dev` 不依赖 nginx 也能联调评论和旅行助手。

## 7. 部署与 CI

### 7.1 固定发布流程（MacBook → Mac mini）

**所有开发都在 MacBook 完成；Mac mini 是部署/运行机，不接受直接编辑。**

1. MacBook 修改、提交并推送 `master`。
2. Mac mini 上 `git pull --ff-only`（目录 `/Users/mac/coding-log-web`）。
3. 前端内容/配置：常驻 `vuepress dev` 热更新；改了 `config.ts`、新增一级目录，需重启 8080 进程。
4. 旅行助手后端：改动 `backend/travel_assistant/` 后需 `launchctl kickstart -k gui/$(id -u)/ai.openclaw.travel-api`（或卸载/加载 plist）重启服务。
5. Artalk：配置/二进制在 `/Users/mac/artalk`，**不在本仓库**，发布流程不涉及。
6. nginx 配置：仓库内 `nginx/server/*.conf` 被主配置 include；改完先 `nginx -t`，再 reload。属于高风险操作。

### 7.2 模板遗留的发布方式（当前未使用）

- `deploy.sh`：本地 `npm run build`，进入 `docs/.vuepress/dist`，`git init` 后强推 `gh-pages`。
- `.github/workflows/ci.yml`：`master` push → Node 18 → `yarn build` → 强推 `gh-pages`。
- `.github/workflows/baiduPush.yml`：push 及每天 23:00 UTC 运行 `npm run baiduPush`，生成 `urls.txt` 后推送给百度。
- `vercel.json`：只声明 `/assets/js|css` 的 immutable 缓存头，本地 nginx 未使用。

> 判断改动是否需要同步线上时，以第 7.1 节为准；`gh-pages` 产物不是当前线上来源。

## 8. 数据流

### 8.1 内容

```
Markdown（含 frontmatter）
  → VuePress 读取 + 主题钩子补全元数据/侧边栏
  → webpack 编译（Vue 2 运行时 + 预渲染 HTML）
  → docs/.vuepress/dist 或 dev server 内存产物
  → nginx 反代
  → 浏览器
```

### 8.2 评论（Artalk）

```
浏览器文章页
  → enhanceApp.js 在 .theme-vdoing-content 内挂载 #artalk-comments
  → Artalk JS（server = window.location.origin，site = 三木 vlog）
  → nginx /api/ → 127.0.0.1:23366
  → Artalk → SQLite /Users/mac/artalk/data/artalk.db
```

管理面板：`https://seres-ai.com/sidebar/` → nginx → 23366。主题切换时 `enhanceApp.js` 通过 MutationObserver 同步 Artalk 深浅色。

### 8.3 旅行助手与高德

```
TravelAssistant.vue
  → POST /api/travel/plan
  → nginx /api/travel/ → 127.0.0.1:8090
  → planner.py（规则版行程/预算）→ 可选高德 Web 服务（AMAP_WEB_KEY/SECRET）
  → JSON 返回前端

高德 JS API（地图）
  → /_AMapService/{path}
  → nginx → 127.0.0.1:8090 → https://restapi.amap.com
```

## 9. 外部依赖与配置项

| 项 | 当前值 | 位置 |
| --- | --- | --- |
| 站点域名常量 | `xugaoyi.com`（模板残留，与实际域名不符） | `config.ts` 顶部 `DOMAIN_NAME`/`WEB_SITE` |
| 站点标题 | 三木 vlog | `locales['/'].title` |
| 导航仓库链接 | `pyeden` | `themeConfig.repo` |
| 博主/作者 | Evan Xu / xugaoyi（链接指向 pyeden） | `blogger`、`author`、`extendFrontmatter` |
| 评论站点名 | 三木 vlog | `enhanceApp.js` 的 `ARTALK_SITE`；Artalk `site_default` |
| Artalk 服务 | `127.0.0.1:23366`，SQLite | `/Users/mac/artalk/`（Mac mini，仓库外） |
| 旅行助手服务 | `127.0.0.1:8090` | `backend/travel_assistant/` + LaunchAgent `ai.openclaw.travel-api` |
| 高德密钥 | `AMAP_*` 四项 | 仓库根 `.env`（gitignore，不提交） |
| 百度统计 | hm 码在 `config/baiduCode.ts` | 已启用 |
| 备案 | 蜀ICP备2026018223号 | `footer.copyrightInfo` |
| 图片 | `jsd.cdn.zzko.cn`、`raw.githubusercontent.com` | 文章内远程引用 |
| CNAME | `docs/.vuepress/public/CNAME` 内容为 `b.xugaoyi.com` | 原样发布；与实际域名不符，属模板残留 |

## 10. 现状评估与风险

1. **P0 线上是 dev server**：无压缩/长效缓存、带 HMR WebSocket，进程崩溃即全站不可用，内存占用高。已产出 `STATIC-HOSTING-PLAN.md` 评估 `build` + 静态托管，尚未切换。
2. **P0 Artalk 启动方式不持久**：`ai.openclaw.artalk` 是 `launchctl submit` 的临时作业，未找到 plist；机器重启/用户注销后评论服务不会自动恢复。建议补一个带 `RunAtLoad`/`KeepAlive` 的 LaunchAgent 并纳入运维文档。
3. **P1 站点身份残留**：`DOMAIN_NAME=xugaoyi.com`、作者/博主仍是 xugaoyi/Evan Xu、`public/CNAME=b.xugaoyi.com`、页脚版权为 Evan Xu；与「三木 vlog」「seres-ai.com」不一致，影响 sitemap、SEO 与编辑链接。
4. **P1 评论链路与 nginx 强耦合**：Artalk 使用同源 `window.location.origin`，必须保留 `/api/` 与 `/sidebar/` 反代；同时 `/api/travel/` 必须保持比 `/api/` 更长。
5. **P1 凭据边界**：`config.ts` 已无 `clientID/clientSecret`（2026-10-26 复核），旧评论账号信息只在 git 历史；Artalk `app_key` 在仓库外 `config.yml`；高德密钥在 gitignore 的 `.env`。任何情况下不要把上述值写进仓库。
6. **P1 依赖不可复现**：`package-lock.json`、`yarn.lock`、`pnpm-lock.yaml` 均被 `.gitignore` 忽略；本机虽有 `package-lock.json` 但未跟踪，CI 仍用 `yarn` 无锁安装。
7. **P2 `docs/07.hello_agents` 已无 docsify 残留**：2026-10-26 实际 `ls -a` 只见编号 `.md`，旧文档所述 `index.html`、`_sidebar*.md`、`.nojekyll`、`README_EN.md` 均不存在，原风险关闭。仓库根 `project-docs/hello_agents-source/` 目前是未跟踪的本地素材，除非明确需要，不要提交。
8. **P2 `vdoing/` 未启用**：容易误改；主题定制应先确认加载路径。
9. **P2 无 lint / 单测 / 构建门禁**：CI 只负责部署，不校验 frontmatter、死链、重复 permalink。
10. **P2 双副本手工同步**：MacBook 与 Mac mini 可能漂移；发布前应确认线上 HEAD。
11. **P3 `.idea/` 未忽略**：`git status` 中为 untracked，易误提交 IDE 配置。
12. **P3 内容体积**：`docs/` 约 139MB，其中 `docs/.vuepress/dist` 约 92MB（构建产物），源内容约 47MB、253 个 md；dev server 首次编译与内存压力偏高。
13. **P3 本地直连 8888 无法自测**：`listen 8888 ssl proxy_protocol` 需要 PROXY 头；排障请走公网域名或 frpc 链路。

## 11. 相关文档

- 开发规范与操作手册：`project-docs/DEVELOPMENT.md`
- 静态托管评估：`project-docs/STATIC-HOSTING-PLAN.md`
- 速查与文档索引：`project-docs/README.md`
