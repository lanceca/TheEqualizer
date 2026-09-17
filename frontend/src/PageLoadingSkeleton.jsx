import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import { SkeletonBlock } from './Skeleton.jsx'
import './PageLoadingSkeleton.css'

function layoutVariant() {
  if (document.body.classList.contains('staff-shell-body') || document.querySelector('.staff-layout')) return 'staff'
  if (document.querySelector('.public-layout') || document.querySelector('.reader-homepage') || document.querySelector('.reader-article-page')) return 'public'
  return 'generic'
}

function navigatesInCurrentTab(rawUrl) {
  if (!rawUrl) return false
  let url
  try { url = new URL(rawUrl, window.location.href) } catch { return false }
  if (!['http:', 'https:'].includes(url.protocol) || url.origin !== window.location.origin) return false
  if (url.pathname === window.location.pathname && url.search === window.location.search && url.hash) return false
  if (/(^|\/)(download|downloads)(\/|$)/i.test(url.pathname) || /download[-_]/i.test(url.pathname) || /\.pdf$/i.test(url.pathname)) return false
  return true
}

function PublicSkeleton() {
  return <div className="eq-page-public" aria-hidden="true">
    <div className="eq-page-public-header"><SkeletonBlock className="eq-page-logo"/><div className="eq-page-brand"><SkeletonBlock className="eq-page-brand-title"/><SkeletonBlock className="eq-page-brand-sub"/></div><SkeletonBlock className="eq-page-header-pill"/><SkeletonBlock className="eq-page-header-pill"/></div>
    <div className="eq-page-public-nav">{Array.from({length:5},(_,i)=><SkeletonBlock key={i} className="eq-page-nav-pill"/>)}</div>
    <div className="eq-page-reader"><SkeletonBlock className="eq-page-kicker"/><SkeletonBlock className="eq-page-title"/><SkeletonBlock className="eq-page-hero"/><SkeletonBlock className="eq-page-story-title"/><SkeletonBlock className="eq-page-line"/><SkeletonBlock className="eq-page-line short"/><div className="eq-page-story-grid">{Array.from({length:3},(_,i)=><div className="eq-page-story-card" key={i}><SkeletonBlock className="eq-page-card-image"/><SkeletonBlock className="eq-page-card-title"/><SkeletonBlock className="eq-page-line short"/></div>)}</div></div>
  </div>
}
function StaffSkeleton() {
  return (
    <div className="eq-page-staff" aria-hidden="true">
      <section className="eq-page-staff-content">
        <SkeletonBlock className="eq-page-kicker"/>
        <SkeletonBlock className="eq-page-title"/>
        <SkeletonBlock className="eq-page-line"/>

        <div className="eq-page-workflow-list">
          {Array.from(
            { length: 4 },
            (_, i) => (
              <div
                className="eq-page-workflow-card"
                key={i}
              >
                <SkeletonBlock className="eq-page-workflow-thumb"/>

                <div>
                  <SkeletonBlock className="eq-page-chip"/>
                  <SkeletonBlock className="eq-page-card-title"/>
                  <SkeletonBlock className="eq-page-line"/>
                  <SkeletonBlock className="eq-page-line short"/>
                </div>
              </div>
            ),
          )}
        </div>
      </section>
    </div>
  )
}

function staffLoadingRegionStyle() {
  const region =
    document.querySelector(
      '[data-page-loading-region="staff-content"]',
    )
    || document.querySelector('.staff-content')

  if (!region) {
    return null
  }

  const rect = region.getBoundingClientRect()

  const top = Math.max(0, rect.top)
  const left = Math.max(0, rect.left)
  const right = Math.min(
    window.innerWidth,
    rect.right,
  )
  const bottom = Math.min(
    window.innerHeight,
    rect.bottom,
  )

  return {
    top: `${top}px`,
    left: `${left}px`,
    width: `${Math.max(0, right - left)}px`,
    height: `${Math.max(0, bottom - top)}px`,
  }
}
function GenericSkeleton(){return <div className="eq-page-generic" aria-hidden="true"><SkeletonBlock className="eq-page-title"/><SkeletonBlock className="eq-page-line"/><SkeletonBlock className="eq-page-line short"/><SkeletonBlock className="eq-page-generic-panel"/></div>}

export default function PageLoadingSkeleton() {
  const [visible,setVisible]=useState(false)
  const visibleRef=useRef(false)
  const variant=useMemo(layoutVariant,[])
  const hide=useCallback(()=>{visibleRef.current=false;setVisible(false)},[])
  const show=useCallback(()=>{if(visibleRef.current)return;visibleRef.current=true;try{flushSync(()=>setVisible(true))}catch{setVisible(true)}},[])
  useEffect(()=>{
    function onClick(event){if(event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;const link=event.target.closest?.('a[href]');if(!link||link.hasAttribute('download')||link.dataset.noPageLoader==='true'||(link.target&&link.target.toLowerCase()!=='_self')||!navigatesInCurrentTab(link.href))return;show()}
    function onSubmit(event){if(event.defaultPrevented)return;const form=event.target;if(!(form instanceof HTMLFormElement)||form.dataset.noPageLoader==='true'||(form.target&&form.target.toLowerCase()!=='_self')||(form.method||'get').toLowerCase()==='dialog'||!navigatesInCurrentTab(form.action||window.location.href))return;show()}
    document.addEventListener('click',onClick);document.addEventListener('submit',onSubmit);window.addEventListener('pageshow',hide)
    return()=>{document.removeEventListener('click',onClick);document.removeEventListener('submit',onSubmit);window.removeEventListener('pageshow',hide)}
  },[hide,show])
  if (!visible) return null

  const staffRegionStyle =
    variant === 'staff'
      ? staffLoadingRegionStyle()
      : null

  /*
   * Staff pages keep the persistent site header and workspace sidebar
   * visible while navigation is in progress. Only the changing
   * .staff-content region receives a loading skeleton.
   */
  if (variant === 'staff') {
    if (!staffRegionStyle) {
      return null
    }

    return (
      <div
        className="eq-page-overlay is-staff"
        style={staffRegionStyle}
        role="status"
        aria-live="polite"
        aria-label="Loading workspace content"
      >
        <span className="eq-page-sr">
          Loading workspace content…
        </span>

        <StaffSkeleton/>
      </div>
    )
  }

  return (
    <div
      className={`eq-page-overlay is-${variant}`}
      role="status"
      aria-live="polite"
      aria-label="Loading page"
    >
      <span className="eq-page-sr">
        Loading page…
      </span>

      {variant === 'public'
        ? <PublicSkeleton/>
        : <GenericSkeleton/>}
    </div>
  )
}
