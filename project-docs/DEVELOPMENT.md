# coding-log-web 开发规范与操作手册

> 与 `ARCHITECTURE.md` 配套。所有规则以「不破坏现有 URL、侧边栏和评论」为前提。

## 1. 环境与常用命令

```bash
cd /Users/futuredeng/PycharmProjects/coding-log-web   # MacBook 开发副本
npm install                 # 首次或依赖变更后
npm run dev                 # 开发服务器，http://localhost:8080
npm run build               # 产出 docs/.vuepress/dist
npm run editFm              # 按 utils/config.yml 批量改 frontmatter（有交互确认）
npm run baiduPush           # 生成 urls.txt 并推送百度（需联网/ token）
bash deploy.sh              # 模板遗留：强推 gh-pages，当前线上不用
```

- Node 要求 >= 18；macOS/Linux 用 `dev`/`build`，Windows 用 `dev:win`/`build:win`（`utils/check.js` 会拦截用错的脚本）。
- 不要绕过 npm 脚本直接执行 `vuepress`，否则缺少 `NODE_OPTIONS=--openssl-legacy-provider`，Webpack 4 在 Node 17+ 会报 `ERR_OSSL_EVP_UNSUPPORTED`。
- 端口固定 8080；被占用时先 `lsof -nP -iTCP:8080 -sTCP:LISTEN`。

## 2. 目录与命名硬规则

1. 结构化栏目（`docs/` 下除 `.vuepress`、`@pages`、`_posts` 外）的**每个目录、每个 md 文件**都必须以 `数字.` 开头，例如 `01.前端/25.JavaScript文章/01.变量.md`。
2. 数字只用于排序，可留间隔（10、20、30）方便插入；同级数字重复会覆盖并打印 warning。
3. 缺数字前缀的项不会进入侧边栏，构建日志会出现 `序号出错` 警告。
4. `_posts/` 是例外：**不要加数字前缀**，只允许「分类目录/标题.md」两级；文件名中间不要出现多余的点。
5. 项目维护文档放 `project-docs/`，**绝不能放进 `docs/`**，否则会被当成博客文章发布。
6. 新增一级栏目 = 新目录 + `00.目录页/` 下的 Catalogue 页 + `config.ts` 导航项，三处缺一不可。
7. 不要手改 `docs/@pages/`（自动生成/删除）、`docs/.vuepress/dist/`、`node_modules/`。
8. 不要指望修改 `vdoing/` 生效；当前加载的是 npm 主题包。

## 3. Frontmatter 规范

### 3.1 普通文章

