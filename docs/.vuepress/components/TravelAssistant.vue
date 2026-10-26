<template>
  <section class="ta">
    <header class="ta-hero">
      <p class="ta-kicker"><i></i>TRAVEL LAB / FASTAPI</p>
      <h2>把一趟旅行，拆成可执行的每一天</h2>
      <p class="ta-lead">输入目的地、日期与偏好，自动生成逐日行程、预算明细和实用提示。出发前规划、路上看今日、随时分享给同行人。</p>
      <div class="ta-meta">
        <span>逐日安排</span>
        <span>今日卡片</span>
        <span>附近推荐</span>
        <span>打包清单</span>
      </div>
    </header>

    <nav class="ta-modes" aria-label="旅行助手视图">
      <button
        v-for="tab in modeTabs"
        :key="tab.key"
        type="button"
        class="ta-mode"
        :class="{ active: mode === tab.key }"
        :disabled="tab.disabled"
        :aria-pressed="mode === tab.key"
        @click="selectMode(tab.key)"
      >
        {{ tab.label }}<em v-if="tab.badge">{{ tab.badge }}</em>
      </button>
      <span v-if="readOnly" class="ta-readonly">共享行程 · 只读</span>
    </nav>

    <div ref="mapWrap" class="ta-map-wrap" :class="{ 'is-fullscreen': mapFullscreen }">
      <button
        class="ta-map-fs"
        type="button"
        :aria-label="mapFullscreen ? '退出全屏' : '全屏查看'"
        :title="mapFullscreen ? '退出全屏（Esc）' : '全屏查看'"
        @click="toggleMapFullscreen"
      >{{ mapFullscreen ? '✕' : '⛶' }}</button>
      <div ref="mapEl" class="ta-map"></div>
      <div v-if="!result" class="ta-map-empty">生成行程后，这里会显示每天的路线与景点位置</div>
      <div v-else class="ta-map-legend">
        <button class="ta-legend-chip" :class="{ active: activeDay === null }" @click="focusDay(null)">全部</button>
        <button
          v-for="(day, i) in result.days"
          :key="day.date"
          class="ta-legend-chip"
          :class="{ active: activeDay === i }"
          @click="focusDay(i)"
        >
          <i :style="{ background: dayColors[i % dayColors.length] }"></i>{{ day.date }} · {{ day.theme }}
        </button>
        <em v-if="!hasCoords">该目的地暂无坐标数据</em>
      </div>
    </div>

    <form v-show="mode === 'plan' && !readOnly" class="ta-form" @submit.prevent="submit">
      <div class="ta-fields">
        <label class="ta-field ta-field-wide ta-field-origin">
          <span>出发地</span>
          <div class="ta-origin-row">
            <input v-model.trim="form.origin" type="text" placeholder="例如：北京站 / 当前位置" />
            <button class="ta-locate" type="button" :disabled="locating" @click="locateOrigin">
              {{ locating ? '定位中…' : '定位' }}
            </button>
          </div>
        </label>
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

      <div class="ta-profile">
        <div class="ta-profile-row">
          <span class="ta-label">同行人</span>
          <div class="ta-chips">
            <button
              v-for="opt in profileOptions.companions"
              :key="opt.value"
              type="button"
              class="ta-chip"
              :class="{ active: form.profile.companions === opt.value }"
              @click="setProfile('companions', opt.value)"
            >{{ opt.label }}</button>
          </div>
        </div>
        <div class="ta-profile-row">
          <span class="ta-label">节奏</span>
          <div class="ta-chips">
            <button
              v-for="opt in profileOptions.pace"
              :key="opt.value"
              type="button"
              class="ta-chip"
              :class="{ active: form.profile.pace === opt.value }"
              @click="setProfile('pace', opt.value)"
            >{{ opt.label }}</button>
          </div>
        </div>
        <div class="ta-profile-row">
          <span class="ta-label">交通偏好</span>
          <div class="ta-chips">
            <button
              v-for="opt in profileOptions.transport"
              :key="opt.value"
              type="button"
              class="ta-chip"
              :class="{ active: form.profile.transport === opt.value }"
              @click="setProfile('transport', opt.value)"
            >{{ opt.label }}</button>
          </div>
        </div>
        <div class="ta-profile-row">
          <span class="ta-label">住宿预算</span>
          <div class="ta-chips">
            <button
              v-for="opt in profileOptions.lodging_budget"
              :key="opt.value"
              type="button"
              class="ta-chip"
              :class="{ active: form.profile.lodging_budget === opt.value }"
              @click="setProfile('lodging_budget', opt.value)"
            >{{ opt.label }}</button>
          </div>
        </div>
        <div class="ta-profile-row">
          <span class="ta-label">忌口</span>
          <div class="ta-chips">
            <button
              v-for="opt in profileOptions.dietary"
              :key="opt.value"
              type="button"
              class="ta-chip"
              :class="{ active: form.profile.dietary.includes(opt.value) }"
              :aria-pressed="form.profile.dietary.includes(opt.value)"
              @click="toggleProfile('dietary', opt.value)"
            >{{ opt.label }}</button>
          </div>
        </div>
        <div class="ta-profile-row">
          <span class="ta-label">无障碍</span>
          <div class="ta-chips">
            <button
              v-for="opt in profileOptions.accessibility"
              :key="opt.value"
              type="button"
              class="ta-chip"
              :class="{ active: form.profile.accessibility.includes(opt.value) }"
              :aria-pressed="form.profile.accessibility.includes(opt.value)"
              @click="toggleProfile('accessibility', opt.value)"
            >{{ opt.label }}</button>
          </div>
        </div>
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

    <p v-if="mode === 'plan' && readOnly" class="ta-error">共享行程为只读模式，如需重新规划请打开新页面。</p>

    <div v-if="loading" class="ta-skeleton" aria-hidden="true">
      <div class="ta-skeleton-row" v-for="n in 3" :key="n"></div>
    </div>

    <p v-if="error" class="ta-error" role="alert">{{ error }}</p>

    <div v-if="result && mode === 'itinerary'" ref="resultEl" class="ta-result">
      <div class="ta-summary">
        <div class="ta-summary-head">
          <h3>{{ result.destination || form.destination }}</h3>
          <span v-if="result.budget && result.budget.level" class="ta-level">{{ result.budget.level }}</span>
          <span v-else-if="readOnly" class="ta-level">共享行程</span>
        </div>
        <p v-if="result.summary">{{ result.summary }}</p>
        <div class="ta-summary-meta">
          <span>{{ daysCount }} 天</span>
          <span>{{ form.travelers }} 人</span>
          <span>{{ form.start_date }} → {{ form.end_date }}</span>
          <span v-if="profileSummary">{{ profileSummary }}</span>
        </div>
      </div>

      <div v-if="result.budget" class="ta-budget">
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
          <strong>¥{{ money(perPerson) }}</strong>
        </div>
      </div>

      <div v-if="result.budget" class="ta-usage" :class="{ over: result.budget.remaining < 0 }">
        <div class="ta-usage-bar"><i :style="{ width: usagePercent + '%' }"></i></div>
        <span>预算使用 {{ usagePercent }}%</span>
      </div>

      <div v-if="result.budget" class="ta-budget-detail">
        <span>住宿 ¥{{ money(result.budget.hotel) }}</span>
        <span>餐饮 ¥{{ money(result.budget.food) }}</span>
        <span>门票 ¥{{ money(result.budget.tickets) }}</span>
        <span>市内交通 ¥{{ money(result.budget.transport) }}</span>
        <span v-if="result.budget.buffer != null">机动 ¥{{ money(result.budget.buffer) }}</span>
      </div>

      <div class="ta-toolbar">
        <button class="ta-ghost" type="button" :disabled="sharing" @click="shareLink">{{ sharing ? '生成链接…' : '分享链接' }}</button>
        <button class="ta-ghost" type="button" @click="copyText">{{ copied ? '已复制 ✓' : '复制行程' }}</button>
        <button class="ta-ghost" type="button" @click="downloadIcs">下载 .ics</button>
        <button class="ta-ghost" type="button" @click="downloadJson">下载 .json</button>
        <button v-if="!readOnly" class="ta-ghost" type="button" @click="resetPlan">重新规划</button>
        <span v-if="toast" class="ta-toast" role="status">{{ toast }}</span>
      </div>

      <div class="ta-days">
        <article v-for="(day, index) in result.days" :key="day.date" class="ta-day">
          <span class="ta-day-dot" aria-hidden="true">{{ index + 1 }}</span>
          <header class="ta-day-header">
            <div class="ta-day-date">
              <strong>{{ day.date }}</strong>
              <span>{{ day.weekday }}</span>
              <b v-if="day.route_km" class="ta-day-stat">驾车 {{ day.route_km }} km · {{ day.route_min }} 分钟</b>
              <b v-else-if="day.distance_km" class="ta-day-stat">{{ day.distance_km }} km</b>
            </div>
            <em v-if="day.theme">{{ day.theme }}</em>
          </header>

          <div v-if="day.weather" class="ta-day-weather">
            <span class="ta-w-main">{{ day.weather.text || '天气未知' }}</span>
            <span v-if="day.weather.temp_min != null">{{ day.weather.temp_min }}°~{{ day.weather.temp_max }}°</span>
            <span v-if="day.weather.rain_prob != null">降水 {{ day.weather.rain_prob }}%</span>
            <span v-if="day.weather.uv">紫外线 {{ day.weather.uv }}</span>
            <em v-if="day.weather.source">{{ weatherSourceLabel(day.weather.source) }}</em>
          </div>

          <div class="ta-day-facts">
            <p v-if="day.clothing"><b>穿衣</b>{{ day.clothing }}</p>
            <p v-if="day.lodging_area"><b>住宿</b>{{ day.lodging_area }}</p>
            <p v-if="day.transport_note"><b>交通</b>{{ day.transport_note }}<template v-if="day.buffer_min != null"> · 缓冲 {{ day.buffer_min }} 分钟</template></p>
          </div>

          <div v-if="day.warnings && day.warnings.length" class="ta-day-warn">
            <span v-for="text in day.warnings" :key="text">{{ text }}</span>
          </div>

          <ul class="ta-items">
            <li v-for="item in day.items" :key="itemKey(item)" class="ta-item" :class="'is-' + (item.type || 'attraction')">
              <time>{{ item.time || '—' }}</time>
              <div class="ta-item-body">
                <strong>{{ nameOf(item) }}</strong>
                <small class="ta-item-meta">
                  <i class="ta-type">{{ typeLabel(item.type) }}</i>
                  <template v-if="item.duration"> · {{ item.duration }}</template>
                </small>
                <p v-if="item.reason" class="ta-reason">{{ item.reason }}</p>
                <p v-if="item.note">{{ item.note }}</p>
                <p v-if="item.indoor_alternative" class="ta-indoor">室内备选：{{ item.indoor_alternative }}</p>
                <div class="ta-item-links">
                  <a v-if="item.navigation_url || hasLatLng(item)" :href="amapNavUrl(item)" target="_blank" rel="noopener noreferrer">高德导航</a>
                  <a v-if="item.external_url" :href="item.external_url" target="_blank" rel="noopener noreferrer">详情</a>
                  <span v-if="item.address" class="ta-addr">{{ item.address }}</span>
                </div>
                <div class="ta-fb">
                  <button type="button" class="ta-fb-btn" :class="{ on: fb(item).helpful === true }" @click="sendFeedback(item, { helpful: true })">有用</button>
                  <button type="button" class="ta-fb-btn" :class="{ on: fb(item).helpful === false }" @click="sendFeedback(item, { helpful: false })">没用</button>
                  <span class="ta-fb-sep" aria-hidden="true"></span>
                  <button type="button" class="ta-fb-btn" :class="{ on: fb(item).visited === true }" @click="sendFeedback(item, { visited: true })">去了</button>
                  <button type="button" class="ta-fb-btn" :class="{ on: fb(item).visited === false }" @click="sendFeedback(item, { visited: false })">没去</button>
                  <span v-if="fb(item).saving" class="ta-fb-hint">保存中…</span>
                  <span v-else-if="fb(item).error" class="ta-fb-hint err">{{ fb(item).error }}</span>
                </div>
              </div>
              <span v-if="item.cost" class="ta-cost">¥{{ item.cost }}</span>
            </li>
          </ul>
        </article>
      </div>

      <section v-if="packingGroups.length" class="ta-packing">
        <header class="ta-section-head">
          <h3>打包清单</h3>
          <span class="ta-section-meta">已备 {{ packedCount }} / {{ packTotal }}</span>
        </header>
        <div class="ta-pack-grid">
          <div v-for="group in packingGroups" :key="group.name" class="ta-pack-group">
            <h4>{{ group.name }}</h4>
            <label
              v-for="entry in group.items"
              :key="entry.name"
              class="ta-pack-item"
              :class="{ done: isPacked(group.name, entry.name) }"
            >
              <input type="checkbox" :checked="isPacked(group.name, entry.name)" @change="togglePacked(group.name, entry.name)" />
              <span class="ta-pack-name">{{ entry.name }}<b v-if="entry.required" class="ta-required">必带</b></span>
              <small v-if="entry.reason">{{ entry.reason }}</small>
            </label>
          </div>
        </div>
        <ul v-if="packingNotes.length" class="ta-pack-notes">
          <li v-for="note in packingNotes" :key="note">{{ note }}</li>
        </ul>
      </section>

      <div v-if="result.tips && result.tips.length" class="ta-tips">
        <h3>实用提示</h3>
        <ul>
          <li v-for="tip in result.tips" :key="tip">{{ tip }}</li>
        </ul>
      </div>
    </div>

    <div v-if="result && mode === 'today'" class="ta-today">
      <header class="ta-today-head">
        <div>
          <p class="ta-today-kicker">TODAY · 第 {{ todayIndex + 1 }} 天</p>
          <h3>{{ todayDay.date }} {{ todayDay.weekday }} · {{ todayDay.theme }}</h3>
          <p v-if="!todayInRange" class="ta-today-note">当前不在行程日期内，展示第 1 天安排</p>
        </div>
        <button class="ta-ghost" type="button" @click="selectMode('itinerary')">查看完整行程</button>
      </header>

      <div class="ta-today-grid">
        <article class="ta-today-card">
          <header class="ta-card-head">
            <h4>天气与穿衣</h4>
            <button type="button" class="ta-mini" :disabled="weatherLoading" @click="refreshWeather">{{ weatherLoading ? '刷新中…' : '刷新' }}</button>
          </header>
          <div class="ta-temp">
            <strong>{{ todayWeatherData.text || '天气未知' }}</strong>
            <span v-if="todayWeatherData.temp_min != null">{{ todayWeatherData.temp_min }}° ~ {{ todayWeatherData.temp_max }}°</span>
          </div>
          <div class="ta-weather-meta">
            <span v-if="todayWeatherData.rain_prob != null">降水 {{ todayWeatherData.rain_prob }}%</span>
            <span v-if="todayWeatherData.uv">紫外线 {{ todayWeatherData.uv }}</span>
            <em v-if="todayWeatherData.source">{{ weatherSourceLabel(todayWeatherData.source) }}</em>
          </div>
          <p class="ta-clothing">{{ todayDay.clothing || '以当日天气为准，备一件薄外套。' }}</p>
        </article>

        <article class="ta-today-card">
          <header class="ta-card-head"><h4>下一站</h4></header>
          <template v-if="nextStop">
            <p class="ta-next-time">{{ nextStop.item.time }}<span>· 第 {{ nextStop.index + 1 }} / {{ nextStop.total }} 站</span></p>
            <strong class="ta-next-name">{{ nameOf(nextStop.item) }}</strong>
            <p v-if="nextStop.item.reason" class="ta-next-reason">{{ nextStop.item.reason }}</p>
            <p v-if="nextStop.item.note" class="ta-next-note">{{ nextStop.item.note }}</p>
            <div class="ta-next-actions">
              <a v-if="amapNavUrl(nextStop.item)" :href="amapNavUrl(nextStop.item)" target="_blank" rel="noopener noreferrer">开始导航</a>
              <a v-if="nextStop.item.external_url" :href="nextStop.item.external_url" target="_blank" rel="noopener noreferrer">详情</a>
            </div>
          </template>
          <p v-else class="ta-muted">今天没有安排，慢一点也很好。</p>
        </article>

        <article class="ta-today-card">
          <header class="ta-card-head"><h4>路线与住宿</h4></header>
          <p v-if="todayDay.transport_note" class="ta-route-note">{{ todayDay.transport_note }}</p>
          <p v-if="todayDay.buffer_min != null" class="ta-muted">景点间预留 {{ todayDay.buffer_min }} 分钟缓冲</p>
          <p class="ta-lodging"><b>住宿区域</b>{{ todayDay.lodging_area || '未指定' }}</p>
          <button type="button" class="ta-mini" @click="switchPoi('lodging')">查看周边酒店</button>
        </article>

        <article class="ta-today-card ta-emergency-card">
          <header class="ta-card-head"><h4>紧急入口</h4></header>
          <ul class="ta-emergency-list">
            <li v-for="num in emergencyNumbers" :key="num.number + num.name">
              <span>{{ num.name }}</span>
              <a :href="'tel:' + num.number">{{ num.number }}</a>
            </li>
          </ul>
          <a v-if="hospital && hospital.navigation_url" class="ta-hospital" :href="hospital.navigation_url" target="_blank" rel="noopener noreferrer">医院导航：{{ hospital.name || '附近医院' }}</a>
          <p v-else-if="hospital && hospital.name" class="ta-muted">{{ hospital.name }}<template v-if="hospital.address"> · {{ hospital.address }}</template></p>
          <button type="button" class="ta-mini" @click="switchPoi('emergency')">周边医院/药店</button>
        </article>
      </div>

      <section class="ta-poi">
        <header class="ta-poi-head">
          <div>
            <h3>附近推荐</h3>
            <span v-if="poi.source === 'fallback'" class="ta-fallback">静态推荐 · 非实时数据</span>
            <span v-else-if="poi.source === 'amap'" class="ta-live">高德实时</span>
          </div>
          <button type="button" class="ta-mini" :disabled="poi.loading" @click="loadPoi(poi.category, true)">刷新</button>
        </header>
        <div class="ta-poi-tabs">
          <button
            v-for="tab in poiTabs"
            :key="tab.key"
            type="button"
            class="ta-poi-tab"
            :class="{ active: poi.category === tab.key }"
            @click="switchPoi(tab.key)"
          >{{ tab.label }}</button>
        </div>
        <p v-if="poi.loading" class="ta-poi-state">正在查找附近{{ catLabel(poi.category) }}…</p>
        <div v-else-if="poi.error" class="ta-poi-state err">
          {{ poi.error }}
          <button type="button" class="ta-mini" @click="loadPoi(poi.category, true)">重试</button>
        </div>
        <p v-else-if="!poi.items.length" class="ta-poi-state">附近暂无{{ catLabel(poi.category) }}推荐，可稍后刷新。</p>
        <div v-else class="ta-poi-grid">
          <article v-for="p in poi.items" :key="p.id || p.name" class="ta-poi-card">
            <header class="ta-poi-card-head">
              <strong>{{ p.name }}</strong>
              <span v-if="p.distance_m != null" class="ta-poi-distance">{{ formatDistance(p.distance_m) }}</span>
            </header>
            <div class="ta-poi-tags">
              <span v-if="p.type">{{ p.type }}</span>
              <span v-if="p.rating">★ {{ p.rating }}</span>
              <span v-if="p.cost">¥{{ p.cost }}/人</span>
              <span v-if="p.open_status">{{ p.open_status }}</span>
            </div>
            <p v-if="p.address" class="ta-poi-addr">{{ p.address }}</p>
            <p v-if="p.reason" class="ta-poi-reason">{{ p.reason }}</p>
            <div class="ta-poi-actions">
              <a v-if="p.navigation_url" :href="p.navigation_url" target="_blank" rel="noopener noreferrer">导航</a>
              <a v-if="p.external_url" :href="p.external_url" target="_blank" rel="noopener noreferrer">点评/预订</a>
            </div>
          </article>
        </div>
        <p class="ta-poi-note">距离、评分与价格为参考，以商家实际为准。</p>
      </section>

      <section v-if="packingGroups.length" class="ta-today-pack">
        <button type="button" class="ta-ghost" @click="selectMode('itinerary')">查看打包清单（{{ packedCount }}/{{ packTotal }}）</button>
      </section>
    </div>
  </section>
