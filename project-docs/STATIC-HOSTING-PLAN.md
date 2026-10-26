# 静态托管评估与迁移方案

> 评估日期：2026-10-26
> 基线：`master` @ `87238be`（T1 文档提交 `5e797d6` + Leaflet SSR 修复 `87238be`）
> 结论：**GO（有条件）**——构建已通过，目标 nginx 配置已在临时实例验证；切换前需按第 8 节执行，并保留 8080 作为回滚路径。
> 本次评估未修改 Mac mini nginx、未停止 8080、未改动线上文件。

## 1. 现状 vs 目标

| 维度 | 现状（2026-10-26） | 目标 |
| --- | --- | --- |
| 线上进程 | `vuepress dev` 常驻 `*:8080`，nginx `/` 反代 | nginx 直接 `root` 静态文件，无 dev server |
| 内容生效 | 改源码/热更新即时生效 | `git pull` + 构建/同步产物后生效 |
| 性能 | 无压缩、无长缓存、每次请求走 webpack dev server | 预渲染 HTML + 带 hash 静态资源，可长缓存/gzip |
| 稳定性 | 编译错误或进程崩溃直接影响全站 | 静态文件只读，故障面小 |
| HMR | 有 `/sockjs-node/`、`*.hot-update.*` | 生产不需要，切换后移除 |
| 回滚 | 无版本化产物 | 保留 release 目录/nginx 备份，秒级回滚 |
| 评论/旅行助手 | nginx `/api/`、`/api/travel/`、`/sidebar/`、`/_AMapService/` 反代 | **保持不变**，与静态托管解耦 |

## 2. 构建证据

在 MacBook 开发副本执行 `npm run build`（Node v24.22.1 / npm 11.19.1）：

| 指标 | 结果 |
| --- | --- |
| 退出码 | `0` |
| 耗时 | real **50.73s**（另一次 51.16s；Server 35.13s / Client 38.34s） |
| 产物体积 | `docs/.vuepress/dist` **92MB** |
| 文件数 | 720 个文件，其中 254 个 HTML（sitemap 254 locations） |
| 峰值内存 | `maximum resident set size = 5,000,216,576` bytes ≈ **4.66GiB**（机器 16GiB） |
| 构建前/后 `git status` | 无主题自动改写 frontmatter；仅有预期的 `TravelAssistant.vue` 改动与既存 untracked 项 |

### 2.1 构建 warning 清单

- `序号出错` ×5，均在 `docs/04.更多/01.学习/` 下：
  - `Transformer 位置编码机制`
  - `Transformer 位置编码（RoPE 旋转位置编码）`
  - `Transformer 注意力机制 MHA，MQA，GQA`
  - `Transformer 自注意力机制`
  - `常见LLM架构 Encoder-Only Decoder-Only Encoder-Decoder`
- 无「重复 permalink」warning。
- 无「非 .md 文件」warning。
- 另有非阻断提示：Babel 对超过 500KB 的文件降级代码风格；`caniuse-lite` 数据 6 个月未更新（建议 `npx update-browserslist-db@latest`）。

### 2.2 评估中发现并修复的构建阻塞

首次构建 **exit 1**，失败于 `/projects/travel/`：

```
ReferenceError: window is not defined
Failed to resolve async component ...
Error: render function or template not defined in component: TravelAssistant
```

原因：`docs/.vuepress/components/TravelAssistant.vue` 在模块顶层 `import L from 'leaflet'`，Leaflet 加载时访问 `window`，SSR 渲染阶段崩溃。
修复（commit `87238be`）：改为客户端 `initMap()` 中 `await import('leaflet')`，保留 CSS 引入。修复后构建 exit 0，`/projects/travel/` 正常产出。

> 该修复只影响 Leaflet 回退路径的加载时机；高德地图路径未改。

## 3. 构建产物结构

