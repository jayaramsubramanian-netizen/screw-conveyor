import React from 'react'
import type { PageId } from '../../App'

const TABS: { id: PageId; icon: string; label: string }[] = [
  { id: 'calc',    icon: '🔩', label: 'Calculator'  },
  { id: 'family',  icon: '📊', label: 'Family'      },
  { id: 'process', icon: '⚙️', label: 'Process'     },
  { id: 'db',      icon: '🗄️', label: 'Database'    },
  { id: 'help',    icon: '📘', label: 'Manual'      },
]

interface Props { page: PageId; setPage: (p: PageId) => void }

export default function ModuleTabBar({ page, setPage }: Props) {
  return (
    <div style={{
      display: 'flex', alignItems: 'stretch',
      background: '#081321', borderBottom: '1px solid #1c3048',
      flexShrink: 0, height: 34,
    }}>
      {TABS.map(t => {
        const active = page === t.id
        return (
          <button key={t.id} onClick={() => setPage(t.id)} style={{
            display: 'flex', alignItems: 'center', gap: 5,
            padding: '0 16px', border: 'none',
            background: active ? '#101e30' : 'transparent',
            borderBottom: active ? '2px solid #e8a000' : '2px solid transparent',
            borderRight: '1px solid #0d1e30',
            color: active ? '#e8a000' : '#5d7d99',
            fontWeight: active ? 800 : 600, fontSize: 11,
            cursor: 'pointer', letterSpacing: '0.04em', whiteSpace: 'nowrap',
            fontFamily: 'inherit',
          }}>
            <span style={{ fontSize: 13 }}>{t.icon}</span>
            <span>{t.label}</span>
          </button>
        )
      })}
    </div>
  )
}
