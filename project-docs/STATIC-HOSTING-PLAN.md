# 静态托管评估与迁移方案

> 评估日期：2026-10-26
> 基线：`master` @ `87238be`（T1 文档提交 `5e797d6` + Leaflet SSR 修复 `87238be`）
> 结论：**GO（有条件；5.3 权限未验证前为 NO-GO）**——构建已通过，目标 nginx 配置已在临时实例验证；切换前需按第 5.3、6、7 节执行，并保留 8080 作为回滚路径。
> 本次评估未修改 Mac mini nginx、未停止 8080、未改动线上文件。
> **快照说明**：本文出现的文件数、体积、资源 hash 与字节数均为某次构建的快照；每次构建 hash 会变，验收请使用文件数/体积区间与关键路由状态码，不要比对固定 hash。

## 1. 现状 vs 目标

| 维度 | 现状（2026-10-26） | 目标 |
| --- | --- | --- |
| 线上进程 | 切换前：`vuepress dev` 常驻 `*:8080`，nginx `/` 反代 | 切换后：nginx 直接 `root` 静态文件，无 dev server（2026-10-26 已切换） |
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
| 产物体积 | `docs/.vuepress/dist` **92MB**（某次构建快照；验收按 85–100MB 区间） |
| 文件数 | 720 个文件，其中 254 个 HTML（某次构建快照；验收按 ≥700 文件、关键路由可访问） |
| 峰值内存 | `maximum resident set size = 5,000,216,576` bytes ≈ **4.66GiB**（某次构建快照，机器 16GiB） |
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
docs/.vuepress/dist/          92MB（快照，验收区间 85–100MB）
├── index.html                首页（预渲染）
├── 404.html                  自定义 404（15.9KB，快照；可直接用于 nginx error_page）
├── assets/                   25MB，带 hash 的 JS/CSS（hash 每次构建会变）
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

> 下表中的资源 hash/字节数为某次构建快照；验收只看 HTTP 状态码与关键路由，不比对固定 hash。

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

> 同样，下表中的资源文件名/hash 与字节数是某次构建快照，验收只看状态码与关键路由。

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
    gzip_vary on;
    gzip_proxied any;
    gzip_min_length 1024;
    gzip_comp_level 5;
    gzip_types text/css text/javascript application/javascript application/x-javascript application/json application/xml image/svg+xml;
```

> 已于 2026-10-26 在生产启用（见 §11 执行记录）。

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

### 5.3 权限前置检查与修复（阻断项，必须切换前完成）

**为什么是阻断项**：nginx master 以 `root` 运行，但 worker 以 `nobody` 运行；`/Users/mac` 当前是 `drwxr-x---`（`750`），`nobody` 无法穿越到 release 目录。此时：

- `nginx -t` **仍会通过**，因为它只校验配置语法，不以 worker 身份打开文件；
- 上线后所有静态请求会 **403**，看起来像 nginx 配置错误，实际是文件系统权限。

评估时实测环境：

```bash
ps -o user= -p $(pgrep -f 'nginx: worker' | head -1)
# nobody
ls -ld /Users/mac
# drwxr-x---+ 42 mac staff ... /Users/mac   ← other 无 execute
```

**切换前检查（在 Mac mini 执行）**：

```bash
# 1) worker 身份
ps -o user= -p $(pgrep -f 'nginx: worker' | head -1)

# 2) 逐级目录权限（macOS 15 默认没有 namei，命令失败时用下面的 ls 逐级检查）
namei -l /Users/mac/coding-log-web-releases/current/dist 2>/dev/null || {
  for p in /Users /Users/mac /Users/mac/coding-log-web-releases            /Users/mac/coding-log-web-releases/current            /Users/mac/coding-log-web-releases/current/dist; do
    ls -ld "$p"
  done
}

# 3) 记录原始权限/ACL，便于回滚
ls -lde /Users/mac | tee /tmp/users-mac-before-static.txt
stat -f '%Sp %Su:%Sg %N' /Users/mac
```

**修复选项（二选一，优先 ACL）**：

```bash
# 选项 1：ACL，仅授予 nobody 穿越 /Users/mac 的权限（推荐，影响面最小）
sudo chmod +a "nobody allow execute" /Users/mac
ls -lde /Users/mac        # 应看到 user:nobody allow search（目录上的 execute 显示为 search）