```
docs/.vuepress/dist/          92MB
├── index.html                首页（预渲染）
├── 404.html                  自定义 404（15.9KB，可直接用于 nginx error_page）
├── assets/                   25MB，带 hash 的 JS/CSS
├── img/                      42MB，public 静态图
├── pages/                    24MB，文章详情页（每个 permalink 一个目录）
├── projects/                 /projects/、/projects/travel/
├── ai/ archives/ categories/ tags/
├── note/ web/ ui/ technology/ more/ about/ friends/
├── sitemap.xml
└── CNAME                     内容为 b.xugaoyi.com（模板残留，nginx 不使用）
```

VuePress 为每个路由生成独立 `index.html`，**不需要 SPA fallback**；未知路径应返回 404 页面。

## 4. 静态服务实测

### 4.1 本地 Python 静态服务器（8091，MacBook）

`python3 -m http.server 8091 --bind 127.0.0.1`，根目录 `docs/.vuepress/dist`：

| URL | 状态 | 大小 |
| --- | --- | --- |
| `/` | 200 | 49,109B |
| `/pages/8143cc480faf9a11/`（深层文章） | 200 | 46,082B |
| `/projects/` | 200 | 38,294B |
| `/projects/travel/` | 200 | 35,697B |
| `/ai/` | 200 | 34,652B |
| `/archives/` | 200 | 42,783B |
| `/categories/` | 200 | 49,566B |
| `/tags/` | 200 | 51,214B |
| `/assets/css/0.styles.6f1606c2.css` | 200 | 259,218B |
| `/assets/js/app.075a6fc4.js` | 200 | 1,014,988B |
| `/404.html` | 200 | 15,952B |
| `/random-not-exist-xyz/` | 404 | 469B（Python 默认页） |
| `/pages/notexist123/` | 404 | 469B |
| `/projects/travel`（无斜杠） | 301 | — |

同时确认：静态服务器下 `/api/travel/health`、`/api/v2/comments`、`/sidebar/` 均 404——**评论与旅行助手必须继续由 nginx 反代**，不能只靠静态服务。

### 4.2 目标 nginx 配置验证（临时 8092，MacBook）

用独立 nginx 实例（独立 pid/log，不触碰生产）加载第 5 节配置：

| URL | 状态 | 说明 |
| --- | --- | --- |
| `/` | 200 | 首页 |
| `/pages/8143cc480faf9a11/` | 200 | 深层文章 |
| `/projects/` | 200 | 项目页 |
| `/projects/travel/` | 200 | 旅行助手页 |
| `/archives/` `/categories/` `/tags/` | 200 | 索引页 |
| `/assets/css/0.styles.6f1606c2.css` | 200 | `Cache-Control: public, max-age=2592000, immutable` |
| `/random-not-exist-xyz/` | 404 | 返回自定义 `404.html`（15,952B） |
| `/projects/travel` | 301 | 目录补斜杠 |
| `/404.html` | 404 | `internal` 限制，仅错误页内部使用 |

## 5. nginx 改造方案

### 5.1 推荐方案 A：nginx 直接托管（无需额外进程）

在 `nginx/server/https.conf` 的 `server { ... }` 内增加 `root`/`index`，并替换现有 `location /`：

**现状（节选）**

```nginx
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
```

**目标（替换后）**

```nginx
    # 发布目录（建议用 release + symlink，见第 6 节）
    root /Users/mac/coding-log-web-releases/current/dist;
    index index.html;

    # 带 hash 的构建资源，可长缓存
    location /assets/ {
        try_files $uri =404;
        add_header Cache-Control "public, max-age=2592000, immutable";
    }

    # public 图片，中等缓存
    location /img/ {
        try_files $uri =404;
        add_header Cache-Control "public, max-age=604800";
    }

    # 预渲染页面；HTML 不缓存，保证发布后立即生效
    location / {
        try_files $uri $uri/ $uri.html =404;
        add_header Cache-Control "no-cache";
    }

    error_page 404 /404.html;
    location = /404.html {
        internal;
    }
```

**同时删除**（切换完成后）：

```nginx
    location /sockjs-node/ { ... }
    location ~* \.hot-update\.(js|json)$ { ... }
```

**必须保留**：`/sidebar/`、`/_AMapService/`、`/api/travel/`、`/api/`、`/openclaw`、`/__openclaw__/`。前缀匹配按最长优先，`/api/travel/` 仍会胜过 `/api/`。

