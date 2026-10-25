<template>
  <section class="ps">
    <div class="ps-bg" aria-hidden="true">
      <span class="ps-orb ps-orb-a"></span>
      <span class="ps-orb ps-orb-b"></span>
      <span class="ps-orb ps-orb-c"></span>
      <span class="ps-grid"></span>
      <span class="ps-scan"></span>
    </div>

    <div class="ps-inner">
      <header class="ps-hero">
        <div class="ps-eyebrow"><i></i> PROJECT LAB / 2026</div>
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
          <span class="ps-card-sheen"></span>
          <div class="ps-card-head">
            <span class="ps-icon ps-icon-cyan" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none"><path d="M3 11.5 21 4l-7.5 18-2.7-7.3L3 11.5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="m10.8 14.7 3.7-3.7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
            </span>
            <span class="ps-status ps-live"><i></i> LIVE</span>
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
          <span class="ps-card-sheen"></span>
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
.ps {
  --ps-cyan: #22d3ee;
  --ps-violet: #8b5cf6;
  --ps-lime: #a3e635;
  --ps-pink: #f472b6;
  position: relative;
  width: 100vw;
  margin-left: calc(50% - 50vw);
  margin-right: calc(50% - 50vw);
  margin-top: -1.4rem;
  overflow: hidden;
  background: #060b16;
  color: #e5e7eb;
  isolation: isolate;
}
.ps-bg { position: absolute; inset: 0; overflow: hidden; pointer-events: none; }
.ps-orb { position: absolute; border-radius: 50%; filter: blur(70px); opacity: .5; }
.ps-orb-a { width: 420px; height: 420px; left: -120px; top: -120px; background: rgba(34, 211, 238, .45); }
.ps-orb-b { width: 460px; height: 460px; right: -160px; top: 120px; background: rgba(139, 92, 246, .38); }
.ps-orb-c { width: 320px; height: 320px; left: 35%; bottom: -180px; background: rgba(244, 114, 182, .22); }
.ps-grid {
  position: absolute; inset: 0;
  background-image: linear-gradient(rgba(148, 163, 184, .09) 1px, transparent 1px), linear-gradient(90deg, rgba(148, 163, 184, .09) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: linear-gradient(to bottom, rgba(0,0,0,.9), transparent 85%);
}
.ps-scan {
  position: absolute; inset: 0;
  background: linear-gradient(115deg, transparent 35%, rgba(34, 211, 238, .06) 48%, transparent 60%);
  transform: translateX(-100%);
  animation: ps-scan 9s linear infinite;
}
.ps-inner { position: relative; max-width: 1120px; margin: 0 auto; padding: 4.5rem 1.5rem 2.5rem; }
.ps-hero { max-width: 760px; margin-bottom: 2.5rem; }
.ps-eyebrow { display: inline-flex; align-items: center; gap: .5rem; font-size: .72rem; letter-spacing: .22em; color: #67e8f9; }
.ps-eyebrow i { width: 7px; height: 7px; border-radius: 50%; background: var(--ps-cyan); box-shadow: 0 0 12px var(--ps-cyan); animation: ps-pulse 2s ease-in-out infinite; }
.ps-hero h1 { margin: .8rem 0 1rem; font-size: clamp(2rem, 5vw, 3.4rem); line-height: 1.12; letter-spacing: -.03em; color: #f8fafc; }
.ps-hero h1 span { background: linear-gradient(100deg, #67e8f9, #a78bfa 55%, #f0abfc); -webkit-background-clip: text; background-clip: text; color: transparent; }
.ps-lead { max-width: 620px; margin: 0; color: #94a3b8; line-height: 1.8; font-size: .98rem; }
.ps-stats { display: flex; gap: 2.4rem; margin-top: 1.8rem; }
.ps-stats div { display: flex; flex-direction: column; gap: .2rem; }
.ps-stats b { font-size: 1.35rem; color: #f8fafc; font-variant-numeric: tabular-nums; }
.ps-stats span { font-size: .72rem; letter-spacing: .08em; color: #64748b; }
.ps-cards { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 1rem; }
.ps-card {
  position: relative;
  grid-column: span 6;
  display: flex;
  flex-direction: column;
  min-height: 260px;
  padding: 1.25rem 1.3rem 1.1rem;
  border: 1px solid rgba(148, 163, 184, .18);
  border-radius: 16px;
  background: linear-gradient(145deg, rgba(255,255,255,.055), rgba(255,255,255,.018));
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  transition: transform .35s ease, border-color .35s ease, box-shadow .35s ease;
}
.ps-card::before {
  content: ''; position: absolute; inset: 0; opacity: 0; transition: opacity .35s ease;
  background: radial-gradient(220px circle at var(--mx, 50%) var(--my, 50%), rgba(34, 211, 238, .12), transparent 70%);
}
.ps-card:hover { transform: translateY(-6px); border-color: rgba(34, 211, 238, .45); box-shadow: 0 18px 50px rgba(2, 8, 20, .55); }
.ps-card:hover::before { opacity: 1; }
.ps-card-featured { grid-column: span 7; border-color: rgba(34, 211, 238, .3); background: linear-gradient(145deg, rgba(34, 211, 238, .1), rgba(139, 92, 246, .07) 55%, rgba(255,255,255,.02)); }
.ps-card-featured::after {
  content: ''; position: absolute; width: 180px; height: 180px; right: -50px; top: -50px; border-radius: 50%;
  background: rgba(34, 211, 238, .18); filter: blur(40px);
}
.ps-cards .ps-card:nth-child(2) { grid-column: span 5; }
.ps-cards .ps-card:nth-child(3) { grid-column: span 5; }
.ps-card-soon { grid-column: span 7; opacity: .76; border-style: dashed; }
.ps-card-sheen { position: absolute; inset: 0; background: linear-gradient(110deg, transparent 30%, rgba(255,255,255,.08) 45%, transparent 60%); transform: translateX(-120%); transition: transform .7s ease; }
.ps-card:hover .ps-card-sheen { transform: translateX(120%); }
.ps-card-head { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 1.15rem; }
.ps-icon { display: inline-flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 12px; border: 1px solid currentColor; }
.ps-icon svg { width: 22px; height: 22px; }
.ps-icon-cyan { color: #67e8f9; background: rgba(34, 211, 238, .08); box-shadow: 0 0 24px rgba(34, 211, 238, .14); }
.ps-icon-violet { color: #c4b5fd; background: rgba(139, 92, 246, .1); }
.ps-icon-lime { color: #bef264; background: rgba(163, 230, 53, .08); }
.ps-icon-pink { color: #f9a8d4; background: rgba(244, 114, 182, .08); }
.ps-status { display: inline-flex; align-items: center; gap: .4rem; font-size: .64rem; letter-spacing: .14em; color: #94a3b8; }
.ps-status i { width: 6px; height: 6px; border-radius: 50%; background: #4ade80; box-shadow: 0 0 10px #4ade80; animation: ps-pulse 2s ease-in-out infinite; }
.ps-live { color: #86efac; }
.ps-series { color: #c4b5fd; }
.ps-soon { color: #f9a8d4; }
.ps-card h2 { position: relative; margin: 0 0 .6rem; font-size: 1.3rem; color: #f8fafc; letter-spacing: -.01em; }
.ps-card p { position: relative; margin: 0 0 1rem; color: #94a3b8; font-size: .86rem; line-height: 1.75; }
.ps-tags { display: flex; flex-wrap: wrap; gap: .4rem; margin-bottom: 1rem; }
.ps-tags span { padding: .16rem .5rem; border: 1px solid rgba(148, 163, 184, .2); border-radius: 999px; font-size: .66rem; color: #cbd5e1; background: rgba(255,255,255,.025); }
.ps-card-foot { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-top: auto; padding-top: .9rem; border-top: 1px solid rgba(148, 163, 184, .12); font-size: .72rem; color: #64748b; }
.ps-card-foot b { color: #67e8f9; font-weight: 600; white-space: nowrap; }
.ps-card-foot em { font-style: normal; display: inline-block; transition: transform .25s ease; }
.ps-card:hover .ps-card-foot em { transform: translateX(4px); }
.ps-muted { color: #64748b !important; }
.ps-footer { display: flex; align-items: center; gap: 1rem; margin-top: 2.2rem; font-size: .62rem; letter-spacing: .18em; color: #475569; }
.ps-footer-line { flex: 1; height: 1px; background: linear-gradient(90deg, rgba(34,211,238,.35), transparent); }
@keyframes ps-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .35; } }
@keyframes ps-scan { to { transform: translateX(100%); } }
@media (max-width: 900px) {
  .ps-inner { padding-top: 3.2rem; }
  .ps-card, .ps-card-featured, .ps-cards .ps-card:nth-child(2), .ps-cards .ps-card:nth-child(3), .ps-card-soon { grid-column: span 12; }
  .ps-card { min-height: 0; }
  .ps-stats { gap: 1.5rem; }
}
@media (max-width: 560px) {
  .ps-inner { padding-left: 1rem; padding-right: 1rem; }
  .ps-hero h1 { font-size: 2rem; }
  .ps-stats { flex-wrap: wrap; gap: 1rem 1.6rem; }
  .ps-card-foot { align-items: flex-start; flex-direction: column; gap: .35rem; }
}
@media (prefers-reduced-motion: reduce) {
  .ps-scan, .ps-eyebrow i, .ps-status i { animation: none; }
  .ps-card, .ps-card-sheen { transition: none; }
}
</style>
