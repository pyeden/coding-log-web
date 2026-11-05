import Artalk from 'artalk'
import 'artalk/dist/Artalk.css'

// 修复 vdoing 悬浮按钮（返回顶部 / 去评论）在固定滚动容器下的行为
// 站点把滚动交给了 .theme-container（position:fixed + overflow-y:auto），
// 而主题组件用的是 window.scrollTo / window.pageYOffset，所以点击没有反应。
const BTN_FIX_FLAG = '__vdoingButtonsPatched__'
const COMMENT_SELECTORS = ['#artalk-comments', '#vuepress-plugin-comment', '#valine-vuepress-comment', '.vssue']

const getScroller = () =>
  document.querySelector('.theme-container') || document.scrollingElement

const findComment = () => {
  for (const sel of COMMENT_SELECTORS) {
    const el = document.querySelector(sel)
    if (el) return el
  }
  return null
}

const syncCommentButton = () => {
  const box = document.querySelector('.buttons')
  if (!box) return
  // 没有评论区的页面（如首页）隐藏“去评论”，避免点了没反应
  box.classList.toggle('no-comment', !findComment())
}

const scrollToElement = target => {
  if (!target) return
  const sc = getScroller()
  if (!sc) return
  if (sc === document.scrollingElement) {
    window.scrollTo({
      top: target.getBoundingClientRect().top + window.pageYOffset - 70,
      behavior: 'smooth'
    })
    return
  }
  const top =
    target.getBoundingClientRect().top - sc.getBoundingClientRect().top + sc.scrollTop - 70
  sc.scrollTo({ top: Math.max(top, 0), behavior: 'smooth' })
}

const scrollToTop = () => {
  const sc = getScroller()
  if (!sc) return
  if (sc === document.scrollingElement) window.scrollTo({ top: 0, behavior: 'smooth' })
  else sc.scrollTo({ top: 0, behavior: 'smooth' })
}

function installButtonFix () {
  if (window[BTN_FIX_FLAG]) return
  window[BTN_FIX_FLAG] = true

  // 捕获阶段拦截，阻止主题自身的 window.scrollTo 逻辑
  document.addEventListener(
    'click',
    e => {
      const el =
        e.target instanceof Element
          ? e.target.closest('.buttons .go-to-top, .buttons .go-to-comment')
          : null
      if (!el) return
      e.preventDefault()
      e.stopPropagation()

      if (el.classList.contains('go-to-top')) {
        scrollToTop()
        return
      }

      const comment = findComment()
      if (!comment) return
      scrollToElement(comment)
      // gitalk 异步加载会撑高页面，稍后按需校正一次并聚焦输入框
      setTimeout(() => {
        const sc = getScroller()
        if (sc && sc !== document.scrollingElement) {
          const rect = comment.getBoundingClientRect()
          const box = sc.getBoundingClientRect()
          const visible = rect.top < box.bottom - 120 && rect.bottom > box.top + 70
          if (!visible) scrollToElement(comment)
        }
        const field =
          comment.querySelector('textarea') || comment.querySelector('input')
        if (field) field.focus({ preventScroll: true })
      }, 900)
    },
    true
  )

  const boot = () => {
    syncCommentButton()
    // 评论区（gitalk）是异步渲染的，补几次同步
    setTimeout(syncCommentButton, 800)
    setTimeout(syncCommentButton, 2000)
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot)
  } else {
    boot()
  }
  window.addEventListener('load', boot)
}


// 全站卡片：指针跟随 3D 倾斜（事件委托，只安装一次）
// 仅 hover: hover + 精细指针 + 非 reduced-motion 时生效
const TILT_SELECTOR = '.home-wrapper .banner .feature, .theme-container .card-box, .theme-container .post, .theme-container .column-wrapper, .ps-card'
const TILT_MAX = 6
// 宽卡片按宽度收敛角度时保留一个下限，否则大卡片几乎看不出倾斜
const TILT_MIN = 4.5
// 悬停到卡片中心时也保留基础倾角；否则 --rx 归零会覆盖 CSS 的静态 3D，看起来像失效
const TILT_BASE = 2
const TILT_RESET_DELAY = 90
const TILT_FLAG = '__cardTiltInstalled__'
const TILT_MQ = '(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)'

