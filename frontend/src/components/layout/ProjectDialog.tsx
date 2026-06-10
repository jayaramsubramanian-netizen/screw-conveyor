import React, { useState } from 'react'
import type { ProjectMeta } from '../../App'

interface Props {
  meta: ProjectMeta
  setMeta: (m: ProjectMeta) => void
  onClose: () => void
}

export default function ProjectDialog({ meta, setMeta, onClose }: Props) {
  const [local, setLocal] = useState<ProjectMeta>({ ...meta })

  const field = (key: keyof ProjectMeta, label: string, placeholder = '') => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <label style={{
        fontSize: 10, fontWeight: 700, color: '#5d7d99',
        textTransform: 'uppercase', letterSpacing: '0.08em',
      }}>{label}</label>
      <input
        value={local[key]}
        placeholder={placeholder}
        onChange={e => setLocal(p => ({ ...p, [key]: e.target.value }))}
        style={{
          background: '#0b1522', border: '1px solid #2a4a72', borderRadius: 4,
          padding: '6px 10px', color: '#ddeaf6', fontSize: 11,
          fontFamily: 'inherit', outline: 'none', width: '100%', boxSizing: 'border-box',
        }}
      />
    </div>
  )

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,.75)', zIndex: 3000,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
    }}>
      <div style={{
        background: '#101e30', border: '1px solid #2a4a72', borderRadius: 8,
        width: '100%', maxWidth: 560, boxShadow: '0 24px 80px rgba(0,0,0,.8)',
        display: 'flex', flexDirection: 'column',
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '14px 20px', borderBottom: '1px solid #1c3048',
        }}>
          <span style={{ fontSize: 16 }}>📋</span>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 800, fontSize: 13, color: '#ddeaf6' }}>Project Information</div>
            <div style={{ fontSize: 10, color: '#5d7d99', marginTop: 2 }}>
              These fields print on every equipment report
            </div>
          </div>
          <button onClick={onClose} style={{
            padding: '4px 10px', borderRadius: 4, border: '1px solid #1c3048',
            background: 'transparent', color: '#5d7d99', cursor: 'pointer', fontSize: 11,
          }}>✕</button>
        </div>

        {/* Fields */}
        <div style={{
          padding: '18px 20px',
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14,
        }}>
          {field('project',  'Project Name',    'e.g. Cement Plant Expansion')}
          {field('tagNo',    'Equipment Tag',   'e.g. SC-101-A')}
          {field('client',   'Client / Company','e.g. Acme Industries')}
          {field('engineer', 'Engineer',        'e.g. J. Smith')}
          {field('approved', 'Approved By',     'e.g. P. Jones')}
          {field('rev',      'Revision',        'e.g. A')}
          {field('docNo',    'Document No.',    'e.g. VEC-2026-001')}
          {field('site',     'Site / Location', 'e.g. Pune, India')}
        </div>

        {/* Notes */}
        <div style={{ padding: '0 20px 18px' }}>
          <label style={{
            fontSize: 10, fontWeight: 700, color: '#5d7d99',
            textTransform: 'uppercase', letterSpacing: '0.08em',
            display: 'block', marginBottom: 4,
          }}>Design Notes / Scope</label>
          <textarea
            value={local.notes}
            rows={3}
            placeholder="Enter design scope, special conditions, deviations…"
            onChange={e => setLocal(p => ({ ...p, notes: e.target.value }))}
            style={{
              width: '100%', background: '#0b1522', border: '1px solid #2a4a72',
              borderRadius: 4, padding: '6px 10px', color: '#ddeaf6', fontSize: 11,
              fontFamily: 'inherit', outline: 'none', resize: 'vertical',
              boxSizing: 'border-box',
            }}
          />
        </div>

        {/* Actions */}
        <div style={{
          display: 'flex', justifyContent: 'flex-end', gap: 8,
          padding: '12px 20px', borderTop: '1px solid #1c3048',
        }}>
          <button onClick={onClose} style={{
            padding: '7px 20px', borderRadius: 4, border: '1px solid #1c3048',
            background: 'transparent', color: '#5d7d99', cursor: 'pointer', fontSize: 12,
          }}>Cancel</button>
          <button onClick={() => { setMeta(local); onClose() }} style={{
            padding: '7px 24px', borderRadius: 4, border: '1px solid #e8a000',
            background: 'rgba(232,160,0,.12)', color: '#e8a000',
            cursor: 'pointer', fontSize: 12, fontWeight: 700,
          }}>✓ Save to Report</button>
        </div>
      </div>
    </div>
  )
}
