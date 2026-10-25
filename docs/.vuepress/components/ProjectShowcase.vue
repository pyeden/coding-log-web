<template>
  <section class="ps">
    <div class="ps-inner">
      <header class="ps-hero">
        <p class="ps-eyebrow"><i></i>PROJECT LAB / 2026</p>
        <h1>把想法做成<br /><span>可运行的项目</span></h1>
        <p class="ps-lead">这里是三木的实验场：智能体、旅行规划、内容系统，以及正在路上的新想法。</p>
        <div class="ps-stats">
          <div><b>02</b><span>在线项目</span></div>
          <div><b>16</b><span>AI 技术章节</span></div>
          <div><b>100%</b><span>自建部署</span></div>
        </div>
      </header>

      <div class="ps-cards">
        <a class="ps-card ps-card-featured" href="/projects/travel/" @mousemove="onMove">
          <div class="ps-card-head">
            <span class="ps-icon ps-icon-cyan" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none"><path d="M3 11.5 21 4l-7.5 18-2.7-7.3L3 11.5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="m10.8 14.7 3.7-3.7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
            </span>
            <span class="ps-status ps-live"><i></i>LIVE</span>
          </div>
          <h2>智能旅行助手</h2>
          <p>输入目的地、日期与偏好，自动生成逐日行程、预算明细和实用提示。前端 Vue，后端 FastAPI，已接入线上 API。</p>
          <div class="ps-tags"><span>FastAPI</span><span>Vue</span><span>Agent</span></div>
          <div class="ps-card-foot"><span>3 天行程 · 预算估算 · 实时 API</span><b>进入项目 <em>→</em></b></div>
        </a>

        <a class="ps-card" href="/ai/" @mousemove="onMove">
          <div class="ps-card-head">
            <span class="ps-icon ps-icon-violet" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none"><path d="M5 4.5h6.5A2.5 2.5 0 0 1 14 7v13H7.5A2.5 2.5 0 0 1 5 17.5v-13Z" stroke="currentColor" stroke-width="1.6"/><path d="M19 4.5h-5A2.5 2.5 0 0 0 11.5 7v13H17a2.5 2.5 0 0 0 2-2.5v-13Z" stroke="currentColor" stroke-width="1.6"/><path d="M8 8h2.5M8 12h2.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
            </span>
            <span class="ps-status ps-series">SERIES</span>
          </div>
          <h2>AI 技术专栏</h2>
          <p>《Hello-Agents》16 章学习笔记：从智能体范式、记忆检索到 MCP 与多智能体实战。</p>
          <div class="ps-tags"><span>LLM</span><span>Agent</span><span>MCP</span></div>
          <div class="ps-card-foot"><span>16 章 · 持续更新</span><b>开始阅读 <em>→</em></b></div>
        </a>

        <a class="ps-card" href="/archives/" @mousemove="onMove">
          <div class="ps-card-head">
            <span class="ps-icon ps-icon-lime" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none"><rect x="4" y="4" width="16" height="16" rx="2.5" stroke="currentColor" stroke-width="1.6"/><path d="m8 9 2.5 2L8 13M13 15h3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </span>
            <span class="ps-status">ENGINE</span>
          </div>
          <h2>博客系统</h2>
          <p>VuePress + vdoing 的内容底座：Markdown 驱动、结构化侧边栏、自动归档与站内索引。</p>
          <div class="ps-tags"><span>VuePress</span><span>vdoing</span><span>Markdown</span></div>
          <div class="ps-card-foot"><span>252 篇文章 · 持续迭代</span><b>浏览归档 <em>→</em></b></div>
        </a>

        <div class="ps-card ps-card-soon" @mousemove="onMove">
          <div class="ps-card-head">
            <span class="ps-icon ps-icon-pink" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none"><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="12" cy="12" r="3.2" stroke="currentColor" stroke-width="1.6"/></svg>
            </span>
            <span class="ps-status ps-soon">COMING SOON</span>
          </div>
          <h2>下一个实验</h2>
          <p>更多智能体应用、数据工具和可视化实验正在孵化。有想一起做的想法，欢迎来聊。</p>
          <div class="ps-tags"><span>IDEA</span><span>BUILD</span><span>SHIP</span></div>
          <div class="ps-card-foot"><span>正在孵化</span><b class="ps-muted">敬请期待</b></div>
        </div>
      </div>

      <footer class="ps-footer">
        <span>BUILT WITH CURIOSITY</span>
        <span class="ps-footer-line"></span>
        <span>FastAPI · VuePress · OpenClaw</span>
      </footer>
    </div>
  </section>
</template>

<script>
export default {
  name: 'ProjectShowcase',
  methods: {
    onMove(event) {
      const el = event.currentTarget
      const rect = el.getBoundingClientRect()
      el.style.setProperty('--mx', `${event.clientX - rect.left}px`)
      el.style.setProperty('--my', `${event.clientY - rect.top}px`)
    },
  },
}
</script>

<style scoped>
/* 项目页：完全复用站点设计 token（--site-*），只做栏目级排版 */
.ps {
  --ps-cyan: #22d3ee;
  --ps-violet: #8b5cf6;
  position: relative;
  width: 100%;
  margin: 0;
  color: var(--site-text);
}
.ps-inner {
  width: 100%;
  margin: 0 auto;
}