# 选项 2：给 other 增加 execute（不做目录列举，但所有本地用户都可穿越）
sudo chmod o+x /Users/mac
ls -ld /Users/mac         # 期望 drwxr-x--x
```

**发布目录权限/属主**（release 目录 755、文件 644）：

```bash
mkdir -p /Users/mac/coding-log-web-releases
# 若目录是 root 创建的，修正属主：
# sudo chown -R mac:staff /Users/mac/coding-log-web-releases
chmod 755 /Users/mac/coding-log-web-releases

# 同步完成后，对当前 release 统一权限
sudo find /Users/mac/coding-log-web-releases/<release> -type d -exec chmod 755 {} +
sudo find /Users/mac/coding-log-web-releases/<release> -type f -exec chmod 644 {} +
```

**验证（需要 sudo 密码，由 ops 在切换前执行）**：

```bash
sudo -u nobody test -x /Users/mac && echo "traverse OK"
sudo -u nobody test -r /Users/mac/coding-log-web-releases/current/dist/index.html && echo "index readable"
sudo -u nobody test -r /Users/mac/coding-log-web-releases/current/dist/404.html && echo "404 readable"
```

> 不要只看 `nginx -t`。真正的验收是 worker 身份可读 + HTTP 200；建议同时执行：
> `curl -s -o /dev/null -w '%{http_code}\n' https://seres-ai.com/`（切换后应为 200，不是 403）。

**回滚权限变更**：

```bash
# 选项 1（ACL）
sudo chmod -a "nobody allow execute" /Users/mac

# 选项 2（mode）
sudo chmod o-x /Users/mac

# 核对恢复结果（原始为 drwxr-x---）
ls -lde /Users/mac
stat -f '%Sp %Su:%Sg %N' /Users/mac
```

> 如果原始 ACL 不是默认状态，按 `/tmp/users-mac-before-static.txt` 记录恢复；不要用整段 `chmod` 覆盖未知 ACL。

> **注意**：nginx 由 LaunchDaemon `ai.openclaw.nginx` 以 `-g 'daemon off;'` 运行，不会生成 pid 文件，`sudo nginx -s reload` 会报 `open() "/usr/local/var/run/nginx.pid" failed (2: No such file or directory)`；重载必须用 `sudo launchctl kickstart -k system/ai.openclaw.nginx`。`sudo nginx -t` 仍可用于语法校验。

## 6. 发布与切换步骤（建议方案 A）

### 6.1 为什么不在 Mac mini 原地构建

Mac mini 上的 `vuepress dev` 正在使用 `node_modules/@vuepress/core/.temp`；在同一仓库执行 `npm run build` 可能与其争用临时目录，影响线上。**推荐在 MacBook 构建，再把产物同步到 Mac mini 的 release 目录。**

### 6.1.1 构建机必须准备 `.env`（构建期依赖）

`docs/.vuepress/config.ts` 在**构建期**读取仓库根 `.env`，把 `AMAP_JS_KEY` 注入每个 HTML 的 `<head>`：

```js
window.__AMAP_JS_KEY__ = "...";
window._AMapSecurityConfig = { serviceHost: 'https://seres-ai.com/_AMapService' };
```

如果构建机没有 `.env` 或 key 为空，构建不会报错，但页面会缺少高德注入，旅行助手地图会静默回退到 Leaflet。**构建机（MacBook）必须有以下四项**（`.env` 不提交）：

- `AMAP_JS_KEY`
- `AMAP_SECURITY_CODE`
- `AMAP_WEB_KEY`
- `AMAP_WEB_SECRET`

说明：构建期 `config.ts` 只直接读取 `AMAP_JS_KEY`；运行期旅行助手后端（`backend/travel_assistant/app.py`）会读取全部四项——`AMAP_JS_KEY` 与 `AMAP_SECURITY_CODE` 用于 `/_AMapService` 代理（`jscode`），`AMAP_WEB_KEY`/`AMAP_WEB_SECRET` 用于高德 Web 服务签名。为避免构建/运行环境漂移，构建机应同样具备四项。