可选性能项（放在 `server` 或 `http`）：

```nginx
    gzip on;
    gzip_min_length 1024;
    gzip_types text/css application/javascript application/json image/svg+xml;
```

### 5.2 备选方案 B：launchd 守护静态服务器，nginx 不动

仅当运维坚持保留「8080 进程模型」时使用。缺点：多一个进程、需自行处理缓存/压缩/404，不推荐。

部署前先 `mkdir -p /Users/mac/coding-log-web/logs`。

`~/Library/LaunchAgents/ai.openclaw.coding-log-web-static.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>ai.openclaw.coding-log-web-static</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>-m</string>
    <string>http.server</string>
    <string>8080</string>
    <string>--bind</string>
    <string>127.0.0.1</string>
    <string>--directory</string>
    <string>/Users/mac/coding-log-web-releases/current/dist</string>
  </array>
  <key>WorkingDirectory</key><string>/Users/mac/coding-log-web-releases/current/dist</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>5</integer>
  <key>StandardOutPath</key><string>/Users/mac/coding-log-web/logs/static.log</string>
  <key>StandardErrorPath</key><string>/Users/mac/coding-log-web/logs/static.log</string>
</dict>
</plist>
```

> `python3 -m http.server` 不支持自定义缓存头、gzip 和自定义 404，只适合临时过渡。若走方案 B，建议改用成熟静态服务器并单独验证。

## 6. 发布与切换步骤（建议方案 A）

### 6.1 为什么不在 Mac mini 原地构建

Mac mini 上的 `vuepress dev` 正在使用 `node_modules/@vuepress/core/.temp`；在同一仓库执行 `npm run build` 可能与其争用临时目录，影响线上。**推荐在 MacBook 构建，再把产物同步到 Mac mini 的 release 目录。**

### 6.2 切换步骤

1. **MacBook 构建并校验**

   ```bash
   cd <MacBook 上的 coding-log-web>
   npm run build
   find docs/.vuepress/dist -type f | wc -l          # 期望 720
   du -sh docs/.vuepress/dist                        # 期望 ~92M
   ```

2. **同步到 Mac mini 的版本化目录**（SSH/rsync 权限需事先确认）

   ```bash
   rsync -a --delete docs/.vuepress/dist/ \
     mac@<mac-mini>:/Users/mac/coding-log-web-releases/2026-10-26-87238be/dist/
   ```

3. **在 Mac mini 建立 current 软链并保留上一版**

   ```bash
   cd /Users/mac/coding-log-web-releases
   ln -sfn 2026-10-26-87238be current
   ls -l current
   ```

4. **预检 nginx 配置**（不 reload）

   ```bash
   cd /Users/mac/coding-log-web
   sudo cp nginx/server/https.conf nginx/server/https.conf.bak-$(date +%F-%H%M)
   # 按第 5.1 节修改 https.conf
   sudo nginx -t
   ```

5. **灰度验证**：用独立 nginx 实例监听 `127.0.0.1:8890`，`root` 指向 `current/dist`，通过 SSH 隧道或带 Host 头请求验证第 7 节清单；确认后再 reload 生产。

6. **切换生产**

   ```bash
   sudo nginx -s reload
   ```

   8080 继续运行，不停止；保留至少 24–48 小时作为回滚路径。

7. **观察与收尾**：检查 nginx access/error log、`https://seres-ai.com/`、评论、旅行助手；稳定后再决定是否停止 8080 并删除 HMR location（第二次 reload）。

### 6.3 回滚

```bash
cd /Users/mac/coding-log-web
sudo cp nginx/server/https.conf.bak-<timestamp> nginx/server/https.conf
sudo nginx -t
sudo nginx -s reload
```

因为 8080 dev server 一直在跑，回滚后 `/` 立即恢复原状。若已停止 8080，先按第 10.2 节重启 dev server。

## 7. 切换后验证清单