/* ---------- Hero ---------- */
.ps-hero { max-width: 700px; }
.ps-eyebrow {
  display: inline-flex; align-items: center; gap: .5rem;
  margin: 0; font-size: .68rem; font-weight: 600;
  letter-spacing: .18em; text-transform: uppercase;
  color: var(--site-accent-text);
}
.ps-eyebrow i {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--ps-cyan); box-shadow: 0 0 10px var(--ps-cyan);
}
.ps-hero h1 {
  margin: .85rem 0 .9rem;
  font-size: 2.15rem; line-height: 1.35;
  letter-spacing: -.02em; color: #f8fafc; font-weight: 650;
}
.ps-hero h1 span {
  background: linear-gradient(100deg, #67e8f9, #a78bfa 60%);
  -webkit-background-clip: text; background-clip: text;
  color: transparent; -webkit-text-fill-color: transparent;
}
.ps-lead {
  margin: 0; max-width: 620px;
  font-size: .95rem; line-height: 1.85; color: var(--site-muted);
}
.ps-stats { display: flex; flex-wrap: wrap; gap: 1.5rem; margin-top: 1.5rem; }
.ps-stats div {
  display: flex; flex-direction: column; gap: .15rem;
  padding-left: .9rem; border-left: 2px solid var(--site-border);
}
.ps-stats div:first-child { border-left-color: rgba(34, 211, 238, .5); }
.ps-stats b {
  font-size: 1.25rem; font-weight: 650; line-height: 1.2;
  color: #f8fafc; font-variant-numeric: tabular-nums;
}
.ps-stats span { font-size: .72rem; letter-spacing: .04em; color: var(--site-muted); }

/* ---------- 卡片栅格 ---------- */
.ps-cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  margin-top: 2.2rem;
}
.ps-card {
  position: relative;
  display: flex; flex-direction: column;
  padding: 1.15rem 1.2rem 1rem;
  background-color: var(--site-card);
  border: 1px solid var(--site-border);
  border-radius: 14px;
  box-shadow: 0 12px 32px var(--site-shadow);
  color: inherit; text-decoration: none; overflow: hidden;
  transition: transform .3s ease, border-color .3s ease, box-shadow .3s ease;
}
.ps-card:hover {
  transform: translateY(-3px);
  border-color: rgba(34, 211, 238, .35);
  box-shadow: 0 18px 44px var(--site-shadow);
}
.ps-card-featured {
  grid-column: 1 / -1;
  background-image: linear-gradient(135deg, rgba(34, 211, 238, .09), rgba(139, 92, 246, .05) 60%, transparent);
  border-color: rgba(34, 211, 238, .22);
}
.ps-card-featured::after {
  content: ''; position: absolute; right: -60px; top: -60px;
  width: 180px; height: 180px; border-radius: 50%;
  background: rgba(34, 211, 238, .16); filter: blur(46px);
  pointer-events: none;
}
.ps-card-soon { grid-column: 1 / -1; border-style: dashed; opacity: .8; }

.ps-card-head {
  position: relative;
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
}
.ps-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 38px; height: 38px; border-radius: 10px;
  border: 1px solid var(--site-border);
  background-color: rgba(255, 255, 255, .03);
  color: var(--site-accent-text);
}
.ps-icon svg { width: 20px; height: 20px; }
.ps-icon-violet { color: #c4b5fd; }
.ps-icon-lime { color: #bef264; }
.ps-icon-pink { color: #f9a8d4; }
.ps-status {
  display: inline-flex; align-items: center; gap: .4rem;
  font-size: .64rem; letter-spacing: .12em; color: var(--site-muted);
}
.ps-status i {
  width: 5px; height: 5px; border-radius: 50%;
  background: #4ade80; box-shadow: 0 0 8px #4ade80;
}
.ps-live { color: #86efac; }
.ps-series { color: #c4b5fd; }
.ps-soon { color: #f9a8d4; }

.ps-card h2 {
  position: relative;
  margin: .85rem 0 .45rem;
  font-size: 1.12rem; font-weight: 650; letter-spacing: -.01em;
  color: #f8fafc;
}
.ps-card p {
  position: relative;
  margin: 0 0 1rem;
  font-size: .84rem; line-height: 1.7; color: var(--site-muted);
}
.ps-tags { position: relative; display: flex; flex-wrap: wrap; gap: .4rem; margin-bottom: 1rem; }
.ps-tags span {
  padding: .16rem .5rem;
  border: 1px solid var(--site-border); border-radius: 999px;
  font-size: .66rem; color: var(--site-muted);
  background-color: rgba(255, 255, 255, .02);
}
.ps-card-foot {
  position: relative;
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  margin-top: auto; padding-top: .85rem;
  border-top: 1px solid var(--site-border);
  font-size: .72rem; color: var(--site-muted);
}
.ps-card-foot b { color: var(--site-accent-text); font-weight: 600; white-space: nowrap; }
.ps-card-foot em { font-style: normal; display: inline-block; transition: transform .25s ease; }
.ps-card:hover .ps-card-foot em { transform: translateX(3px); }
.ps-muted { color: var(--site-muted) !important; }

.ps-footer {
  display: flex; align-items: center; gap: 1rem;
  margin-top: 1.75rem; padding-top: 1rem;
  border-top: 1px solid var(--site-border);
  font-size: .66rem; letter-spacing: .14em; color: var(--site-muted);
}
.ps-footer-line { flex: 1; height: 1px; background: linear-gradient(90deg, rgba(34, 211, 238, .35), transparent); }

@media (max-width: 719px) {
  .ps-hero h1 { font-size: 1.75rem; }
  .ps-cards { grid-template-columns: minmax(0, 1fr); }
  .ps-card-featured, .ps-card-soon { grid-column: auto; }
  .ps-stats { gap: 1.1rem; }
  .ps-card-foot { flex-direction: column; align-items: flex-start; gap: .35rem; }
}
</style>