let tiltMql = null

const getTiltMql = () => {
  if (tiltMql || typeof window === 'undefined' || typeof window.matchMedia !== 'function') return tiltMql
  tiltMql = window.matchMedia(TILT_MQ)
  return tiltMql
}

const tiltAllowed = () => {
  const mql = getTiltMql()
  return !!mql && mql.matches
}

// 从事件目标向上找卡片；微信二维码卡与分页按钮不参与
const resolveTiltCard = target => {
  if (!target || target.nodeType !== 1) return null
  const el = target.closest(TILT_SELECTOR)
  if (!el) return null
  if (el.id === 'home-wechat-card') return null
  if (el.closest('.pagination')) return null
  return el
}

function installCardTilt () {
  if (typeof window === 'undefined' || typeof document === 'undefined') return
  if (window[TILT_FLAG]) return
  window[TILT_FLAG] = true

  const states = new WeakMap()
  const active = new Set()

  const getState = el => {
    let st = states.get(el)
    if (!st) {
      st = { raf: 0, timer: 0, rx: 0, ry: 0, mx: 50, my: 50 }
      states.set(el, st)
    }
    return st
  }

  const paint = el => {
    const st = states.get(el)
    if (!st) return
    st.raf = 0
    el.style.setProperty('--rx', st.rx.toFixed(2) + 'deg')
    el.style.setProperty('--ry', st.ry.toFixed(2) + 'deg')
    el.style.setProperty('--mx', st.mx.toFixed(1) + '%')
    el.style.setProperty('--my', st.my.toFixed(1) + '%')
  }

  const resetCard = el => {
    const st = states.get(el)
    if (st) {
      clearTimeout(st.timer)
      st.timer = 0
      if (st.raf) {
        cancelAnimationFrame(st.raf)
        st.raf = 0
      }
      st.rx = 0
      st.ry = 0
      st.mx = 50
      st.my = 50
    }
    el.classList.remove('is-tilting')
    // 移除内联变量，回落到 CSS 里的静态 3D 角度
    el.style.removeProperty('--rx')
    el.style.removeProperty('--ry')
    el.style.removeProperty('--mx')
    el.style.removeProperty('--my')
    active.delete(el)
  }

  // 滚动后指针与卡片的相对位置已变，统一复位；
  // 用捕获阶段监听，才能收到 .theme-container（局部滚动容器）的 scroll
  const resetAll = () => {
    Array.from(active).forEach(el => {
      if (!el.isConnected) {
        active.delete(el)
        return
      }
      resetCard(el)
    })
  }

  document.addEventListener('pointerover', e => {
    if (!tiltAllowed()) return
    const el = resolveTiltCard(e.target)
    if (!el) return
    const st = getState(el)
    clearTimeout(st.timer)
    st.timer = 0
    el.classList.add('is-tilting')
    active.add(el)
  }, { passive: true })

  document.addEventListener('pointermove', e => {
    if (!tiltAllowed()) return
    const el = resolveTiltCard(e.target)
    if (!el) return
    const st = getState(el)
    clearTimeout(st.timer)
    st.timer = 0
    el.classList.add('is-tilting')
    active.add(el)

    const r = el.getBoundingClientRect()
    if (!r.width || !r.height) return
    const px = (e.clientX - r.left) / r.width
    const py = (e.clientY - r.top) / r.height
    // 大卡按宽度收敛角度，但保留下限，避免宽卡片几乎看不出效果
    const w = el.offsetWidth || r.width
    const maxDeg = Math.max(TILT_MIN, Math.min(TILT_MAX, (TILT_MAX * 360) / w))
    st.rx = Math.max(-8, Math.min(8, TILT_BASE + (0.5 - py) * maxDeg * 2))
    st.ry = (px - 0.5) * maxDeg * 2
    st.mx = px * 100
    st.my = py * 100
    if (!st.raf) st.raf = requestAnimationFrame(() => paint(el))
  }, { passive: true })

  document.addEventListener('pointerout', e => {
    const el = resolveTiltCard(e.target)
    if (!el) return
    // 在卡片内部子元素之间移动不算离开
    const to = e.relatedTarget
    if (to && el.contains(to)) return
    const st = getState(el)
    clearTimeout(st.timer)
    // 卡片旋转后指针可能瞬间落到盒外，延迟复位避免"卡在一个角度"
    st.timer = setTimeout(() => {
      st.timer = 0
      resetCard(el)
    }, TILT_RESET_DELAY)
  }, { passive: true })

  document.addEventListener('scroll', resetAll, { capture: true, passive: true })

  // 媒体条件变化（例如外接鼠标/关闭动画）时立即复位
  const mql = getTiltMql()
  if (mql) {
    const onChange = () => {
      if (!mql.matches) resetAll()
    }
    if (mql.addEventListener) mql.addEventListener('change', onChange)
    else if (mql.addListener) mql.addListener(onChange)
  }
}


