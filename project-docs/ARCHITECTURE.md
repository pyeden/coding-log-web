# coding-log-web 架构说明

> 面向后续开发/迭代的维护者与 AI agent。
> 核对时间：2026-10-24；基线：`master` @ `104e4b8`（MacBook 与 Mac mini 两份工作副本的 `docs/.vuepress/config.ts` 校验一致）。

## 1. 项目定位

个人技术博客 + 结构化知识库（站点标题「三木 vlog」）。纯静态站点：没有后端、没有数据库，所有内容都是 `docs/` 下的 Markdown；评论依赖 Gitalk（GitHub Issues）。

## 2. 技术栈

| 层 | 选型 | 版本/位置 | 说明 |
| --- | --- | --- | --- |
| 站点框架 | VuePress | 1.8.3（Vue 2） | 经典 VuePress 1.x，Webpack 4 |
| 主题 | vuepress-theme-vdoing | 1.12.9（npm 包） | 知识库 + 博客双形态 |
| 配置 | TypeScript | `docs/.vuepress/config.ts` | 主题支持 TS 配置 |
| 运行时 | Node.js | 要求 >=18；本机实测 v24.22.1 / npm 11.19.1 | 脚本强制 `NODE_OPTIONS=--openssl-legacy-provider` |
| 评论 | vuepress-plugin-comment + Gitalk | 配置见 config.ts | 评论存到 GitHub Issues |
| 搜索 | vuepress-plugin-thirdparty-search | 已启用 | 不加载全文索引，只跳转外部搜索 |
| SEO/统计 | sitemap、百度自动推送、百度统计 | 已启用 | 依赖 `WEB_SITE` 与 hm 码 |
| 部署 | nginx + frp + 常驻 dev server | Mac mini | 见第 7 节 |

常用插件：`one-click-copy`（代码复制）、`demo-block`（可运行示例）、`zooming`（图片放大）、`@vuepress/last-updated`（git 时间）。

## 3. 仓库与运行拓扑

| 角色 | 位置 | 说明 |
| --- | --- | --- |
| 开发副本 | `/Users/futuredeng/PycharmProjects/coding-log-web`（MacBook） | 当前主要编辑副本，`master` |
| 线上副本 | `/Users/mac/coding-log-web`（Mac mini） | nginx 反代目标，独立 clone |
| 远端仓库 | `git@github.com:pyeden/coding-log-web.git` | 分支 `master` |

**固定分工（2026-10-25 确定，长期有效）：所有开发只在 MacBook 上进行；Mac mini 仅负责部署与运行，不在 Mac mini 上编辑代码或内容。**

线上访问链路（现状）：

```
浏览器 https://seres-ai.com
  → 公网 8.137.118.223:443（frps）
  → frpc tcp 8888（开启 v2 proxy protocol）
  → nginx :8888（TLS，还原真实 IP）
  → 127.0.0.1:8080  ← `vuepress dev docs` 常驻进程
  → docs/ 源文件

浏览器 http://seres-ai.com
  → frps :80 → frpc 8887 → nginx :8887 → 301 https
```

**关键事实：线上跑的是 `vuepress dev docs`（开发服务器），不是 `build` 后的静态产物。** 依据：Mac mini 上 8080 进程命令为 `node --max_old_space_size=4096 ./node_modules/vuepress/cli.js dev docs`，`output.log` 显示 `VuePress dev server listening at http://localhost:8080/`。这意味着改源码即时生效，但也带来性能、稳定性和安全风险（见第 10 节）。

## 4. 目录结构

