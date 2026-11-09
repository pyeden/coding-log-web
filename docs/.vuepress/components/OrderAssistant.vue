<template>
  <section class="oa">
    <header class="oa-hero">
      <p class="oa-kicker"><i></i>ORDER LAB / MARKET PRICING</p>
      <h2>提交需求，按市场价自动报价</h2>
      <p class="oa-lead">
        提交需求后，AI 先把需求拆成可验收的功能模块，再按每个模块的人日与市场价核算；
        范围每变一轮，就重新拆解、重新报价。
      </p>
      <ol class="oa-steps">
        <li><b>01</b><span>提交需求</span></li>
        <li><b>02</b><span>AI 拆模块</span></li>
        <li><b>03</b><span>按模块计价</span></li>
      </ol>
    </header>

    <div class="oa-grid">
      <section class="oa-card">
        <div class="oa-head">
          <h3>{{ editingId ? '修改需求' : '新增需求' }}</h3>
          <span>{{ editingId ? '保存后不自动重报价' : 'AI 拆 4–12 个模块后计价' }}</span>
        </div>
        <form @submit.prevent="save">
          <div class="oa-fields">
            <label class="oa-field oa-wide"><span>项目名称 *</span>
              <input v-model.trim="form.title" maxlength="120" placeholder="例如：企业官网改版">
            </label>
            <label class="oa-field"><span>客户 / 联系人</span>
              <input v-model.trim="form.client_name" maxlength="80" placeholder="选填">
            </label>
            <label class="oa-field"><span>联系方式</span>
              <input v-model.trim="form.contact" maxlength="120" placeholder="邮箱 / 微信 / 电话">
            </label>
            <label class="oa-field"><span>需求类别</span>
              <select v-model="form.category">
                <option value="">自动识别</option>
                <option v-for="c in meta.categories" :key="c.key" :value="c.key">{{ c.label }}</option>
              </select>
            </label>
            <label class="oa-field"><span>期望工期（天）</span>
              <input v-model.number="form.deadline_days" type="number" min="1" max="365">
            </label>
            <label class="oa-field oa-wide"><span>需求描述 *</span>
              <textarea v-model.trim="form.description" rows="4" maxlength="5000" placeholder="业务目标、功能范围、验收标准；写清支付/权限/对接等复杂点"></textarea>
            </label>
            <div class="oa-field oa-wide"><span>交付物</span>
              <div class="oa-tag-input">
                <span v-for="(d, i) in form.deliverables" :key="i" class="oa-tag">{{ d }}<button type="button" aria-label="移除" @click="removeDeliverable(i)">×</button></span>
                <input v-model.trim="draft" maxlength="40" placeholder="输入后回车添加" @keydown.enter.prevent="addDeliverable">
              </div>
            </div>
            <label class="oa-field"><span>预算参考（元）</span>
              <input v-model.number="form.budget_expectation" type="number" min="0" placeholder="选填，不参与倒推">
            </label>
            <label class="oa-field"><span>备注</span>
              <input v-model.trim="form.notes" maxlength="1000" placeholder="选填">
            </label>
          </div>
          <p v-if="feedback" class="oa-feedback" :class="'is-' + feedback.type" role="status">{{ feedback.text }}</p>
          <div class="oa-actions">
            <button class="oa-btn primary" type="submit" :disabled="submitting">
              {{ submitting ? (editingId ? '保存中…' : 'AI 拆解报价中…') : (editingId ? '保存修改' : '提交需求并生成报价') }}
            </button>
            <button v-if="editingId" class="oa-btn" type="button" @click="resetForm">取消修改</button>
          </div>
        </form>
      </section>

      <aside class="oa-card">
        <div class="oa-head">
          <h3>我的需求</h3>
          <span>{{ myList.length }} 条</span>
        </div>
        <p v-if="!myList.length" class="oa-empty">本机还没有记录。提交后会保存在当前浏览器；报价由 AI 拆解模块后生成，不公开他人信息。</p>
        <ul class="oa-list">
          <li v-for="it in myList" :key="it.public_id">
            <button type="button" :class="{ on: active && active.public_id === it.public_id }" @click="openDetail(it.public_id)">
              <b>{{ it.title }}</b>
              <span>{{ it.status_label }} · 第 {{ it.current_round }} 轮</span>
              <em v-if="it.latest_quote">{{ money(it.latest_quote.suggested_price) }}</em>
            </button>
          </li>
        </ul>
        <button v-if="myList.length" class="oa-clear" type="button" @click="clearMine">清空本机记录</button>
      </aside>
    </div>

    <section v-if="loadingDetail" class="oa-card oa-state">正在读取需求…</section>

    <section v-else-if="active" ref="detail" class="oa-card oa-detail">
      <div class="oa-detail-head">
        <div>
          <p class="oa-kicker sm">REQUIREMENT / {{ active.public_id.slice(-8) }}</p>
          <h3>{{ active.title }}</h3>
          <p class="oa-meta">
            {{ active.category_label }} · {{ active.client_name || '未留联系人' }} ·
            期望 {{ active.deadline_days }} 天 · 第 {{ active.current_round }} 轮
          </p>
        </div>
        <div class="oa-tools">
          <span class="oa-chip" :class="'st-' + active.status">{{ active.status_label }}</span>
          <button class="oa-btn sm" type="button" @click="editCurrent">编辑信息</button>
          <button v-if="active.status === 'quoted'" class="oa-btn sm primary" type="button" @click="setStatus('confirmed')">确认合作</button>
          <button v-if="active.status === 'confirmed'" class="oa-btn sm primary" type="button" @click="setStatus('in_progress')">开始执行</button>
          <button v-if="active.status === 'in_progress'" class="oa-btn sm primary" type="button" @click="setStatus('closed')">结单</button>
          <button v-if="canCancel" class="oa-btn sm" type="button" @click="setStatus('cancelled')">取消</button>
        </div>
      </div>

      <div v-if="q" class="oa-quote">
        <div class="oa-price">
          <span>建议报价</span>
          <b>{{ money(q.suggested_price) }}</b>
          <em>区间 {{ money(q.amount_min) }} – {{ money(q.amount_max) }}</em>
          <div class="oa-conf"><i :style="{ width: Math.round(q.confidence * 100) + '%' }"></i><span>置信度 {{ Math.round(q.confidence * 100) }}%</span></div>
        </div>
        <div class="oa-basis">
          <p>{{ q.market_basis }}</p>
          <p class="oa-sub">报价版本 {{ q.pricing_version }} · {{ q.decomposition_source === 'llm' ? 'AI 拆解' : '规则拆解' }} · {{ q.module_count }} 个模块 · {{ fmtDate(q.generated_at) }} · 第 {{ q.round_no }} 轮</p>
        </div>
        <div class="oa-table-wrap">
          <table>
            <thead><tr><th>模块 / 阶段</th><th>人日</th><th>人日价</th><th>金额</th></tr></thead>
            <tbody>
              <tr v-for="(b, i) in q.breakdown" :key="i">
                <td>{{ b.phase }}</td><td>{{ b.days }}</td><td>{{ money(b.unit_price) }}</td><td>{{ money(b.amount) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <ul class="oa-assume"><li v-for="(a, i) in q.assumptions" :key="i">{{ a }}</li></ul>
      </div>

      <div v-if="comparison" class="oa-compare">
        <b>与上一轮相比：{{ comparison.delta >= 0 ? '+' : '' }}{{ money(comparison.delta) }}（{{ comparison.delta_pct }}%）</b>
        <ul><li v-for="(r, i) in comparison.reasons" :key="i">{{ r }}</li></ul>
      </div>

      <div class="oa-rounds">
        <h4>轮次与报价记录</h4>
        <ol>
          <li v-for="r in active.rounds" :key="r.round_no">
            <div class="oa-round-head">
              <b>第 {{ r.round_no }} 轮</b><span>{{ fmtDate(r.submitted_at) }}</span>
              <em v-if="r.quote">{{ money(r.quote.suggested_price) }}</em>
            </div>
            <p v-if="r.change_note" class="oa-sub">变更：{{ r.change_note }}</p>
            <p class="oa-desc">{{ r.description }}</p>
            <div class="oa-tags"><span v-for="(d, i) in r.deliverables" :key="i">{{ d }}</span></div>
          </li>
        </ol>
      </div>

      <div class="oa-round-form">
        <h4>提交新一轮</h4>
        <p class="oa-sub">范围变化后提交，按最新范围重新报价，并与上一轮对比。</p>
        <form @submit.prevent="submitRound">
          <label class="oa-field"><span>本轮需求描述 *</span>
            <textarea v-model.trim="roundForm.description" rows="4" maxlength="5000"></textarea>
          </label>
          <div class="oa-field"><span>本轮交付物</span>
            <div class="oa-tag-input">
              <span v-for="(d, i) in roundForm.deliverables" :key="i" class="oa-tag">{{ d }}<button type="button" aria-label="移除" @click="removeRoundDeliverable(i)">×</button></span>
              <input v-model.trim="roundDraft" maxlength="40" placeholder="输入后回车" @keydown.enter.prevent="addRoundDeliverable">
            </div>
          </div>
          <div class="oa-fields">
            <label class="oa-field"><span>期望工期（天）</span>
              <input v-model.number="roundForm.deadline_days" type="number" min="1" max="365">
            </label>
            <label class="oa-field"><span>变更说明</span>
              <input v-model.trim="roundForm.change_note" maxlength="300" placeholder="例如：新增支付模块">
            </label>
          </div>
          <button class="oa-btn primary" type="submit" :disabled="roundSubmitting">
            {{ roundSubmitting ? 'AI 重新拆解中…' : '提交新一轮并重新报价' }}
          </button>
        </form>
      </div>
    </section>

    <div v-if="busy.active" class="oa-loading" role="status" aria-live="polite">
      <div class="oa-loading-card">
        <span class="oa-spinner" aria-hidden="true"></span>
        <p class="oa-loading-kicker">AI QUOTING / MARKET PRICING</p>
        <h3>{{ busy.kind === 'round' ? '正在重新拆解本轮需求' : '正在拆解需求并生成报价' }}</h3>
        <p class="oa-loading-stage">{{ busy.stage }}</p>
        <div class="oa-loading-bar" aria-hidden="true"><i></i></div>
        <p class="oa-loading-hint">已用 {{ busy.elapsed }} 秒 · 通常 10–30 秒，请不要关闭页面</p>
        <ul class="oa-loading-steps">
          <li :class="{ done: busy.elapsed >= 3, on: busy.elapsed < 3 }">理解需求与交付范围</li>
          <li :class="{ done: busy.elapsed >= 8, on: busy.elapsed >= 3 && busy.elapsed < 8 }">拆解功能模块与人日</li>
          <li :class="{ done: busy.elapsed >= 16, on: busy.elapsed >= 8 && busy.elapsed < 16 }">按模块人日 × 市场价核算</li>
          <li :class="{ on: busy.elapsed >= 16 }">校验明细并生成报价</li>
        </ul>
      </div>
    </div>
  </section>
</template>

<script>
const API = '/api/order'
const STORAGE_KEY = 'oa_requirement_ids_v1'

export default {
  name: 'OrderAssistant',
  data() {
    return {
      meta: { categories: [] },
      form: this.blankForm(),
      editingId: '',
      active: null,
      myList: [],
      ids: [],
      loadingDetail: false,
      submitting: false,
      roundSubmitting: false,
      feedback: null,
      comparison: null,
      draft: '',
      roundDraft: '',
      roundForm: this.blankRound(),
      busy: { active: false, kind: 'create', elapsed: 0, stage: '', started: 0 },
      busyTimer: null,
      timer: null
    }
  },
  computed: {
    q() {
      return this.active && this.active.latest_quote ? this.active.latest_quote : null
    },
    canCancel() {
      return this.active && ['quoted', 'confirmed', 'in_progress'].indexOf(this.active.status) >= 0
    }
  },
  mounted() {
    this.loadMeta()
    this.loadMine()
  },
  beforeDestroy() {
    if (this.timer) clearTimeout(this.timer)
    if (this.busyTimer) clearInterval(this.busyTimer)
  },
  methods: {
    blankForm() {
      return {
        title: '',
        client_name: '',
        contact: '',
        category: '',
        description: '',
        deliverables: [],
        deadline_days: 30,
        budget_expectation: '',
        notes: ''
      }
    },
    blankRound() {
      return { description: '', deliverables: [], deadline_days: 30, change_note: '' }
    },
    async api(path, options) {
      const opts = Object.assign({ headers: {} }, options || {})
      if (opts.body && typeof opts.body !== 'string') {
        opts.headers['Content-Type'] = 'application/json'
        opts.body = JSON.stringify(opts.body)
      }
      const res = await fetch(API + path, opts)
      const text = await res.text()
      let data = null
      try { data = text ? JSON.parse(text) : null } catch (e) { data = null }
      if (!res.ok) {
        const err = new Error('HTTP ' + res.status)
        err.payload = data
        throw err
      }
      return data
    },
    errText(err) {
      const p = err.payload || {}
      if (p.error === 'missing_ids') return '缺少需求 ID'
      if (p.fields) {
        const labels = {
          title: '项目名称', description: '需求描述', deadline_days: '工期',
          deliverables: '交付物', budget_expectation: '预算', category: '类别'
        }
        return Object.keys(p.fields).map(function (k) {
          return (labels[k] || k) + '：' + p.fields[k]
        }).join('；')
      }
      return p.error || err.message || '请求失败'
    },
    note(type, text) {
      this.feedback = { type: type, text: text }
      if (this.timer) clearTimeout(this.timer)
      this.timer = setTimeout(() => { this.feedback = null }, 6000)
    },
    async loadMeta() {
      try {
        const data = await this.api('/meta')
        this.meta = data
      } catch (e) { /* meta 失败不阻断表单 */ }
    },
    readIds() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY)
        const list = raw ? JSON.parse(raw) : []
        return Array.isArray(list) ? list.slice(0, 30) : []
      } catch (e) { return [] }
    },
    writeIds(ids) {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(ids.slice(0, 30))) } catch (e) { /* ignore */ }
    },
    saveId(id) {
      const ids = this.readIds()
      if (ids.indexOf(id) < 0) ids.unshift(id)
      this.ids = ids.slice(0, 30)
      this.writeIds(this.ids)
    },
    async loadMine() {
      const ids = this.readIds()
      this.ids = ids
      if (!ids.length) { this.myList = []; return }
      try {
        const data = await this.api('/requirements?ids=' + encodeURIComponent(ids.join(',')))
        this.myList = data.items || []
        const present = {}
        this.myList.forEach(function (it) { present[it.public_id] = true })
        this.ids = ids.filter(function (id) { return present[id] })
        this.writeIds(this.ids)
      } catch (e) { /* 网络失败保留旧列表 */ }
    },
    stageFor(seconds) {
      if (seconds < 3) return '正在理解需求与交付范围…'
      if (seconds < 8) return '正在拆解功能模块并估算人日…'
      if (seconds < 16) return '正在按模块人日 × 市场价核算…'
      return '模块较多，正在校验明细并生成报价…'
    },
    startBusy(kind) {
      this.busy.active = true
      this.busy.kind = kind
      this.busy.elapsed = 0
      this.busy.stage = this.stageFor(0)
      this.busy.started = Date.now()
      if (this.busyTimer) clearInterval(this.busyTimer)
      this.busyTimer = setInterval(() => {
        const seconds = Math.floor((Date.now() - this.busy.started) / 1000)
        this.busy.elapsed = seconds
        this.busy.stage = this.stageFor(seconds)
      }, 500)
    },
    stopBusy() {
      this.busy.active = false
      if (this.busyTimer) {
        clearInterval(this.busyTimer)
        this.busyTimer = null
      }
    },
    validateForm() {
      if (!this.form.title || this.form.title.length < 2) return '项目名称至少 2 个字'
      if (!this.form.description || this.form.description.length < 10) return '需求描述至少 10 个字'
      const d = Number(this.form.deadline_days)
      if (!d || d < 1 || d > 365) return '工期需在 1–365 天之间'
      return ''
    },
    async save() {
      const error = this.validateForm()
      if (error) { this.note('error', error); return }
      const body = {
        title: this.form.title,
        client_name: this.form.client_name,
        contact: this.form.contact,
        category: this.form.category || '',
        description: this.form.description,
        deliverables: this.form.deliverables.slice(),
        deadline_days: Number(this.form.deadline_days),
        budget_expectation: this.form.budget_expectation === '' ? null : Number(this.form.budget_expectation),
        notes: this.form.notes
      }
      this.submitting = true
      const willQuote = !this.editingId
      if (willQuote) this.startBusy('create')
      try {
        let data
        if (this.editingId) {
          data = await this.api('/requirements/' + this.editingId, { method: 'PATCH', body: body })
          this.note('ok', '需求信息已保存。范围有变化请提交新一轮重新报价。')
        } else {
          data = await this.api('/requirements', { method: 'POST', body: body })
          this.saveId(data.public_id)
          this.note('ok', '已生成首轮报价：' + this.money(data.latest_quote.suggested_price))
        }
        this.active = data
        this.comparison = null
        this.editingId = ''
        this.form = this.blankForm()
        this.draft = ''
        await this.loadMine()
        this.scrollDetail()
      } catch (e) {
        this.note('error', this.errText(e))
      } finally {
        this.submitting = false
        if (willQuote) this.stopBusy()
      }
    },
    async openDetail(publicId) {
      this.loadingDetail = true
      try {
        const data = await this.api('/requirements/' + publicId)
        this.active = data
        this.comparison = null
        this.editingId = ''
        this.roundForm = {
          description: data.description,
          deliverables: (data.deliverables || []).slice(),
          deadline_days: data.deadline_days,
          change_note: ''
        }
        this.roundDraft = ''
      } catch (e) {
        this.note('error', this.errText(e))
      } finally {
        this.loadingDetail = false
      }
    },
    editCurrent() {
      if (!this.active) return
      this.editingId = this.active.public_id
      this.form = {
        title: this.active.title,
        client_name: this.active.client_name || '',
        contact: this.active.contact || '',
        category: this.active.category === 'other' ? '' : this.active.category,
        description: this.active.description,
        deliverables: (this.active.deliverables || []).slice(),
        deadline_days: this.active.deadline_days,
        budget_expectation: this.active.budget_expectation === null ? '' : this.active.budget_expectation,
        notes: this.active.notes || ''
      }
      this.note('ok', '已载入需求信息，保存后生效。')
      try { window.scrollTo({ top: 0, behavior: 'smooth' }) } catch (e) { /* ignore */ }
    },
    resetForm() {
      this.form = this.blankForm()
      this.editingId = ''
      this.draft = ''
    },
    addDeliverable() {
      const v = this.draft
      if (!v) return
      if (this.form.deliverables.length >= 20) { this.note('error', '交付物最多 20 项'); return }
      if (this.form.deliverables.indexOf(v) < 0) this.form.deliverables.push(v)
      this.draft = ''
    },
    removeDeliverable(i) { this.form.deliverables.splice(i, 1) },
    addRoundDeliverable() {
      const v = this.roundDraft
      if (!v) return
      if (this.roundForm.deliverables.length >= 20) { this.note('error', '交付物最多 20 项'); return }
      if (this.roundForm.deliverables.indexOf(v) < 0) this.roundForm.deliverables.push(v)
      this.roundDraft = ''
    },
    removeRoundDeliverable(i) { this.roundForm.deliverables.splice(i, 1) },
    async submitRound() {
      if (!this.active) return
      if (!this.roundForm.description || this.roundForm.description.length < 10) {
        this.note('error', '本轮需求描述至少 10 个字'); return
      }
      const d = Number(this.roundForm.deadline_days)
      if (!d || d < 1 || d > 365) { this.note('error', '工期需在 1–365 天之间'); return }
      this.roundSubmitting = true
      this.startBusy('round')
      try {
        const data = await this.api('/requirements/' + this.active.public_id + '/rounds', {
          method: 'POST',
          body: {
            description: this.roundForm.description,
            deliverables: this.roundForm.deliverables.slice(),
            deadline_days: d,
            change_note: this.roundForm.change_note
          }
        })
        this.active = data.requirement
        this.comparison = data.comparison
        this.note('ok', '第 ' + data.round.round_no + ' 轮报价已生成：' + this.money(data.quote.suggested_price))
        await this.loadMine()
        this.scrollDetail()
      } catch (e) {
        this.note('error', this.errText(e))
      } finally {
        this.roundSubmitting = false
        this.stopBusy()
      }
    },
    async setStatus(target) {
      if (!this.active) return
      try {
        const data = await this.api('/requirements/' + this.active.public_id + '/status', {
          method: 'POST', body: { status: target }
        })
        this.active = data
        this.note('ok', '状态已更新为「' + data.status_label + '」')
        await this.loadMine()
      } catch (e) {
        this.note('error', this.errText(e))
      }
    },
    clearMine() {
      try { localStorage.removeItem(STORAGE_KEY) } catch (e) { /* ignore */ }
      this.ids = []
      this.myList = []
      this.active = null
      this.comparison = null
    },
    scrollDetail() {
      this.$nextTick(() => {
        if (this.$refs.detail && this.$refs.detail.scrollIntoView) {
          this.$refs.detail.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      })
    },
    money(n) {
      return '¥' + Number(n || 0).toLocaleString('zh-CN')
    },
    fmtDate(s) {
      if (!s) return ''
      const d = new Date(s)
      if (isNaN(d.getTime())) return s
      return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
    }
  }
}
</script>