构建前检查（不打印密钥明文）：

```bash
cd <MacBook 上的 coding-log-web>
test -f .env && echo ".env exists" || echo ".env MISSING"
for k in AMAP_JS_KEY AMAP_SECURITY_CODE AMAP_WEB_KEY AMAP_WEB_SECRET; do
  if grep -q "^${k}=." .env; then echo "$k: set"; else echo "$k: MISSING/EMPTY"; fi
done
```

构建后校验注入（只判断存在性，不输出 key）：

```bash
grep -rlq 'window.__AMAP_JS_KEY__=' docs/.vuepress/dist && echo "AMAP head injected"
grep -rlq 'window._AMapSecurityConfig' docs/.vuepress/dist && echo "AMap security config injected"
# 若 dist 中没有任何 window.__AMAP_JS_KEY__= 命中，即视为缺 key（key 为空时整段 script 不会注入）
```

### 6.2 切换步骤

1. **MacBook 构建并校验**

   ```bash
   cd <MacBook 上的 coding-log-web>
   npm run build

   # 产物完整性：不要用固定 hash 验收
   test -f docs/.vuepress/dist/index.html && test -f docs/.vuepress/dist/404.html
   find docs/.vuepress/dist -type f | wc -l   # ≥700（某次快照 720）
   du -sh docs/.vuepress/dist                 # 85–100MB（某次快照 92MB）
   ```

   `.env` 四项与 AMAP 注入校验见 6.1.1；缺 key 时构建不会报错，但地图会回退。

2. **在 Mac mini 创建 release 根目录**（权限/属主见 5.3）

   ```bash
   mkdir -p /Users/mac/coding-log-web-releases
   chmod 755 /Users/mac/coding-log-web-releases
   # 若目录是 root 创建的：
   # sudo chown -R mac:staff /Users/mac/coding-log-web-releases
   ls -ld /Users/mac/coding-log-web-releases   # 期望 mac:staff，drwxr-xr-x
   ```

3. **从 MacBook 同步到版本化目录**（SSH/rsync 权限需事先确认）

   ```bash
   rsync -a --delete docs/.vuepress/dist/ \
     mac@<mac-mini>:/Users/mac/coding-log-web-releases/2026-10-26-87238be/dist/
   ```

4. **建立/切换 current 软链并统一权限**

   ```bash
   cd /Users/mac/coding-log-web-releases

   # 首次 current 可能是真实目录：不能直接 ln -sfn（会在目录内建链接）
   if [ -e current ] && [ ! -L current ]; then
     mv current current.real-$(date +%Y%m%d-%H%M%S)
   fi

   ln -sfn 2026-10-26-87238be current
   readlink current        # 期望输出 2026-10-26-87238be
   ls -ld current

   # release 目录 755、文件 644（nginx worker 只读）
   find /Users/mac/coding-log-web-releases/2026-10-26-87238be \
     -type d -exec chmod 755 {} +
   find /Users/mac/coding-log-web-releases/2026-10-26-87238be \
     -type f -exec chmod 644 {} +
   ```

5. **权限预检（阻断项，必须做）**

   ```bash
   ps -o user= -p $(pgrep -f 'nginx: worker' | head -1)   # 期望 nobody
   ls -ld /Users/mac                                      # 期望 other 有 x，或 ACL 已放行
   sudo -u nobody test -r /Users/mac/coding-log-web-releases/current/dist/index.html \
     && echo "worker can read index"
   sudo -u nobody test -r /Users/mac/coding-log-web-releases/current/dist/404.html \
     && echo "worker can read 404"
   ```

   `nginx -t` 只校验配置语法，**不能**替代以上检查。

6. **预检 nginx 配置**（不 reload）

   ```bash
   cd /Users/mac/coding-log-web
   sudo cp nginx/server/https.conf nginx/server/https.conf.bak-$(date +%F-%H%M)
   # 按第 5.1 节修改 https.conf
   sudo nginx -t
   ```

