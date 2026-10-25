<template>
  <section class="ta">
    <header class="ta-header">
      <div>
        <h2>智能旅行助手</h2>
        <p>输入目的地、日期和偏好，生成一份可执行的行程与预算。</p>
      </div>
      <span class="ta-badge">FastAPI · 规则引擎</span>
    </header>

    <form class="ta-form" @submit.prevent="submit">
      <div class="ta-grid">
        <label class="ta-field">
          <span>目的地</span>
          <input v-model.trim="form.destination" type="text" placeholder="例如：北京" required />
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
          @click="togglePreference(item)"
        >{{ item }}</button>
      </div>

      <button class="ta-submit" type="submit" :disabled="loading">
        {{ loading ? '正在规划…' : '生成行程' }}
      </button>
    </form>

    <p v-if="error" class="ta-error">{{ error }}</p>

    <div v-if="result" class="ta-result">
      <div class="ta-summary">
        <p>{{ result.summary }}</p>
        <div class="ta-summary-meta">
          <span>{{ result.destination }}</span>
          <span>{{ result.meta.days }} 天</span>
          <span>{{ result.meta.travelers }} 人</span>
          <span>{{ result.budget.level }}</span>
        </div>
      </div>

      <div class="ta-budget">
        <div><span>总预算</span><strong>¥{{ money(result.budget.budget) }}</strong></div>
        <div><span>预计花费</span><strong>¥{{ money(result.budget.total) }}</strong></div>
        <div><span>预算结余</span><strong :class="{ negative: result.budget.remaining < 0 }">¥{{ money(result.budget.remaining) }}</strong></div>
        <div><span>人均</span><strong>¥{{ money(result.budget.per_person) }}</strong></div>
      </div>

      <div class="ta-budget-detail">
        <span>住宿 ¥{{ money(result.budget.hotel) }}</span>
        <span>餐饮 ¥{{ money(result.budget.food) }}</span>
        <span>门票 ¥{{ money(result.budget.tickets) }}</span>
        <span>市内交通 ¥{{ money(result.budget.transport) }}</span>
      </div>

      <div class="ta-days">
        <article v-for="day in result.days" :key="day.date" class="ta-day">
          <header class="ta-day-header">
            <strong>{{ day.date }}</strong>
            <span>{{ day.weekday }}</span>
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

      <button class="ta-reset" type="button" @click="result = null">重新规划</button>
    </div>
  </section>
</template>

