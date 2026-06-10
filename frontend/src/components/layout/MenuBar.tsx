/**
 * MenuBar.tsx — Windows-style pull-down menu bar.
 * All navigation lives here. No second tab row anywhere.
 * Active page highlighted in the menu labels.
 */
import React, { useState, useRef, useEffect } from 'react'
import type { PageId } from '../../App'
import { PAGE_META } from '../../App'

interface Props {
  page: PageId
  setPage: (p: PageId) => void
  onNewProject: () => void
  onShowAbout: () => void
  onShowShortcuts: () => void
}

export default function MenuBar({ page, setPage, onNewProject, onShowAbout, onShowShortcuts }: Props) {
  const [open, setOpen] = useState<string | null>(null)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(null)
    }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])

  const toggle = (id: string) => setOpen(o => o === id ? null : id)
  const close  = () => setOpen(null)

  // Styled menu item button
  const Item = ({
    pageId, label, action, disabled = false,
  }: {
    pageId?: PageId; label: string; action: () => void; disabled?: boolean
  }) => {
    const isActive = pageId !== undefined && page === pageId
    return (
      <button
        disabled={disabled}
        onClick={() => { action(); close() }}
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          width: '100%', textAlign: 'left',
          padding: '5px 16px', background: isActive ? 'rgba(232,160,0,0.10)' : 'transparent',
          border: 'none', fontSize: 12, cursor: disabled ? 'default' : 'pointer',
          fontFamily: 'inherit', whiteSpace: 'nowrap',
          color: disabled ? '#3a5470' : isActive ? '#e8a000' : '#ddeaf6',
          borderLeft: isActive ? '2px solid #e8a000' : '2px solid transparent',
        }}
        onMouseOver={e => { if (!disabled) (e.currentTarget as HTMLElement).style.background = '#17304d' }}
        onMouseOut={e => {
          (e.currentTarget as HTMLElement).style.background = isActive ? 'rgba(232,160,0,0.10)' : 'transparent'
        }}
      >
        {pageId && <span style={{ fontSize: 12, width: 16 }}>{PAGE_META[pageId].icon}</span>}
        <span>{label}</span>
        {isActive && <span style={{ marginLeft: 'auto', fontSize: 9, color: '#e8a000', paddingLeft: 12 }}>●</span>}
      </button>
    )
  }

  const Div = () => <div style={{ height: 1, background: '#1c3048', margin: '3px 0' }} />

  const Menu = ({ id, label, children }: { id: string; label: string; children: React.ReactNode }) => (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => toggle(id)}
        style={{
          padding: '3px 10px',
          background: open === id ? '#17304d' : 'transparent',
          border: 'none', color: '#ddeaf6', fontSize: 12,
          cursor: 'pointer', fontFamily: 'inherit', borderRadius: 2,
        }}
        onMouseOver={() => { if (open && open !== id) setOpen(id) }}
      >{label}</button>
      {open === id && (
        <div className="dropdown" style={{
          position: 'absolute', top: '100%', left: 0, minWidth: 240,
          zIndex: 2000,
          borderRadius: 4, padding: '4px 0',
        }}>
          {children}
        </div>
      )}
    </div>
  )

  return (
    <div ref={ref} className="vx-menubar" style={{
      display: 'flex', alignItems: 'center', gap: 2,
      padding: '2px 8px', flexShrink: 0, height: 28,
    }}>

      {/* FILE */}
      <Menu id="file" label="File">
        <Item label="New Design / Project…" action={onNewProject} />
        <Item label="Clear &amp; Reload"    action={() => { if (confirm('Clear and reload?')) window.location.reload() }} />
        <Div />
        <Item label="Print Report…"         action={() => window.print()} />
        <Div />
        <Item label="Close"                 action={() => { if (confirm('Close?')) window.close() }} />
      </Menu>

      {/* VIEW — Conveyor */}
      <Menu id="conveyor" label="Conveyor">
        <Item pageId="calc"   label="Screw Conveyor Calculator" action={() => setPage('calc')} />
        <Item pageId="family" label="Family Designer"           action={() => setPage('family')} />
      </Menu>

      {/* VIEW — Process */}
      <Menu id="process" label="Process">
        <Item pageId="mixer"     label="Screw Mixer"     action={() => setPage('mixer')} />
        <Item pageId="dryer"     label="Screw Dryer"     action={() => setPage('dryer')} />
        <Item pageId="cooler"    label="Screw Cooler"    action={() => setPage('cooler')} />
        <Item pageId="separator" label="Separator"       action={() => setPage('separator')} />
        <Item pageId="reactor"   label="Screw Reactor"   action={() => setPage('reactor')} />
        <Item pageId="compactor" label="Compactor"       action={() => setPage('compactor')} />
        <Item pageId="feeder"    label="Feeder / Doser"  action={() => setPage('feeder')} />
      </Menu>

      {/* DATABASE */}
      <Menu id="data" label="Database">
        <Item pageId="db"   label="Material Database" action={() => setPage('db')} />
        <Item pageId="help" label="User Manual"       action={() => setPage('help')} />
      </Menu>

      {/* HELP */}
      <Menu id="help" label="Help">
        <Item label="Keyboard Shortcuts" action={onShowShortcuts} />
        <Div />
        <Item label="About VECTRIX™"     action={onShowAbout} />
      </Menu>
    </div>
  )
}
