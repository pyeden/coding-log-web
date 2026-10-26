# coding-log-web 开发规范与操作手册

> 与 `ARCHITECTURE.md` 配套。所有规则以「不破坏现有 URL、侧边栏和评论」为前提。
> 基线：`master` @ `c3874ef`（2026-10-26）。

## 1. 环境与常用命令

```bash
# MacBook 开发副本（实际路径含用户名）
cd <MacBook 上的 coding-log-web>

npm install                 # 首次或依赖变更后
npm run dev                 # 开发服务器，http://localhost:8080
npm run build               # 产出 docs/.vuepress/dist
npm run editFm              # 按 utils/config.yml 批量改 frontmatter（有交互确认）
npm run baiduPush           # 生成 urls.txt 并推送百度（需联网/ token）
bash deploy.sh              # 模板遗留：强推 gh-pages，当前线上不用
```

旅行助手后端（本地联调时手动启动；线上由 LaunchAgent 守护）：

```bash
cd backend/travel_assistant
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8090
curl http://127.0.0.1:8090/api/travel/health
```

- Node 要求 >= 18；macOS/Linux 用 `dev`/`build`，Windows 用 `dev:win`/`build:win`（`utils/check.js` 会拦截用错的脚本）。
- 不要绕过 npm 脚本直接执行 `vuepress`，否则缺少 `NODE_OPTIONS=--openssl-legacy-provider`，Webpack 4 在 Node 17+ 会报 `ERR_OSSL_EVP_UNSUPPORTED`。
- 端口：站点 8080、旅行助手 8090、Artalk 23366、OpenClaw Gateway 18789、nginx 8887（HTTP→301）/8888（HTTPS）。
- 8080 被占用时先 `lsof -nP -iTCP:8080 -sTCP:LISTEN`。
- 本地 `npm run dev` 已配置 `/api/travel`、`/_AMapService` → 8090，`/api`、`/sidebar` → 23366；不需要本地 nginx 就能联调。

## 2. 目录与命名硬规则

1. 结构化栏目（`docs/` 下除 `.vuepress`、`@pages`、`_posts` 外）的**每个目录、每个 md 文件**都必须以 `数字.` 开头，例如 `01.前端/25.JavaScript文章/01.变量.md`。
2. 数字只用于排序，可留间隔（10、20、30）方便插入；同级数字重复会覆盖并打印 warning。
3. 缺数字前缀的项不会进入侧边栏，构建日志会出现 `序号出错` 警告。
4. `_posts/` 是例外：**不要加数字前缀**，只允许「分类目录/标题.md」两级；文件名中间不要出现多余的点。
5. 项目维护文档放 `project-docs/`，**绝不能放进 `docs/`**，否则会被当成博客文章发布。
6. 新增一级栏目 = 新目录 + `00.目录页/` 下的 Catalogue 页 + `config.ts` 导航项，三处缺一不可。
7. 不要手改 `docs/@pages/`（自动生成/删除）、`docs/.vuepress/dist/`、`node_modules/`。
8. 不要指望修改 `vdoing/` 生效；当前加载的是 npm 主题包。
9. 评论后端 Artalk 的代码/数据在 Mac mini `/Users/mac/artalk`，**不属于本仓库**；不要把它的配置或数据库复制进来。

## 3. Frontmatter 规范

### 3.1 普通文章

```yaml
---
title: 文章标题
date: 2026-10-26 22:45:00
permalink: /pages/a1b2c3/
categories:
  - 前端
tags:
  - JavaScript
author:
  name: 三木
  link: https://github.com/pyeden
---
```

- `title`：必填，和文件名去掉序号后的标题保持一致。
- `date`：`YYYY-MM-DD HH:mm:ss`，用于归档/排序。
- `permalink`：建议保留主题生成的 `/pages/<6位hex>/`，或使用唯一语义路径；**发布后不改**（外链与评论都依赖它）。
- `categories`：可省略（按目录自动推导）；需要跨目录归类时显式填写。
- `tags`：可省略但主题会生成空标签项，建议至少填一个。
- `author`：可省略，`extendFrontmatter` 会注入默认作者（当前仍是模板作者，长期应改成真实作者）。
- `comment: false`：关闭该页评论；Artalk 挂载逻辑会识别。

### 3.2 栏目目录页（`docs/00.目录页/NN.栏目.md`）

```yaml
---
pageComponent:
  name: Catalogue
  data:
    path: 07.hello_agents      # 必须是 docs 下的真实目录名（含数字前缀）
    imgUrl: /img/other.png
    description: 智能体学习笔记
title: 智能体
date: 2026-10-26 22:45:00
permalink: /agents/
sidebar: false
article: false
comment: false
editLink: false
---
```

