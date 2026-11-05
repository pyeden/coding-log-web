<template>
  <section class="ra" :aria-busy="state === 'loading'">
    <header class="ra-hero">
      <p class="ra-kicker"><i></i>RESUME LAB / KNOWLEDGE BASE</p>
      <h2>一份由知识库持续维护的简历</h2>
      <p class="ra-lead">
        这份简历由知识库与博客内容自动汇总生成：只写有出处的事实，
        知识库没有的栏目会明确标注「知识库未收录」，不补写、不推测。
      </p>
      <div class="ra-meta">
        <span v-if="generatedAt" class="ra-meta-item">
          <em>上次更新</em>{{ generatedAt }}
        </span>
        <span class="ra-meta-item"><em>来源</em>内容由知识库自动生成</span>
        <span v-if="writingCount" class="ra-meta-item">
          <em>语料</em>{{ writingCount }} 篇文章
        </span>
      </div>
    </header>

    <!-- 维护面板：仅 ?admin=1 可见 -->
    <section v-if="isAdmin" class="ra-admin" aria-label="简历维护面板">
      <div class="ra-admin-head">
        <h3>维护模式</h3>
        <span class="ra-admin-badge">仅 ?admin=1 可见</span>
      </div>
      <p class="ra-admin-hint">
        令牌只写入当前标签页的 sessionStorage，关闭标签页即失效；刷新接口 30 秒内只允许触发一次。
      </p>
      <div class="ra-admin-row">
        <label class="ra-field">
          <span>刷新令牌</span>
          <input
            v-model="token"
            type="password"
            autocomplete="new-password"
            spellcheck="false"
            placeholder="RESUME_REFRESH_TOKEN"
            @input="persistToken"
          />
        </label>
        <button type="button" class="ra-btn ra-btn-primary" :disabled="refreshing" @click="refresh">
          {{ refreshing ? '更新中…' : '立即更新' }}
        </button>
      </div>
      <p
        v-if="refreshFeedback"
        class="ra-admin-feedback"
        :class="'is-' + refreshFeedback.type"
        role="status"
        aria-live="polite"
      >{{ refreshFeedback.text }}</p>
    </section>

    <!-- 加载中 -->
    <div v-if="state === 'loading'" class="ra-state" role="status">
      <span class="ra-spinner" aria-hidden="true"></span>
      <p class="ra-state-title">正在从知识库读取简历…</p>
      <p class="ra-state-text">第一次生成可能需要几秒。</p>
    </div>

    <!-- 请求失败 -->
    <div v-else-if="state === 'error'" class="ra-state ra-state-error" role="alert">
      <p class="ra-state-title">简历暂时读不出来</p>
      <p class="ra-state-text">{{ errorMessage }}</p>
      <button type="button" class="ra-btn" @click="load()">重新加载</button>
    </div>

    <!-- 空数据 -->
    <div v-else-if="state === 'empty'" class="ra-state" role="status">
      <p class="ra-state-title">知识库还没有可展示的内容</p>
      <p class="ra-state-text">
        接口返回了空简历。补全 resume-kb 的 profile / skills / projects 后重新生成，这里就会出现内容。
      </p>
      <button type="button" class="ra-btn" @click="load()">重新加载</button>
    </div>

    <!-- 正常态 -->
    <div v-else class="ra-body">
      <section class="ra-profile">
        <div class="ra-profile-main">
          <p class="ra-profile-role">{{ profile.title || '软件工程师' }}</p>
          <h3 class="ra-profile-name">{{ profile.name || '未署名' }}</h3>
          <p v-if="profile.summary" class="ra-profile-summary">{{ profile.summary }}</p>
          <div v-if="directions.length" class="ra-chips ra-chips-accent">
            <span v-for="d in directions" :key="d" class="ra-chip">{{ d }}</span>
          </div>
        </div>
        <div v-if="links.length" class="ra-links">
          <a
            v-for="link in links"
            :key="link.url"
            class="ra-link"
            :href="link.url"
            target="_blank"
            rel="noopener noreferrer"
          >
            <span>{{ link.label }}</span><em aria-hidden="true">↗</em>
          </a>
        </div>
      </section>

      <section v-if="skillGroups.length" class="ra-section">
        <h3 class="ra-title">技术能力<em>{{ skillGroups.length }} 组</em></h3>
        <div class="ra-skills">
          <article v-for="group in skillGroups" :key="group.group" class="ra-skill">
            <h4>{{ group.group }}</h4>
            <!-- 有分值：名称 + 水平柱 + 分值；无分值：保持旧 chips -->
            <ul v-if="group.useBars" class="ra-skill-bars">
              <li v-for="(item, i) in group.items" :key="item.name + '-' + i" class="ra-skill-row">
                <span class="ra-skill-name" :title="item.name">{{ item.name }}</span>
                <span
                  class="ra-skill-track"
                  role="progressbar"
                  aria-valuemin="0"
                  aria-valuemax="100"
                  :aria-valuenow="item.level"
                  :aria-label="item.name + ' ' + item.level + ' 分'"
                ><i :style="{ width: item.level + '%' }" aria-hidden="true"></i></span>
                <span class="ra-skill-value" aria-hidden="true">{{ item.level }}</span>
              </li>
            </ul>
            <ul v-else class="ra-skill-chips">
              <li v-for="(item, i) in group.items" :key="item.name + '-' + i">{{ item.name }}</li>
            </ul>
          </article>
        </div>
      </section>

      <section v-if="projects.length" class="ra-section">
        <h3 class="ra-title">项目经历<em>{{ projects.length }} 个</em></h3>
        <div class="ra-projects">
          <article v-for="project in projects" :key="project.name" class="ra-project">
            <header class="ra-project-head">
              <h4>{{ project.name }}</h4>
              <span v-if="projectMeta(project)" class="ra-project-meta">{{ projectMeta(project) }}</span>
            </header>
            <p v-if="project.summary" class="ra-project-summary">{{ project.summary }}</p>
            <ul v-if="project.highlights && project.highlights.length" class="ra-highlights">
              <li v-for="(line, i) in project.highlights" :key="i">{{ line }}</li>
            </ul>
            <p v-if="isSparseProject(project)" class="ra-project-empty">
              简介与技术栈尚未在知识库收录，这里只展示条目名称与链接。
            </p>
            <div class="ra-project-foot">
              <div v-if="project.tech && project.tech.length" class="ra-chips ra-chips-sm">
                <span v-for="tech in project.tech" :key="tech" class="ra-chip">{{ tech }}</span>
              </div>
              <a
                v-if="project.link"
                class="ra-project-link"
                :href="project.link"
                target="_blank"
                rel="noopener noreferrer"
              >查看项目 ↗</a>
            </div>
          </article>
        </div>
      </section>

      <section v-if="writingCount" class="ra-section">
        <h3 class="ra-title">技术写作<em>{{ writingCount }} 篇</em></h3>
        <div class="ra-writing">
          <div class="ra-writing-total">
            <b>{{ writingCount }}</b>
            <span>篇带 permalink 的文章<br />扫描自博客 docs</span>
          </div>
          <ul v-if="series.length" class="ra-series">
            <li v-for="item in series" :key="item.name">
              <span class="ra-series-name">{{ item.name }}</span>
              <span class="ra-series-bar" aria-hidden="true"><i :style="{ width: item.width }"></i></span>
              <span class="ra-series-count">{{ item.count }}</span>
            </li>
          </ul>
        </div>
      </section>

      <section class="ra-section">
        <h3 class="ra-title">工作与教育</h3>
        <div class="ra-duo">
          <article class="ra-panel">
            <h4>工作经历</h4>
            <p v-if="isMissing('工作经历') || !experience.length" class="ra-missing">
              <i aria-hidden="true"></i>知识库未收录
            </p>
            <ul v-else class="ra-entry-list">
              <li v-for="item in experience" :key="item.name">
                <strong>{{ item.name }}</strong>
                <span v-if="projectMeta(item)" class="ra-entry-meta">{{ projectMeta(item) }}</span>
                <span v-if="item.summary" class="ra-entry-text">{{ item.summary }}</span>
              </li>
            </ul>
          </article>

          <article class="ra-panel">
            <h4>教育经历</h4>
            <p v-if="isMissing('教育经历') || !education.length" class="ra-missing">
              <i aria-hidden="true"></i>知识库未收录
            </p>
            <ul v-else class="ra-entry-list">
              <li v-for="item in education" :key="item.name">
                <strong>{{ item.name }}</strong>
                <span v-if="projectMeta(item)" class="ra-entry-meta">{{ projectMeta(item) }}</span>
                <span v-if="item.summary" class="ra-entry-text">{{ item.summary }}</span>
              </li>
            </ul>
          </article>
        </div>
        <p v-if="missingLabels.length" class="ra-note">
          标为「知识库未收录」的栏目不会编造内容；在知识库补齐对应文件后，下次生成会自动出现。
        </p>
      </section>

      <section v-if="honors.length" class="ra-section">
        <h3 class="ra-title">荣誉</h3>
        <ul class="ra-honors">
          <li v-for="(item, i) in honors" :key="i">{{ item }}</li>
        </ul>
      </section>

      <footer class="ra-footer">
        <p>内容由知识库自动生成<span v-if="sourceHash"> · 版本 {{ sourceHash.slice(0, 10) }}</span></p>
        <p v-if="kbFiles.length">来源文件：{{ kbFiles.join(' / ') }}</p>
      </footer>
    </div>
  </section>
