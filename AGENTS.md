# AGENTS.md — coding-log-web

本仓库是 VuePress 1 + vdoing 主题的静态博客/知识库。开发前先读：

- `project-docs/ARCHITECTURE.md` — 架构、路由、构建、部署与风险
- `project-docs/DEVELOPMENT.md` — 规范、流程、排错与硬性约束

## 硬性约束

1. 内容统一放 `docs/`；项目维护文档只放 `project-docs/`，禁止放进 `docs/`。
2. 结构化栏目中的目录和 md 文件必须以 `数字.` 开头；`_posts/` 例外（无序号，仅一级分类子目录）。
3. 不修改已发布文章的 `permalink`（会导致外链失效、Gitalk 评论丢失）。
4. 不手改 `docs/@pages/`、`docs/.vuepress/dist/`、`node_modules/`。
5. `vdoing/` 是未启用的主题源码副本；改它不会生效，除非显式切换为本地主题。
6. 不新增明文密钥/token/证书私钥；发现泄露只报告。
7. 内容或配置改动后至少运行 `npm run build`，如实报告警告；不要未验证就宣称完成。
8. 线上（Mac mini `/Users/mac/coding-log-web`、8080 进程、nginx）属于高风险操作，执行前说明影响并确认。
9. 开发固定在本机 MacBook；Mac mini 仅部署运行，不在 Mac mini 上编辑或提交。

## 常用命令

```bash
npm run dev      # http://localhost:8080
npm run build    # docs/.vuepress/dist
npm run editFm   # 按 utils/config.yml 批量改 frontmatter
```