`permalink` 要与 `config.ts` 导航里的 `link` 完全一致（结尾带 `/`）。

### 3.3 独立页面（关于、友链等）

```yaml
---
title: 关于
date: 2026-10-26 22:45:00
permalink: /about/
sidebar: false
article: false
---
```

`article: false` 让页面不进入分类/标签/归档；`sidebar: false` 隐藏左侧栏。

### 3.4 碎片文章（`docs/_posts/随笔/标题.md`）

```yaml
---
title: 标题
date: 2026-10-26 22:45:00
permalink: /pages/d4e5f6/
sidebar: auto
categories:
  - 随笔
tags:
  - 生活
---
正文第一段……

<!-- more -->

折叠线后的正文。
```

`_posts` 只能有一级子目录（子目录名即分类）。文件名不要带序号。

## 4. 新增文章流程

1. 确认归属栏目；没有合适目录时先按第 5 节建栏目。
2. 在目标目录建 `NN.标题.md`，序号取同级最大值 +10。
3. 粘贴 frontmatter 模板，填 `title/date/categories/tags`；`permalink` 可留空让主题生成（首次 dev 启动会写回文件）。
4. 写正文：标题从 `##` 开始（`#` 留给主题渲染的页面标题）。
5. 本地 `npm run dev` 验证：侧边栏出现、目录页可进入、图片/代码块/链接正常、文章页评论区加载。
6. `npm run build` 确认无新增 warning（重点关注序号、重复 permalink、非 md 文件）。
7. 提交前 `git diff` 检查主题是否自动改写了 frontmatter。

## 5. 新增栏目/导航流程

1. 建目录：`docs/09.新栏目/`（数字接在现有最大编号后）。
2. 目录内放 `NN.第一篇.md` 等文章，确保每项都有数字前缀。
3. 在 `docs/00.目录页/` 建 `NN.新栏目.md`，使用 3.2 模板，`data.path` 写 `09.新栏目`，`permalink` 取一个语义路径。
4. 在 `docs/.vuepress/config.ts` 的 `themeConfig.nav` 增加一项，`link` 指向该 permalink。
5. 如需要首页入口，在 `docs/index.md` 的 `features` 增加卡片（`link` 同 permalink）。
6. 重启 `npm run dev`（侧边栏在启动时生成，热更新不一定覆盖新目录）。
7. 跑 `npm run build`，检查日志没有 `该目录...没有任何文件或文件序号出错`。

## 6. 主题、样式与评论

- 颜色/布局变量：`docs/.vuepress/styles/palette.styl`（覆盖主题变量，默认全部注释）。
- 全局样式：`docs/.vuepress/styles/index.styl`、`design-system.styl`；其中仍保留 `.gt-container` 历史样式，对 Artalk 无影响，可后续清理。
- 配置开关：`config.ts` 的 `themeConfig`（分类/标签/归档、`pageStyle`、`bodyBgImg`、`rightMenuBar`、`defaultMode` 等），改完热更新通常生效。
- 组件级改造（`vdoing/components/*.vue`）：当前不会生效。需要时二选一：
  1. 把 `config.ts` 的 `theme` 改为 `resolve(__dirname, '../../vdoing')`，从此维护本地主题；
  2. 复制主题包到自有插件/主题目录维护，不直接改 `node_modules`。
- 自定义 HTML 模块（广告/公告）：`docs/.vuepress/config/htmlModules.ts`，支持 `homeSidebarB/sidebarT/sidebarB/pageT/pageB/windowLB/windowRB`。
- `docs/.vuepress/config/sidebar.js` 是格式示例，未被引用；改它无效。

### 6.1 Artalk 评论

- 挂载逻辑在 `docs/.vuepress/enhanceApp.js`：文章页在 `.theme-vdoing-content` 内插入 `#artalk-comments`，`server` 取 `window.location.origin`，`site` 为 `三木 vlog`。
- 后端地址 `127.0.0.1:23366`；数据库 `/Users/mac/artalk/data/artalk.db`；管理面板 `https://seres-ai.com/sidebar/`。
- 站点必须保留 nginx `/api/`（API）和 `/sidebar/`（管理面板）反代；本地开发由 `devServer.proxy` 覆盖。
- Artalk 已启用图片验证码（约 3 次操作后触发），测试评论时属于正常现象。
- 管理员账号/密码不在仓库；存放位置待确认，不要写入任何文件。
- 切换深浅色时 `enhanceApp.js` 会同步 Artalk 主题，不要在页面里重复初始化。