```
coding-log-web/
├── docs/                      # VuePress sourceDir，站点全部内容
│   ├── .vuepress/
│   │   ├── config.ts          # 主配置：站点、导航、主题、插件、head
│   │   ├── config/            # sidebar.js（示例/未使用）、htmlModules.ts、baiduCode.ts
│   │   ├── public/            # 原样拷贝的静态资源（img、CNAME）
│   │   ├── styles/            # palette.styl（变量覆盖）、index.styl（全局样式）
│   │   ├── plugins/love-me/   # 本地插件（当前未在 config 中启用）
│   │   └── dist/              # 构建产物，gitignore
│   ├── index.md               # 首页（home: true + features）
│   ├── 00.目录页/             # Catalogue 目录页（/web/、/ui/ 等）
│   ├── 01.前端/ … 06.收藏夹/   # 结构化知识库栏目
│   ├── 07.hello_agents/       # 引入的《Hello-Agents》书籍（含 docsify 残留）
│   ├── @pages/                # archives/categories/tags 索引页（构建时自动维护）
│   ├── _posts/                # 碎片化博客文章（sidebar: auto）
│   └── 《…》笔记/             # 成体系的学习笔记栏目
├── vdoing/                    # 主题源码副本 1.12.9 —— 当前未启用
├── utils/                     # check.js、editFrontmatter.js、baiduPush.js、config.yml
├── nginx/                     # default.conf、https.conf、cert/、acme/
├── .github/workflows/         # ci.yml（gh-pages 部署）、baiduPush.yml
├── deploy.sh                  # 本地 build 后强推 gh-pages（模板遗留）
├── package.json
└── project-docs/              # 本套维护文档（不参与站点构建）
```

**`vdoing/` 不是生效代码。** `config.ts` 写的是 `theme: 'vdoing'`，VuePress 从 `node_modules/vuepress-theme-vdoing` 加载主题；本地 `vdoing/` 只是源码参考。只有把配置改成 `theme: resolve(__dirname, '../../vdoing')` 才会生效。

## 5. 内容模型与路由

### 5.1 侧边栏（structured sidebar）

主题开启 `sidebar: 'structuring'`，构建时由 `vdoing/node_utils/getSidebarData.js` 扫描生成：

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
- 现有约定：文章多为 `/pages/xxxxxx/`；栏目落地页用语义化路径（`/web/`、`/note/git/`、`/about/`、`/archives/`、`/categories/`、`/tags/`）。
- **permalink 一经发布不要修改**：Gitalk 的 issue id 取 permalink（或路径）的最后 16 个字符，改了会丢评论、断外链。

### 5.4 页面类型

| 类型 | 位置 | 关键 frontmatter |
| --- | --- | --- |
| 首页 | `docs/index.md` | `home: true`、`heroText`、`features` |
| 栏目目录页 | `docs/00.目录页/*.md` | `pageComponent: {name: Catalogue, data: {path, imgUrl, description}}`、`article: false` |
| 索引页 | `docs/@pages/*.md` | `archivesPage/tagsPage/categoriesPage: true`（自动生成） |
| 博客文章 | 任意栏目下 | `title/date/permalink/categories/tags` |
| 碎片文章 | `docs/_posts/<分类>/*.md` | `sidebar: auto`、`<!-- more -->` |
| 独立页 | 如 `05.关于/01.关于.md` | `sidebar: false`、`article: false` |

## 6. 构建流水线

```
npm run dev
├─ predev: node utils/check.js dev   # Windows 平台误用 export 脚本时直接退出
├─ predev: vdoing                    # 检查 Node >= 18
└─ node --max_old_space_size=4096 ./node_modules/vuepress/cli.js dev docs
   → http://localhost:8080

npm run build
├─ prebuild: 同上
└─ vuepress build docs
   → docs/.vuepress/dist（gitignore）
```

启动/构建时主题钩子（`vdoing/index.js`）依次执行：

1. `setFrontmatter`：补齐 `title/date/permalink/categories/tags`，并合并 `extendFrontmatter`（当前注入 `author: xugaoyi`）。
2. `getSidebarData`：生成结构化侧边栏与目录页元数据。
3. `createPage/deletePage`：按 `category/tag/archive` 开关维护 `@pages/`。

Markdown 配置：`lineNumbers: true`；`extractHeaders: h2–h6`（侧边栏可显示到 h6，但 `sidebarDepth: 2`）。

## 7. 部署与 CI

### 7.1 固定发布流程（MacBook → Mac mini）

**所有开发都在 MacBook 完成；Mac mini 是部署/运行机，不接受直接编辑。**

1. MacBook 修改、提交并推送 `master`。
2. Mac mini 上 `git pull`（目录 `/Users/mac/coding-log-web`）。
3. 常驻的 `vuepress dev` 热更新；若改了 `config.ts`、新增一级目录，需要重启进程。
4. nginx 配置基本不动：`:8887` 跳转 HTTPS，`:8888` TLS 终止后反代 `127.0.0.1:8080`；`/openclaw` 反代 `127.0.0.1:18789`（与本博客无关）。

