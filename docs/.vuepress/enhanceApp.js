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


// 首页卡片：指针跟随 3D 倾斜（仅 hover: hover + 精细指针 + 非 reduced-motion）
const TILT_SELECTOR = '.home-wrapper .banner .feature, .theme-container .card-box, .theme-container .post, .theme-container .column-wrapper, .ps-card'
const TILT_MAX = 6

const tiltAllowed = () =>
  typeof window !== 'undefined' &&
  window.matchMedia('(hover: hover) and (pointer: fine)').matches &&
  !window.matchMedia('(prefers-reduced-motion: reduce)').matches

function bindFeatureTilt () {
  if (!tiltAllowed()) return 0
  let bound = 0
  document.querySelectorAll(TILT_SELECTOR).forEach(el => {
    if (el.__tiltBound) return
    // 微信二维码卡片不参与 3D 倾斜，避免影响扫码与右栏宽度
    if (el.id === 'home-wechat-card') return
    // 分页按钮也带 card-box 类，但不是卡片，跳过
    if (el.closest && el.closest('.pagination')) return
    el.__tiltBound = true
    bound++
    let raf = 0
    let rx = 0
    let ry = 0
    let mx = 50
    let my = 50
    let leaveTimer = 0
    const apply = () => {
      raf = 0
      el.style.setProperty('--rx', rx.toFixed(2) + 'deg')
      el.style.setProperty('--ry', ry.toFixed(2) + 'deg')
      el.style.setProperty('--mx', mx.toFixed(1) + '%')
      el.style.setProperty('--my', my.toFixed(1) + '%')
    }
    const reset = () => {
      if (raf) {
        cancelAnimationFrame(raf)
        raf = 0
      }
      rx = 0
      ry = 0
      // 移除内联变量，回落到 CSS 里的静态 3D 角度
      el.style.removeProperty('--rx')
      el.style.removeProperty('--ry')
      el.style.removeProperty('--mx')
      el.style.removeProperty('--my')
    }
    el.addEventListener('pointerenter', () => {
      clearTimeout(leaveTimer)
      el.classList.add('is-tilting')
    })
    el.addEventListener('pointermove', e => {
      clearTimeout(leaveTimer)
      const r = el.getBoundingClientRect()
      const px = (e.clientX - r.left) / r.width
      const py = (e.clientY - r.top) / r.height
      // 大卡按宽度收敛角度，避免倾斜后指针被"甩出"卡片导致反复重置
      const w = el.offsetWidth || r.width
      const maxDeg = Math.min(TILT_MAX, Math.max(2.5, (TILT_MAX * 360) / w))
      rx = (0.5 - py) * maxDeg * 2
      ry = (px - 0.5) * maxDeg * 2
      mx = px * 100
      my = py * 100
      if (!raf) raf = requestAnimationFrame(apply)
    })
    el.addEventListener('pointerleave', () => {
      // 卡片旋转后指针可能瞬间落到盒外，延迟复位避免"卡在一个角度"
      clearTimeout(leaveTimer)
      leaveTimer = setTimeout(() => {
        el.classList.remove('is-tilting')
        reset()
      }, 90)
    })
    window.addEventListener('scroll', reset, { passive: true })
  })
  return bound
}

function scheduleTiltBinding () {
  [200, 600, 1200].forEach(delay => setTimeout(bindFeatureTilt, delay))
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
    darkMode: artalkMode(),
  })
  artalkMountedPath = path
  setTimeout(syncCommentButton, 300)
  setTimeout(syncCommentButton, 1200)
}

const watchArtalkTheme = () => {
  const obs = new MutationObserver(() => {
    if (artalkInstance && typeof artalkInstance.setDarkMode === 'function') {
      artalkInstance.setDarkMode(artalkMode())
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
    '<img src="/img/wechat-qr.jpg" alt="三木的微信二维码" loading="lazy">' +
    '<p>微信扫码联系我</p>'
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
  scheduleTiltBinding()
  watchArtalkTheme()
  mountArtalk(router.currentRoute.path)
  setTimeout(() => mountArtalk(router.currentRoute.path), 800)
  window.addEventListener('load', () => mountArtalk(router.currentRoute.path))
  window.addEventListener('load', scheduleTiltBinding)
  router.afterEach(to => {
    setTimeout(syncCommentButton, 600)
    setTimeout(syncCommentButton, 2000)
    scheduleTiltBinding()
    mountArtalk(to.path)
    setTimeout(() => mountArtalk(to.path), 700)
  })
}