</template>

<script>
import 'leaflet/dist/leaflet.css'

// Leaflet 在模块加载时访问 window，SSR 构建会报 "window is not defined"。
// 改为客户端首次使用地图时动态加载。
let L = null

const pad = value => String(value).padStart(2, '0')
const formatDate = date => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`


const PI = Math.PI
const A = 6378245.0
const EE = 0.00669342162296594323
function outOfChina (lng, lat) {
  return !(lng > 73.66 && lng < 135.05 && lat > 3.86 && lat < 53.55)
}
function transformLat (lng, lat) {
  let ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * Math.sqrt(Math.abs(lng))
  ret += (20.0 * Math.sin(6.0 * lng * PI) + 20.0 * Math.sin(2.0 * lng * PI)) * 2.0 / 3.0
  ret += (20.0 * Math.sin(lat * PI) + 40.0 * Math.sin(lat / 3.0 * PI)) * 2.0 / 3.0
  ret += (160.0 * Math.sin(lat / 12.0 * PI) + 320 * Math.sin(lat * PI / 30.0)) * 2.0 / 3.0
  return ret
}
function transformLng (lng, lat) {
  let ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * Math.sqrt(Math.abs(lng))
  ret += (20.0 * Math.sin(6.0 * lng * PI) + 20.0 * Math.sin(2.0 * lng * PI)) * 2.0 / 3.0
  ret += (20.0 * Math.sin(lng * PI) + 40.0 * Math.sin(lng / 3.0 * PI)) * 2.0 / 3.0
  ret += (150.0 * Math.sin(lng / 12.0 * PI) + 300.0 * Math.sin(lng / 30.0 * PI)) * 2.0 / 3.0
  return ret
}
function gcj02ToWgs84 (lng, lat) {
  if (outOfChina(lng, lat)) return [lng, lat]
  const [gLng, gLat] = wgs84ToGcj02(lng, lat)
  return [lng * 2 - gLng, lat * 2 - gLat]
}

function wgs84ToGcj02 (lng, lat) {
  if (outOfChina(lng, lat)) return [lng, lat]
  let dLat = transformLat(lng - 105.0, lat - 35.0)
  let dLng = transformLng(lng - 105.0, lat - 35.0)
  const radLat = lat / 180.0 * PI
  let magic = Math.sin(radLat)
  magic = 1 - EE * magic * magic
  const sqrtMagic = Math.sqrt(magic)
  dLat = (dLat * 180.0) / ((A * (1 - EE)) / (magic * sqrtMagic) * PI)
  dLng = (dLng * 180.0) / (A / sqrtMagic * Math.cos(radLat) * PI)
  return [lng + dLng, lat + dLat]
}

export default {
  name: 'TravelAssistant',
  data () {
    const start = new Date()
    start.setDate(start.getDate() + 7)
    const end = new Date(start)
    end.setDate(start.getDate() + 2)
    return {
      mode: 'plan',
      form: {
        destination: '北京',
        origin: '',
        origin_lng: null,
        origin_lat: null,
        start_date: formatDate(start),
        end_date: formatDate(end),
        budget: 3000,
        travelers: 2,
        preferences: ['历史', '美食'],
        profile: {
          companions: 'couple',
          pace: 'balanced',
          dietary: [],
          accessibility: [],
          transport: 'public',
          lodging_budget: 'comfort',
        },
      },
      preferenceOptions: ['历史', '自然', '美食', '艺术', '亲子', '购物', '夜景'],
      profileOptions: {
        companions: [
          { value: 'solo', label: '独自' },
          { value: 'couple', label: '情侣' },
          { value: 'friends', label: '朋友' },
          { value: 'family_kids', label: '亲子' },
          { value: 'family_elderly', label: '带长辈' },
        ],
        pace: [
          { value: 'relaxed', label: '轻松' },
          { value: 'balanced', label: '均衡' },
          { value: 'packed', label: '紧凑' },
        ],
        transport: [
          { value: 'public', label: '公共交通' },
          { value: 'taxi', label: '打车' },
          { value: 'drive', label: '自驾' },
          { value: 'walk', label: '步行' },
        ],
        lodging_budget: [
          { value: 'budget', label: '经济' },
          { value: 'comfort', label: '舒适' },
          { value: 'premium', label: '高端' },
        ],
        dietary: [
          { value: 'vegetarian', label: '素食' },
          { value: 'halal', label: '清真' },
          { value: 'no_spicy', label: '不吃辣' },
          { value: 'no_seafood', label: '不吃海鲜' },
          { value: 'nut_allergy', label: '坚果过敏' },
        ],
        accessibility: [
          { value: 'step_free', label: '无台阶' },
          { value: 'elevator', label: '电梯优先' },
          { value: 'avoid_long_walk', label: '少走路' },
        ],
      },
      loading: false,
      locating: false,
      error: '',
      result: null,
      copied: false,
      map: null,
      mapFullscreen: false,
      provider: 'leaflet',
      mapLayerGroup: null,
      dayBounds: [],
      activeDay: null,
      shared: false,
      sharing: false,
      shareId: '',
      readOnly: false,
      todayWeather: null,
      weatherLoading: false,
      feedback: {},
      packing: {},
      poi: { category: 'food', items: [], source: '', loading: false, error: '', cache: {}, reqId: 0 },
      toast: '',
      toastTimer: null,
      dayColors: ['#22d3ee', '#8b5cf6', '#f472b6', '#a3e635', '#fbbf24', '#fb7185'],
    }
  },
  computed: {
    modeTabs () {
      return [
        { key: 'plan', label: '规划', disabled: this.readOnly },
        { key: 'itinerary', label: '行程', disabled: !this.result, badge: this.daysCount ? this.daysCount + '天' : '' },
        { key: 'today', label: '今日', disabled: !this.result },
      ]
    },
    daysCount () {
      return (this.result && this.result.days && this.result.days.length) || 0
    },
    perPerson () {
      if (!this.result || !this.result.budget) return 0
      const budget = this.result.budget
      if (budget.per_person != null) return budget.per_person
      const travelers = Number(this.form.travelers) || 1
      return Math.round((Number(budget.total) || 0) / travelers)
    },
    usagePercent () {
      if (!this.result || !this.result.budget) return 0
      const { total, budget } = this.result.budget
      if (!budget) return 0
      return Math.min(100, Math.max(0, Math.round((total / budget) * 100)))
    },
    hasCoords () {
      if (!this.result || !this.result.days) return false
      return this.result.days.some(day => (day.items || []).some(item => this.hasLatLng(item)))
    },
    todayStr () {
      return formatDate(new Date())
    },
    todayIndex () {
      if (!this.result || !this.result.days || !this.result.days.length) return 0
      const index = this.result.days.findIndex(day => day.date === this.todayStr)
      return index >= 0 ? index : 0
    },
    todayInRange () {
      if (!this.result || !this.result.days) return false
      return this.result.days.some(day => day.date === this.todayStr)
    },
    todayDay () {
      if (!this.result || !this.result.days || !this.result.days.length) return {}
      return this.result.days[this.todayIndex] || this.result.days[0] || {}
    },
    todayWeatherData () {
      if (this.todayWeather) return this.todayWeather
      return (this.todayDay && this.todayDay.weather) || {}
    },
    nextStop () {
      const day = this.todayDay
      const items = (day && day.items) || []
      if (!items.length) return null
      const sorted = items.slice().sort((a, b) => this.timeToMinutes(a.time) - this.timeToMinutes(b.time))
      let index = 0
      if (this.todayInRange) {
        const now = new Date()
        const nowMin = now.getHours() * 60 + now.getMinutes()
        const found = sorted.findIndex(item => this.timeToMinutes(item.time) >= nowMin)
        index = found >= 0 ? found : 0
      }
      return { item: sorted[index], index, total: sorted.length }
    },
    packingGroups () {
      const packing = this.result && this.result.packing
      return (packing && packing.categories) || []
    },
    packingNotes () {
      const packing = this.result && this.result.packing
      return (packing && packing.notes) || []
    },
    packTotal () {
      return this.packingGroups.reduce((sum, group) => sum + ((group.items && group.items.length) || 0), 0)
    },
    packedCount () {
      let count = 0
      this.packingGroups.forEach(group => {
        (group.items || []).forEach(entry => {
          if (this.isPacked(group.name, entry.name)) count++
        })
      })
      return count
    },
    profileSummary () {
      if (!this.result || !this.result.profile) return ''
      const profile = this.result.profile
      const companions = this.profileLabel('companions', profile.companions)
      const pace = this.profileLabel('pace', profile.pace)
      return [companions, pace].filter(Boolean).join(' · ')
    },
    emergencyNumbers () {
      const numbers = this.result && this.result.emergency && this.result.emergency.numbers
      if (numbers && numbers.length) return numbers
      return [
        { name: '报警', number: '110' },
        { name: '急救', number: '120' },
        { name: '火警', number: '119' },
      ]
    },
    hospital () {
      return (this.result && this.result.emergency && this.result.emergency.hospital) || null
    },
    poiTabs () {
      return [
        { key: 'food', label: '吃饭' },
        { key: 'lodging', label: '住宿' },
        { key: 'transport', label: '交通' },
        { key: 'emergency', label: '紧急' },
      ]
    },
  },
  mounted () {
    this.prefillFromQuery()
    this.initMap()
    this.loadShareFromQuery()
    document.addEventListener('keydown', this.onMapKeydown)
  },
  beforeDestroy () {
    document.removeEventListener('keydown', this.onMapKeydown)
    if (this.toastTimer) clearTimeout(this.toastTimer)
    document.body.style.overflow = ''
    if (this.map) {
      this.map.remove()
      this.map = null
    }
    if (this.amap) {
      this.amap.destroy()
      this.amap = null
    }
  },
  watch: {
    result () {
      this.activeDay = null
      this.$nextTick(() => this.renderMap())
    },
    mode (value) {
      if (value === 'today') {
        this.$nextTick(() => {
          this.renderMap()
          this.ensurePoi()
        })
      } else if (value === 'itinerary') {
        this.$nextTick(() => this.renderMap())
      }
    },
  },
  methods: {
    async initMap () {
      if (!this.$refs.mapEl || this.map) return
      if (window.__AMAP_JS_KEY__) {
        try {
          await this.loadAMap()
          this.initAmap()
          return
        } catch (e) {
          console.warn('[travel] 高德地图初始化失败，回退 Leaflet', e)
        }
      }
      if (!L) {
        const mod = await import('leaflet')
        L = mod.default || mod
      }
      this.initLeaflet()
    },
    loadAMap () {
      if (window.AMap) return Promise.resolve()
      return new Promise((resolve, reject) => {
        const script = document.createElement('script')
        script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(window.__AMAP_JS_KEY__)}&plugin=AMap.Scale,AMap.ToolBar`
        script.onload = resolve
        script.onerror = reject
        document.head.appendChild(script)
      })
    },
    toggleMapFullscreen () {
      this.mapFullscreen = !this.mapFullscreen
      document.body.style.overflow = this.mapFullscreen ? 'hidden' : ''
      setTimeout(() => {
        if (this.amap && typeof this.amap.resize === 'function') this.amap.resize()
        if (this.map && typeof this.map.invalidateSize === 'function') this.map.invalidateSize()
      }, 260)
    },
    onMapKeydown (event) {
      if (event.key === 'Escape' && this.mapFullscreen) {
        event.preventDefault()
        this.toggleMapFullscreen()
      }
    },
    firstStop () {
      const day = this.result && this.result.days && this.result.days[0]
      const item = day && day.items.find(i => typeof i.lat === 'number' && typeof i.lng === 'number')
      if (!item) return null
      const [lng, lat] = wgs84ToGcj02(item.lng, item.lat)
      return [lng, lat]
    },
    initAmap () {
      if (this.amap) return
      this.provider = 'amap'
      const dark = !document.body.classList.contains('theme-mode-light') && !document.body.classList.contains('theme-mode-read')
      const center = this.firstStop()
      this.amap = new window.AMap.Map(this.$refs.mapEl, {
        zoom: center ? 11 : 4,
        center: center || [108.9, 34.5],
        viewMode: '2D',
        mapStyle: dark ? 'amap://styles/darkblue' : 'amap://styles/normal',
      })
      this.amapOverlays = []
      this.amap.on('click', event => this.handleMapClick(event))
      this.renderMap()
    },
    async handleMapClick (event) {
      if (!event || !event.lnglat) return
      const lng = Number(event.lnglat.getLng().toFixed(6))
      const lat = Number(event.lnglat.getLat().toFixed(6))
      await this.ensureGeocoder()
      const address = await this.reverseGeocode(lng, lat)
      const label = address || `${lat.toFixed(5)}, ${lng.toFixed(5)}`
      const box = document.createElement('div')
      box.className = 'ta-map-pick'
      box.innerHTML = `
        <strong>${label}</strong>
        <div class="ta-map-pick-meta">${lat.toFixed(5)}, ${lng.toFixed(5)}</div>
        <div class="ta-map-pick-actions">
          <button type="button" data-act="origin">设为出发点</button>
          <button type="button" data-act="dest">设为目的地</button>
        </div>`
      const info = new window.AMap.InfoWindow({
        content: box,
        offset: new window.AMap.Pixel(0, -12),
      })
      info.open(this.amap, [lng, lat])
      box.querySelector('[data-act="origin"]').addEventListener('click', () => {
        const [wLng, wLat] = gcj02ToWgs84(lng, lat)
        this.form.origin = address || `${lat.toFixed(5)}, ${lng.toFixed(5)}`
        this.form.origin_lng = Number(wLng.toFixed(6))
        this.form.origin_lat = Number(wLat.toFixed(6))
        this.error = ''
        info.close()
      })
      box.querySelector('[data-act="dest"]').addEventListener('click', () => {
        this.form.destination = address || `${lat.toFixed(5)}, ${lng.toFixed(5)}`
        this.error = ''
        info.close()
      })
    },
    initLeaflet () {
      this.provider = 'leaflet'
      this.map = L.map(this.$refs.mapEl, {
        center: [34.5, 108.9],
        zoom: 4,
        zoomControl: true,
        scrollWheelZoom: false,
        attributionControl: true,
      })
      const dark = !document.body.classList.contains('theme-mode-light') && !document.body.classList.contains('theme-mode-read')
      const tile = dark
        ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
        : 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'
      L.tileLayer(tile, {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap &copy; CARTO',
      }).addTo(this.map)
      this.mapLayerGroup = L.layerGroup().addTo(this.map)
      this.renderMap()
    },
    renderMap () {
      if (this.provider === 'amap') {
        this.renderAMap()
        return
      }
      if (!this.map || !this.mapLayerGroup) return
      this.mapLayerGroup.clearLayers()
      if (!this.result) return
      const bounds = []
      this.dayBounds = []
      this.result.days.forEach((day, dayIndex) => {
        const color = this.dayColors[dayIndex % this.dayColors.length]
        const points = day.items
          .filter(item => typeof item.lat === 'number' && typeof item.lng === 'number')
          .map(item => ({ item, latlng: [item.lat, item.lng] }))
        if (!points.length) return
        if (points.length > 1) {
          L.polyline(points.map(p => p.latlng), {
            color,
            weight: 3,
            opacity: 0.75,
            dashArray: '6 8',
            lineCap: 'round',
          }).addTo(this.mapLayerGroup)
        }
        points.forEach(({ item, latlng }, index) => {
          const icon = L.divIcon({
            className: 'ta-map-pin',
            html: `<span style="--pin:${color}">${index + 1}</span>`,
            iconSize: [26, 26],
            iconAnchor: [13, 13],
          })
          const popup = `<strong>${item.time} ${this.nameOf(item)}</strong><br><small>${item.type}${item.duration && item.duration !== '—' ? ' · ' + item.duration : ''}</small>${item.cost ? `<br><small>¥${item.cost}/人</small>` : ''}`
          L.marker(latlng, { icon }).bindPopup(popup).addTo(this.mapLayerGroup)
          bounds.push(latlng)
        })
        this.dayBounds[dayIndex] = points.map(p => p.latlng)
      })
      if (!bounds.length) return
      if (bounds.length === 1) {
        this.map.setView(bounds[0], 13)
      } else {
        this.map.fitBounds(bounds, { padding: [36, 36], maxZoom: 13 })
      }
      setTimeout(() => this.map && this.map.invalidateSize(), 200)
    },
    prefillFromQuery () {
      const params = new URLSearchParams(window.location.search)
      if (!params.has('destination')) return
      const read = (key, fallback) => (params.has(key) ? params.get(key) : fallback)
      this.form.destination = read('destination', this.form.destination)
      this.form.start_date = read('start', this.form.start_date)
      this.form.end_date = read('end', this.form.end_date)
      this.form.budget = Number(read('budget', this.form.budget)) || this.form.budget
      this.form.travelers = Number(read('travelers', this.form.travelers)) || this.form.travelers
      const prefs = read('prefs', '')
      if (prefs) this.form.preferences = prefs.split(',').filter(Boolean)
      if (params.get('auto') === '1') this.$nextTick(() => this.submit())
    },
    focusDay (index) {
      if (this.provider === 'amap') {
        if (!this.amap) return
        this.activeDay = index
        const points = index === null
          ? this.dayBounds.flat().filter(Boolean)
          : (this.dayBounds[index] || [])
        if (!points.length) return
        if (points.length === 1) this.amap.setZoomAndCenter(13, points[0])
        else this.amap.setFitView(points.map(p => new window.AMap.Marker({ position: p })), false, [40, 40, 40, 40], 14)
        return
      }
      if (!this.map) return
      this.activeDay = index
      const points = index === null
        ? this.dayBounds.flat().filter(Boolean)
        : (this.dayBounds[index] || [])
      if (!points.length) return
      if (points.length === 1) {
        this.map.setView(points[0], 13)
      } else {
        this.map.fitBounds(points, { padding: [40, 40], maxZoom: 14 })
      }
    },
    async shareLink () {
      if (!this.result) return
      this.sharing = true
      this.toast = ''
      try {
        const response = await fetch('/api/travel/share', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ plan: this.result }),
        })
        const data = await response.json().catch(() => ({}))
        if (!response.ok || !data.id) throw new Error(data.detail || '分享服务暂不可用，请稍后重试。')
        this.shareId = data.id
        const url = 'https://seres-ai.com/projects/travel/?share=' + data.id
        await this.copyToClipboard(url)
        this.toastNow('分享链接已复制')
      } catch (err) {
        this.toastNow(err.message || '分享失败，请稍后重试。')
      } finally {
        this.sharing = false
      }
    },

    renderAMap () {
      if (!this.amap) return
      this.amap.clearMap()
      this.amapOverlays = []
      this.dayBounds = []
      if (!this.result) return
      const { AMap } = window
      this.result.days.forEach((day, dayIndex) => {
        const color = this.dayColors[dayIndex % this.dayColors.length]
        const points = day.items
          .filter(item => typeof item.lat === 'number' && typeof item.lng === 'number')
          .map(item => {
            const [lng, lat] = wgs84ToGcj02(item.lng, item.lat)
            return { item, position: [lng, lat] }
          })
        if (!points.length) return
        const dayLatLngs = points.map(p => p.position)
        points.forEach(({ item, position }, index) => {
          const marker = new AMap.Marker({
            position,
            content: `<span class="ta-map-pin" style="--pin:${color}"><span>${index + 1}</span></span>`,
            offset: new AMap.Pixel(-13, -13),
          })
          marker.on('click', () => {
            const info = `${item.time} ${this.nameOf(item)}<br><small>${item.type}${item.cost ? ' · ¥' + item.cost + '/人' : ''}</small>`
            new AMap.InfoWindow({ content: info, offset: new AMap.Pixel(0, -18) }).open(this.amap, position)
          })
          this.amap.add(marker)
          this.amapOverlays.push(marker)
        })
        this.dayBounds[dayIndex] = dayLatLngs
      })

      // 出发地：单独标记 + 到首站的虚线
      const origin = this.result.origin
      if (origin) {
        const position = [origin.lng, origin.lat]
        const marker = new AMap.Marker({
          position,
          content: `<span class="ta-map-origin">出发</span>`,
          offset: new AMap.Pixel(-20, -18),
        })
        marker.on('click', () => {
          new AMap.InfoWindow({ content: `出发地：${origin.name || ''}`, offset: new AMap.Pixel(0, -18) }).open(this.amap, position)
        })
        this.amap.add(marker)
        this.amapOverlays.push(marker)
      }

      this.drawRealRoutes()

      if (this.amapOverlays.length && this._fitResult !== this.result) {
        this._fitResult = this.result
        // 等首屏瓦片完成后再 fit，避免频繁缩放取消瓦片请求（net::ERR_ABORTED）
        setTimeout(() => {
          if (this.amap && this.amapOverlays.length) {
            this.amap.setFitView(this.amapOverlays, false, [40, 40, 40, 40], 14)
          }
        }, 350)
      }
      this.enrichRoutes()
    },
    async drivingPath (from, to) {
      return new Promise(resolve => {
        this._driving.search(from, to, (status, result) => {
          if (status === 'complete' && result.routes && result.routes[0]) {
            const route = result.routes[0]
            const path = (route.steps || []).reduce((acc, step) => {
              (step.path || []).forEach(p => acc.push([p.lng, p.lat]))
              return acc
            }, [])
            resolve({
              path: path.length ? path : null,
              tolls: Number(route.tolls || 0),
              lights: Number(route.traffic_lights || 0),
              distance: Number(route.distance || 0),
              time: Number(route.time || 0),
            })
          } else {
            resolve(null)
          }
        })
      })
    },
    addRouteLabel (position, text, color) {
      const label = new window.AMap.Text({
        text,
        position,
        anchor: 'center',
        offset: new window.AMap.Pixel(0, -10),
        style: {
          'background-color': 'rgba(4, 18, 26, 0.86)',
          'border': `1px solid ${color}`,
          'color': '#dbe7f3',
          'padding': '2px 6px',
          'border-radius': '6px',
          'font-size': '10px',
          'line-height': '14px',
          'white-space': 'nowrap',
        },
      })
      this.amap.add(label)
      this._routeLines.push(label)
    },
    async drawRealRoutes () {
      if (!this.amap || !this.result) return
      await this.ensureDriving()
      if (!this._routeLines) this._routeLines = []
      this._routeLines.forEach(line => this.amap.remove(line))
      this._routeLines = []
      const draw = (path, color, dashed) => {
        const line = new window.AMap.Polyline({
          path,
          strokeColor: color,
          strokeWeight: 4,
          strokeOpacity: 0.88,
          strokeStyle: dashed ? 'dashed' : 'solid',
          lineJoin: 'round',
          showDir: true,
        })
        this.amap.add(line)
        this._routeLines.push(line)
      }
      let lastPoint = null
      for (let i = 0; i < this.result.days.length; i++) {
        const day = this.result.days[i]
        const color = this.dayColors[i % this.dayColors.length]
        const stops = day.items
          .filter(item => typeof item.lat === 'number' && typeof item.lng === 'number')
          .map(item => {
            const [lng, lat] = wgs84ToGcj02(item.lng, item.lat)
            return [lng, lat]
          })
        let tolls = 0
        let lights = 0
        for (let k = 0; k < stops.length - 1; k++) {
          const seg = await this.drivingPath(stops[k], stops[k + 1])
          const path = seg && seg.path
          draw(path || [stops[k], stops[k + 1]], color, !path)
          const meta = (day.segments || [])[k]
          if (seg || meta) {
            const km = meta ? meta.km : Math.round(seg.distance / 100) / 10
            const tollsValue = meta ? meta.tolls : Math.round(seg.tolls)
            const lightsValue = meta ? meta.lights : seg.lights
            tolls += tollsValue
            lights += lightsValue
            this.addRouteLabel(
              path ? path[Math.floor(path.length / 2)] : stops[k],
              `${km} km · 过路费 ¥${tollsValue} · ${lightsValue} 红灯`,
              color
            )
          }
        }
        if (stops.length) lastPoint = stops[stops.length - 1]
        if (tolls || lights) {
          this.$set(day, 'tolls', Math.round(tolls))
          this.$set(day, 'lights', lights)
        }
      }
      const origin = this.result.origin
      const first = this.dayBounds[0] && this.dayBounds[0][0]
      if (origin && first) {
        const from = [origin.lng, origin.lat]
        const seg = await this.drivingPath(from, first)
        const path = seg && seg.path
        draw(path || [from, first], '#fbbf24', !path)
        const oMeta = this.result.origin
        if (seg || oMeta) {
          const oKm = oMeta && oMeta.to_first_km != null ? oMeta.to_first_km : Math.round(seg.distance / 100) / 10
          const oTolls = oMeta && oMeta.tolls != null ? oMeta.tolls : Math.round(seg.tolls)
          const oLights = oMeta && oMeta.lights != null ? oMeta.lights : seg.lights
          this.addRouteLabel(
            path ? path[Math.floor(path.length / 2)] : from,
            `出发 ${oKm} km · 过路费 ¥${oTolls} · ${oLights} 红灯`,
            '#fbbf24'
          )
        }
      }
      // 返程：最后一天最后一个景点 → 出发地
      if (origin && lastPoint) {
        const to = [origin.lng, origin.lat]
        const seg = await this.drivingPath(lastPoint, to)
        const path = seg && seg.path
        draw(path || [lastPoint, to], '#fbbf24', !path)
        const rMeta = this.result.return_leg
        if (seg || rMeta) {
          const rKm = rMeta ? rMeta.km : Math.round(seg.distance / 100) / 10
          const rTolls = rMeta ? rMeta.tolls : Math.round(seg.tolls)
          const rLights = rMeta ? rMeta.lights : seg.lights
          this.addRouteLabel(
            path ? path[Math.floor(path.length / 2)] : to,
            `返程 ${rKm} km · 过路费 ¥${rTolls} · ${rLights} 红灯`,
            '#fbbf24'
          )
        }
      }
    },
    ensureDriving () {
      if (this._driving) return Promise.resolve(this._driving)
      return new Promise(resolve => {
        window.AMap.plugin(['AMap.Driving'], () => {
          this._driving = new window.AMap.Driving({
            policy: window.AMap.DrivingPolicy.LEAST_TIME,
            hideMarkers: true,
            showTraffic: false,
          })
          resolve(this._driving)
        })
      })
    },
    routeBetween (from, to) {
      return new Promise(resolve => {
        this._driving.search(from, to, (status, result) => {
          if (status === 'complete' && result.routes && result.routes[0]) {
            resolve({ distance: result.routes[0].distance, time: result.routes[0].time })
          } else {
            resolve(null)
          }
        })
      })
    },
    async enrichRoutes () {
      if (!window.AMap || !this.result) return
      // 后端已用高德 Web 服务算好真实路线时，前端不再重复请求
      const multiStopDays = this.result.days.filter(day => day.items.filter(i => i.lat && i.lng).length > 1)
      if (multiStopDays.length && multiStopDays.every(day => day.route_km)) return
      await this.ensureDriving()
      for (let i = 0; i < this.result.days.length; i++) {
        const day = this.result.days[i]
        const stops = day.items
          .filter(item => typeof item.lat === 'number' && typeof item.lng === 'number')
          .map(item => {
            const [lng, lat] = wgs84ToGcj02(item.lng, item.lat)
            return [lng, lat]
          })
        if (stops.length < 2) continue
        let meters = 0
        let seconds = 0
        let ok = false
        for (let k = 0; k < stops.length - 1; k++) {
          const seg = await this.routeBetween(stops[k], stops[k + 1])
          if (seg) {
            meters += seg.distance
            seconds += seg.time
            ok = true
          }
        }
        if (ok) {
          this.$set(day, 'route_km', Math.round(meters / 100) / 10)
          this.$set(day, 'route_min', Math.max(1, Math.round(seconds / 60)))
        }
      }
    },
    ensureGeocoder () {
      if (this._geocoder) return Promise.resolve(this._geocoder)
      return new Promise(resolve => {
        if (!window.AMap) return resolve(null)
        window.AMap.plugin(['AMap.Geocoder'], () => {
          this._geocoder = new window.AMap.Geocoder({})
          resolve(this._geocoder)
        })
      })
    },
    reverseGeocode (lng, lat) {
      return new Promise(resolve => {
        if (!this._geocoder) return resolve('')
        this._geocoder.getAddress([lng, lat], (status, result) => {
          if (status === 'complete' && result.regeocode && result.regeocode.formattedAddress) {
            resolve(result.regeocode.formattedAddress)
          } else {
            resolve('')
          }
        })
      })
    },
    async locateOrigin () {
      if (!navigator.geolocation) {
        this.error = '当前浏览器不支持定位，请手动填写出发地。'
        return
      }
      this.locating = true
      this.error = ''
      try {
        await this.ensureGeocoder()
        const position = await new Promise((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject, {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 60000,
          })
        })
        const lng = Number(position.coords.longitude.toFixed(6))
        const lat = Number(position.coords.latitude.toFixed(6))
        this.form.origin_lng = lng
        this.form.origin_lat = lat
        const [gLng, gLat] = wgs84ToGcj02(lng, lat)
        const address = await this.reverseGeocode(gLng, gLat)
        this.form.origin = address || `${lat.toFixed(4)}, ${lng.toFixed(4)}`
        if (this.amap) this.amap.setZoomAndCenter(13, [gLng, gLat])
      } catch (err) {
        const message = err && (err.message || err.msg)
        this.error = `定位失败：${message || '请检查定位权限'}，可手动填写或点击地图选点。`
      } finally {
        this.locating = false
      }
    },
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
      this.toast = ''
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
        this.applyResult(data)
        this.mode = 'itinerary'
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
    copyText () {
      if (!this.result) return
      const destination = this.result.destination || this.form.destination
      const lines = [destination + ' · ' + this.daysCount + ' 天 · ' + this.form.travelers + ' 人', '']
      this.result.days.forEach(day => {
        lines.push(day.date + ' ' + (day.weekday || '') + ' · ' + (day.theme || ''))
        if (day.weather && day.weather.text) {
          lines.push('  天气：' + day.weather.text + ' ' + (day.weather.temp_min != null ? day.weather.temp_min + '°~' + day.weather.temp_max + '°' : ''))
        }
        if (day.clothing) lines.push('  穿衣：' + day.clothing)
        if (day.lodging_area) lines.push('  住宿：' + day.lodging_area)
        if (day.transport_note) {
          lines.push('  交通：' + day.transport_note + (day.buffer_min != null ? '（缓冲 ' + day.buffer_min + ' 分钟）' : ''))
        }
        ;(day.items || []).forEach(item => {
          const meta = [this.typeLabel(item.type)]
          if (item.duration) meta.push(item.duration)
          if (item.cost) meta.push('¥' + item.cost + '/人')
          lines.push('  ' + (item.time || '') + ' ' + this.nameOf(item) + '（' + meta.join(' · ') + '）')
          if (item.note) lines.push('    ' + item.note)
          if (item.reason) lines.push('    推荐：' + item.reason)
          if (item.indoor_alternative) lines.push('    室内备选：' + item.indoor_alternative)
        })
        lines.push('')
      })
      if (this.result.budget) {
        lines.push('预算 ¥' + this.money(this.result.budget.budget) + ' / 预计 ¥' + this.money(this.result.budget.total))
      }
      if (this.result.tips && this.result.tips.length) {
        lines.push('')
        lines.push('提示：')
        this.result.tips.forEach(tip => lines.push('  · ' + tip))
      }
      const text = lines.join('\n')
      this.copyToClipboard(text).then(() => {
        this.copied = true
        setTimeout(() => { this.copied = false }, 2000)
      })
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
    selectMode (key) {
      if (key === 'plan' && this.readOnly) return
      if ((key === 'itinerary' || key === 'today') && !this.result) return
      this.mode = key
    },
    nameOf (item) {
      if (!item) return ''
      return item.name || item.title || '行程安排'
    },
    typeLabel (type) {
      const labels = { attraction: '景点', meal: '用餐', lodging: '住宿', transport: '交通', rest: '休息' }
      return labels[type] || '安排'
    },
    hasLatLng (item) {
      if (!item) return false
      const lat = Number(item.lat)
      const lng = Number(item.lng)
      return Number.isFinite(lat) && Number.isFinite(lng) && lat !== 0 && lng !== 0
    },
    itemKey (item) {
      if (!item) return ''
      return item.id || ((item.time || '') + '-' + this.nameOf(item))
    },
    timeToMinutes (value) {
      const match = /^(\d{1,2}):(\d{2})/.exec(String(value || ''))
      if (!match) return 24 * 60
      return Number(match[1]) * 60 + Number(match[2])
    },
    setProfile (key, value) {
      this.form.profile[key] = value
    },
    toggleProfile (key, value) {
      const list = this.form.profile[key]
      const index = list.indexOf(value)
      if (index >= 0) list.splice(index, 1)
      else list.push(value)
    },
    profileLabel (key, value) {
      const options = this.profileOptions[key] || []
      const found = options.find(option => option.value === value)
      return found ? found.label : ''
    },
    applyResult (data) {
      const plan = (data && data.plan) ? data.plan : data
      this.result = plan
      this.todayWeather = null
      this.feedback = {}
      this.poi = { category: 'food', items: [], source: '', loading: false, error: '', cache: {}, reqId: this.poi.reqId + 1 }
      this.initFeedback()
      this.loadPacking()
      if (plan && plan.days && plan.days.length) {
        this.form.start_date = plan.days[0].date || this.form.start_date
        this.form.end_date = plan.days[plan.days.length - 1].date || this.form.end_date
      }
      if (plan && plan.destination) this.form.destination = plan.destination
      if (plan && plan.travelers) this.form.travelers = plan.travelers
    },
    initFeedback () {
      this.feedback = {}
      if (!this.result || !this.result.days) return
      this.result.days.forEach(day => {
        (day.items || []).forEach(item => {
          this.$set(this.feedback, this.itemKey(item), { helpful: null, visited: null, saving: false, error: '' })
        })
      })
    },
    fb (item) {
      if (!item) return { helpful: null, visited: null, saving: false, error: '' }
      return this.feedback[this.itemKey(item)] || { helpful: null, visited: null, saving: false, error: '' }
    },
    async sendFeedback (item, patch) {
      if (!this.result || !item) return
      const key = this.itemKey(item)
      const current = this.fb(item)
      const previous = { helpful: current.helpful, visited: current.visited }
      const next = Object.assign({}, previous, patch)
      this.$set(this.feedback, key, { helpful: next.helpful, visited: next.visited, saving: true, error: '' })
      try {
        const response = await fetch('/api/travel/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            plan_id: this.result.plan_id || '',
            item_id: item.id || key,
            helpful: next.helpful,
            visited: next.visited,
            note: '',
          }),
        })
        if (!response.ok) {
          const data = await response.json().catch(() => ({}))
          throw new Error(data.detail || '反馈保存失败')
        }
        this.$set(this.feedback, key, { helpful: next.helpful, visited: next.visited, saving: false, error: '' })
      } catch (err) {
        this.$set(this.feedback, key, { helpful: previous.helpful, visited: previous.visited, saving: false, error: '同步失败' })
        setTimeout(() => {
          const state = this.feedback[key]
          if (state && state.error) this.$set(this.feedback, key, Object.assign({}, state, { error: '' }))
        }, 2600)
      }
    },
    loadShareFromQuery () {
      const params = new URLSearchParams(window.location.search)
      const id = params.get('share')
      if (id) this.loadShare(id)
    },
    async loadShare (id) {
      this.loading = true
      this.error = ''
      try {
        const response = await fetch('/api/travel/share/' + encodeURIComponent(id))
        const data = await response.json().catch(() => ({}))
        if (response.status === 404) throw new Error('共享行程不存在或已过期。')
        if (!response.ok) throw new Error(data.detail || '共享行程加载失败。')
        const plan = data.plan || data
        this.readOnly = true
        this.shareId = id
        this.applyResult(plan)
        this.mode = 'itinerary'
      } catch (err) {
        this.error = err.message || '共享行程加载失败。'
        this.mode = 'plan'
      } finally {
        this.loading = false
      }
    },
    resetPlan () {
      this.result = null
      this.mode = 'plan'
      this.todayWeather = null
      this.toast = ''
      this.activeDay = null
      this.$nextTick(() => this.renderMap())
    },
    toastNow (message) {
      this.toast = message
      if (this.toastTimer) clearTimeout(this.toastTimer)
      this.toastTimer = setTimeout(() => { this.toast = '' }, 3200)
    },
    weatherSourceLabel (source) {
      if (source === 'amap') return '高德天气'
      if (source === 'fallback') return '季节参考'
      return ''
    },
    async refreshWeather () {
      if (!this.result || !this.todayDay || !this.todayDay.date) return
      this.weatherLoading = true
      try {
        const params = new URLSearchParams({
          destination: this.result.destination || this.form.destination,
          date: this.todayDay.date,
        })
        const response = await fetch('/api/travel/weather?' + params.toString())
        const data = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error(data.detail || '天气刷新失败。')
        this.todayWeather = data
        this.toastNow('天气已更新')
      } catch (err) {
        this.toastNow(err.message || '天气刷新失败，请稍后重试。')
      } finally {
        this.weatherLoading = false
      }
    },
    poiCenter () {
      if (!this.result || !this.result.days) return null
      const days = this.result.days
      const order = [this.todayDay].concat(days)
      for (let i = 0; i < order.length; i++) {
        const items = (order[i] && order[i].items) || []
        const found = items.find(item => this.hasLatLng(item))
        if (found) return { lat: Number(found.lat), lng: Number(found.lng) }
      }
      return null
    },
    async loadPoi (category, force) {
      if (!this.result) return
      const cat = category || this.poi.category
      this.poi.category = cat
      const center = this.poiCenter()
      if (!center) {
        this.poi.items = []
        this.poi.source = ''
        this.poi.error = '当前行程暂无坐标，无法搜索附近推荐。'
        return
      }
      const cacheKey = cat + ':' + center.lat.toFixed(3) + ',' + center.lng.toFixed(3)
      if (!force && this.poi.cache[cacheKey]) {
        this.poi.items = this.poi.cache[cacheKey].items
        this.poi.source = this.poi.cache[cacheKey].source
        this.poi.error = ''
        return
      }
      const reqId = this.poi.reqId + 1
      this.poi.reqId = reqId
      this.poi.loading = true
      this.poi.error = ''
      const params = new URLSearchParams({
        category: cat,
        lat: String(center.lat),
        lng: String(center.lng),
        radius: '1500',
        limit: '6',
      })
      const destination = this.result.destination || this.form.destination
      if (destination) params.set('destination', destination)
      const dietary = (this.form.profile && this.form.profile.dietary) || []
      if (dietary.length) params.set('dietary', dietary.join(','))
      try {
        const response = await fetch('/api/travel/poi?' + params.toString())
        const data = await response.json().catch(() => ({}))
        if (this.poi.reqId !== reqId) return
        if (!response.ok) throw new Error(data.detail || '附近推荐加载失败。')
        const items = Array.isArray(data.items) ? data.items : []
        const source = data.source || 'amap'
        this.$set(this.poi.cache, cacheKey, { items, source })
        this.poi.items = items
        this.poi.source = source
      } catch (err) {
        if (this.poi.reqId !== reqId) return
        this.poi.items = []
        this.poi.source = ''
        this.poi.error = err.message || '附近推荐加载失败，请稍后重试。'
      } finally {
        if (this.poi.reqId === reqId) this.poi.loading = false
      }
    },
    switchPoi (category) {
      this.poi.category = category
      this.loadPoi(category)
    },
    ensurePoi () {
      if (!this.result) return
      if (this.poi.loading || this.poi.items.length) return
      this.loadPoi(this.poi.category)
    },
    catLabel (category) {
      const labels = { food: '吃饭', lodging: '住宿', transport: '交通', emergency: '紧急' }
      return labels[category] || '推荐'
    },
    formatDistance (value) {
      const distance = Number(value)
      if (!Number.isFinite(distance)) return ''
      if (distance < 1000) return Math.round(distance) + ' m'
      return (distance / 1000).toFixed(1) + ' km'
    },
    amapNavUrl (item) {
      if (!item) return ''
      if (item.navigation_url) return item.navigation_url
      if (!this.hasLatLng(item)) return ''
      const [lng, lat] = wgs84ToGcj02(Number(item.lng), Number(item.lat))
      const name = encodeURIComponent(this.nameOf(item))
      return 'https://uri.amap.com/marker?position=' + lng.toFixed(6) + ',' + lat.toFixed(6) + '&name=' + name + '&src=seres-ai&coordinate=gaode&callnative=1'
    },
    packingStorageKey () {
      const id = (this.result && this.result.plan_id) || this.shareId || (this.form.destination + '-' + this.form.start_date)
      return 'ta-packing:' + id
    },
    loadPacking () {
      try {
        const raw = window.localStorage.getItem(this.packingStorageKey())
        this.packing = raw ? (JSON.parse(raw) || {}) : {}
      } catch (err) {
        this.packing = {}
      }
    },
    savePacking () {
      try {
        window.localStorage.setItem(this.packingStorageKey(), JSON.stringify(this.packing))
      } catch (err) {}
    },
    isPacked (category, name) {
      return !!this.packing[category + '|' + name]
    },
    togglePacked (category, name) {
      const key = category + '|' + name
      this.$set(this.packing, key, !this.packing[key])
      this.savePacking()
    },
    copyToClipboard (text) {
      return new Promise(resolve => {
        const done = () => resolve(true)
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done).catch(() => this.fallbackCopy(text, done))
        } else {
          this.fallbackCopy(text, done)
        }
      })
    },
    downloadFile (name, content, type) {
      const blob = new Blob([content], { type })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = name
      document.body.appendChild(anchor)
      anchor.click()
      setTimeout(() => {
        document.body.removeChild(anchor)
        URL.revokeObjectURL(url)
      }, 0)
    },
    safeName (value) {
      return String(value || 'travel').replace(/[\\/:*?"<>|\s]+/g, '-')
    },
    downloadJson () {
      if (!this.result) return
      const name = this.safeName(this.result.destination || this.form.destination) + '-' + this.form.start_date + '.json'
      this.downloadFile(name, JSON.stringify(this.result, null, 2), 'application/json;charset=utf-8')
      this.toastNow('已下载 .json')
    },
    downloadIcs () {
      if (!this.result) return
      const name = this.safeName(this.result.destination || this.form.destination) + '-' + this.form.start_date + '.ics'
      this.downloadFile(name, this.buildIcs(), 'text/calendar;charset=utf-8')
      this.toastNow('已下载 .ics 日历')
    },
    buildIcs () {
      const lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//seres-ai//travel-assistant//CN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'X-WR-CALNAME:' + this.icsEscape(this.result.destination || this.form.destination),
      ]
      const stamp = this.icsStamp(new Date())
      this.result.days.forEach(day => {
        (day.items || []).forEach(item => {
          const start = this.combineDateTime(day.date, item.time)
          if (!start) return
          const end = new Date(start.getTime() + this.durationMinutes(item.duration) * 60000)
          const uid = (item.id || (day.date + '-' + (item.time || ''))) + '@seres-ai.com'
          lines.push('BEGIN:VEVENT')
          lines.push('UID:' + this.icsEscape(uid))
          lines.push('DTSTAMP:' + stamp)
          lines.push('DTSTART:' + this.icsLocal(start))
          lines.push('DTEND:' + this.icsLocal(end))
          lines.push('SUMMARY:' + this.icsEscape(this.nameOf(item)))
          const location = [item.address, day.lodging_area].filter(Boolean).join(' / ')
          if (location) lines.push('LOCATION:' + this.icsEscape(location))
          const desc = [
            this.typeLabel(item.type),
            item.note,
            item.reason,
            item.indoor_alternative ? '室内备选：' + item.indoor_alternative : '',
          ].filter(Boolean).join('；')
          if (desc) lines.push('DESCRIPTION:' + this.icsEscape(desc))
          lines.push('END:VEVENT')
        })
      })
      lines.push('END:VCALENDAR')
      return lines.join('\r\n')
    },
    combineDateTime (dateStr, timeStr) {
      const dateMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(dateStr || ''))
      if (!dateMatch) return null
      let hours = 9
      let minutes = 0
      const timeMatch = /^(\d{1,2}):(\d{2})/.exec(String(timeStr || ''))
      if (timeMatch) {
        hours = Number(timeMatch[1])
        minutes = Number(timeMatch[2])
      }
      return new Date(Number(dateMatch[1]), Number(dateMatch[2]) - 1, Number(dateMatch[3]), hours, minutes, 0, 0)
    },
    durationMinutes (value) {
      if (!value) return 60
      const text = String(value)
      const hours = /(\d+(?:\.\d+)?)\s*(?:h|小时|hr)/i.exec(text)
      if (hours) return Math.max(15, Math.round(Number(hours[1]) * 60))
      const minutes = /(\d+(?:\.\d+)?)\s*(?:min|分钟|分)/i.exec(text)
      if (minutes) return Math.max(15, Math.round(Number(minutes[1])))
      return 60
    },
    icsLocal (date) {
      return date.getFullYear() + pad(date.getMonth() + 1) + pad(date.getDate()) + 'T' + pad(date.getHours()) + pad(date.getMinutes()) + '00'
    },
    icsStamp (date) {
      return date.getUTCFullYear() + pad(date.getUTCMonth() + 1) + pad(date.getUTCDate()) + 'T' + pad(date.getUTCHours()) + pad(date.getUTCMinutes()) + pad(date.getUTCSeconds()) + 'Z'
    },
    icsEscape (value) {
      return String(value || '')
        .replace(/\\/g, '\\\\')
        .replace(/\n/g, '\\n')
        .replace(/,/g, '\\,')
        .replace(/;/g, '\\;')
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
.ta-map-wrap {
  position: relative;
  margin-bottom: 1.4rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16));
  border-radius: 16px;
  overflow: hidden;
  background-color: var(--site-card, rgba(13,24,41,.8));
  box-shadow: 0 12px 32px var(--site-shadow, rgba(0,0,0,.38));
}
.ta-map { height: 340px; width: 100%; background: rgba(8, 14, 24, .6); }
.ta-map-fs {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 600;
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--site-border, rgba(120,160,200,.2));
  border-radius: 9px;
  background-color: rgba(6, 11, 22, .78);
  color: var(--site-text, #dbe7f3);
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  backdrop-filter: blur(8px);
  transition: border-color .2s ease, color .2s ease, background-color .2s ease;
}
.ta-map-fs:hover { border-color: rgba(34, 211, 238, .5); color: var(--site-accent-text, #67e8f9); background-color: rgba(34, 211, 238, .12); }
.ta-map-wrap.is-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 9999;
  margin: 0;
  border: 0;
  border-radius: 0;
  display: flex;
  flex-direction: column;
  background-color: var(--bodyBg, #04070f);
}
.ta-map-wrap.is-fullscreen .ta-map { flex: 1 1 auto; height: auto; min-height: 0; }
.ta-map-wrap.is-fullscreen .ta-map-legend { flex: none; }

.ta-map-empty {
  position: absolute; inset: auto 0 0 0;
  padding: .6rem .9rem;
  font-size: .76rem; color: var(--site-muted, #8ea3b8);
  background-image: linear-gradient(180deg, transparent, rgba(4, 8, 16, .72));
}
:deep(.ta-map-pick) { min-width: 200px; font-size: 12px; line-height: 1.5; }
:deep(.ta-map-pick strong) { display: block; color: #f8fafc; font-size: 12px; }
:deep(.ta-map-pick-meta) { color: var(--site-muted, #8ea3b8); margin: 2px 0 8px; font-size: 11px; }
:deep(.ta-map-pick-actions) { display: flex; gap: 6px; }
:deep(.ta-map-pick-actions button) {
  flex: 1;
  padding: 4px 8px;
  border: 1px solid rgba(34, 211, 238, .45);
  border-radius: 6px;
  background: rgba(34, 211, 238, .1);
  color: var(--site-accent-text, #67e8f9);
  font-size: 11px;
  cursor: pointer;
}
:deep(.ta-map-pick-actions button:hover) { background: rgba(34, 211, 238, .2); }
.ta-map-legend {
  display: flex; flex-wrap: wrap; gap: .45rem .85rem;
  padding: .6rem .9rem;
  border-top: 1px solid var(--site-border, rgba(120,160,200,.16));
  font-size: .72rem; color: var(--site-muted, #8ea3b8);
  background-color: rgba(255, 255, 255, .02);
}
.ta-legend-chip {
  display: inline-flex; align-items: center; gap: .35rem;
  padding: .15rem .5rem;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  color: var(--site-muted, #8ea3b8);
  font-size: .72rem; cursor: pointer;
  transition: color .2s ease, border-color .2s ease, background-color .2s ease;
}
.ta-legend-chip:hover { color: var(--site-text, #dbe7f3); }
.ta-legend-chip.active { color: var(--site-accent-text, #67e8f9); border-color: rgba(34,211,238,.4); background-color: rgba(34,211,238,.08); }
.ta-day-stat {
  padding: .1rem .4rem; border-radius: 5px;
  font-size: .68rem; font-weight: 500;
  color: var(--site-muted, #8ea3b8);
  background-color: rgba(255,255,255,.04);
}
.ta-map-legend i { width: 8px; height: 8px; border-radius: 50%; box-shadow: 0 0 8px currentColor; }
.ta-map-legend em { font-style: normal; color: #fda4af; }
:deep(.ta-map-pin span) {
  display: flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 50%;
  font-size: .7rem; font-weight: 700; color: #04121a;
  background: var(--pin, #22d3ee);
  border: 2px solid rgba(4, 18, 26, .55);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--pin, #22d3ee) 22%, transparent), 0 6px 14px rgba(0, 0, 0, .35);
}
:deep(.leaflet-container) { font: inherit; background: transparent; }
:deep(.leaflet-popup-content-wrapper), :deep(.leaflet-popup-tip) {
  background: var(--site-elevated, #111c30);
  color: var(--site-text, #dbe7f3);
  border: 1px solid var(--site-border, rgba(120,160,200,.16));
}
:deep(.leaflet-popup-content) { margin: .7rem .9rem; font-size: .78rem; line-height: 1.6; }
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
.ta-origin-row { display: flex; gap: .5rem; }
.ta-origin-row input { flex: 1; min-width: 0; }
.ta-locate {
  flex: none;
  padding: .55rem .95rem;
  border: 1px solid rgba(34, 211, 238, .4);
  border-radius: 10px;
  background-color: rgba(34, 211, 238, .08);
  color: var(--site-accent-text, #67e8f9);
  font: inherit;
  font-size: .84rem;
  cursor: pointer;
  transition: background-color .2s ease, transform .2s ease;
}
.ta-locate:hover { background-color: rgba(34, 211, 238, .16); transform: translateY(-1px); }
.ta-locate:disabled { opacity: .6; cursor: wait; }
:deep(.ta-map-origin) {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 3px 9px;
  border-radius: 999px;
  background: #fbbf24;
  color: #1a1305;
  font-size: 11px; font-weight: 700;
  box-shadow: 0 0 0 3px rgba(251, 191, 36, .18), 0 6px 14px rgba(0, 0, 0, .35);
}

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
.ta-skeleton { margin-top: 1.2rem; display: grid; gap: .6rem; }
.ta-skeleton-row {
  height: 64px; border-radius: 14px;
  border: 1px solid var(--site-border, rgba(120,160,200,.16));
  background-image: linear-gradient(90deg, rgba(255,255,255,.03) 25%, rgba(255,255,255,.08) 37%, rgba(255,255,255,.03) 63%);
  background-size: 400% 100%;
  animation: ta-shimmer 1.4s ease infinite;
}
@keyframes ta-shimmer { 0% { background-position: 100% 50%; } 100% { background-position: 0 50%; } }
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
.ta-day-warn { display: flex; flex-wrap: wrap; gap: .4rem; margin: 0 0 .55rem; }
.ta-day-warn span {
  padding: .16rem .55rem;
  border: 1px solid rgba(245, 158, 11, .35);
  border-radius: 6px;
  background-color: rgba(245, 158, 11, .08);
  color: #fbbf24;
  font-size: .72rem;
}
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

/* ===== 三态导航 / 画像 ===== */
.ta-modes {
  display: flex; flex-wrap: wrap; align-items: center; gap: .35rem;
  width: fit-content; max-width: 100%;
  margin: 0 0 1rem; padding: .3rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16));
  border-radius: 999px;
  background-color: rgba(255, 255, 255, .02);
}
.ta-mode {
  padding: .38rem .9rem;
  border: 0; border-radius: 999px;
  background-color: transparent;
  color: var(--site-muted, #8ea3b8);
  font: inherit; font-size: .82rem; cursor: pointer;
  transition: color .2s ease, background-color .2s ease;
}
.ta-mode:hover:not(:disabled) { color: var(--site-text, #dbe7f3); background-color: rgba(255, 255, 255, .05); }
.ta-mode.active {
  color: #04121a; font-weight: 650;
  background-color: var(--site-accent, #22d3ee);
  box-shadow: 0 6px 18px var(--site-glow, rgba(34,211,238,.18));
}
.ta-mode:disabled { opacity: .38; cursor: not-allowed; }
.ta-mode em { margin-left: .3rem; font-style: normal; font-size: .66rem; opacity: .75; }
.ta-readonly {
  margin-left: .35rem; padding: .2rem .6rem;
  border: 1px solid rgba(251,191,36,.35); border-radius: 999px;
  background-color: rgba(251,191,36,.08);
  color: #fbbf24; font-size: .7rem;
}

.ta-profile { display: grid; gap: .55rem; margin-top: 1rem; }
.ta-profile-row {
  display: grid; grid-template-columns: 68px minmax(0, 1fr);
  gap: .6rem; align-items: start;
}
.ta-chips { display: flex; flex-wrap: wrap; gap: .4rem; min-width: 0; }

/* ===== 行程：天气 / 事实 / 类型 / 链接 / 反馈 ===== */
.ta-day-weather {
  display: flex; flex-wrap: wrap; align-items: center; gap: .35rem;
  margin: 0 0 .5rem; font-size: .73rem; color: var(--site-muted, #8ea3b8);
}
.ta-day-weather span {
  padding: .14rem .5rem; border-radius: 6px;
  background-color: rgba(255, 255, 255, .04);
}
.ta-day-weather .ta-w-main { color: var(--site-accent-text, #67e8f9); }
.ta-day-weather em { font-style: normal; font-size: .68rem; opacity: .75; }
.ta-day-facts { display: grid; gap: .25rem; margin: 0 0 .55rem; }
.ta-day-facts p { margin: 0; font-size: .8rem; line-height: 1.6; color: var(--site-muted, #8ea3b8); overflow-wrap: anywhere; }
.ta-day-facts b {
  display: inline-block; margin-right: .45rem; padding: .05rem .35rem;
  border: 1px solid rgba(34,211,238,.18); border-radius: 4px;
  font-size: .68rem; font-weight: 600; color: var(--site-text, #dbe7f3);
  background-color: rgba(34,211,238,.1);
}
.ta-item-body { min-width: 0; }
.ta-item-meta { display: flex; align-items: center; flex-wrap: wrap; gap: .25rem; }
.ta-type {
  padding: .02rem .35rem; border-radius: 4px;
  font-style: normal; font-size: .68rem;
  color: var(--site-accent-text, #67e8f9);
  border: 1px solid rgba(34,211,238,.25);
  background-color: rgba(34,211,238,.07);
}
.ta-item.is-meal .ta-type { color: #fbbf24; border-color: rgba(251,191,36,.3); background-color: rgba(251,191,36,.08); }
.ta-item.is-lodging .ta-type { color: #c4b5fd; border-color: rgba(139,92,246,.3); background-color: rgba(139,92,246,.1); }
.ta-item.is-transport .ta-type { color: #93c5fd; border-color: rgba(96,165,250,.3); background-color: rgba(96,165,250,.1); }
.ta-item.is-rest .ta-type { color: #a3e635; border-color: rgba(163,230,53,.3); background-color: rgba(163,230,53,.08); }
.ta-reason { color: var(--site-accent-text, #67e8f9) !important; opacity: .85; }
.ta-indoor {
  display: inline-block; margin: .3rem 0 0 !important;
  padding: .12rem .45rem;
  border: 1px dashed rgba(139,92,246,.4); border-radius: 6px;
  background-color: rgba(139,92,246,.08);
  color: #c4b5fd !important; font-size: .74rem !important;
}
.ta-item-links { display: flex; flex-wrap: wrap; align-items: center; gap: .6rem; margin-top: .3rem; font-size: .74rem; }
.ta-item-links a, .ta-next-actions a, .ta-poi-actions a {
  color: var(--site-accent-text, #67e8f9); text-decoration: none;
  border-bottom: 1px solid rgba(34,211,238,.35);
}
.ta-item-links a:hover, .ta-next-actions a:hover, .ta-poi-actions a:hover { border-bottom-color: #67e8f9; }
.ta-addr { color: var(--site-muted, #8ea3b8); font-size: .72rem; overflow-wrap: anywhere; }

.ta-fb { display: flex; flex-wrap: wrap; align-items: center; gap: .3rem; margin-top: .4rem; }
.ta-fb-btn {
  padding: .12rem .48rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16)); border-radius: 999px;
  background-color: transparent;
  color: var(--site-muted, #8ea3b8);
  font: inherit; font-size: .7rem; cursor: pointer;
  transition: color .2s ease, border-color .2s ease, background-color .2s ease;
}
.ta-fb-btn:hover { color: var(--site-text, #dbe7f3); border-color: rgba(34,211,238,.4); }
.ta-fb-btn.on { color: #04121a; font-weight: 600; background-color: var(--site-accent, #22d3ee); border-color: var(--site-accent, #22d3ee); }
.ta-fb-sep { width: 1px; height: 12px; margin: 0 .2rem; background-color: var(--site-border, rgba(120,160,200,.2)); }
.ta-fb-hint { font-size: .68rem; color: var(--site-muted, #8ea3b8); }
.ta-fb-hint.err { color: #fda4af; }

.ta-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem; margin-top: 1rem; }
.ta-toast { font-size: .76rem; color: #a3e635; }

/* ===== 打包清单 ===== */
.ta-packing {
  margin-top: 1.2rem; padding: 1rem 1.15rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16)); border-radius: 14px;
  background-color: rgba(255, 255, 255, .02);
}
.ta-section-head { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; margin-bottom: .7rem; }
.ta-section-head h3 { margin: 0; font-size: 1rem; color: #f8fafc; }
.ta-section-meta { font-size: .74rem; color: var(--site-muted, #8ea3b8); font-variant-numeric: tabular-nums; }
.ta-pack-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: .7rem; }
.ta-pack-group {
  min-width: 0; padding: .6rem .7rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16)); border-radius: 10px;
  background-color: rgba(255, 255, 255, .02);
}
.ta-pack-group h4 { margin: 0 0 .45rem; font-size: .8rem; color: var(--site-accent-text, #67e8f9); }
.ta-pack-item {
  display: grid; grid-template-columns: 16px minmax(0, 1fr);
  gap: .4rem; align-items: start; padding: .22rem 0; cursor: pointer;
}
.ta-pack-item input { width: 14px; height: 14px; margin-top: .15rem; accent-color: var(--site-accent, #22d3ee); cursor: pointer; }
.ta-pack-name { display: flex; flex-wrap: wrap; align-items: center; gap: .35rem; font-size: .82rem; color: var(--site-text, #dbe7f3); }
.ta-required {
  padding: .02rem .3rem; border: 1px solid rgba(251,191,36,.35); border-radius: 4px;
  font-size: .62rem; color: #fbbf24;
}
.ta-pack-item small { grid-column: 2; font-size: .7rem; line-height: 1.45; color: var(--site-muted, #8ea3b8); }
.ta-pack-item.done .ta-pack-name { opacity: .55; text-decoration: line-through; }
.ta-pack-notes { margin: .7rem 0 0; padding-left: 1.1rem; font-size: .76rem; color: var(--site-muted, #8ea3b8); }

/* ===== 今日 ===== */
.ta-today { margin-top: 1.4rem; animation: ta-fade .35s ease both; }
.ta-today-head { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 1rem; margin-bottom: .9rem; }
.ta-today-kicker { margin: 0 0 .25rem; font-size: .68rem; font-weight: 600; letter-spacing: .16em; color: var(--site-accent-text, #67e8f9); }
.ta-today-head h3 { margin: 0; font-size: 1.12rem; color: #f8fafc; }
.ta-today-note { margin: .3rem 0 0; font-size: .74rem; color: #fbbf24; }
.ta-today-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .8rem; }
.ta-today-card {
  min-width: 0; padding: .9rem 1rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16)); border-radius: 14px;
  background-color: var(--site-card, rgba(13,24,41,.8));
}
.ta-card-head { display: flex; justify-content: space-between; align-items: center; gap: .5rem; margin-bottom: .55rem; }
.ta-card-head h4 { margin: 0; font-size: .8rem; font-weight: 600; letter-spacing: .04em; color: var(--site-muted, #8ea3b8); }
.ta-temp { display: flex; flex-wrap: wrap; align-items: baseline; gap: .5rem; }
.ta-temp strong { font-size: 1.5rem; color: #f8fafc; }
.ta-temp span { font-size: .86rem; color: var(--site-accent-text, #67e8f9); font-variant-numeric: tabular-nums; }
.ta-weather-meta { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .35rem; font-size: .72rem; color: var(--site-muted, #8ea3b8); }
.ta-weather-meta em { font-style: normal; opacity: .8; }
.ta-clothing {
  margin: .6rem 0 0; padding: .45rem .6rem;
  border-left: 2px solid rgba(34,211,238,.5); border-radius: 0 6px 6px 0;
  background-color: rgba(34,211,238,.05);
  font-size: .8rem; line-height: 1.6; color: var(--site-text, #dbe7f3);
}
.ta-next-time { margin: 0; font-size: .74rem; color: var(--site-accent-text, #67e8f9); font-variant-numeric: tabular-nums; }
.ta-next-time span { margin-left: .35rem; color: var(--site-muted, #8ea3b8); }
.ta-next-name { display: block; margin: .2rem 0; font-size: 1rem; color: #f8fafc; overflow-wrap: anywhere; }
.ta-next-reason, .ta-next-note { margin: .2rem 0 0; font-size: .78rem; line-height: 1.55; color: var(--site-muted, #8ea3b8); }
.ta-next-actions { display: flex; gap: .7rem; margin-top: .55rem; font-size: .78rem; }
.ta-muted { margin: .3rem 0; font-size: .78rem; color: var(--site-muted, #8ea3b8); }
.ta-route-note { margin: 0 0 .3rem; font-size: .8rem; line-height: 1.6; color: var(--site-text, #dbe7f3); }
.ta-lodging { margin: .5rem 0 .55rem; font-size: .82rem; color: var(--site-text, #dbe7f3); }
.ta-lodging b {
  display: inline-block; margin-right: .4rem; padding: .02rem .35rem;
  border: 1px solid rgba(139,92,246,.25); border-radius: 4px;
  background-color: rgba(139,92,246,.12);
  font-size: .68rem; color: #c4b5fd;
}
.ta-mini {
  padding: .18rem .55rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16)); border-radius: 6px;
  background-color: transparent;
  color: var(--site-accent-text, #67e8f9);
  font: inherit; font-size: .72rem; cursor: pointer;
}
.ta-mini:hover { border-color: rgba(34,211,238,.45); background-color: rgba(34,211,238,.08); }
.ta-mini:disabled { opacity: .5; cursor: wait; }
.ta-emergency-list { list-style: none; margin: 0 0 .5rem; padding: 0; display: grid; gap: .3rem; }
.ta-emergency-list li { display: flex; justify-content: space-between; gap: .6rem; font-size: .82rem; color: var(--site-text, #dbe7f3); }
.ta-emergency-list a { color: #fda4af; font-weight: 600; text-decoration: none; }
.ta-hospital { display: block; margin-bottom: .5rem; font-size: .76rem; color: var(--site-accent-text, #67e8f9); }

/* ===== 附近推荐 ===== */
.ta-poi {
  margin-top: 1.1rem; padding: 1rem 1.1rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16)); border-radius: 14px;
  background-color: rgba(255, 255, 255, .02);
}
.ta-poi-head { display: flex; justify-content: space-between; align-items: center; gap: .8rem; margin-bottom: .6rem; }
.ta-poi-head h3 { margin: 0; font-size: 1rem; color: #f8fafc; }
.ta-fallback, .ta-live {
  display: inline-block; margin-left: .5rem; padding: .1rem .45rem;
  border: 1px solid rgba(251,191,36,.35); border-radius: 999px;
  background-color: rgba(251,191,36,.08);
  font-size: .68rem; color: #fbbf24;
}
.ta-live { border-color: rgba(34,211,238,.35); background-color: rgba(34,211,238,.08); color: var(--site-accent-text, #67e8f9); }
.ta-poi-tabs { display: flex; flex-wrap: wrap; gap: .35rem; margin-bottom: .7rem; }
.ta-poi-tab {
  padding: .25rem .7rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16)); border-radius: 999px;
  background-color: transparent;
  color: var(--site-muted, #8ea3b8);
  font: inherit; font-size: .78rem; cursor: pointer;
}
.ta-poi-tab:hover { color: var(--site-text, #dbe7f3); }
.ta-poi-tab.active { color: #04121a; font-weight: 600; background-color: var(--site-accent, #22d3ee); border-color: var(--site-accent, #22d3ee); }
.ta-poi-state { margin: .6rem 0; font-size: .8rem; color: var(--site-muted, #8ea3b8); }
.ta-poi-state.err { color: #fda4af; }
.ta-poi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: .65rem; }
.ta-poi-card {
  min-width: 0; padding: .7rem .8rem;
  border: 1px solid var(--site-border, rgba(120,160,200,.16)); border-radius: 10px;
  background-color: var(--site-card, rgba(13,24,41,.8));
  display: flex; flex-direction: column; gap: .3rem;
}
.ta-poi-card-head { display: flex; justify-content: space-between; align-items: baseline; gap: .5rem; }
.ta-poi-card-head strong { font-size: .88rem; color: #f8fafc; overflow-wrap: anywhere; }
.ta-poi-distance { flex: none; font-size: .7rem; color: var(--site-accent-text, #67e8f9); font-variant-numeric: tabular-nums; }
.ta-poi-tags { display: flex; flex-wrap: wrap; gap: .3rem; font-size: .68rem; color: var(--site-muted, #8ea3b8); }
.ta-poi-tags span { padding: .05rem .35rem; border-radius: 4px; background-color: rgba(255, 255, 255, .04); }
.ta-poi-addr, .ta-poi-reason { margin: 0; font-size: .74rem; line-height: 1.5; color: var(--site-muted, #8ea3b8); overflow-wrap: anywhere; }
.ta-poi-reason { color: var(--site-text, #dbe7f3); opacity: .85; }
.ta-poi-actions { display: flex; gap: .6rem; margin-top: .2rem; font-size: .74rem; }
.ta-poi-note { margin: .65rem 0 0; font-size: .68rem; color: var(--site-muted, #8ea3b8); opacity: .8; }
.ta-today-pack { margin-top: 1rem; }

@media (max-width: 860px) {
  .ta-today-grid { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 720px) {
  .ta-today-grid { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .ta-modes { width: 100%; border-radius: 12px; }
  .ta-mode { flex: 1 1 0; padding: .4rem .3rem; text-align: center; }
  .ta-profile-row { grid-template-columns: 1fr; gap: .25rem; }
  .ta-map { height: 250px; }
  .ta-day-date, .ta-day-header { flex-wrap: wrap; }
  .ta-poi-grid, .ta-pack-grid { grid-template-columns: 1fr; }
  .ta-toolbar .ta-ghost { flex: 1 1 auto; text-align: center; }
  .ta-today-head { flex-direction: column; align-items: stretch; }
  .ta-poi-head { flex-wrap: wrap; }
}

</style>