</template>

<script>
const API_LATEST = '/api/resume/latest'
const API_REFRESH = '/api/resume/refresh'
const TOKEN_KEY = 'resume-admin-token'

export default {
  name: 'ResumeAssistant',
  data() {
    return {
      state: 'loading', // loading | ready | empty | error
      doc: null,
      errorMessage: '',
      isAdmin: false,
      token: '',
      refreshing: false,
      refreshFeedback: null,
    }
  },
  computed: {
    profile() {
      return (this.doc && this.doc.profile) || {}
    },
    directions() {
      const list = this.profile.directions
      return Array.isArray(list) ? list.filter(Boolean) : []
    },
    links() {
      const list = this.profile.links
      if (!Array.isArray(list)) return []
      return list.filter(link => link && link.url)
    },
    skillGroups() {
      const list = this.doc && this.doc.skills
      if (!Array.isArray(list)) return []
      return list
        .filter(group => group && group.group && Array.isArray(group.items) && group.items.length)
        .map(group => {
          // levels 与 items 按下标对齐；旧快照没有 levels 时全部按 0 处理
          const levels = Array.isArray(group.levels) ? group.levels : []
          const items = group.items
            .map((name, i) => ({ name, level: this.normalizeLevel(levels[i]) }))
            .filter(item => Boolean(item.name))
          return {
            group: group.group,
            items,
            useBars: items.some(item => item.level > 0),
          }
        })
        .filter(group => group.items.length)
    },
    projects() {
      const list = this.doc && this.doc.projects
      return Array.isArray(list) ? list.filter(item => item && item.name) : []
    },
    experience() {
      const list = this.doc && this.doc.experience
      return Array.isArray(list) ? list.filter(item => item && item.name) : []
    },
    education() {
      const list = this.doc && this.doc.education
      return Array.isArray(list) ? list.filter(item => item && item.name) : []
    },
    honors() {
      const list = this.doc && this.doc.honors
      return Array.isArray(list) ? list.filter(Boolean) : []
    },
    writingCount() {
      const writing = (this.doc && this.doc.writing) || {}
      return Number(writing.article_count) || 0
    },
    series() {
      const writing = (this.doc && this.doc.writing) || {}
      const list = Array.isArray(writing.series) ? writing.series : []
      const max = list.reduce((m, item) => Math.max(m, Number(item && item.count) || 0), 0) || 1
      return list
        .filter(item => item && item.name)
        .slice(0, 12)
        .map(item => ({
          name: item.name,
          count: Number(item.count) || 0,
          width: Math.max(6, Math.round(((Number(item.count) || 0) / max) * 100)) + '%',
        }))
    },
    missingLabels() {
      const list = this.doc && this.doc.missing
      return Array.isArray(list) ? list.filter(Boolean) : []
    },
    kbFiles() {
      const source = (this.doc && this.doc.source) || {}
      return Array.isArray(source.kb_files) ? source.kb_files : []
    },
    sourceHash() {
      const source = (this.doc && this.doc.source) || {}
      return source.source_hash ? String(source.source_hash) : ''
    },
    generatedAt() {
      return this.formatTime(this.doc && this.doc.generated_at)
    },
  },
  mounted() {
    try {
      this.isAdmin = new URLSearchParams(window.location.search).get('admin') === '1'
      if (this.isAdmin) {
        this.token = window.sessionStorage.getItem(TOKEN_KEY) || ''
      }
    } catch (err) {
      this.isAdmin = false
    }
    this.load()
  },
  methods: {
    normalizeLevel(value) {
      const num = Number(value)
      if (!Number.isFinite(num) || num <= 0) return 0
      return Math.min(100, Math.round(num))
    },
    async load(options) {
      const silent = Boolean(options && options.silent)
      if (!silent) {
        this.state = 'loading'
        this.errorMessage = ''
      }
      try {
        const response = await fetch(API_LATEST, {
          headers: { Accept: 'application/json' },
          cache: 'no-store',
        })
        if (!response.ok) {
          const error = new Error('HTTP ' + response.status)
          error.status = response.status
          throw error
        }
        const data = await response.json()
        this.doc = data && typeof data === 'object' ? data : null
        this.state = this.hasContent() ? 'ready' : 'empty'
      } catch (error) {
        if (silent) {
          this.refreshFeedback = {
            type: 'warn',
            text: '刷新请求已提交，但重新读取简历失败，请稍后点「重新加载」。',
          }
          return
        }
        this.state = 'error'
        this.errorMessage = this.describeError(error)
      }
    },
    hasContent() {
      if (!this.doc) return false
      const profile = this.doc.profile || {}
      return Boolean(
        profile.name ||
        profile.summary ||
        (Array.isArray(this.doc.skills) && this.doc.skills.length) ||
        (Array.isArray(this.doc.projects) && this.doc.projects.length)
      )
    },
    describeError(error) {
      if (error && error.status) {
        if (error.status === 404) {
          return '简历接口返回 404：服务可能未挂载 /api/resume 路由，或开发代理未生效。'
        }
        if (error.status >= 500) {
          return '简历服务返回 ' + error.status + '：生成失败，服务端仍保留上一版数据，请稍后重试。'
        }
        return '简历接口返回 HTTP ' + error.status + '，请稍后重试。'
      }
      return '请求没有到达简历服务：后端可能未启动，或开发代理未生效。确认 8092 端口可用后重试。'
    },
    async refresh() {
      const token = this.token.trim()
      if (!token) {
        this.refreshFeedback = { type: 'warn', text: '请先填入刷新令牌再点「立即更新」。' }
        return
      }
      this.refreshing = true
      this.refreshFeedback = null
      try {
        const response = await fetch(API_REFRESH, {
          method: 'POST',
          headers: {
            Accept: 'application/json',
            'X-Resume-Token': token,
          },
        })
        if (response.status === 200) {
          let body = null
          try {
            body = await response.json()
          } catch (err) {
            body = null
          }
          const changed = Boolean(body && body.changed)
          this.refreshFeedback = {
            type: 'ok',
            text: changed ? '已重新生成，内容有更新。' : '已重新生成，内容与上一版一致（来源未变化）。',
          }
          await this.load({ silent: true })
        } else if (response.status === 401) {
          this.refreshFeedback = { type: 'error', text: '令牌无效（401）：请核对 RESUME_REFRESH_TOKEN 后重试。' }
        } else if (response.status === 429) {
          this.refreshFeedback = { type: 'warn', text: '刷新过于频繁（429）：30 秒内只能触发一次，请稍后再试。' }
        } else {
          this.refreshFeedback = { type: 'error', text: '刷新失败（HTTP ' + response.status + '），请查看服务日志后重试。' }
        }
      } catch (err) {
        this.refreshFeedback = { type: 'error', text: '无法连接简历服务（网络错误），请确认 8092 服务已启动。' }
      } finally {
        this.refreshing = false
      }
    },
    persistToken() {
      try {
        window.sessionStorage.setItem(TOKEN_KEY, this.token)
      } catch (err) {
        /* 隐私模式下 sessionStorage 不可用时静默忽略 */
      }
    },
    isMissing(label) {
      return this.missingLabels.some(item => String(item).indexOf(label) !== -1)
    },
    projectMeta(item) {
      return [item.role, item.period].filter(Boolean).join(' · ')
    },
    isSparseProject(item) {
      const hasSummary = Boolean(item && item.summary)
      const hasHighlights = Boolean(item && item.highlights && item.highlights.length)
      const hasTech = Boolean(item && item.tech && item.tech.length)
      return !hasSummary && !hasHighlights && !hasTech
    },
    formatTime(value) {
      if (!value) return ''
      const date = new Date(value)
      if (isNaN(date.getTime())) return String(value)
      const pad = n => (n < 10 ? '0' + n : String(n))
      return (
        date.getFullYear() + '-' + pad(date.getMonth() + 1) + '-' + pad(date.getDate()) +
        ' ' + pad(date.getHours()) + ':' + pad(date.getMinutes())
      )
    },
  },
}
</script>

