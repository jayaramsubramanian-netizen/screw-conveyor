/**
 * App.tsx — VECTRIX™ application root
 *
 * Layout:
 *   TitleBar (26px) — logo + brand + active module indicator (right side)
 *   MenuBar  (28px) — Windows-style pull-down menus
 *   <main>          — page content (NO second tab bar row)
 *
 * Each process module is an independent page/tab.
 */
import React, { useState, useCallback, useEffect } from 'react'
import TitleBar        from './components/layout/TitleBar'
import MenuBar         from './components/layout/MenuBar'
import ProjectDialog   from './components/layout/ProjectDialog'
import AboutDialog     from './components/layout/AboutDialog'
import ShortcutsDialog from './components/layout/ShortcutsDialog'
import CalcPage        from './components/pages/CalcPage'
import FamilyPage      from './components/pages/FamilyPage'
import MixerPage       from './components/pages/MixerPage'
import DryerPage       from './components/pages/DryerPage'
import CoolerPage      from './components/pages/CoolerPage'
import SeparatorPage   from './components/pages/SeparatorPage'
import ReactorPage     from './components/pages/ReactorPage'
import CompactorPage   from './components/pages/CompactorPage'
import FeederPage     from './components/pages/FeederPage'
import DatabasePage    from './components/pages/DatabasePage'
import ManualPage      from './components/pages/ManualPage'

export type PageId =
  | 'calc' | 'family' | 'feeder'
  | 'mixer' | 'dryer' | 'cooler' | 'separator' | 'reactor' | 'compactor'
  | 'db' | 'help'

export const PAGE_META: Record<PageId, { icon: string; label: string; group: string }> = {
  calc:      { icon: '🔩', label: 'Screw Conveyor Designer',   group: 'conveyor'  },
  family:    { icon: '📊', label: 'Family Designer',           group: 'conveyor'  },
  mixer:     { icon: '🌀', label: 'Screw Mixer',               group: 'process'   },
  dryer:     { icon: '🌡️', label: 'Screw Dryer',               group: 'process'   },
  cooler:    { icon: '❄️', label: 'Screw Cooler',              group: 'process'   },
  separator: { icon: '🔀', label: 'Separator',                  group: 'process'   },
  reactor:   { icon: '⚗️', label: 'Screw Reactor',             group: 'process'   },
  compactor: { icon: '🗜️', label: 'Compactor',                  group: 'process'   },
  feeder:    { icon: '🎚️', label: 'Feeder / Doser',            group: 'process'   },
  db:        { icon: '🗄️', label: 'Material Database',          group: 'reference' },
  help:      { icon: '📘', label: 'User Manual',               group: 'reference' },
}

export interface ProjectMeta {
  project: string; tagNo: string; client: string; engineer: string
  approved: string; rev: string; docNo: string; site: string; notes: string
}

const DEFAULT_META: ProjectMeta = {
  project: '', tagNo: '', client: '', engineer: '',
  approved: '', rev: 'A', docNo: '', site: '', notes: '',
}

export default function App() {
  const [page,          setPage]          = useState<PageId>('calc')
  const [projectMeta,   setProjectMeta]   = useState<ProjectMeta>(DEFAULT_META)
  const [showProject,   setShowProject]   = useState(false)
  const [showAbout,     setShowAbout]     = useState(false)
  const [showShortcuts, setShowShortcuts] = useState(false)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.altKey) {
        const map: Record<string, PageId> = {
          '1': 'calc', '2': 'family', '3': 'mixer', '4': 'dryer',
          '5': 'cooler', '6': 'separator', '7': 'reactor', '8': 'compactor',
          '9': 'db', '0': 'help',
        }
        if (map[e.key]) { e.preventDefault(); setPage(map[e.key]) }
      }
      if (e.key === 'Escape') {
        setShowProject(false); setShowAbout(false); setShowShortcuts(false)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const handleNewProject    = useCallback(() => setShowProject(true),    [])
  const handleShowAbout     = useCallback(() => setShowAbout(true),      [])
  const handleShowShortcuts = useCallback(() => setShowShortcuts(true),  [])

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      background: '#07111e', color: '#ddeaf6',
      fontFamily: "'Barlow', system-ui, sans-serif", overflow: 'hidden',
    }}>
      {/* ── TITLE BAR — includes active module indicator ── */}
      <TitleBar page={page} />

      {/* ── MENU BAR — all navigation here, no second tab row ── */}
      <MenuBar
        page={page}
        setPage={setPage}
        onNewProject={handleNewProject}
        onShowAbout={handleShowAbout}
        onShowShortcuts={handleShowShortcuts}
      />

      {/* ── MAIN CONTENT ── */}
      <main style={{ flex: 1, overflow: 'hidden', position: 'relative', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        {page === 'calc'      && <CalcPage      meta={projectMeta} />}
        {page === 'family'    && <FamilyPage    />}
        {page === 'mixer'     && <MixerPage     />}
        {page === 'dryer'     && <DryerPage     />}
        {page === 'cooler'    && <CoolerPage    />}
        {page === 'separator' && <SeparatorPage />}
        {page === 'reactor'   && <ReactorPage   />}
        {page === 'compactor' && <CompactorPage />}
        {page === 'feeder'    && <FeederPage />}
        {page === 'db'        && <DatabasePage  setPage={setPage} />}
        {page === 'help'      && <ManualPage    />}
      </main>

      {showProject   && <ProjectDialog meta={projectMeta} setMeta={setProjectMeta} onClose={() => setShowProject(false)} />}
      {showAbout     && <AboutDialog     onClose={() => setShowAbout(false)} />}
      {showShortcuts && <ShortcutsDialog onClose={() => setShowShortcuts(false)} />}
    </div>
  )
}
