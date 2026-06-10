import React from 'react'

const SHORTCUTS = [
  ['Alt+1', 'Calculator'],
  ['Alt+2', 'Family Designer'],
  ['Alt+3', 'Process Modules'],
  ['Alt+4', 'Database'],
  ['Alt+5', 'User Manual'],
  ['Escape', 'Close dialogs'],
]

export default function ShortcutsDialog({ onClose }: { onClose: () => void }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,.7)', zIndex: 3000,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{
        background: '#101e30', border: '1px solid #2a4a72', borderRadius: 8,
        padding: '24px 32px', minWidth: 320, boxShadow: '0 16px 64px rgba(0,0,0,.8)',
      }}>
        <div style={{ fontSize: 13, fontWeight: 800, color: '#ddeaf6', marginBottom: 16 }}>
          Keyboard Shortcuts
        </div>
        {SHORTCUTS.map(([k, d]) => (
          <div key={k} style={{
            display: 'flex', justifyContent: 'space-between',
            padding: '5px 0', borderBottom: '1px solid #1c3048', gap: 24,
          }}>
            <code style={{
              fontSize: 11, color: '#e8a000', background: 'rgba(232,160,0,.08)',
              padding: '1px 6px', borderRadius: 3, border: '1px solid rgba(232,160,0,.2)',
            }}>{k}</code>
            <span style={{ fontSize: 11, color: '#5d7d99' }}>{d}</span>
          </div>
        ))}
        <button onClick={onClose} style={{
          marginTop: 16, padding: '5px 20px', borderRadius: 4,
          background: 'rgba(74,158,255,.1)', border: '1px solid #4a9eff',
          color: '#4a9eff', cursor: 'pointer', fontSize: 11, fontWeight: 700,
        }}>Close</button>
      </div>
    </div>
  )
}