- [ ] `https://seres-ai.com/` 200，首页样式/图片正常
- [ ] 深层文章（如 `/pages/8143cc480faf9a11/`）200，代码高亮/图片正常
- [ ] `/projects/`、`/projects/travel/`、`/ai/`、`/archives/`、`/categories/`、`/tags/` 均 200
- [ ] 任意不存在路径返回自定义 404，且状态码为 404（不是 200）
- [ ] `/assets/*` 返回 `Cache-Control: immutable`，HTML 返回 `no-cache`
- [ ] `/api/travel/health` 200 且返回 `{"status":"ok",...}`；旅行助手页面可生成行程
- [ ] `/sidebar/` 200，Artalk 管理面板可登录
- [ ] 文章页评论区加载、可提交（注意图片验证码）
- [ ] `/openclaw` 不受影响
- [ ] 8080 仍可访问（回滚路径），`lsof -nP -iTCP:8080 -sTCP:LISTEN` 有进程
- [ ] nginx error log 无新增 5xx/上游错误

## 8. 风险与缓解

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| Artalk 同源依赖 | 评论/管理面板失效 | 保留 `/api/`、`/sidebar/`；切换后立即验证 |
| `/api/travel/` 被 `/api/` 接管 | 旅行助手 404/错误响应 | 保留更长前缀；`nginx -t` + curl health |
| HMR 丢失 | 线上不再热更新 | 发布改为 pull + 构建 + 同步；属预期 |
| 缓存策略错误 | 用户看到旧 HTML 或资源 404 | HTML `no-cache`；assets 带 hash + immutable；发布后抽查 |
| 构建耗时/内存 | Mac mini 上构建可能影响 dev server | 在 MacBook 构建后 rsync；避免与 dev 共用 `.temp` |
| 404 行为 | 未知路径返回 200 或默认页 | `try_files ... =404` + `error_page 404 /404.html`（已实测） |
| 目录无斜杠 | 链接 301，SEO 可接受 | 保持站内链接带 `/`；nginx 自动 301 已实测 |
| dist 不在 git | 无法靠 `git pull` 得到产物 | release 目录 + 校验和/文件数；保留上一版 |
| nginx `proxy_protocol` | 本地直连 8888 无法自测 | 通过公网域名或临时 8890 实例验证 |
| 旧 permalink/评论 | 改路径会丢评论 | 不改已发布 permalink；本次迁移不涉及路径变更 |
| 5 个序号 warning | 侧边栏可能缺项 | 与静态托管无关，单独修复 |
| Artalk 进程非持久 | 重启后评论不可用 | 独立 P0 项：补 LaunchAgent |
| CNAME 残留 | 仅静态文件，不影响 nginx | 后续统一站点身份时处理 |

## 9. 验证边界（未做/待确认）

- 未在 Mac mini 执行构建或 rsync（按约束不改生产）；SSH/rsync 权限与目标目录需确认。
- 未 reload 生产 nginx；第 5.1 节配置仅在 MacBook 临时 nginx 实例验证。
- 未在真实浏览器中做交互回归（地图、评论提交、验证码）；切换灰度阶段必须补。
- 未测并发/压测；静态文件预期显著优于 dev server，但需上线后观察。
- 生产 8080、Artalk、旅行助手、公网 200 在评估期间保持运行；未做任何变更。

## 10. Go / No-Go

**GO（有条件）**

理由：

1. `npm run build` 已 exit 0，产物完整（254 HTML / 720 文件），关键路由与静态资源全部 200。
2. 目标 nginx `root + try_files + error_page 404` 已在临时实例验证，404/301/缓存头符合预期。
3. `/api/`、`/api/travel/`、`/sidebar/`、`/_AMapService/` 与静态托管解耦，方案不改这些 location。
4. 回滚路径简单：保留 8080 + nginx 配置备份，reload 即恢复。

前置条件：

- 采用「MacBook 构建 + rsync 到 release 目录」，不要在 Mac mini 的 dev server 上原地构建。
- 切换前完成一次灰度（8890 临时实例 + 浏览器回归：评论、旅行助手、地图）。
- 切换后 24–48 小时内保留 8080 与上一版 release。
- Artalk 持久化（LaunchAgent）作为并行 P0 项处理，不阻塞本次静态切换，但需尽快补。
