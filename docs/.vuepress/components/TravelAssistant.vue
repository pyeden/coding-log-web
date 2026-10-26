<template>
  <section class="ta">
    <header class="ta-hero">
      <p class="ta-kicker"><i></i>TRAVEL LAB / FASTAPI</p>
      <h2>把一趟旅行，拆成可执行的每一天</h2>
      <p class="ta-lead">输入目的地、日期与偏好，自动生成逐日行程、预算明细和实用提示。规则引擎实时计算，无需登录。</p>
      <div class="ta-meta">
        <span>逐日安排</span>
        <span>预算估算</span>
        <span>偏好匹配</span>
      </div>
    </header>

    <form class="ta-form" @submit.prevent="submit">
      <div class="ta-fields">
        <label class="ta-field ta-field-wide">
          <span>目的地</span>
          <input v-model.trim="form.destination" type="text" placeholder="城市或地区，例如 北京" required />
        </label>
        <label class="ta-field">
          <span>人数</span>
          <input v-model.number="form.travelers" type="number" min="1" max="10" required />
        </label>
        <label class="ta-field">
          <span>出发日期</span>
          <input v-model="form.start_date" type="date" required />
        </label>
        <label class="ta-field">
          <span>返程日期</span>
          <input v-model="form.end_date" type="date" required />
        </label>
        <label class="ta-field">
          <span>总预算（元）</span>
          <input v-model.number="form.budget" type="number" min="100" step="100" required />
        </label>
      </div>

      <div class="ta-prefs">
        <span class="ta-label">偏好</span>
        <button
          v-for="item in preferenceOptions"
          :key="item"
          type="button"
          class="ta-chip"
          :class="{ active: form.preferences.includes(item) }"
          :aria-pressed="form.preferences.includes(item)"
          @click="togglePreference(item)"
        >{{ item }}</button>
      </div>

      <div class="ta-actions">
        <button class="ta-submit" type="submit" :disabled="loading">
          <span v-if="loading" class="ta-spinner" aria-hidden="true"></span>
          {{ loading ? '正在规划…' : '生成行程' }}
        </button>
        <span class="ta-hint">预计 1–3 秒返回，可反复调整后重新生成</span>
      </div>
    </form>

    <p v-if="error" class="ta-error" role="alert">{{ error }}</p>

    <div v-if="result" ref="resultEl" class="ta-result">
      <div class="ta-summary">
        <div class="ta-summary-head">
          <h3>{{ result.destination }}</h3>
          <span class="ta-level">{{ result.budget.level }}</span>
        </div>
        <p>{{ result.summary }}</p>
        <div class="ta-summary-meta">
          <span>{{ result.meta.days }} 天</span>
          <span>{{ result.meta.travelers }} 人</span>
          <span>{{ form.start_date }} → {{ form.end_date }}</span>
        </div>
      </div>

      <div class="ta-budget">
        <div class="ta-stat">
          <span>总预算</span>
          <strong>¥{{ money(result.budget.budget) }}</strong>
        </div>
        <div class="ta-stat">
          <span>预计花费</span>
          <strong>¥{{ money(result.budget.total) }}</strong>
        </div>
        <div class="ta-stat">
          <span>预算结余</span>
          <strong :class="{ negative: result.budget.remaining < 0 }">¥{{ money(result.budget.remaining) }}</strong>
        </div>
        <div class="ta-stat">
          <span>人均</span>
          <strong>¥{{ money(result.budget.per_person) }}</strong>
        </div>
      </div>

      <div class="ta-usage" :class="{ over: result.budget.remaining < 0 }">
        <div class="ta-usage-bar"><i :style="{ width: usagePercent + '%' }"></i></div>
        <span>预算使用 {{ usagePercent }}%</span>
      </div>

      <div class="ta-budget-detail">
        <span>住宿 ¥{{ money(result.budget.hotel) }}</span>
        <span>餐饮 ¥{{ money(result.budget.food) }}</span>
        <span>门票 ¥{{ money(result.budget.tickets) }}</span>
        <span>市内交通 ¥{{ money(result.budget.transport) }}</span>
      </div>

      <div class="ta-days">
        <article v-for="(day, index) in result.days" :key="day.date" class="ta-day">
          <span class="ta-day-dot" aria-hidden="true">{{ index + 1 }}</span>
          <header class="ta-day-header">
            <div class="ta-day-date">
              <strong>{{ day.date }}</strong>
              <span>{{ day.weekday }}</span>
            </div>
            <em>{{ day.theme }}</em>
          </header>
          <ul class="ta-items">
            <li v-for="item in day.items" :key="item.time + item.title" class="ta-item">
              <time>{{ item.time }}</time>
              <div class="ta-item-body">
                <strong>{{ item.title }}</strong>
                <small>{{ item.type }}<template v-if="item.duration && item.duration !== '—'"> · {{ item.duration }}</template></small>
                <p v-if="item.note">{{ item.note }}</p>
              </div>
              <span v-if="item.cost" class="ta-cost">¥{{ item.cost }}/人</span>
            </li>
          </ul>
        </article>
      </div>

      <div class="ta-tips">
        <h3>实用提示</h3>
        <ul>
          <li v-for="tip in result.tips" :key="tip">{{ tip }}</li>
        </ul>
      </div>

      <div class="ta-result-actions">
        <button class="ta-ghost" type="button" @click="copyPlan">{{ copied ? '已复制 ✓' : '复制行程' }}</button>
        <button class="ta-ghost" type="button" @click="result = null">重新规划</button>
      </div>
    </div>
  </section>