<style scoped>
/* 简历维护助手：沿用站点 token（--site-*），栏目级排版，不引入新主题 */
.ra {
  margin: 1.5rem 0;
  color: var(--site-text, var(--textColor));
  --ra-card: var(--site-card, rgba(13, 24, 41, .8));
  --ra-border: var(--site-border, rgba(120, 160, 200, .16));
  --ra-muted: var(--site-muted, #8ea3b8);
  --ra-accent: var(--site-accent-text, #67e8f9);
  --ra-cyan: #22d3ee;
}

/* ---------- Hero ---------- */
.ra-hero { max-width: 660px; }
.ra-kicker {
  display: inline-flex; align-items: center; gap: .5rem;
  margin: 0; font-size: .68rem; font-weight: 600;
  letter-spacing: .18em; text-transform: uppercase;
  color: var(--ra-accent);
}
.ra-kicker i {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--ra-cyan); box-shadow: 0 0 10px var(--ra-cyan);
}
.ra-hero h2 {
  margin: .8rem 0 .8rem;
  font-size: clamp(1.6rem, 3.4vw, 2.05rem);
  line-height: 1.4; letter-spacing: -.01em;
  font-weight: 650; color: var(--site-text, #f8fafc);
}
.ra-lead {
  margin: 0; font-size: .92rem; line-height: 1.85;
  color: var(--ra-muted);
}
.ra-meta {
  display: flex; flex-wrap: wrap; gap: .45rem .5rem;
  margin-top: 1.1rem;
}
.ra-meta-item {
  display: inline-flex; align-items: baseline; gap: .35rem;
  padding: .28rem .6rem;
  border: 1px solid var(--ra-border); border-radius: 999px;
  font-size: .72rem; color: var(--site-text, #dbe7f3);
  background-color: rgba(255, 255, 255, .03);
  font-variant-numeric: tabular-nums;
}
.ra-meta-item em {
  font-style: normal; font-size: .66rem;
  letter-spacing: .06em; color: var(--ra-muted);
}

/* ---------- 维护面板 ---------- */
.ra-admin {
  margin-top: 1.3rem;
  padding: 1rem 1.1rem 1.05rem;
  border: 1px dashed rgba(245, 158, 11, .45);
  border-radius: 12px;
  background-color: rgba(245, 158, 11, .05);
}
.ra-admin-head {
  display: flex; flex-wrap: wrap; align-items: center; gap: .6rem;
}
.ra-admin h3 {
  margin: 0; font-size: .92rem; font-weight: 650;
  color: var(--site-text, #f8fafc);
}
.ra-admin-badge {
  padding: .12rem .45rem; border-radius: 6px;
  border: 1px solid rgba(245, 158, 11, .4);
  font-size: .64rem; letter-spacing: .04em;
  color: #fbbf24;
}
.ra-admin-hint {
  margin: .45rem 0 .8rem;
  font-size: .74rem; line-height: 1.7; color: var(--ra-muted);
}
.ra-admin-row {
  display: flex; flex-wrap: wrap; align-items: flex-end; gap: .6rem;
}
.ra-field {
  display: flex; flex-direction: column; gap: .3rem;
  flex: 1 1 220px; min-width: 0;
}
.ra-field > span { font-size: .72rem; color: var(--ra-muted); }
.ra-field input {
  width: 100%; box-sizing: border-box;
  padding: .45rem .6rem;
  border: 1px solid var(--ra-border); border-radius: 8px;
  background-color: rgba(255, 255, 255, .04);
  color: var(--site-text, #dbe7f3);
  font-size: .8rem; font-family: inherit;
}
.ra-field input:focus {
  outline: none;
  border-color: rgba(34, 211, 238, .55);
  box-shadow: 0 0 0 3px rgba(34, 211, 238, .12);
}
.ra-btn {
  padding: .46rem .95rem;
  border: 1px solid var(--ra-border); border-radius: 8px;
  background-color: rgba(255, 255, 255, .04);
  color: var(--site-text, #dbe7f3);
  font-size: .8rem; font-family: inherit; cursor: pointer;
  transition: border-color .2s ease, color .2s ease, background-color .2s ease;
}
.ra-btn:hover:not(:disabled) {
  border-color: rgba(34, 211, 238, .5);
  color: var(--ra-accent);
  background-color: rgba(34, 211, 238, .1);
}
.ra-btn:disabled { opacity: .55; cursor: not-allowed; }
.ra-btn-primary {
  border-color: rgba(34, 211, 238, .45);
  background-color: rgba(34, 211, 238, .12);
  color: var(--ra-accent);
  white-space: nowrap;
}
.ra-admin-feedback {
  margin: .7rem 0 0;
  font-size: .76rem; line-height: 1.6;
}
.ra-admin-feedback.is-ok { color: #4ade80; }
.ra-admin-feedback.is-warn { color: #fbbf24; }
.ra-admin-feedback.is-error { color: #f87171; }

/* ---------- 状态 ---------- */
.ra-state {
  display: flex; flex-direction: column; align-items: flex-start; gap: .45rem;
  padding: 1.4rem 1.2rem;
  border: 1px solid var(--ra-border); border-radius: 14px;
  background-color: var(--ra-card);
}
.ra-state-title { margin: 0; font-size: .92rem; font-weight: 650; color: var(--site-text, #f8fafc); }
.ra-state-text { margin: 0; font-size: .8rem; line-height: 1.7; color: var(--ra-muted); max-width: 52ch; }
.ra-state .ra-btn { margin-top: .35rem; }
.ra-state .ra-spinner { margin-bottom: .2rem; }
.ra-spinner {
  width: 16px; height: 16px; border-radius: 50%;
  border: 2px solid rgba(34, 211, 238, .22);
  border-top-color: var(--ra-cyan);
  animation: ra-spin .8s linear infinite;
}
@keyframes ra-spin { to { transform: rotate(360deg); } }

/* ---------- 个人信息 ---------- */
.ra-body { display: flex; flex-direction: column; gap: 1.9rem; margin-top: 1.3rem; }
.ra-profile {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1.5rem; align-items: start;
  padding: 1.35rem 1.4rem;
  border: 1px solid rgba(34, 211, 238, .22);
  border-radius: 16px;
  background-color: var(--ra-card);
  background-image: linear-gradient(135deg, rgba(34, 211, 238, .09), rgba(139, 92, 246, .05) 60%, transparent);
  box-shadow: 0 12px 32px var(--site-shadow, rgba(0, 0, 0, .3));
}
.ra-profile-main { min-width: 0; }
.ra-profile-role {
  margin: 0; font-size: .7rem; font-weight: 600;
  letter-spacing: .14em; text-transform: uppercase;
  color: var(--ra-accent);
}
.ra-profile-name {
  margin: .45rem 0 .6rem;
  font-size: 1.5rem; font-weight: 650; letter-spacing: -.01em;
  color: var(--site-text, #f8fafc);
}
.ra-profile-summary {
  margin: 0 0 .9rem; max-width: 56ch;
  font-size: .84rem; line-height: 1.8; color: var(--ra-muted);
}
.ra-links {
  display: flex; flex-direction: column; gap: .4rem;
  min-width: 148px;
}
.ra-link {
  display: flex; align-items: center; justify-content: space-between; gap: .8rem;
  padding: .38rem .7rem;
  border: 1px solid var(--ra-border); border-radius: 9px;
  font-size: .76rem; color: var(--site-text, #dbe7f3);
  text-decoration: none; background-color: rgba(255, 255, 255, .03);
  overflow-wrap: anywhere;
  transition: border-color .2s ease, color .2s ease, background-color .2s ease;
}
.ra-link em { font-style: normal; color: var(--ra-muted); }
.ra-link:hover {
  border-color: rgba(34, 211, 238, .5);
  color: var(--ra-accent);
  background-color: rgba(34, 211, 238, .1);
}
.ra-link:hover em { color: var(--ra-accent); }

/* ---------- 通用 chips / 章节 ---------- */
.ra-chips { display: flex; flex-wrap: wrap; gap: .4rem; }
.ra-chip {
  padding: .16rem .52rem;
  border: 1px solid var(--ra-border); border-radius: 999px;
  font-size: .72rem; color: var(--ra-muted);
  background-color: rgba(255, 255, 255, .03);
}
.ra-chips-accent .ra-chip {
  border-color: rgba(34, 211, 238, .32);
  background-color: rgba(34, 211, 238, .08);
  color: var(--ra-accent);
}
.ra-chips-sm .ra-chip { font-size: .68rem; }
.ra-section { min-width: 0; }
.ra-title {
  display: flex; align-items: baseline; gap: .55rem;
  margin: 0 0 .85rem; padding-bottom: .5rem;
  font-size: .95rem; font-weight: 650; letter-spacing: .01em;
  color: var(--site-text, #f8fafc);
  border-bottom: 1px solid var(--ra-border);
}
.ra-title em {
  font-style: normal; font-size: .7rem;
  letter-spacing: .04em; color: var(--ra-muted);
  font-variant-numeric: tabular-nums;
}

/* ---------- 技术能力 ---------- */
.ra-skills {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .75rem;
}
.ra-skill {
  min-width: 0;
  padding: .85rem .95rem;
  border: 1px solid var(--ra-border); border-radius: 12px;
  background-color: var(--ra-card);
}
.ra-skill h4 {
  margin: 0 0 .55rem;
  font-size: .8rem; font-weight: 600; letter-spacing: .02em;
  color: var(--site-text, #f8fafc);
}
/* 旧快照（无 levels）回退为 chips */
.ra-skill-chips { display: flex; flex-wrap: wrap; gap: .35rem; margin: 0; padding: 0; list-style: none; }
.ra-skill-chips li {
  padding: .1rem .42rem; border-radius: 6px;
  font-size: .72rem; color: var(--ra-muted);
  background-color: rgba(120, 160, 200, .1);
}
/* 有分值：名称 → 轨道 → 分值 */
.ra-skill-bars {
  display: flex; flex-direction: column; gap: .5rem;
  margin: 0; padding: 0; list-style: none;
}
.ra-skill-row { display: flex; align-items: center; gap: .55rem; min-width: 0; margin: 0; }
.ra-skill-name {
  flex: 0 1 auto; min-width: 0; max-width: 42%;
  font-size: .72rem; line-height: 1.5; color: var(--ra-muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.ra-skill-track {
  flex: 1 1 0; min-width: 24px; height: 6px; border-radius: 999px;
  background-color: rgba(120, 160, 200, .16);
  overflow: hidden;
}
.ra-skill-track i {
  display: block; height: 100%; border-radius: inherit;
  background-image: linear-gradient(90deg, rgba(34, 211, 238, .75), rgba(139, 92, 246, .75));
  transition: width 600ms cubic-bezier(.22, .61, .36, 1);
}
.ra-skill-value {
  flex: none; width: 2.2rem; text-align: right;
  font-size: .7rem; color: var(--ra-muted);
  font-variant-numeric: tabular-nums;
}

/* ---------- 项目 ---------- */
.ra-projects { display: flex; flex-direction: column; gap: .75rem; }
.ra-project {
  padding: .9rem 1rem .85rem;
  border: 1px solid var(--ra-border); border-left: 2px solid rgba(34, 211, 238, .45);
  border-radius: 12px;
  background-color: var(--ra-card);
}
.ra-project-head {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: .3rem .7rem;
}
.ra-project-head h4 {
  margin: 0; font-size: .95rem; font-weight: 650;
  color: var(--site-text, #f8fafc);
}
.ra-project-meta {
  font-size: .7rem; letter-spacing: .03em;
  color: var(--ra-muted); font-variant-numeric: tabular-nums;
}
.ra-project-summary {
  margin: .5rem 0 0; font-size: .82rem; line-height: 1.75;
  color: var(--ra-muted);
}
.ra-highlights {
  margin: .55rem 0 0; padding-left: 1.05rem;
  font-size: .78rem; line-height: 1.75; color: var(--ra-muted);
}
.ra-highlights li { margin-bottom: .15rem; }
.ra-highlights li::marker { color: rgba(34, 211, 238, .6); }
.ra-project-foot {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
  gap: .5rem .8rem; margin-top: .7rem;
}
.ra-project-empty {
  margin: .5rem 0 0; font-size: .76rem; line-height: 1.7;
  color: var(--ra-muted); font-style: italic;
}
.ra-project-link {
  font-size: .74rem; color: var(--ra-accent); text-decoration: none;
  overflow-wrap: anywhere;
}
.ra-project-link:hover { text-decoration: underline; }

/* ---------- 技术写作 ---------- */
.ra-writing {
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr);
  gap: 1.2rem; align-items: start;
  padding: 1rem 1.1rem;
  border: 1px solid var(--ra-border); border-radius: 12px;
  background-color: var(--ra-card);
}
.ra-writing-total { display: flex; flex-direction: column; gap: .2rem; }
.ra-writing-total b {
  font-size: 1.9rem; font-weight: 650; line-height: 1.1;
  color: var(--site-text, #f8fafc);
  font-variant-numeric: tabular-nums;
}
.ra-writing-total span { font-size: .7rem; line-height: 1.6; color: var(--ra-muted); }
.ra-series { display: flex; flex-direction: column; gap: .42rem; margin: 0; padding: 0; list-style: none; }
.ra-series li {
  display: grid;
  grid-template-columns: minmax(64px, 30%) minmax(0, 1fr) 2.2rem;
  align-items: center; gap: .6rem;
}
.ra-series-name {
  font-size: .74rem; color: var(--ra-muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.ra-series-bar {
  display: block; height: 5px; border-radius: 999px;
  background-color: rgba(120, 160, 200, .16);
  overflow: hidden;
}
.ra-series-bar i {
  display: block; height: 100%; border-radius: inherit;
  background-image: linear-gradient(90deg, rgba(34, 211, 238, .75), rgba(139, 92, 246, .75));
}
.ra-series-count {
  font-size: .7rem; text-align: right; color: var(--ra-muted);
  font-variant-numeric: tabular-nums;
}

/* ---------- 工作 / 教育 ---------- */
.ra-duo {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .75rem;
}
.ra-panel {
  padding: .9rem 1rem;
  border: 1px solid var(--ra-border); border-radius: 12px;
  background-color: var(--ra-card);
  min-width: 0;
}
.ra-panel h4 {
  margin: 0 0 .6rem; font-size: .78rem; font-weight: 600;
  letter-spacing: .03em; color: var(--site-text, #f8fafc);
}
.ra-missing {
  display: inline-flex; align-items: center; gap: .45rem;
  margin: 0; padding: .45rem .7rem;
  border: 1px dashed var(--ra-border); border-radius: 9px;
  font-size: .76rem; color: var(--ra-muted);
}
.ra-missing i {
  width: 6px; height: 6px; border-radius: 50%;
  background: #f59e0b; flex: none;
}
.ra-entry-list { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: .6rem; }
.ra-entry-list strong { display: block; font-size: .82rem; color: var(--site-text, #f8fafc); }
.ra-entry-meta { display: block; font-size: .7rem; color: var(--ra-muted); margin-top: .1rem; }
.ra-entry-text { display: block; font-size: .78rem; line-height: 1.7; color: var(--ra-muted); margin-top: .2rem; }
.ra-note {
  margin: .7rem 0 0; font-size: .72rem; line-height: 1.7; color: var(--ra-muted);
}
.ra-honors { margin: 0; padding-left: 1.05rem; font-size: .8rem; line-height: 1.8; color: var(--ra-muted); }
.ra-honors li::marker { color: rgba(34, 211, 238, .6); }

.ra-footer {
  margin-top: -.4rem; padding-top: .8rem;
  border-top: 1px solid var(--ra-border);
  font-size: .7rem; line-height: 1.7; color: var(--ra-muted);
}
.ra-footer p { margin: 0; }

/* ---------- 响应式 ---------- */
@media (max-width: 980px) {
  .ra-skills { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 720px) {
  .ra-hero h2 { font-size: 1.5rem; }
  .ra-profile { grid-template-columns: minmax(0, 1fr); gap: 1rem; padding: 1.15rem 1.1rem; }
  .ra-links { flex-direction: row; flex-wrap: wrap; min-width: 0; }
  .ra-link { flex: 1 1 130px; }
  .ra-skills { grid-template-columns: minmax(0, 1fr); }
  .ra-duo { grid-template-columns: minmax(0, 1fr); }
  .ra-writing { grid-template-columns: minmax(0, 1fr); gap: .9rem; }
  .ra-writing-total { flex-direction: row; align-items: baseline; gap: .5rem; }
  .ra-series li { grid-template-columns: minmax(56px, 38%) minmax(0, 1fr) 2rem; gap: .5rem; }
  .ra-admin-row { align-items: stretch; }
  .ra-admin-row .ra-btn { width: 100%; }
  .ra-project-foot { align-items: flex-start; }
}
@media (prefers-reduced-motion: reduce) {
  .ra-spinner { animation-duration: 2.4s; }
  .ra-skill-track i { transition: none; }
}
</style>