```yaml
---
title: 文章标题
date: 2026-10-24 22:45:00
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
- `permalink`：建议保留主题生成的 `/pages/<6位hex>/`，或使用唯一语义路径；**发布后不改**。
- `categories`：可省略（按目录自动推导）；需要跨目录归类时显式填写。
- `tags`：可省略但主题会生成空标签项，建议至少填一个。
- `author`：可省略，`extendFrontmatter` 会注入默认作者；长期应改成真实作者。

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
date: 2026-10-24 22:45:00
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
date: 2026-10-24 22:45:00
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
date: 2026-10-24 22:45:00
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
5. 本地 `npm run dev` 验证：侧边栏出现、目录页可进入、图片/代码块/链接正常。
6. `npm run build` 确认无新增 warning（重点关注序号、重复 permalink、非 md 文件）。
7. 提交前 `git diff` 检查主题是否自动改写了 frontmatter。

## 5. 新增栏目/导航流程

1. 建目录：`docs/08.新栏目/`（数字接在现有最大编号后）。
2. 目录内放 `NN.第一篇.md` 等文章，确保每项都有数字前缀。
3. 在 `docs/00.目录页/` 建 `05.新栏目.md`，使用 3.2 模板，`data.path` 写 `08.新栏目`，`permalink` 取一个语义路径。
4. 在 `docs/.vuepress/config.ts` 的 `themeConfig.nav` 增加一项，`link` 指向该 permalink。
5. 如需要首页入口，在 `docs/index.md` 的 `features` 增加卡片（`link` 同 permalink）。
6. 重启 `npm run dev`（侧边栏在启动时生成，热更新不一定覆盖新目录）。
7. 跑 `npm run build`，检查日志没有 `该目录...没有任何文件或文件序号出错`。

## 6. 主题与样式定制

- 颜色/布局变量：`docs/.vuepress/styles/palette.styl`（覆盖主题变量，默认全部注释）。
- 全局样式：`docs/.vuepress/styles/index.styl`（已有 Gitalk、demo、搜索框定制）。
- 配置开关：`config.ts` 的 `themeConfig`（分类/标签/归档、`pageStyle`、`bodyBgImg`、`rightMenuBar`、`defaultMode` 等），改完热更新通常生效。
- 组件级改造（`vdoing/components/*.vue`）：当前不会生效。需要时二选一：
  1. 把 `config.ts` 的 `theme` 改为 `resolve(__dirname, '../../vdoing')`，从此维护本地主题；
  2. 复制主题包到自有插件/主题目录维护，不直接改 `node_modules`。
- 自定义 HTML 模块（广告/公告）：`docs/.vuepress/config/htmlModules.ts`，支持 `homeSidebarB/sidebarT/sidebarB/pageT/pageB/windowLB/windowRB`。
- `docs/.vuepress/config/sidebar.js` 是格式示例，未被引用；改它无效。

## 7. 图片与静态资源

- 站点级资源放 `docs/.vuepress/public/img/`，引用 `/img/xxx.png`。
- 文章图片优先用图床/CDN（现有 `jsd.cdn.zzko.cn`）；外链需保证长期可访问。
- 本地图片放在文章同级目录并用相对路径；`07.hello_agents/images/` 即此模式。
- 需要禁止点击放大时给图片加 `class="no-zoom"`（`zooming` 插件排除该 class）。
- 大图先压缩；`docs/` 已约 7.8MB，避免继续膨胀。

## 8. Markdown 写法约定

- 自定义容器：`::: tip`、`::: warning`、`::: danger`、`::: details`、`::: demo`，容器前后留空行。
- 代码块必须标语言（```js / ```bash / ```vue），否则没有高亮；全局已开启行号。
- 内链使用 permalink 绝对路径（`/pages/xxx/`、`/web/`），不要写相对文件路径，避免改目录后失效。
- 摘要折叠用 `<!-- more -->`（主要影响首页/列表展示）。
- 标题层级从 `##` 开始，最多到 `######`；侧边栏会提取 h2–h6。
- 可复用组件：`Badge`、`CodeBlock`、`CodeGroup`（主题全局组件），以及 `demo-block` 插件语法。
- 中文文件名可用，但链接要使用编码后的路径；能避免就避免在 permalink 中使用中文。

## 9. 配置修改规范

| 文件 | 允许改什么 | 注意 |
| --- | --- | --- |
| `config.ts` | 站点标题/描述、nav、主题开关、插件参数、head | 改动会热更新；`DOMAIN_NAME` 影响 sitemap 与百度搜索链接 |
| `config/htmlModules.ts` | 侧边栏/页面注入的 HTML | 已在 `extraWatchFiles` 中，改动会触发重编 |
| `config/baiduCode.ts` | 百度统计 hm 码 | 公开可见，不是密钥 |
| `styles/*.styl` | 主题变量与全局样式 | 改坏会导致整站样式异常，先在 dev 验证 |
| `utils/config.yml` | 批量 frontmatter 的路径/字段 | 有交互确认，执行前先 commit |
| `package.json` scripts | 构建命令/内存参数 | 保持 `NODE_OPTIONS` 兼容 Node 17+ |
| `nginx/*.conf` | 反代/证书/端口 | 改完需 `nginx -t` 再 reload；Mac mini 上操作 |

**安全红线**：不要在仓库里新增密钥、token、证书私钥。现有 Gitalk `clientSecret`、百度推送 token 属于历史遗留，应轮换并改为环境变量（见第 12 节）。

## 10. 构建与发布流程

### 10.1 本地自检清单

- [ ] `npm run dev` 无红色报错，侧边栏/目录页/文章可访问
- [ ] `npm run build` 成功，日志无「序号出错」「序号重复」「非 .md 文件」警告
- [ ] `git diff` 只包含预期改动（主题可能自动补 frontmatter）
- [ ] 新 permalink 全局唯一：`grep -r "permalink: /pages/xxxxxx/" docs`
- [ ] 没有把维护文档、临时文件放进 `docs/`

### 10.2 发布到线上（Mac mini）

固定流程：**MacBook 开发 → commit/push → Mac mini 部署**。禁止在 Mac mini 上直接编辑代码或内容。

```bash
# MacBook
git add -A && git commit -m "内容: 简述本次改动" && git push origin master

# Mac mini
cd /Users/mac/coding-log-web
git status                 # 确认无本地改动
git pull --ff-only origin master
# 改了 config.ts / 新增一级目录时重启 8080 进程；纯内容改动会热更新
```

重启前先确认进程：`lsof -nP -iTCP:8080 -sTCP:LISTEN`。重启后检查 `output.log` 出现 `Compiled successfully`，再访问 `https://seres-ai.com`。

> 当前线上是 dev server，发布即热更新；这也是为什么必须避免在线上直接编辑文件。

## 11. 排错手册

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `ERR_OSSL_EVP_UNSUPPORTED` | 直接跑 vuepress，缺 legacy provider | 用 `npm run dev/build` |
| 侧边栏缺文章 | 文件/目录没有数字前缀，或同级序号重复 | 看构建 warning，改文件名 |
| 目录页空白 | `Catalogue.data.path` 与真实目录名不一致 | 改成含数字前缀的目录名 |
| 新栏目 404 | 导航 link 与 permalink 不一致，或没建目录页 | 对齐两处路径，结尾加 `/` |
| 文章 404 | `base` 配置或 permalink 冲突 | 检查 `config.ts` 的 `base`、全局搜 permalink |
| 评论不显示 | Gitalk 仓库/owner/clientID 不匹配当前域名；或 permalink 改过 | 检查插件配置与 issue id（permalink 后 16 位） |
| 构建内存不足 | 文章/图片过多 | 已设 `--max_old_space_size=4096`，必要时提高 |
| Windows 脚本失败 | 用了 `export` 版本 | 改用 `dev:win`/`build:win` |
| `vdoing: command not found` | 未安装依赖 | `npm install` |
| 8080 被占用 | 旧 dev server 未退出 | `lsof` 找 PID 后结束，再启动 |

## 12. 已知问题与建议（按优先级）

1. **P0 线上架构**：把 `vuepress dev` 换成 `npm run build` + 静态托管，并加进程守护/健康检查；否则任何编译错误都会直接影响线上。
2. **P0 凭据**：轮换 Gitalk `clientSecret` 与百度推送 token，改由环境变量注入；清理 git 历史中的明文（需单独评估）。
3. **P1 站点身份**：统一替换 `DOMAIN_NAME`、`repo`、`blogger`、`author`、`extendFrontmatter`、Gitalk owner/repo、备案信息，避免指向 xugaoyi。
4. **P1 hello_agents 清理**：移除 `index.html`、`_sidebar*.md`、`.nojekyll`、`README_EN.md`/`Preface.md` 等 docsify 残留；或整体移出 `docs/`。当前它们会作为文章进入分类与归档。
5. **P1 依赖锁定**：提交 `package-lock.json`，CI 改用 `npm ci`；同步修正 `ci.yml` 的 yarn 流程。
6. **P2 CI 门禁**：增加 frontmatter 校验（必填字段、重复 permalink）、死链检查和 `npm run build` 失败即阻断。
7. **P2 双副本治理**：明确「MacBook 编辑、Mac mini 只读运行」，发布前校验两端 HEAD；避免线上手改。
8. **P3 仓库卫生**：`.gitignore` 增加 `.idea/`、`output.log`；删除未启用的 `vdoing/` 或明确标注为参考副本。
9. **P3 文档内链接**：为 `project-docs/` 增加索引并在 README 中引用，降低后续接手成本。

## 13. 给 AI agent 的硬性约束

1. 动手前先读 `project-docs/ARCHITECTURE.md` 与本文；涉及线上时先确认当前 HEAD 与进程状态。
2. 不改 `docs/@pages/`、`docs/.vuepress/dist/`、`node_modules/`、证书与私钥。
3. 不改已发布文章的 `permalink`；必须改时先说明评论/外链影响并取得确认。
4. 不把维护文档写进 `docs/`；统一放 `project-docs/`。
5. 不修改 `vdoing/` 来「修主题」，除非任务明确要求切换为本地主题。
6. 任何内容改动后至少运行 `npm run build`；失败或出现新 warning 时如实报告，不宣称完成。
7. 不新增明文密钥；发现凭据泄露只报告，不复制、不外传。
8. 线上操作（git pull、重启 8080、nginx reload）属于高风险动作，执行前说明影响并确认。
9. 开发机固定为 MacBook；Mac mini 只用于部署与运行，不在 Mac mini 上编辑或提交代码。