// 项目页等 comment:false 的页面偶尔会被评论组件误挂载（插件 afterEach 读到旧 frontmatter），这里兜底清理
const COMMENT_DOM_SELECTORS = ['#vuepress-plugin-comment', '.gt-container']

function installCommentGuard (router) {
  if (window.__commentGuardInstalled__) return
  window.__commentGuardInstalled__ = true

  let allowed = true

  const pageAllowsComment = path => {
    try {
      const app = document.querySelector('#app') && document.querySelector('#app').__vue__
      const pages = (app && app.$site && app.$site.pages) || []
      const page = pages.find(p => p.path === path)
      const fm = page && page.frontmatter
      if (!fm) return true
      return fm.comment !== false && fm.comments !== false
    } catch (e) {
      return true
    }
  }

  const purge = () => {
    if (allowed) return
    COMMENT_DOM_SELECTORS.forEach(sel => {
      document.querySelectorAll(sel).forEach(el => el.remove())
    })
  }

  const observer = new MutationObserver(mutations => {
    if (allowed) return
    mutations.forEach(m => {
      m.addedNodes && m.addedNodes.forEach(node => {
        if (node.nodeType !== 1) return
        const el = node
        if (el.id === 'vuepress-plugin-comment' || el.classList.contains('gt-container')) {
          el.remove()
        } else if (el.querySelector && el.querySelector('#vuepress-plugin-comment, .gt-container')) {
          el.querySelectorAll('#vuepress-plugin-comment, .gt-container').forEach(n => n.remove())
        }
      })
    })
  })

  const start = () => {
    observer.observe(document.body, { childList: true, subtree: true })
  }
  if (document.body) start()
  else document.addEventListener('DOMContentLoaded', start)

  router.afterEach(to => {
    allowed = pageAllowsComment(to.path)
    if (allowed) return
    // 插件自带的 1s 延时与异步渲染，需要多次兜底
    ;[0, 120, 600, 1200, 2200].forEach(ms => setTimeout(purge, ms))
  })
}


// ============================================================
// Artalk 评论：文章页挂载，切换路由时销毁重建
// ============================================================
const ARTALK_SITE = '三木 vlog'
let artalkInstance = null

const pageAllowsComments = path => {
  try {
    const app = document.querySelector('#app') && document.querySelector('#app').__vue__
    const pages = (app && app.$site && app.$site.pages) || []
    if (!pages.length) return null // 数据未就绪，上层重试
    const page = pages.find(p => p.path === path)
    if (!page) return null
    const fm = page.frontmatter
    if (!fm) return null
    return fm.comment !== false && fm.comments !== false && fm.article !== false && fm.home !== true
  } catch (e) {
    return null
  }
}