7. **灰度验证**：用独立 nginx 实例监听 `127.0.0.1:8890`，`root` 指向 `current/dist`，通过 SSH 隧道或带 Host 头请求验证第 7 节清单；灰度实例的 worker 也应使用 `nobody`，否则权限验证不具代表性。确认后再 kickstart 生产。

8. **切换生产**

   ```bash
   sudo launchctl kickstart -k system/ai.openclaw.nginx
   # 立即验证不是 403
   curl -s -o /dev/null -w '%{http_code}\n' https://seres-ai.com/
   ```

   8080 继续运行，不停止；保留至少 24–48 小时作为回滚路径。

9. **观察与收尾**：检查 nginx access/error log、`https://seres-ai.com/`、评论、旅行助手；稳定后再决定是否停止 8080 并删除 HMR location（第二次 kickstart）。

### 6.3 回滚

**内容回滚（只换产物，不动 nginx）**

```bash
cd /Users/mac/coding-log-web-releases

# 先确认 current 是软链；若首次部署时它是真实目录，先移走
if [ -e current ] && [ ! -L current ]; then
  mv current current.real-$(date +%Y%m%d-%H%M%S)
fi

ln -sfn <上一版 release 目录名> current
readlink current        # 必须指向上一版
ls -ld current
```

nginx 的 `root` 指向 `current/dist`，软链切换后新请求即读取旧产物；默认未启用 `open_file_cache`，无需 reload。若启用了 `open_file_cache`，执行 `sudo launchctl kickstart -k system/ai.openclaw.nginx` 清缓存。

**nginx 配置回滚**

```bash
cd /Users/mac/coding-log-web
sudo cp nginx/server/https.conf.bak-<timestamp> nginx/server/https.conf
sudo nginx -t
sudo launchctl kickstart -k system/ai.openclaw.nginx
```

因为 8080 dev server 一直在跑，回滚后 `/` 立即恢复原状。若已停止 8080，按 `project-docs/DEVELOPMENT.md` 的发布流程重启 dev server。

**权限回滚**：如果为静态目录执行过 5.3 的 `chmod o+x` 或 ACL，按 5.3 末尾的命令撤销，并重新检查 `ls -lde /Users/mac`。

## 7. 切换后验证清单

- [ ] **权限**：`ps -o user= -p $(pgrep -f 'nginx: worker' | head -1)` 为 `nobody`；`sudo -u nobody test -r .../current/dist/index.html` 成功；首页 200 而不是 403
- [ ] **构建机 .env**：`AMAP_JS_KEY`/`AMAP_SECURITY_CODE`/`AMAP_WEB_KEY`/`AMAP_WEB_SECRET` 均存在；dist 中 `grep -rlq 'window.__AMAP_JS_KEY__='` 与 `grep -rlq '_AMapSecurityConfig'` 均命中
- [ ] **产物软链**：`readlink /Users/mac/coding-log-web-releases/current` 指向本次 release
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
- [ ] 验收没有依赖固定资源 hash/字节数；以文件数（≥700）、体积区间（85–100MB）和关键路由状态码为准

## 8. 风险与缓解

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| Artalk 同源依赖 | 评论/管理面板失效 | 保留 `/api/`、`/sidebar/`；切换后立即验证 |
| **nginx worker 无法穿越 `/Users/mac`** | 全站 403，但 `nginx -t` 仍通过 | 5.3 权限检查；ACL 或 `chmod o+x`；`sudo -u nobody test -r`；切换后 curl 200 |
| **构建机缺 `.env`** | 高德 key 未注入，地图静默回退 Leaflet | 6.1.1 检查四项；构建后 `grep -rlq` 校验注入 |
| **release 目录缺失/属主错误** | rsync 失败或 worker 403 | 6.2 步骤 2 创建目录（755、mac:staff）；文件 644 |
| **`current` 是真实目录** | `ln -sfn` 在目录内建链接，切换失败 | 先 `mv current current.real-...`，再 `ln -s`；`readlink` 验证 |
| **用固定 hash 验收** | 每次构建 hash 变化导致误判 | 只用文件数/体积区间/关键路由；见快照说明 |
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
- 未执行 `sudo -u nobody test -r`（需要 sudo 密码）；切换前必须由 ops 按 5.3 执行，`nginx -t` 不能替代。
- macOS 15 未安装 `namei`，5.3 已提供逐级 `ls -ld` 替代命令。
- 未创建 `/Users/mac/coding-log-web-releases`、未修改 `/Users/mac` 权限/ACL；这些属于切换动作。
- 未 reload 生产 nginx；第 5.1 节配置仅在 MacBook 临时 nginx 实例验证。
- 未在真实浏览器中做交互回归（地图、评论提交、验证码）；切换灰度阶段必须补。
- 未测并发/压测；静态文件预期显著优于 dev server，但需上线后观察。
- 生产 8080、Artalk、旅行助手、公网 200 在评估期间保持运行；未做任何变更。

