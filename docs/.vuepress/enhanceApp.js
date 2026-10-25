// 修复 vdoing 悬浮按钮（返回顶部 / 去评论）在固定滚动容器下的行为
// 站点把滚动交给了 .theme-container（position:fixed + overflow-y:auto），
// 而主题组件用的是 window.scrollTo / window.pageYOffset，所以点击没有反应。
const BTN_FIX_FLAG = '__vdoingButtonsPatched__'
const COMMENT_SELECTORS = ['#vuepress-plugin-comment', '#valine-vuepress-comment', '.vssue']

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
      setTimeout(() => {
        const field = comment.querySelector('textarea, input')
        if (field) field.focus({ preventScroll: true })
      }, 650)
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

export default ({ router }) => {
  if (typeof window === 'undefined') return
  installButtonFix()
  router.afterEach(() => {
    setTimeout(syncCommentButton, 600)
    setTimeout(syncCommentButton, 2000)
  })
}