const artalkMode = () =>
  document.body.classList.contains('theme-mode-light') ? 'light' : 'dark'

const destroyArtalk = () => {
  if (artalkInstance) {
    try {
      artalkInstance.destroy()
    } catch (e) {}
    artalkInstance = null
  }
  const old = document.getElementById('artalk-comments')
  if (old && old.parentNode) old.parentNode.removeChild(old)
}

let artalkMountedPath = null

const mountArtalk = (path, attempt = 0) => {
  const allowed = pageAllowsComments(path)

  if (allowed === false) {
    destroyArtalk()
    artalkMountedPath = null
    syncCommentButton()
    return
  }

  // 数据或页面内容还没渲染好：重试，而不是直接放弃
  if (allowed === null || !document.querySelector('.theme-vdoing-content')) {
    if (attempt < 14) setTimeout(() => mountArtalk(path, attempt + 1), 250)
    return
  }

  const existing = document.getElementById('artalk-comments')
  if (artalkMountedPath === path && existing) return

  destroyArtalk()
  const host = document.querySelector('.theme-vdoing-content')
  if (!host) return
  const el = document.createElement('div')
  el.id = 'artalk-comments'
  host.appendChild(el)
  artalkInstance = new Artalk({
    el: '#artalk-comments',
    server: window.location.origin,
    site: ARTALK_SITE,
    darkMode: artalkMode() === 'dark',
  })
  artalkMountedPath = path
  setTimeout(syncCommentButton, 300)
  setTimeout(syncCommentButton, 1200)
}

const watchArtalkTheme = () => {
  const obs = new MutationObserver(() => {
    if (artalkInstance && typeof artalkInstance.setDarkMode === 'function') {
      artalkInstance.setDarkMode(artalkMode() === 'dark')
    }
  })
  obs.observe(document.body, { attributes: true, attributeFilter: ['class'] })
}

// 首页右侧栏微信二维码卡片（仅首页显示，插入 .main-right 末尾）
const WECHAT_CARD_ID = 'home-wechat-card'

const syncWechatCard = () => {
  if (!document.body) return
  const existing = document.getElementById(WECHAT_CARD_ID)
  const path = window.location.pathname
  const isHome = path === '/' || path === '/index.html'
  if (!isHome) {
    if (existing) existing.remove()
    return
  }
  if (existing) return
  const host = document.querySelector('.main-right')
  if (!host) return
  const card = document.createElement('aside')
  card.id = WECHAT_CARD_ID
  card.className = 'home-wechat card-box'
  card.setAttribute('aria-label', '微信二维码')
  card.innerHTML =
    '<img src="/img/wechat-qr-v3.jpg" alt="三木的微信二维码" loading="lazy">'
  host.appendChild(card)
}

// 首页内容、右侧栏都是异步渲染的，多次兜底挂载
const scheduleWechatCard = () => {
  [0, 150, 500, 1200, 2200].forEach(ms => setTimeout(syncWechatCard, ms))
}

export default ({ router }) => {
  if (typeof window === 'undefined') return
  installButtonFix()
  scheduleWechatCard()
  window.addEventListener('load', scheduleWechatCard)
  router.afterEach(() => scheduleWechatCard())
  installCommentGuard(router)
  installCardTilt()
  watchArtalkTheme()
  mountArtalk(router.currentRoute.path)
  setTimeout(() => mountArtalk(router.currentRoute.path), 800)
  window.addEventListener('load', () => mountArtalk(router.currentRoute.path))
  router.afterEach(to => {
    setTimeout(syncCommentButton, 600)
    setTimeout(syncCommentButton, 2000)
    mountArtalk(to.path)
    setTimeout(() => mountArtalk(to.path), 700)
  })
}