#### 6.1.1 服务守护（LaunchAgent，2026-10-26）

当前线上由 `~/Library/LaunchAgents/ai.openclaw.artalk.plist` 守护，仓库副本在 `project-docs/ops/ai.openclaw.artalk.plist`（两份内容一致）。

- 纯 `KeepAlive` 方案实测不可靠：Artalk 被 `kill -TERM` 后 launchd 在 10s/30s 内没有拉起，`state = not running`、`last exit code = 0`，并出现 `pended nondemand spawn = inefficient` 节流。
- 因此 plist 改为 **包装循环**：Artalk 退出后 3 秒自动重启；launchd 只负责守住 wrapper。实测 kill Artalk 子进程后 3–7 秒恢复，PID 变化、23366 重新监听。
- 失败备份在 `/Users/mac/artalk/ai.openclaw.artalk.plist.failed-20261026-141905`，**不要复用**（纯 KeepAlive 版本）。

常用命令：

```bash
# 状态：应看到 state = running，pid 为 wrapper；子进程用 pgrep -x artalk
launchctl print gui/$(id -u)/ai.openclaw.artalk
pgrep -fl "artalk server"
# 重载（bootstrap 报 EIO 时用 load 回退）
launchctl bootout gui/$(id -u)/ai.openclaw.artalk
launchctl load -w -S Aqua ~/Library/LaunchAgents/ai.openclaw.artalk.plist
# 强制重启 wrapper
launchctl kickstart -k gui/$(id -u)/ai.openclaw.artalk
# 验证
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:23366/sidebar/
```

- 回滚到临时提交方式：`launchctl bootout gui/$(id -u)/ai.openclaw.artalk`，再执行 `launchctl submit -l ai.openclaw.artalk -- /bin/bash -c 'cd /Users/mac/artalk && exec ./artalk server -c config.yml >> /Users/mac/artalk/server.log 2>&1'`。
- **限制**：LaunchAgent 在用户登录后运行；当前 Mac mini 未设置 `autoLoginUser`。若要求“重启无人登录也自动恢复”，需改用 LaunchDaemon（以 `mac` 用户运行）或开启自动登录；不要把 Artalk 配成 root 守护。

### 6.2 旅行助手

- 前端组件 `docs/.vuepress/components/TravelAssistant.vue`，页面 `docs/08.项目/01.旅行助手.md`。
- 后端 `backend/travel_assistant/`；接口 `GET /api/travel/health`、`GET /api/travel/`、`POST /api/travel/plan`、`GET|POST /_AMapService/{path}`。
- 高德密钥来自仓库根 `.env`：`AMAP_WEB_KEY`、`AMAP_WEB_SECRET`、`AMAP_JS_KEY`、`AMAP_SECURITY_CODE`；`.env` 已在 `.gitignore`，**永不提交**。
- 线上守护：LaunchAgent `ai.openclaw.travel-api`（`RunAtLoad` + `KeepAlive`），日志 `backend/travel_assistant/server.log`。
- 生产 nginx 必须保留 `/api/travel/`（长于 `/api/`）和 `/_AMapService/`，否则分别被 Artalk 接管或 404。

## 7. 图片与静态资源

- 站点级资源放 `docs/.vuepress/public/img/`，引用 `/img/xxx.png`。
- 文章图片优先用图床/CDN（现有 `jsd.cdn.zzko.cn`）；外链需保证长期可访问。
- 本地图片放在文章同级目录并用相对路径；`07.hello_agents/images/` 即此模式。
- 需要禁止点击放大时给图片加 `class="no-zoom"`（`zooming` 插件排除该 class）。
- 大图先压缩；`docs/` 源内容约 47MB（另有约 92MB 构建产物），避免继续膨胀。

## 8. Markdown 写法约定

- 自定义容器：`::: tip`、`::: warning`、`::: danger`、`::: details`、`::: demo`，容器前后留空行。
- 代码块必须标语言（```js / ```bash / ```vue），否则没有高亮；全局已开启行号。
- 内链使用 permalink 绝对路径（`/pages/xxx/`、`/web/`），不要写相对文件路径，避免改目录后失效。
- 摘要折叠用 `<!-- more -->`（主要影响首页/列表展示）。
- 标题层级从 `##` 开始，最多到 `######`；侧边栏会提取 h2–h6。
- 可复用组件：`Badge`、`CodeBlock`、`CodeGroup`（主题全局组件）、`ProjectShowcase`、`TravelAssistant`，以及 `demo-block` 插件语法。
- 中文文件名可用，但链接要使用编码后的路径；能避免就避免在 permalink 中使用中文。

