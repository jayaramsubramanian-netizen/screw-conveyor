/**
 * TitleBar.tsx
 * Top strip (26px). Shows:
 *   Left:  VECTRIX™ logo + brand
 *   Centre: active module name with icon (replaces the old second tab row)
 *   Right: v2.5.0
 */
import React from 'react'
import type { PageId } from '../../App'
import { PAGE_META } from '../../App'

function VectrixLogo() {
  return (
    <svg width="20" height="20" viewBox="0 0 22 22" fill="none" style={{ flexShrink: 0 }}>
      <circle cx="11" cy="11" r="10" stroke="#e8a000" strokeWidth="1.5" fill="none"/>
      <path d="M5 11 L11 5 L17 11 L11 17 Z" fill="#e8a000" fillOpacity="0.15" stroke="#e8a000" strokeWidth="1.2"/>
      <circle cx="11" cy="11" r="3.5" fill="#e8a000"/>
      {[[-10,0],[10,0],[0,-10],[0,10]].map(([dx,dy],i) => (
        <line key={i} x1={11} y1={11} x2={11+dx!} y2={11+dy!}
          stroke="#e8a000" strokeWidth="1.2" opacity="0.6"/>
      ))}
    </svg>
  )
}

interface Props { page: PageId }

export default function TitleBar({ page }: Props) {
  const meta = PAGE_META[page]

  return (
    <div className="vx-titlebar" style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '0 12px', flexShrink: 0, height: 26, userSelect: 'none',
    }}>
      {/* Left: brand */}
      <VectrixLogo />
      <span style={{ fontSize: 11, fontWeight: 800, color: '#c8192e', letterSpacing: '0.10em', fontFamily: "'Barlow Condensed',sans-serif" }}>
        VECTRIX™
      </span>
      <span style={{ color: '#5a7080', fontSize: 11, flexShrink: 0 }}>|</span>
      <span style={{ fontSize: 10, color: '#3a4850', letterSpacing: '0.08em', flexShrink: 0, fontFamily: "'Barlow',sans-serif", fontWeight: 500 }}>
        A Jayveecons Engineering Platform
      </span>

      <div style={{ flex: 1 }} />

      {/* Centre-right: active module indicator */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        background: 'rgba(200,25,46,0.12)', border: '1px solid rgba(200,25,46,0.35)',
        borderRadius: 4, padding: '0 10px', height: 18,
      }}>
        <span style={{ fontSize: 11 }}>{meta.icon}</span>
        <span style={{ fontSize: 10, fontWeight: 700, color: '#c8192e', letterSpacing: '0.08em', fontFamily: "'Barlow Condensed',sans-serif" }}>
          {meta.label}
        </span>
      </div>

      <div style={{ width: 16 }} />
      <span style={{ fontSize: 9, color: '#3a4850', letterSpacing: '0.10em', flexShrink: 0, fontFamily: "'Barlow Condensed',sans-serif", fontWeight: 600 }}>
        v2.5.0
      </span>
    </div>
  )
}