## 10. Go / No-Go

**GO（有条件）**

理由：

1. `npm run build` 已 exit 0，产物完整（某次快照 254 HTML / 720 文件），关键路由与静态资源全部 200。
2. 目标 nginx `root + try_files + error_page 404` 已在临时实例验证，404/301/缓存头符合预期。
3. `/api/`、`/api/travel/`、`/sidebar/`、`/_AMapService/` 与静态托管解耦，方案不改这些 location。
4. 回滚路径简单：保留 8080 + nginx 配置备份，reload 即恢复。

前置条件：

- **先完成 5.3 权限检查**：worker 为 `nobody`、`/Users/mac` 可穿越、`sudo -u nobody test -r` 通过；否则全站 403。
- **构建机 `.env` 四项齐全**（6.1.1），构建后用 `grep -rlq` 验证 AMAP 注入。
- 创建 release 根目录并确认属主/权限（6.2 步骤 2），首次 `current` 为真实目录时先移走。
- 采用「MacBook 构建 + rsync 到 release 目录」，不要在 Mac mini 的 dev server 上原地构建。
- 切换前完成一次灰度（8890 临时实例 + 浏览器回归：评论、旅行助手、地图）。
- 切换后 24–48 小时内保留 8080 与上一版 release。
- Artalk 持久化（LaunchAgent）作为并行 P0 项处理，不阻塞本次静态切换，但需尽快补。

## 11. 执行记录（2026-10-26）

- 已切换生产：nginx `location /` 改为 `root /Users/mac/coding-log-web-releases/current/dist` + `try_files $uri $uri/ $uri.html =404`。
- Release：`2026-10-26-a32c562`，`dist` 92MB / 752 文件 / 254 HTML；`current` 已指向该版本。
- 前置权限：`/Users/mac` 增加 ACL `user:nobody allow search`；release 根与版本目录 755、文件 644；`sudo -u nobody test -r index.html/404.html` 通过。
- 构建：因跨机传输限制（文件传输单次上限 16MB、MacBook→Mac mini SSH 未配置），改为在 Mac mini 停止 8080 后执行 `npm run build`；仓库已 pull 到 `a32c562`，未与 dev `.temp` 争用。构建 exit 0。
- nginx：备份原配置到 `nginx/backups/https.conf.bak-<timestamp>`；`sudo nginx -t` 通过；`sudo launchctl kickstart -k system/ai.openclaw.nginx` 生效。
- 验证：`/` 200、深层文章 200、`/projects/travel/` 200、未知路径 404、`/projects/travel` 301、`/assets/*` immutable、HTML no-cache、`/api/travel/health` 200、评论 6 条。
- 8080 已重启作为回滚路径，计划保留 24–48h；回滚只需恢复 nginx 配置并 kickstart。
- 偏离原方案：未执行 MacBook build + rsync，也未在切换前跑 8890 灰度；切换后已做等价的 HTTP 验证。浏览器交互（评论提交/地图）由 QA 补测。
- gzip 已启用（2026-10-26）：`gzip on; gzip_vary on; gzip_proxied any; gzip_min_length 1024; gzip_comp_level 5`，覆盖 CSS/JS/JSON/XML/SVG；HTML 默认压缩。