## 9. 配置修改规范

| 文件 | 允许改什么 | 注意 |
| --- | --- | --- |
| `config.ts` | 站点标题/描述、nav、主题开关、插件参数、head、devServer 代理 | 改动会热更新；`DOMAIN_NAME` 影响 sitemap 与百度搜索链接 |
| `enhanceApp.js` | Artalk 挂载、按钮修复、评论兜底、动效 | 改坏会影响全站评论/交互，先在 dev 验证 |
| `config/htmlModules.ts` | 侧边栏/页面注入的 HTML | 已在 `extraWatchFiles` 中，改动会触发重编 |
| `config/baiduCode.ts` | 百度统计 hm 码 | 公开可见，不是密钥 |
| `styles/*.styl` | 主题变量与全局样式 | 改坏会导致整站样式异常，先在 dev 验证 |
| `utils/config.yml` | 批量 frontmatter 的路径/字段 | 有交互确认，执行前先 commit |
| `package.json` scripts | 构建命令/内存参数 | 保持 `NODE_OPTIONS` 兼容 Node 17+ |
| `backend/travel_assistant/*` | 旅行助手路由/规划逻辑 | 依赖 `.env`；改后需重启 8090 |
| `nginx/*.conf` | 反代/证书/端口 | 改完需 `nginx -t` 再 reload；Mac mini 上操作 |

**安全红线**：不要在仓库里新增密钥、token、证书私钥。高德密钥只放在 gitignore 的 `.env`；Artalk `app_key` 只在 Mac mini `/Users/mac/artalk/config.yml`；发现泄露只报告，不复制、不外传。

## 10. 构建与发布流程

### 10.1 本地自检清单

- [ ] `npm run dev` 无红色报错，侧边栏/目录页/文章可访问
- [ ] 文章页评论区能加载（Artalk 23366 可达）
- [ ] 旅行助手页面能出结果（8090 可达，或接受 502 并说明后端未启动）
- [ ] `npm run build` 成功，日志无「序号出错」「序号重复」「非 .md 文件」警告
- [ ] `git diff` 只包含预期改动（主题可能自动补 frontmatter）
- [ ] 新 permalink 全局唯一：`grep -r "permalink: /pages/xxxxxx/" docs`
- [ ] 没有把维护文档、临时文件放进 `docs/`
- [ ] 没有提交 `.env`、证书、日志、`dist/`、`node_modules/`

### 10.2 发布到线上（Mac mini）

固定流程：**MacBook 开发 → commit/push → Mac mini 部署**。禁止在 Mac mini 上直接编辑代码或内容。

```bash
# MacBook
git add <具体文件> && git commit -m "内容: 简述本次改动" && git push origin master

# Mac mini
cd /Users/mac/coding-log-web
git status                 # 确认无本地改动
git pull --ff-only origin master
# 纯内容改动：8080 的 dev server 会热更新
# 改了 config.ts / 新增一级目录：重启 8080 进程
# 改了 backend/travel_assistant：重启旅行助手
launchctl kickstart -k gui/$(id -u)/ai.openclaw.travel-api
```

重启 8080 前先确认进程：`lsof -nP -iTCP:8080 -sTCP:LISTEN`。重启后检查 `output.log` 出现 `Compiled successfully`，再访问 `https://seres-ai.com`。

> 当前线上是 dev server，发布即热更新；这也是为什么必须避免在线上直接编辑文件。