<script>
const pad = (value) => String(value).padStart(2, '0')
const formatDate = (date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`

export default {
  name: 'TravelAssistant',
  data() {
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
    }
  },
  methods: {
    togglePreference(item) {
      const index = this.form.preferences.indexOf(item)
      if (index >= 0) this.form.preferences.splice(index, 1)
      else this.form.preferences.push(item)
    },
    money(value) {
      return Number(value || 0).toLocaleString('zh-CN')
    },
    async submit() {
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
      } catch (err) {
        this.error = err.message || '网络异常，请确认后端服务已启动。'
      } finally {
        this.loading = false
      }
    },
  },
}
</script>

<style scoped>
.ta {
  margin: 1.5rem 0;
  padding: 1.5rem;
  border: 1px solid var(--borderColor);
  border-radius: 12px;
  background: var(--mainBg);
  color: var(--textColor);
}
.ta-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.25rem;
}
.ta-header h2 { margin: 0 0 .35rem; font-size: 1.5rem; }
.ta-header p { margin: 0; opacity: .7; }
.ta-badge {
  flex: none;
  padding: .25rem .6rem;
  border-radius: 999px;
  background: rgba(17, 168, 205, .12);
  color: #11a8cd;
  font-size: .78rem;
}
.ta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .9rem 1rem;
}
.ta-field { display: flex; flex-direction: column; gap: .35rem; }
.ta-field span, .ta-label { font-size: .85rem; opacity: .7; }
.ta-field input {
  width: 100%;
  box-sizing: border-box;
  padding: .6rem .7rem;
  border: 1px solid var(--borderColor);
  border-radius: 8px;
  background: transparent;
  color: var(--textColor);
  font: inherit;
}
.ta-field input:focus { outline: 2px solid rgba(17, 168, 205, .35); border-color: #11a8cd; }
.ta-prefs { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem; margin: 1rem 0; }
.ta-chip {
  padding: .3rem .7rem;
  border: 1px solid var(--borderColor);
  border-radius: 999px;
  background: transparent;
  color: var(--textColor);
  cursor: pointer;
  font-size: .82rem;
}
.ta-chip.active { border-color: #11a8cd; background: rgba(17, 168, 205, .12); color: #11a8cd; }
.ta-submit {
  padding: .7rem 1.2rem;
  border: 0;
  border-radius: 8px;
  background: #11a8cd;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}
.ta-submit:disabled { opacity: .6; cursor: wait; }
.ta-error { margin-top: 1rem; color: #d9534f; }
.ta-result { margin-top: 1.5rem; }
.ta-summary {
  padding: 1rem 1.1rem;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(17, 168, 205, .12), rgba(17, 168, 205, .03));
}
.ta-summary p { margin: 0 0 .6rem; line-height: 1.7; }
.ta-summary-meta { display: flex; flex-wrap: wrap; gap: .5rem; }
.ta-summary-meta span { padding: .15rem .5rem; border-radius: 6px; background: rgba(17, 168, 205, .1); font-size: .78rem; }
.ta-budget { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .6rem; margin-top: 1rem; }
.ta-budget div { padding: .7rem; border: 1px solid var(--borderColor); border-radius: 8px; }
.ta-budget span { display: block; font-size: .75rem; opacity: .65; }
.ta-budget strong { display: block; margin-top: .25rem; font-size: 1.1rem; }
.ta-budget .negative { color: #d9534f; }
.ta-budget-detail { display: flex; flex-wrap: wrap; gap: .5rem 1rem; margin-top: .7rem; font-size: .82rem; opacity: .75; }
.ta-days { margin-top: 1.25rem; }
.ta-day { padding: .9rem 1rem; border-left: 3px solid #11a8cd; margin-bottom: 1rem; background: rgba(150, 150, 150, .04); }
.ta-day-header { display: flex; align-items: baseline; flex-wrap: wrap; gap: .5rem; margin-bottom: .6rem; }
.ta-day-header span { font-size: .8rem; opacity: .6; }
.ta-day-header em { margin-left: auto; font-style: normal; color: #11a8cd; font-size: .8rem; }
.ta-items { list-style: none; margin: 0; padding: 0; }
.ta-item { display: grid; grid-template-columns: 52px minmax(0, 1fr) auto; gap: .7rem; padding: .5rem 0; border-top: 1px dashed var(--borderColor); }
.ta-item time { font-variant-numeric: tabular-nums; opacity: .7; font-size: .82rem; }
.ta-item-body strong { display: block; font-size: .92rem; }
.ta-item-body small { display: block; margin-top: .15rem; opacity: .6; font-size: .76rem; }
.ta-item-body p { margin: .25rem 0 0; font-size: .8rem; opacity: .7; line-height: 1.5; }
.ta-cost { white-space: nowrap; font-size: .8rem; color: #11a8cd; }
.ta-tips { margin-top: 1.25rem; padding: 1rem 1.1rem; border-radius: 10px; background: rgba(150, 150, 150, .05); }
.ta-tips h3 { margin: 0 0 .5rem; font-size: 1rem; }
.ta-tips ul { margin: 0; padding-left: 1.2rem; }
.ta-tips li { margin: .3rem 0; line-height: 1.6; font-size: .86rem; }
.ta-reset { margin-top: 1rem; padding: .5rem 1rem; border: 1px solid var(--borderColor); border-radius: 8px; background: transparent; color: var(--textColor); cursor: pointer; }
@media (max-width: 720px) {
  .ta { padding: 1rem; }
  .ta-header { flex-direction: column; }
  .ta-grid, .ta-budget { grid-template-columns: 1fr; }
  .ta-item { grid-template-columns: 44px minmax(0, 1fr); }
  .ta-cost { grid-column: 2; }
}
</style>