### 7.2 模板遗留的发布方式（当前未使用）

- `deploy.sh`：本地 `npm run build`，进入 `docs/.vuepress/dist`，`git init` 后强推 `gh-pages`。
- `.github/workflows/ci.yml`：`master` push → Node 18 → `yarn build` → 强推 `gh-pages`（使用 `GITHUB_TOKEN`）。
- `.github/workflows/baiduPush.yml`：push 及每天 23:00 UTC 运行 `npm run baiduPush`，生成 `urls.txt` 后推送给百度。
- `vercel.json`：只声明 `/assets/js|css` 的 immutable 缓存头，本地 nginx 未使用。

> 判断改动是否需要同步线上时，以第 7.1 节为准；`gh-pages` 产物不是当前线上来源。

## 8. 数据流

```
Markdown（含 frontmatter）
  → VuePress 读取 + vdoing 钩子补全元数据/侧边栏
  → webpack 编译（Vue 2 运行时 + 预渲染 HTML）
  → docs/.vuepress/dist 或 dev server 内存产物
  → nginx 反代
  → 浏览器
```

评论：浏览器 → Gitalk → GitHub API → `xugaoyi/blog-gitalk-comment` 的 Issues。
统计/收录：百度统计脚本、百度自动推送、sitemap。

## 9. 外部依赖与配置项

| 项 | 当前值 | 位置 |
| --- | --- | --- |
| 站点域名常量 | `xugaoyi.com` | `config.ts` 顶部 `DOMAIN_NAME`/`WEB_SITE` |
| 站点标题 | 三木 vlog | `locales['/'].title` |
| 导航仓库链接 | `xugaoyi/vuepress-theme-vdoing` | `themeConfig.repo` |
| 博主/作者 | Evan Xu / xugaoyi | `blogger`、`author`、`extendFrontmatter` |
| 评论仓库 | `xugaoyi/blog-gitalk-comment` | `vuepress-plugin-comment` |
| 百度统计 | hm 码在 `config/baiduCode.ts` | 已启用 |
| 备案 | 蜀ICP备2026018223号 | `footer.copyrightInfo` |
| 图片 | `jsd.cdn.zzko.cn`、`raw.githubusercontent.com` | 文章内远程引用 |
| CNAME | `docs/.vuepress/public/CNAME` | 原样发布 |

## 10. 现状评估与风险

1. **线上是 dev server**：无压缩、无长效缓存、带 HMR/WebSocket，进程崩溃即全站不可用，内存占用高。建议改为 `npm run build` + 静态文件服务（nginx root 或 `http-server`），并用 launchd/pm2 守护。
2. **模板身份残留**：域名、repo、作者、博主、评论仓库仍是 xugaoyi 的默认值；若站点对外是「三木 vlog」，搜索结果、编辑链接、评论都会指向错误目标。
3. **Gitalk `clientSecret` 明文写在公开仓库的 `config.ts`**：属于凭据泄露，应轮换并改为环境变量/构建注入。
4. **依赖不可复现**：`package-lock.json`、`yarn.lock`、`pnpm-lock.yaml` 全被 `.gitignore` 忽略，CI 却用 `yarn` 无锁安装。
5. **`docs/07.hello_agents` 混入 docsify 产物**：`index.html`、`_sidebar.md`、`_sidebar_en.md`、`.nojekyll`、`README_EN.md`、`Preface.md` 与 `前言.md` 重复；这些 `.md` 带 frontmatter，会被当作正常文章发布，污染分类/归档。建议移出 `docs/` 或加 `article: false` + 排除构建。
6. **`vdoing/` 未启用**：容易误改；主题定制应先确认加载路径。
7. **无 lint / 单测 / 构建门禁**：CI 只负责部署，不校验 frontmatter、死链、重复 permalink。
8. **双副本手工同步**：MacBook 与 Mac mini 可能漂移；发布前应确认线上 HEAD。
9. **`.idea/` 未忽略**：`git status` 中为 untracked，易误提交 IDE 配置。
10. **内容体积**：`docs/` 约 7.8MB、255 个 md，其中 hello_agents 图片占比较大；dev server 首次编译与内存压力偏高。

## 11. 相关文档

- 开发规范与操作手册：`project-docs/DEVELOPMENT.md`
- 速查与文档索引：`project-docs/README.md`