## 11. 排错手册

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `ERR_OSSL_EVP_UNSUPPORTED` | 直接跑 vuepress，缺 legacy provider | 用 `npm run dev/build` |
| 侧边栏缺文章 | 文件/目录没有数字前缀，或同级序号重复 | 看构建 warning，改文件名 |
| 目录页空白 | `Catalogue.data.path` 与真实目录名不一致 | 改成含数字前缀的目录名 |
| 新栏目 404 | 导航 link 与 permalink 不一致，或没建目录页 | 对齐两处路径，结尾加 `/` |
| 文章 404 | `base` 配置或 permalink 冲突 | 检查 `config.ts` 的 `base`、全局搜 permalink |
| 评论不显示 | Artalk 23366 未启动；nginx 缺 `/api/`；`site` 不匹配；页面 `comment: false` | `launchctl print gui/$(id -u)/ai.openclaw.artalk`；`curl -I https://seres-ai.com/api/`；核对 `ARTALK_SITE` 与 `site_default` |
| 评论提交 403 / 要求验证码 | Artalk 图片验证码（约 3 次操作后触发） | 正常完成验证码；或评估 `captcha.action_limit`，不要随意关闭 |
| `/sidebar/` 404 | nginx 缺 `/sidebar/`，或 Artalk 未启动 | 检查 location 与 23366 |
| 旅行助手 502/500 | 8090 未启动、`.venv` 缺失、依赖未装 | `curl 127.0.0.1:8090/api/travel/health`；`launchctl print ... travel-api`；看 `server.log` |
| 旅行助手接口 404 但评论正常 | `/api/travel/` 被 `/api/` 接管 | 确认 nginx 保留更长的 `/api/travel/` |
| 地图空白/高德报错 | `.env` 缺 `AMAP_JS_KEY`/`AMAP_SECURITY_CODE`，或 `/_AMapService` 未反代 | 检查 `.env` 与 nginx location；重启 8090 |
| 高德 Web 服务 403 | `AMAP_WEB_KEY`/`AMAP_WEB_SECRET` 不匹配或未签名 | 核对高德控制台，重启 8090 |
| 本地 `curl https://127.0.0.1:8888` 失败 | nginx 需 PROXY protocol 头 | 走 `https://seres-ai.com` 或 frpc 链路验证 |
| 构建内存不足 | 文章/图片过多 | 已设 `--max_old_space_size=4096`，必要时提高 |
| Windows 脚本失败 | 用了 `export` 版本 | 改用 `dev:win`/`build:win` |
| `vdoing: command not found` | 未安装依赖 | `npm install` |
| 8080 被占用 | 旧 dev server 未退出 | `lsof` 找 PID 后结束，再启动 |

## 12. 已知问题与建议（按优先级）

1. **P0 线上架构**：把 `vuepress dev` 换成 `npm run build` + 静态托管，并加进程守护/健康检查；方案见 `STATIC-HOSTING-PLAN.md`。
2. **P0 Artalk 持久化（已处理 2026-10-26）**：`ai.openclaw.artalk` 已改为 `/Library/LaunchDaemons/ai.openclaw.artalk.plist`（`UserName=mac` + wrapper 循环 + `RunAtLoad`/`KeepAlive`），开机即启动、不依赖登录；仓库副本在 `project-docs/ops/`；用户 LaunchAgent 作为回退保留。
3. **P1 站点身份**：统一替换 `DOMAIN_NAME`、`repo`、`blogger`、`author`、`extendFrontmatter`、`public/CNAME`、页脚版权，避免指向 xugaoyi。
4. **P1 评论/旅行助手路由**：nginx 中 `/api/`、`/api/travel/`、`/sidebar/`、`/_AMapService/` 任何调整都要回归评论和旅行助手。
5. **P1 依赖锁定**：提交 `package-lock.json`，CI 改用 `npm ci`；同步修正 `ci.yml` 的 yarn 流程。
6. **P2 CI 门禁**：增加 frontmatter 校验（必填字段、重复 permalink）、死链检查和 `npm run build` 失败即阻断。
7. **P2 双副本治理**：明确「MacBook 编辑、Mac mini 只读运行」，发布前校验两端 HEAD；避免线上手改。
8. **P3 仓库卫生**：`.gitignore` 增加 `.idea/`、`output.log`；处理未跟踪的 `project-docs/hello_agents-source/`；删除未启用的 `vdoing/` 或明确标注为参考副本。
9. **P3 历史样式**：`styles/index.styl` 仍保留 `.gt-container` 选择器，可清理但无功能影响。

## 13. 给 AI agent 的硬性约束

1. 动手前先读 `project-docs/ARCHITECTURE.md` 与本文；涉及线上时先确认当前 HEAD 与进程状态。
2. 不改 `docs/@pages/`、`docs/.vuepress/dist/`、`node_modules/`、证书与私钥。
3. 不改已发布文章的 `permalink`；必须改时先说明外链/评论影响并取得确认。
4. 不把维护文档写进 `docs/`；统一放 `project-docs/`。
5. 不修改 `vdoing/` 来「修主题」，除非任务明确要求切换为本地主题。
6. 任何内容改动后至少运行 `npm run build`；失败或出现新 warning 时如实报告，不宣称完成。
7. 不新增明文密钥；`.env`、Artalk 配置、证书、日志都不进 git。
8. 线上操作（git pull、重启 8080/8090、nginx reload）属于高风险动作，执行前说明影响并确认。
9. 开发机固定为 MacBook；Mac mini 只用于部署与运行，不在 Mac mini 上编辑或提交代码。
10. 评论是 Artalk（同源 `/api/`），不要重新引入已停用的旧评论插件方案。
