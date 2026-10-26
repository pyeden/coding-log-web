# 开机自启服务（LaunchDaemons）

线上项目的常驻服务统一放在 `/Library/LaunchDaemons/`，开机即启动，不依赖用户登录。

| 服务 | Label | 端口 | 运行身份 | 日志/配置 |
| --- | --- | --- | --- | --- |
| 博客 dev server（回滚） | `ai.openclaw.codinglogweb.dev` | 8080 | `mac` | 公网已由 nginx 静态 release 提供；8080 仅回滚 |
| 旅行助手 API | `ai.openclaw.travel-api` | 8090 | `mac` | `backend/travel_assistant/server.log` |
| Artalk 评论 | `ai.openclaw.artalk` | 23366 | `mac` | `/Users/mac/artalk/server.log` |
| nginx（静态主站） | `ai.openclaw.nginx` | 8887/8888 | `root`（worker `nobody`） | root=`coding-log-web-releases/current/dist`；配置在 `nginx/server/*` |
| frpc 隧道 | `com.frpc.tunnel` | 80/443 隧道 | `mac` | `frp_0.68.0_darwin_amd64/frpc.launchd.log` |

## 常用命令

```bash
# 状态
launchctl print system/ai.openclaw.codinglogweb.dev
launchctl print system/ai.openclaw.travel-api
launchctl print system/com.frpc.tunnel
launchctl print system/ai.openclaw.nginx
launchctl print system/ai.openclaw.artalk

# 重启单个服务
sudo launchctl kickstart -k system/<label>

# 重新加载 plist
sudo launchctl bootout system/<label> 2>/dev/null || true
sudo launchctl bootstrap system /Library/LaunchDaemons/<label>.plist
```

## 注意

- 旧的用户 LaunchAgent（`ai.openclaw.travel-api`、`com.frpc.tunnel`、`homebrew.mxcl.nginx`、`ai.openclaw.artalk`）已改名并 `bootout`，避免与 daemon 重复；文件名形如 `*.disabled-by-daemon-*`。
- nginx 的 `include /Users/mac/coding-log-web/nginx/server/*` 会加载目录下所有文件；`.bak` 必须放到 `nginx/backups/`，否则会重复 `listen`/`server_name`。
- 改 nginx 配置后：`sudo nginx -t` → `sudo launchctl kickstart -k system/ai.openclaw.nginx`。
- 博客 dev server 首次启动需要 15–25s 编译；期间公网可能 502，属预期。
- **OpenClaw Gateway（18789）仍是 LaunchAgent**，属于当前会话宿主，未纳入本目录；它随用户登录启动。若要它也开机自启，需要单独维护窗口处理。