<style scoped>
.oa { --oa-cyan: #22d3ee; --oa-line: var(--site-border, rgba(120,160,200,.16)); margin: 1.4rem 0 2rem; color: var(--site-text, inherit); }
.oa * { box-sizing: border-box; }
.oa-hero { max-width: 720px; }
.oa-kicker { display: inline-flex; align-items: center; gap: .5rem; margin: 0; font-size: .68rem; font-weight: 600; letter-spacing: .16em; color: var(--site-accent-text, #67e8f9); text-transform: uppercase; }
.oa-kicker i { width: 6px; height: 6px; border-radius: 50%; background: var(--oa-cyan); box-shadow: 0 0 10px var(--oa-cyan); }
.oa-kicker.sm { font-size: .6rem; }
.oa-hero h2 { margin: .8rem 0 .7rem; font-size: 2rem; line-height: 1.35; letter-spacing: -.02em; color: var(--site-text, #f8fafc); }
.oa-lead { margin: 0; max-width: 640px; font-size: .94rem; line-height: 1.85; color: var(--site-muted, #8ea3b8); }
.oa-steps { display: flex; flex-wrap: wrap; gap: .5rem 1.4rem; padding: 0; margin: 1.1rem 0 0; list-style: none; }
.oa-steps li { display: flex; align-items: baseline; gap: .45rem; font-size: .8rem; color: var(--site-muted, #8ea3b8); }
.oa-steps b { color: var(--site-accent-text, #67e8f9); font-variant-numeric: tabular-nums; }
.oa-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(0, .65fr); gap: 1rem; margin-top: 1.5rem; align-items: start; }
.oa-card { padding: 1.1rem 1.2rem; border: 1px solid var(--oa-line); border-radius: 16px; background: var(--site-card, rgba(13,24,41,.8)); box-shadow: 0 12px 32px var(--site-shadow, rgba(0,0,0,.25)); min-width: 0; }
.oa-head { display: flex; justify-content: space-between; align-items: baseline; gap: .8rem; margin-bottom: .9rem; }
.oa-head h3, .oa-detail h3 { margin: 0; font-size: 1.1rem; color: var(--site-text, #f8fafc); }
.oa-head span { font-size: .72rem; color: var(--site-muted, #8ea3b8); }
.oa-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem .9rem; }
.oa-field { display: flex; flex-direction: column; gap: .3rem; min-width: 0; }
.oa-field.oa-wide { grid-column: span 2; }
.oa-field > span { font-size: .76rem; color: var(--site-muted, #8ea3b8); }
.oa-field input, .oa-field select, .oa-field textarea { width: 100%; padding: .58rem .7rem; border: 1px solid var(--oa-line); border-radius: 9px; background: rgba(255,255,255,.03); color: var(--site-text, inherit); font: inherit; font-size: .88rem; }
.oa-field textarea { resize: vertical; min-height: 88px; }
.oa-field input:focus, .oa-field select:focus, .oa-field textarea:focus { outline: 2px solid rgba(34,211,238,.35); outline-offset: 1px; border-color: rgba(34,211,238,.5); }
.oa-tag-input { display: flex; flex-wrap: wrap; gap: .35rem; padding: .45rem; border: 1px solid var(--oa-line); border-radius: 9px; background: rgba(255,255,255,.03); }
.oa-tag-input input { flex: 1 1 120px; min-width: 0; border: 0; background: transparent; color: inherit; font: inherit; font-size: .84rem; padding: .1rem; }
.oa-tag-input input:focus { outline: none; }
.oa-tag { display: inline-flex; align-items: center; gap: .25rem; padding: .14rem .45rem; border: 1px solid var(--oa-line); border-radius: 999px; font-size: .72rem; color: var(--site-text, inherit); }
.oa-tag button { border: 0; background: transparent; color: var(--site-muted, #8ea3b8); cursor: pointer; font-size: .85rem; line-height: 1; padding: 0; }
.oa-actions { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: .9rem; }
.oa-btn { padding: .55rem .95rem; border: 1px solid var(--oa-line); border-radius: 9px; background: rgba(255,255,255,.04); color: var(--site-text, inherit); font: inherit; font-size: .85rem; cursor: pointer; }
.oa-btn:hover { border-color: rgba(34,211,238,.45); }
.oa-btn.primary { background: rgba(34,211,238,.14); border-color: rgba(34,211,238,.5); color: var(--site-accent-text, #67e8f9); font-weight: 600; }
.oa-btn.sm { padding: .35rem .65rem; font-size: .76rem; }
.oa-btn[disabled] { opacity: .6; cursor: wait; }
.oa-feedback { margin: .7rem 0 0; padding: .5rem .65rem; border-radius: 8px; font-size: .82rem; }
.oa-feedback.is-ok { background: rgba(34,197,94,.12); color: #86efac; border: 1px solid rgba(34,197,94,.3); }
.oa-feedback.is-error { background: rgba(244,63,94,.12); color: #fda4af; border: 1px solid rgba(244,63,94,.3); }
.oa-empty { margin: 0; font-size: .82rem; line-height: 1.7; color: var(--site-muted, #8ea3b8); }
.oa-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .4rem; }
.oa-list button { width: 100%; text-align: left; padding: .55rem .65rem; border: 1px solid var(--oa-line); border-radius: 9px; background: rgba(255,255,255,.02); color: inherit; font: inherit; cursor: pointer; display: grid; grid-template-columns: 1fr auto; gap: .15rem .5rem; }
.oa-list button.on, .oa-list button:hover { border-color: rgba(34,211,238,.45); background: rgba(34,211,238,.06); }
.oa-list b { font-size: .84rem; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.oa-list span { font-size: .7rem; color: var(--site-muted, #8ea3b8); }
.oa-list em { grid-row: span 2; align-self: center; font-style: normal; font-size: .8rem; font-weight: 600; color: var(--site-accent-text, #67e8f9); }
.oa-clear { margin-top: .7rem; border: 0; background: transparent; color: var(--site-muted, #8ea3b8); font-size: .74rem; cursor: pointer; padding: 0; }
.oa-state { margin-top: 1rem; font-size: .85rem; color: var(--site-muted, #8ea3b8); }
.oa-detail { margin-top: 1rem; }
.oa-detail-head { display: flex; flex-wrap: wrap; justify-content: space-between; gap: .8rem; }
.oa-meta { margin: .35rem 0 0; font-size: .78rem; color: var(--site-muted, #8ea3b8); }
.oa-tools { display: flex; flex-wrap: wrap; gap: .4rem; align-items: center; }
.oa-chip { padding: .18rem .55rem; border-radius: 999px; font-size: .72rem; border: 1px solid var(--oa-line); }
.oa-chip.st-quoted { color: #fcd34d; border-color: rgba(252,211,77,.4); }
.oa-chip.st-confirmed, .oa-chip.st-in_progress { color: #86efac; border-color: rgba(134,239,172,.4); }
.oa-chip.st-closed { color: #93c5fd; border-color: rgba(147,197,253,.4); }
.oa-chip.st-cancelled { color: #fda4af; border-color: rgba(253,164,175,.4); }
.oa-quote { display: grid; grid-template-columns: minmax(0, .8fr) minmax(0, 1.2fr); gap: .9rem 1.2rem; margin-top: 1rem; padding: .9rem 1rem; border: 1px solid rgba(34,211,238,.28); border-radius: 14px; background: linear-gradient(135deg, rgba(34,211,238,.08), rgba(139,92,246,.05)); }
.oa-price span { display: block; font-size: .72rem; color: var(--site-muted, #8ea3b8); }
.oa-price b { display: block; margin: .15rem 0; font-size: 2rem; line-height: 1.15; color: var(--site-accent-text, #67e8f9); font-variant-numeric: tabular-nums; }
.oa-price em { font-style: normal; font-size: .76rem; color: var(--site-muted, #8ea3b8); }
.oa-conf { display: flex; align-items: center; gap: .5rem; margin-top: .5rem; }
.oa-conf i { display: block; height: 5px; border-radius: 999px; background: linear-gradient(90deg, #22d3ee, #8b5cf6); max-width: 140px; }
.oa-conf span { font-size: .7rem; color: var(--site-muted, #8ea3b8); white-space: nowrap; }
.oa-basis p { margin: 0 0 .3rem; font-size: .8rem; line-height: 1.65; color: var(--site-text, inherit); }
.oa-sub { margin: .2rem 0 0; font-size: .73rem; color: var(--site-muted, #8ea3b8); }
.oa-table-wrap { grid-column: 1 / -1; overflow-x: auto; }
.oa-table-wrap table { width: 100%; min-width: 460px; border-collapse: collapse; font-size: .78rem; }
.oa-table-wrap th, .oa-table-wrap td { padding: .45rem .5rem; border-bottom: 1px solid var(--oa-line); text-align: left; }
.oa-table-wrap th { color: var(--site-muted, #8ea3b8); font-weight: 500; }
.oa-table-wrap td:nth-child(n+2), .oa-table-wrap th:nth-child(n+2) { text-align: right; }
.oa-assume { grid-column: 1 / -1; margin: 0; padding-left: 1.1rem; font-size: .73rem; line-height: 1.7; color: var(--site-muted, #8ea3b8); }
.oa-compare { margin-top: .9rem; padding: .7rem .85rem; border: 1px solid rgba(139,92,246,.3); border-radius: 10px; background: rgba(139,92,246,.07); font-size: .8rem; }
.oa-compare ul { margin: .35rem 0 0; padding-left: 1.1rem; color: var(--site-muted, #8ea3b8); font-size: .76rem; line-height: 1.7; }
.oa-rounds, .oa-round-form { margin-top: 1.2rem; }
.oa-rounds h4, .oa-round-form h4 { margin: 0 0 .6rem; font-size: .95rem; }
.oa-rounds ol { list-style: none; margin: 0; padding: 0 0 0 .8rem; border-left: 2px solid var(--oa-line); display: flex; flex-direction: column; gap: .7rem; }
.oa-rounds li { position: relative; padding-left: .2rem; }
.oa-round-head { display: flex; flex-wrap: wrap; align-items: baseline; gap: .6rem; font-size: .8rem; }
.oa-round-head b { color: var(--site-text, inherit); }
.oa-round-head span { color: var(--site-muted, #8ea3b8); font-size: .72rem; }
.oa-round-head em { margin-left: auto; font-style: normal; font-weight: 600; color: var(--site-accent-text, #67e8f9); }
.oa-desc { margin: .3rem 0; font-size: .8rem; line-height: 1.7; color: var(--site-text, inherit); }
.oa-tags { display: flex; flex-wrap: wrap; gap: .3rem; }
.oa-tags span { padding: .12rem .45rem; border: 1px solid var(--oa-line); border-radius: 999px; font-size: .68rem; color: var(--site-muted, #8ea3b8); }
.oa-round-form form { display: flex; flex-direction: column; gap: .7rem; }

/* 全屏 AI 报价 loading */
.oa-loading { position: fixed; inset: 0; z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 1rem; background: rgba(3, 8, 16, .72); backdrop-filter: blur(6px); }
.oa-loading-card { width: min(430px, 100%); padding: 1.5rem 1.4rem 1.35rem; border: 1px solid rgba(34, 211, 238, .38); border-radius: 18px; background: var(--site-card, #0d1829); box-shadow: 0 24px 70px rgba(0, 0, 0, .45); }
.oa-spinner { display: block; width: 34px; height: 34px; margin-bottom: 1rem; border-radius: 50%; border: 3px solid rgba(34, 211, 238, .2); border-top-color: #22d3ee; animation: oa-spin .8s linear infinite; }
.oa-loading-kicker { margin: 0 0 .45rem; font-size: .64rem; font-weight: 600; letter-spacing: .16em; color: var(--site-accent-text, #67e8f9); }
.oa-loading-card h3 { margin: 0 0 .35rem; font-size: 1.05rem; color: var(--site-text, #f8fafc); }
.oa-loading-stage { margin: 0; font-size: .84rem; color: var(--site-text, #dbe7f3); }
.oa-loading-bar { height: 4px; margin: .9rem 0 .55rem; border-radius: 999px; background: rgba(255, 255, 255, .08); overflow: hidden; }
.oa-loading-bar i { display: block; width: 40%; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #22d3ee, #8b5cf6); animation: oa-slide 1.25s ease-in-out infinite; }
.oa-loading-hint { margin: 0; font-size: .72rem; color: var(--site-muted, #8ea3b8); }
.oa-loading-steps { list-style: none; margin: .9rem 0 0; padding: 0; display: flex; flex-direction: column; gap: .34rem; font-size: .76rem; color: var(--site-muted, #8ea3b8); }
.oa-loading-steps li::before { content: "○"; display: inline-block; width: 1rem; margin-right: .35rem; color: rgba(142, 163, 184, .6); }
.oa-loading-steps li.done { color: var(--site-text, #dbe7f3); }
.oa-loading-steps li.done::before { content: "✓"; color: #86efac; }
.oa-loading-steps li.on { color: var(--site-accent-text, #67e8f9); }
.oa-loading-steps li.on::before { content: "●"; color: #22d3ee; }
@keyframes oa-spin { to { transform: rotate(360deg); } }
@keyframes oa-slide { 0% { transform: translateX(-100%); } 100% { transform: translateX(300%); } }
@media (prefers-reduced-motion: reduce) { .oa-spinner, .oa-loading-bar i { animation-duration: 2.4s; } }
@media (max-width: 900px) { .oa-grid { grid-template-columns: minmax(0, 1fr); } .oa-quote { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 640px) { .oa-hero h2 { font-size: 1.65rem; } .oa-fields { grid-template-columns: minmax(0, 1fr); } .oa-field.oa-wide { grid-column: auto; } .oa-card { padding: .9rem; } .oa-price b { font-size: 1.7rem; } }
</style>