</template>

<script>
const pad = value => String(value).padStart(2, '0')
const formatDate = date => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`

export default {
  name: 'TravelAssistant',
  data () {
    const start = new Date()
    start.setDate(start.getDate() + 7)
    const end = new Date(start)
    end.setDate(start.getDate() + 2)
    return {
      form: {
        destination: '北京',
        start_date: formatDate(start),
        end_date: formatDate(end),
        budget: 3000,
        travelers: 2,
        preferences: ['历史', '美食'],
      },
      preferenceOptions: ['历史', '自然', '美食', '艺术', '亲子', '购物', '夜景'],
      loading: false,
      error: '',
      result: null,
      copied: false,
    }
  },
  computed: {
    usagePercent () {
      if (!this.result) return 0
      const { total, budget } = this.result.budget
      if (!budget) return 0
      return Math.min(100, Math.max(0, Math.round((total / budget) * 100)))
    },
  },
  methods: {
    togglePreference (item) {
      const index = this.form.preferences.indexOf(item)
      if (index >= 0) this.form.preferences.splice(index, 1)
      else this.form.preferences.push(item)
    },
    money (value) {
      return Number(value || 0).toLocaleString('zh-CN')
    },
    async submit () {
      this.error = ''
      if (this.form.end_date < this.form.start_date) {
        this.error = '返程日期不能早于出发日期。'
        return
      }
      this.loading = true
      try {
        const response = await fetch('/api/travel/plan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.form),
        })
        const data = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error(data.detail || '规划失败，请稍后重试。')
        this.result = data
        this.$nextTick(() => {
          const el = this.$refs.resultEl
          if (!el) return
          const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
          el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' })
        })
      } catch (err) {
        this.error = err.message || '网络异常，请确认后端服务已启动。'
      } finally {
        this.loading = false
      }
    },
    copyPlan () {
      if (!this.result) return
      const lines = [`${this.result.destination} · ${this.result.meta.days} 天 · ${this.result.meta.travelers} 人`, '']
      this.result.days.forEach(day => {
        lines.push(`${day.date} ${day.weekday} · ${day.theme}`)
        day.items.forEach(item => {
          lines.push(`  ${item.time} ${item.title}${item.duration && item.duration !== '—' ? `（${item.duration}）` : ''}`)
        })
        lines.push('')
      })
      lines.push(`预算 ¥${this.money(this.result.budget.budget)} / 预计 ¥${this.money(this.result.budget.total)}`)
      const text = lines.join('\n')
      const done = () => {
        this.copied = true
        setTimeout(() => { this.copied = false }, 2000)
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(() => this.fallbackCopy(text, done))
      } else {
        this.fallbackCopy(text, done)
      }
    },
    fallbackCopy (text, done) {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      try {
        document.execCommand('copy')
        done()
      } catch (e) {}
      document.body.removeChild(ta)
    },
  },
}
</script>

<style scoped>
/* 旅行助手：沿用站点 token 的深色科技风 */
.ta {
  margin: 1.5rem 0;
  color: var(--site-text, var(--textColor));
}
.ta-hero { margin-bottom: 1.6rem; }
.ta-kicker {
  display: inline-flex; align-items: center; gap: .5rem;
  margin: 0; font-size: .68rem; font-weight: 600;
  letter-spacing: .18em; text-transform: uppercase;
  color: var(--site-accent-text, #67e8f9);
}
.ta-kicker i {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--site-accent, #22d3ee);
  box-shadow: 0 0 10px var(--site-accent, #22d3ee);
}
.ta-hero h2 {
  margin: .8rem 0 .7rem;
  font-size: 2rem; line-height: 1.35; letter-spacing: -.02em;
  color: #f8fafc;
  background-image: linear-gradient(100deg, #f8fafc, #67e8f9 55%, #c4b5fd);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
}
.ta-lead {
  margin: 0; max-width: 640px;
  font-size: .95rem; line-height: 1.85; color: var(--site-muted, #8ea3b8);
}
.ta-meta { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1rem; }
.ta-meta span {
  padding: .18rem .6rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16));
  border-radius: 999px;
  font-size: .72rem; color: var(--site-muted, #8ea3b8);
  background-color: rgba(255, 255, 255, .02);
}

/* 表单 */
.ta-form {
  padding: 1.25rem 1.3rem 1.15rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16));
  border-radius: 16px;
  background-color: var(--site-card, rgba(13,24,41,.8));
  box-shadow: 0 12px 32px var(--site-shadow, rgba(0,0,0,.38));
}
.ta-fields {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .9rem 1rem;
}
.ta-field { display: flex; flex-direction: column; gap: .35rem; }
.ta-field-wide { grid-column: span 2; }
.ta-field span { font-size: .78rem; letter-spacing: .02em; color: var(--site-muted, #8ea3b8); }
.ta-field input {
  width: 100%; box-sizing: border-box;
  padding: .62rem .72rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16));
  border-radius: 10px;
  background-color: rgba(255, 255, 255, .02);
  color: var(--site-text, #dbe7f3);
  font: inherit; font-size: .9rem;
  transition: border-color .2s ease, box-shadow .2s ease, background-color .2s ease;
}
.ta-field input:hover { border-color: rgba(34, 211, 238, .28); }
.ta-field input:focus {
  outline: none;
  border-color: var(--site-accent, #22d3ee);
  box-shadow: 0 0 0 3px var(--site-glow, rgba(34,211,238,.14));
  background-color: rgba(255, 255, 255, .04);
}
.ta-prefs { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem; margin: 1.1rem 0 1rem; }
.ta-label { font-size: .78rem; color: var(--site-muted, #8ea3b8); margin-right: .2rem; }
.ta-chip {
  padding: .28rem .68rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16));
  border-radius: 999px;
  background-color: rgba(255, 255, 255, .02);
  color: var(--site-muted, #8ea3b8);
  font-size: .8rem; cursor: pointer;
  transition: color .2s ease, border-color .2s ease, background-color .2s ease, transform .2s ease;
}
.ta-chip:hover { color: var(--site-text, #dbe7f3); border-color: rgba(34, 211, 238, .35); transform: translateY(-1px); }
.ta-chip.active {
  color: var(--site-accent-text, #67e8f9);
  border-color: rgba(34, 211, 238, .55);
  background-color: var(--site-glow, rgba(34,211,238,.14));
  box-shadow: 0 0 18px var(--site-glow, rgba(34,211,238,.14));
}
.ta-actions { display: flex; align-items: center; gap: .9rem; flex-wrap: wrap; }
.ta-submit {
  display: inline-flex; align-items: center; gap: .5rem;
  padding: .68rem 1.25rem;
  border: 1px solid rgba(34, 211, 238, .35);
  border-radius: 10px;
  background-color: var(--site-accent, #22d3ee);
  color: #04121a; font-weight: 650; font-size: .9rem;
  cursor: pointer;
  box-shadow: 0 10px 30px var(--site-glow, rgba(34,211,238,.14));
  transition: transform .2s ease, box-shadow .2s ease, opacity .2s ease;
}
.ta-submit:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 16px 38px var(--site-glow, rgba(34,211,238,.22)); }
.ta-submit:active:not(:disabled) { transform: translateY(0) scale(.99); }
.ta-submit:disabled { opacity: .7; cursor: wait; }
.ta-spinner {
  width: 14px; height: 14px; border-radius: 50%;
  border: 2px solid rgba(4, 18, 26, .35);
  border-top-color: #04121a;
  animation: ta-spin .8s linear infinite;
}
@keyframes ta-spin { to { transform: rotate(360deg); } }
.ta-hint { font-size: .76rem; color: var(--site-muted, #8ea3b8); }
.ta-error {
  margin: 1rem 0 0; padding: .7rem .9rem;
  border: 1px solid rgba(244, 63, 94, .35);
  border-radius: 10px;
  background-color: rgba(244, 63, 94, .08);
  color: #fda4af; font-size: .86rem;
}

/* 结果 */
.ta-result { margin-top: 1.6rem; animation: ta-fade .35s ease both; }
@keyframes ta-fade { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
.ta-summary {
  padding: 1.1rem 1.25rem;
  border: 1px solid rgba(34, 211, 238, .22);
  border-radius: 16px;
  background-image: linear-gradient(135deg, rgba(34, 211, 238, .10), rgba(139, 92, 246, .06) 60%, transparent);
}
.ta-summary-head { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.ta-summary-head h3 { margin: 0; font-size: 1.25rem; color: #f8fafc; }
.ta-level {
  padding: .2rem .6rem; border-radius: 999px;
  font-size: .72rem; color: var(--site-accent-text, #67e8f9);
  border: 1px solid rgba(34, 211, 238, .35);
  background-color: rgba(34, 211, 238, .08);
}
.ta-summary p { margin: .6rem 0 .8rem; line-height: 1.8; font-size: .92rem; color: var(--site-text, #dbe7f3); }
.ta-summary-meta { display: flex; flex-wrap: wrap; gap: .45rem; }
.ta-summary-meta span {
  padding: .15rem .55rem; border-radius: 6px;
  font-size: .74rem; color: var(--site-muted, #8ea3b8);
  background-color: rgba(255, 255, 255, .04);
}
.ta-budget {
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .6rem; margin-top: 1rem;
}
.ta-stat {
  padding: .8rem .9rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16));
  border-radius: 12px;
  background-color: var(--site-card, rgba(13,24,41,.8));
  transition: transform .25s ease, border-color .25s ease, box-shadow .25s ease;
}
.ta-stat:hover { transform: translateY(-3px); border-color: rgba(34, 211, 238, .35); box-shadow: 0 14px 32px var(--site-shadow, rgba(0,0,0,.38)); }
.ta-stat span { display: block; font-size: .72rem; color: var(--site-muted, #8ea3b8); }
.ta-stat strong { display: block; margin-top: .3rem; font-size: 1.15rem; color: #f8fafc; font-variant-numeric: tabular-nums; }
.ta-stat .negative { color: #fb7185; }
.ta-usage { display: flex; align-items: center; gap: .75rem; margin-top: .7rem; font-size: .74rem; color: var(--site-muted, #8ea3b8); }
.ta-usage-bar {
  flex: 1; height: 6px; border-radius: 999px;
  background-color: rgba(255, 255, 255, .06);
  overflow: hidden;
}
.ta-usage-bar i {
  display: block; height: 100%;
  background-image: linear-gradient(90deg, #22d3ee, #8b5cf6);
  border-radius: inherit;
  transition: width .5s ease;
}
.ta-usage.over .ta-usage-bar i { background-image: linear-gradient(90deg, #fb7185, #f472b6); }
.ta-budget-detail { display: flex; flex-wrap: wrap; gap: .45rem .6rem; margin-top: .75rem; }
.ta-budget-detail span {
  padding: .16rem .55rem; border-radius: 6px;
  font-size: .74rem; color: var(--site-muted, #8ea3b8);
  border: 1px solid var(--site-border, rgba(120,160,200,.16));
}

/* 行程时间线 */
.ta-days { position: relative; margin-top: 1.5rem; padding-left: 1.6rem; }
.ta-days::before {
  content: ''; position: absolute; left: 7px; top: 6px; bottom: 6px; width: 1px;
  background-image: linear-gradient(180deg, rgba(34, 211, 238, .5), rgba(139, 92, 246, .25), transparent);
}
.ta-day { position: relative; padding: .95rem 1.05rem 1rem; margin-bottom: .9rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16));
  border-radius: 14px;
  background-color: var(--site-card, rgba(13,24,41,.8));
  transition: transform .25s ease, border-color .25s ease, box-shadow .25s ease;
}
.ta-day:hover { transform: translateY(-3px); border-color: rgba(34, 211, 238, .3); box-shadow: 0 16px 36px var(--site-shadow, rgba(0,0,0,.38)); }
.ta-day-dot {
  position: absolute; left: -1.6rem; top: 1.05rem;
  width: 16px; height: 16px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: .6rem; font-weight: 700; color: #04121a;
  background-color: var(--site-accent, #22d3ee);
  box-shadow: 0 0 0 3px rgba(34, 211, 238, .15);
}
.ta-day-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: .5rem; }
.ta-day-date { display: flex; align-items: baseline; gap: .5rem; }
.ta-day-date strong { font-size: .95rem; color: #f8fafc; font-variant-numeric: tabular-nums; }
.ta-day-date span { font-size: .76rem; color: var(--site-muted, #8ea3b8); }
.ta-day-header em { font-style: normal; font-size: .74rem; color: var(--site-accent-text, #67e8f9); }
.ta-items { list-style: none; margin: 0; padding: 0; }
.ta-item {
  display: grid; grid-template-columns: 52px minmax(0, 1fr) auto;
  gap: .7rem; padding: .55rem 0;
  border-top: 1px dashed var(--site-border, rgba(120,160,200,.16));
}
.ta-items .ta-item:first-child { border-top: 0; }
.ta-item time { font-size: .8rem; color: var(--site-muted, #8ea3b8); font-variant-numeric: tabular-nums; padding-top: .1rem; }
.ta-item-body strong { display: block; font-size: .92rem; color: #f8fafc; }
.ta-item-body small { display: block; margin-top: .15rem; font-size: .74rem; color: var(--site-muted, #8ea3b8); }
.ta-item-body p { margin: .25rem 0 0; font-size: .8rem; line-height: 1.55; color: var(--site-muted, #8ea3b8); }
.ta-cost {
  white-space: nowrap; font-size: .78rem;
  color: var(--site-accent-text, #67e8f9);
  padding-top: .1rem;
}

.ta-tips {
  margin-top: 1.1rem; padding: 1rem 1.15rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16));
  border-radius: 14px;
  background-color: rgba(255, 255, 255, .02);
}
.ta-tips h3 { margin: 0 0 .5rem; font-size: .95rem; color: #f8fafc; }
.ta-tips ul { margin: 0; padding-left: 1.1rem; }
.ta-tips li { margin: .3rem 0; line-height: 1.65; font-size: .84rem; color: var(--site-muted, #8ea3b8); }
.ta-result-actions { display: flex; gap: .6rem; margin-top: 1.1rem; }
.ta-ghost {
  padding: .5rem .95rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16));
  border-radius: 9px;
  background-color: transparent;
  color: var(--site-text, #dbe7f3);
  font-size: .84rem; cursor: pointer;
  transition: border-color .2s ease, color .2s ease, background-color .2s ease;
}
.ta-ghost:hover { border-color: rgba(34, 211, 238, .4); color: var(--site-accent-text, #67e8f9); background-color: rgba(34, 211, 238, .06); }

@media (max-width: 860px) {
  .ta-fields { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .ta-field-wide { grid-column: span 2; }
  .ta-budget { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 640px) {
  .ta-hero h2 { font-size: 1.6rem; }
  .ta-form { padding: 1rem; }
  .ta-fields { grid-template-columns: 1fr; }
  .ta-field-wide { grid-column: auto; }
  .ta-budget { grid-template-columns: 1fr 1fr; }
  .ta-days { padding-left: 1.35rem; }
  .ta-item { grid-template-columns: 44px minmax(0, 1fr); }
  .ta-cost { grid-column: 2; padding-top: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .ta-result, .ta-spinner { animation: none; }
  .ta-stat, .ta-day, .ta-chip, .ta-submit, .ta-usage-bar i { transition: none; }
}
</style>
