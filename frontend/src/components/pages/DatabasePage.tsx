/**
 * DatabasePage.tsx — Full 6-tab database with CRUD on every table.
 *
 * Tabs: Materials | Process Apps | Gearboxes | Motors | Drives | Costs
 *
 * KEY FEATURE: Applications column on Materials shows module coverage.
 * Each app badge is GREEN if the material has the required fields for that module,
 * AMBER if partial, RED/grey if missing critical fields.
 * This tells the user which modules will work for this material,
 * and which need the material record to be completed first.
 */
import React, { useState } from 'react'
import axios from 'axios'
import { useQueryClient, useQuery } from '@tanstack/react-query'
import { useMaterials, useCategories, useBearings, useGearboxes, useCalcStore } from '../../hooks/useCalculator'
import type { MaterialOut, BearingOut, GearboxOut } from '../../types/api'
import type { PageId } from '../../App'

const C = {
  panel: '#0d1c2e', border: '#162438', text: '#ddeaf6',
  muted: '#5d7d99', faint: '#3a5470', accent: '#c8192e',
  green: '#1fb86e', red: '#e05252', amber: '#d98e00', blue: '#4a9eff',
  teal: '#2dd4bf', purple: '#a78bfa',
}

const ss = (s: React.CSSProperties): React.CSSProperties => s

// ── Application module definitions and required fields ────────────
const APP_DEFS: Record<string, {
  label: string; icon: string; col: string
  required: (keyof MaterialOut)[]; recommended: (keyof MaterialOut)[]
}> = {
  conv:    { label: 'Conveyor',     icon: '🔩', col: C.blue,
             required: ['rho','fill_max','lambda_ref'],
             recommended: ['flowability','abr','cls','moist'] },
  dry:     { label: 'Dryer',        icon: '🌡️', col: '#c8192e',
             required: ['rho','moist','temp_max'],
             recommended: ['fill_max','flowability'] },
  cool:    { label: 'Cooler',       icon: '❄️', col: C.teal,
             required: ['rho','temp_max'],
             recommended: ['fill_max'] },
  mix:     { label: 'Mixer',        icon: '🌀', col: C.purple,
             required: ['rho','fill_max'],
             recommended: ['flowability','particle_class'] },
  sep:     { label: 'Separator',    icon: '🔀', col: C.green,
             required: ['rho','particle_class'],
             recommended: ['flowability'] },
  react:   { label: 'Reactor',      icon: '⚗️', col: '#a78bfa',
             required: ['rho','temp_max'],
             recommended: ['fill_max','flowability'] },
  compact: { label: 'Compactor',    icon: '🗜️', col: C.red,
             required: ['rho','bridging_risk'],
             recommended: ['fill_max','flowability'] },
  feed:    { label: 'Feeder',       icon: '⚖️', col: '#d98e00',
             required: ['rho','fill_max','flowability'],
             recommended: ['bridging_risk','cohesion'] },
}

function AppCoverage({ mat }: { mat: MaterialOut }) {
  const apps: string[] = (mat.app as any) || []
  if (apps.length === 0) return <span style={ss({ color: C.faint, fontSize: 9 })}>—</span>

  return (
    <div style={ss({ display: 'flex', flexWrap: 'wrap', gap: 2 })}>
      {apps.map(appId => {
        const def = APP_DEFS[appId]
        if (!def) return null
        const missingReq  = def.required.filter(f => mat[f] == null || mat[f] === '')
        const missingRec  = def.recommended.filter(f => mat[f] == null || mat[f] === '')
        const status = missingReq.length > 0 ? 'missing' : missingRec.length > 0 ? 'partial' : 'ok'
        const bgCol = status === 'ok' ? def.col + '22'
                    : status === 'partial' ? C.amber + '22'
                    : C.red + '22'
        const borderCol = status === 'ok' ? def.col + '88'
                        : status === 'partial' ? C.amber + '88'
                        : C.red + '88'
        const textCol = status === 'ok' ? def.col
                      : status === 'partial' ? C.amber
                      : C.red

        const tooltip = status === 'ok'
          ? `${def.label}: all required fields present`
          : status === 'partial'
          ? `${def.label}: recommended fields missing: ${missingRec.join(', ')}`
          : `${def.label}: REQUIRED fields missing: ${missingReq.join(', ')}`

        return (
          <span key={appId} title={tooltip} style={ss({
            display: 'inline-flex', alignItems: 'center', gap: 2,
            padding: '1px 5px', borderRadius: 3, fontSize: 9, fontWeight: 700,
            background: bgCol, border: `1px solid ${borderCol}`, color: textCol,
            cursor: 'default', whiteSpace: 'nowrap',
          })}>
            {def.icon} {def.label}
            {status === 'missing' && <span style={ss({ fontSize: 8 })}>⚠</span>}
          </span>
        )
      })}
    </div>
  )
}

// ── Flags column ──────────────────────────────────────────────────
const FLAG_META: Record<string, { label: string; col: string }> = {
  L: { label: 'Lumpy',     col: C.amber  },
  M: { label: 'Moist',     col: C.blue   },
  O: { label: 'Oily',      col: '#d98e00' },
  U: { label: 'Dusty',     col: C.purple },
  X: { label: 'Explosive', col: C.red    },
}

function FlagsCell({ flags }: { flags?: string | null }) {
  if (!flags) return <span style={ss({ color: C.faint, fontSize: 9 })}>—</span>
  return (
    <div style={ss({ display: 'flex', gap: 2 })}>
      {flags.split('').map(f => {
        const meta = FLAG_META[f]
        return meta ? (
          <span key={f} title={meta.label} style={ss({
            display: 'inline-block', padding: '1px 4px', borderRadius: 3,
            fontSize: 9, fontWeight: 800, background: meta.col + '22',
            border: `1px solid ${meta.col}55`, color: meta.col,
          })}>{f}</span>
        ) : null
      })}
    </div>
  )
}

// ── Shared form field ─────────────────────────────────────────────
function FInput({ label, value, onChange, type = 'text', step, placeholder }: {
  label: string; value: string | number; onChange: (v: string) => void
  type?: string; step?: string; placeholder?: string
}) {
  return (
    <div style={ss({ marginBottom: 8 })}>
      <div style={ss({ fontSize: 10, color: C.muted, fontWeight: 700,
        textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 3 })}>{label}</div>
      <input type={type} value={value} step={step} placeholder={placeholder}
        onChange={e => onChange(e.target.value)}
        style={ss({ width: '100%', background: '#081321', border: `1px solid ${C.border}`,
          borderRadius: 4, padding: '5px 8px', color: C.text, fontSize: 11,
          fontFamily: type === 'number' ? 'monospace' : 'inherit',
          outline: 'none', boxSizing: 'border-box' })} />
    </div>
  )
}

function FSelect({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void; options: string[]
}) {
  return (
    <div style={ss({ marginBottom: 8 })}>
      <div style={ss({ fontSize: 10, color: C.muted, fontWeight: 700,
        textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 3 })}>{label}</div>
      <select value={value} onChange={e => onChange(e.target.value)}
        style={ss({ width: '100%', background: '#081321', border: `1px solid ${C.border}`,
          borderRadius: 4, padding: '5px 8px', color: C.text, fontSize: 11,
          fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box' })}>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  )
}

// ── Generic modal wrapper ─────────────────────────────────────────
function Modal({ title, icon, onClose, onSave, saving, error, children }: {
  title: string; icon: string; onClose: () => void; onSave: () => void
  saving: boolean; error: string; children: React.ReactNode
}) {
  return (
    <div style={ss({ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.75)',
      zIndex: 3000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 })}>
      <div style={ss({ background: C.panel, border: '1px solid #2a4a72', borderRadius: 8,
        width: '100%', maxWidth: 620, maxHeight: '90vh', display: 'flex', flexDirection: 'column',
        boxShadow: '0 24px 80px rgba(0,0,0,.8)' })}>
        <div style={ss({ display: 'flex', alignItems: 'center', gap: 10,
          padding: '14px 20px', borderBottom: `1px solid ${C.border}` })}>
          <span style={ss({ fontSize: 16 })}>{icon}</span>
          <span style={ss({ fontWeight: 800, fontSize: 13, color: C.text, flex: 1 })}>{title}</span>
          <button onClick={onClose} style={ss({ padding: '4px 10px', borderRadius: 4,
            border: `1px solid ${C.border}`, background: 'transparent',
            color: C.muted, cursor: 'pointer', fontSize: 11 })}>✕</button>
        </div>
        <div style={ss({ overflowY: 'auto', padding: '16px 20px',
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' })}>
          {children}
        </div>
        {error && (
          <div style={ss({ margin: '0 20px', padding: '5px 10px', fontSize: 11,
            color: C.red, background: 'rgba(224,82,82,.08)', borderRadius: 4 })}>{error}</div>
        )}
        <div style={ss({ display: 'flex', justifyContent: 'flex-end', gap: 8,
          padding: '12px 20px', borderTop: `1px solid ${C.border}` })}>
          <button onClick={onClose} style={ss({ padding: '7px 20px', borderRadius: 4,
            border: `1px solid ${C.border}`, background: 'transparent',
            color: C.muted, cursor: 'pointer', fontSize: 12 })}>Cancel</button>
          <button onClick={onSave} disabled={saving} style={ss({ padding: '7px 24px', borderRadius: 4,
            border: `1px solid ${C.accent}`, background: 'rgba(232,160,0,.12)',
            color: C.accent, cursor: 'pointer', fontSize: 12, fontWeight: 700 })}>
            {saving ? 'Saving…' : '✓ Save'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Delete confirm ────────────────────────────────────────────────
function DeleteConfirm({ name, onConfirm, onCancel }: {
  name: string; onConfirm: () => void; onCancel: () => void
}) {
  return (
    <div style={ss({ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.7)',
      zIndex: 3000, display: 'flex', alignItems: 'center', justifyContent: 'center' })}>
      <div style={ss({ background: C.panel, border: '1px solid #2a4a72', borderRadius: 8,
        padding: '24px 32px', minWidth: 340, boxShadow: '0 16px 64px rgba(0,0,0,.8)' })}>
        <div style={ss({ fontSize: 13, fontWeight: 800, color: C.text, marginBottom: 8 })}>Confirm Delete</div>
        <div style={ss({ fontSize: 11, color: C.muted, marginBottom: 20 })}>
          Remove <strong style={ss({ color: C.text })}>{name}</strong>? This cannot be undone.
        </div>
        <div style={ss({ display: 'flex', gap: 8, justifyContent: 'flex-end' })}>
          <button onClick={onCancel} style={ss({ padding: '6px 20px', borderRadius: 4,
            border: `1px solid ${C.border}`, background: 'transparent',
            color: C.muted, cursor: 'pointer', fontSize: 12 })}>Cancel</button>
          <button onClick={onConfirm} style={ss({ padding: '6px 20px', borderRadius: 4,
            border: `1px solid ${C.red}`, background: 'rgba(224,82,82,.12)',
            color: C.red, cursor: 'pointer', fontSize: 12, fontWeight: 700 })}>Delete</button>
        </div>
      </div>
    </div>
  )
}

// ── Table header ──────────────────────────────────────────────────
function TH({ children }: { children: React.ReactNode }) {
  return <th style={ss({ padding: '6px 10px', textAlign: 'left', color: C.muted,
    fontWeight: 700, borderBottom: `1px solid ${C.border}`, whiteSpace: 'nowrap',
    fontSize: 11, background: '#081321' })}>{children}</th>
}
function TD({ children, mono = false, faint = false }: {
  children: React.ReactNode; mono?: boolean; faint?: boolean
}) {
  return <td style={ss({ padding: '5px 10px', fontFamily: mono ? 'monospace' : 'inherit',
    color: faint ? C.faint : C.text, fontSize: 11 })}>{children}</td>
}
function CustomBadge() {
  return <span style={ss({ marginLeft: 5, fontSize: 8, color: C.blue,
    background: 'rgba(74,158,255,.12)', border: '1px solid rgba(74,158,255,.3)',
    borderRadius: 3, padding: '1px 4px' })}>CUSTOM</span>
}
function ActionBtns({ isCustom, onEdit, onDelete }: {
  isCustom: boolean; onEdit: () => void; onDelete?: () => void
}) {
  return (
    <div style={ss({ display: 'flex', gap: 4 })}>
      <button onClick={onEdit} style={ss({ fontSize: 9, padding: '2px 7px', borderRadius: 3,
        border: `1px solid ${C.blue}`, background: 'transparent',
        color: C.blue, cursor: 'pointer' })}>✏️ Edit</button>
      {isCustom && onDelete && (
        <button onClick={onDelete} style={ss({ fontSize: 9, padding: '2px 7px', borderRadius: 3,
          border: `1px solid ${C.red}`, background: 'transparent',
          color: C.red, cursor: 'pointer' })}>🗑</button>
      )}
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════
// MATERIAL FORM
// ═════════════════════════════════════════════════════════════════
const EMPTY_MAT = {
  name: '', category: '', rho: '', rho_min: '', rho_max: '',
  lambda_ref: '', fill_max: '', abr: 'Low', cls: 'I',
  particle_class: 'B6', flowability: '2',
  moist: '', aor: '', cohesion: '', temp_max: '', bridging_risk: '',
  flags: '', note: '',
  app: [] as string[],
}

function MaterialFormModal({ initial, onSave, onClose, title }: {
  initial?: Partial<typeof EMPTY_MAT & { app: string[] }>
  onSave: (d: any) => Promise<void>; onClose: () => void; title: string
}) {
  const [form, setForm] = useState({ ...EMPTY_MAT, ...(initial || {}) })
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')
  const set = (k: string) => (v: string) => setForm(p => ({ ...p, [k]: v }))
  const toggleApp = (id: string) => setForm(p => ({
    ...p,
    app: p.app.includes(id) ? p.app.filter(a => a !== id) : [...p.app, id],
  }))

  const handleSave = async () => {
    if (!form.name) { setErr('Name is required'); return }
    setSaving(true); setErr('')
    try {
      await onSave({
        name: form.name, category: form.category || null,
        rho: parseFloat(form.rho) || 1.0,
        rho_min: parseFloat(form.rho_min) || null,
        rho_max: parseFloat(form.rho_max) || null,
        lambda_ref: parseFloat(form.lambda_ref) || null,
        fill_max: parseFloat(form.fill_max) || 0.30,
        abr: form.abr, cls: form.cls,
        particle_class: form.particle_class || null,
        flowability: parseInt(form.flowability) || null,
        moist: parseFloat(form.moist) || 0,
        aor: parseFloat(form.aor) || null,
        cohesion: parseFloat(form.cohesion) || null,
        temp_max: parseFloat(form.temp_max) || null,
        bridging_risk: parseFloat(form.bridging_risk) || null,
        flags: form.flags || null,
        app: form.app,
        note: form.note || null,
      })
    } catch (e: any) { setErr(e?.response?.data?.detail || e?.message || 'Save failed') }
    finally { setSaving(false) }
  }

  return (
    <Modal title={title} icon="🧪" onClose={onClose} onSave={handleSave} saving={saving} error={err}>
      <div style={ss({ gridColumn: '1/-1', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' })}>
        <FInput label="Name *"              value={form.name}         onChange={set('name')} />
        <FInput label="Category"            value={form.category}     onChange={set('category')} />
        <FInput label="Bulk Density ρ (t/m³)" value={form.rho}       onChange={set('rho')}         type="number" step="0.01" />
        <FInput label="ρ_min"               value={form.rho_min}      onChange={set('rho_min')}     type="number" step="0.01" />
        <FInput label="ρ_max"               value={form.rho_max}      onChange={set('rho_max')}     type="number" step="0.01" />
        <FInput label="λ_ref"               value={form.lambda_ref}   onChange={set('lambda_ref')}  type="number" step="0.01" />
        <FInput label="Fill max"            value={form.fill_max}     onChange={set('fill_max')}    type="number" step="0.01" />
        <FInput label="Moisture %"          value={form.moist}        onChange={set('moist')}       type="number" step="0.1" />
        <FInput label="Angle of Repose °"   value={form.aor}          onChange={set('aor')}         type="number" step="1" />
        <FInput label="Cohesion (kPa)"      value={form.cohesion}     onChange={set('cohesion')}    type="number" step="0.1" />
        <FInput label="Max Temp °C"         value={form.temp_max}     onChange={set('temp_max')}    type="number" step="5" />
        <FInput label="Bridging Risk (0–1)" value={form.bridging_risk} onChange={set('bridging_risk')} type="number" step="0.05" />
        <FInput label="Flags (e.g. OUX)"    value={form.flags}        onChange={set('flags')} />
        <FInput label="Note"                value={form.note}         onChange={set('note')} />
        <FSelect label="Abrasiveness" value={form.abr}           onChange={set('abr')}
          options={['Low','Medium','High','Very High']} />
        <FSelect label="CEMA Class"   value={form.cls}           onChange={set('cls')}
          options={['I','II','III','IV']} />
        <FSelect label="Particle Class" value={form.particle_class} onChange={set('particle_class')}
          options={['A200','A100','A40','B6','C1/2','D3','D7']} />
        <FSelect label="Flowability"   value={form.flowability}  onChange={set('flowability')}
          options={['1','2','3','4']} />
        {/* Applications */}
        <div style={ss({ gridColumn: '1/-1', marginBottom: 8 })}>
          <div style={ss({ fontSize: 10, color: C.muted, fontWeight: 700,
            textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 })}>
            Applications (tick modules this material is validated for)
          </div>
          <div style={ss({ display: 'flex', flexWrap: 'wrap', gap: 6 })}>
            {Object.entries(APP_DEFS).map(([id, def]) => {
              const active = form.app.includes(id)
              return (
                <button key={id} onClick={() => toggleApp(id)} type="button" style={ss({
                  padding: '4px 10px', borderRadius: 4, cursor: 'pointer', fontSize: 10,
                  fontFamily: 'inherit', fontWeight: 700,
                  border: `1px solid ${active ? def.col : C.border}`,
                  background: active ? def.col + '22' : 'transparent',
                  color: active ? def.col : C.muted,
                })}>{def.icon} {def.label}</button>
              )
            })}
          </div>
        </div>
      </div>
    </Modal>
  )
}

// ═════════════════════════════════════════════════════════════════
// MAIN DATABASE PAGE
// ═════════════════════════════════════════════════════════════════
type Tab = 'materials' | 'process' | 'gearboxes' | 'motors' | 'drives' | 'costs'

interface Props { setPage: (p: PageId) => void }

export default function DatabasePage({ setPage }: Props) {
  const [tab,        setTab]        = useState<Tab>('materials')
  const [search,     setSearch]     = useState('')
  const [cat,        setCat]        = useState('')
  const [modal,      setModal]      = useState<{ mode: 'add' | 'edit'; row?: any } | null>(null)
  const [delTarget,  setDelTarget]  = useState<string | null>(null)
  const [msg,        setMsg]        = useState<{ text: string; ok: boolean } | null>(null)

  const { data: cats }     = useCategories()
  const { data: mats,     isLoading: mL } = useMaterials({ search: search||undefined, category: cat||undefined })
  const { data: bearings, isLoading: bL } = useBearings()
  const { data: gearboxes,isLoading: gL } = useGearboxes()
  const { data: motors,   isLoading: moL } = useQuery({ queryKey: ['motors'],   queryFn: () => axios.get('/api/v1/motors').then(r=>r.data),   staleTime: 60000 })
  const { data: drives,   isLoading: dL  } = useQuery({ queryKey: ['drives'],   queryFn: () => axios.get('/api/v1/drives').then(r=>r.data),   staleTime: 60000 })
  const { data: costs,    isLoading: cL  } = useQuery({ queryKey: ['costs'],    queryFn: () => axios.get('/api/v1/costs').then(r=>r.data),    staleTime: 60000 })
  const { setInp } = useCalcStore()
  const qc = useQueryClient()

  const flash = (text: string, ok = true) => { setMsg({ text, ok }); setTimeout(()=>setMsg(null), 3500) }
  const inv = (key: string) => qc.invalidateQueries({ queryKey: [key] })

  // ── Generic save dispatcher ────────────────────────────────────
  const handleSave = async (data: any) => {
    const isEdit = modal?.mode === 'edit'
    try {
      if (tab === 'materials') {
        if (isEdit) await axios.put(`/api/v1/materials/${encodeURIComponent(modal!.row.name)}`, data)
        else        await axios.post('/api/v1/materials', data)
        inv('materials')
      } else if (tab === 'gearboxes') {
        if (isEdit) await axios.put(`/api/v1/gearboxes/${encodeURIComponent(modal!.row.model)}`, data)
        else        await axios.post('/api/v1/gearboxes', data)
        inv('gearboxes')
      } else if (tab === 'motors') {
        if (isEdit) await axios.put(`/api/v1/motors/${encodeURIComponent(modal!.row.model)}`, data)
        else        await axios.post('/api/v1/motors', data)
        inv('motors')
      } else if (tab === 'drives') {
        if (isEdit) await axios.put(`/api/v1/drives/${encodeURIComponent(modal!.row.model)}`, data)
        else        await axios.post('/api/v1/drives', data)
        inv('drives')
      } else if (tab === 'costs') {
        if (isEdit) await axios.put(`/api/v1/costs/${encodeURIComponent(modal!.row.item)}`, data)
        else        await axios.post('/api/v1/costs', data)
        inv('costs')
      } else if (tab === 'process' || tab === 'materials') {
        // bearings (shown in process tab)
        if (isEdit) await axios.put(`/api/v1/bearings/${encodeURIComponent(modal!.row.name)}`, data)
        else        await axios.post('/api/v1/bearings', data)
        inv('bearings')
      }
      flash(`✓ ${isEdit ? 'Updated' : 'Added'} successfully`)
      setModal(null)
    } catch (e: any) {
      throw new Error(e?.response?.data?.detail || e?.message || 'Save failed')
    }
  }

  // ── Generic delete dispatcher ──────────────────────────────────
  const handleDelete = async () => {
    if (!delTarget) return
    try {
      if (tab === 'materials')  await axios.delete(`/api/v1/materials/${encodeURIComponent(delTarget)}`)
      else if (tab === 'gearboxes') await axios.delete(`/api/v1/gearboxes/${encodeURIComponent(delTarget)}`)
      else if (tab === 'motors')    await axios.delete(`/api/v1/motors/${encodeURIComponent(delTarget)}`)
      else if (tab === 'drives')    await axios.delete(`/api/v1/drives/${encodeURIComponent(delTarget)}`)
      else if (tab === 'costs')     await axios.delete(`/api/v1/costs/${encodeURIComponent(delTarget)}`)
      else if (tab === 'process')   await axios.delete(`/api/v1/bearings/${encodeURIComponent(delTarget)}`)
      const keys: Record<Tab, string> = { materials:'materials', process:'bearings',
        gearboxes:'gearboxes', motors:'motors', drives:'drives', costs:'costs' }
      inv(keys[tab])
      flash(`✓ Deleted '${delTarget}'`)
    } catch (e: any) { flash(e?.response?.data?.detail || 'Delete failed', false) }
    setDelTarget(null)
  }

  // ── Tab button ─────────────────────────────────────────────────
  const Tb = (id: Tab, label: string) => (
    <button key={id} onClick={() => setTab(id)} style={ss({
      padding: '6px 14px', border: 'none',
      borderBottom: tab === id ? `2px solid ${C.accent}` : '2px solid transparent',
      background: tab === id ? '#0d1c2e' : 'transparent',
      color: tab === id ? C.accent : C.muted,
      fontWeight: tab === id ? 800 : 600, fontSize: 11,
      cursor: 'pointer', fontFamily: 'inherit', letterSpacing: '0.04em', whiteSpace: 'nowrap',
    })}>{label}</button>
  )

  // ── Shared table wrapper ───────────────────────────────────────
  const TableWrap = ({ loading, empty, children }: { loading: boolean; empty: boolean; children: React.ReactNode }) => (
    <div style={ss({ flex: 1, overflowY: 'auto', border: `1px solid ${C.border}`, borderRadius: 6 })}>
      {loading && <div style={ss({ padding: 16, color: C.muted, fontSize: 11 })}>Loading…</div>}
      {!loading && empty && (
        <div style={ss({ padding: 24, textAlign: 'center', color: C.muted, fontSize: 11 })}>
          No records found. Run <code>python -m backend.db.seed</code>
        </div>
      )}
      {!loading && !empty && children}
    </div>
  )

  return (
    <div style={ss({ display: 'flex', flexDirection: 'column', height: '100%', padding: 12, gap: 8 })}>

      {/* Tabs */}
      <div style={ss({ display: 'flex', borderBottom: `1px solid ${C.border}`, gap: 0, flexShrink: 0 })}>
        {Tb('materials', '🧪 Materials')}
        {Tb('process',   '⚙️ Bearings')}
        {Tb('gearboxes', '🔧 Gearboxes')}
        {Tb('motors',    '🔌 Motors')}
        {Tb('drives',    '🎛️ Drives')}
        {Tb('costs',     '💰 Costs')}
      </div>

      {/* Flash */}
      {msg && (
        <div style={ss({ fontSize: 11, padding: '6px 12px', borderRadius: 4, flexShrink: 0,
          background: msg.ok ? 'rgba(31,184,110,.1)' : 'rgba(224,82,82,.1)',
          border: `1px solid ${msg.ok ? C.green : C.red}`,
          color: msg.ok ? C.green : C.red })}>{msg.text}</div>
      )}

      {/* ══ MATERIALS ══════════════════════════════════════════════ */}
      {tab === 'materials' && (
        <>
          <div style={ss({ display: 'flex', gap: 8, flexShrink: 0 })}>
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search name / CEMA code / note…"
              style={ss({ flex: 1, background: '#081321', border: `1px solid ${C.border}`, borderRadius: 4,
                padding: '6px 10px', color: C.text, fontSize: 11, fontFamily: 'inherit', outline: 'none' })} />
            <select value={cat} onChange={e => setCat(e.target.value)}
              style={ss({ background: '#081321', border: `1px solid ${C.border}`, borderRadius: 4,
                padding: '6px 10px', color: C.text, fontSize: 11, fontFamily: 'inherit', outline: 'none' })}>
              <option value="">All Categories</option>
              {(cats||[]).map(c => <option key={c} value={c}>{c}</option>)}
            </select>
            <button onClick={() => setModal({ mode: 'add' })}
              style={ss({ padding: '6px 14px', borderRadius: 4, border: `1px solid ${C.green}`,
                background: 'rgba(31,184,110,.1)', color: C.green,
                cursor: 'pointer', fontSize: 11, fontWeight: 700, fontFamily: 'inherit', whiteSpace: 'nowrap' })}>
              + Add Material
            </button>
          </div>
          <TableWrap loading={mL} empty={!(mats||[]).length}>
            <table style={ss({ width: '100%', borderCollapse: 'collapse' })}>
              <thead>
                <tr>
                  {['Material Name','Category','ρ t/m³','λ (computed)','Fill max','Ks','Wc','Particle','Flow','Abrasiveness','AoR °','Cohesion kPa','Cls','Moist%','Flags','Applications','CEMA C…'].map(h => (
                    <TH key={h}>{h}</TH>
                  ))}
                  <TH></TH>
                </tr>
              </thead>
              <tbody>
                {(mats||[]).map(m => {
                  // Compute lambda/Ks/Wc client-side for display (mirrors Python engine)
                  const psz: Record<string,number> = {A200:0.075,A100:0.15,A40:0.42,B6:6,'C1/2':12,D3:75,D7:180}
                  const pszVal = psz[m.particle_class||'B6'] || 6
                  const wc = Math.min(Math.max(
                    ({Low:0.25,Medium:0.70,High:1.40,'Very High':2.30}[m.abr]||0.5)*(1+pszVal/100), 0.1), 4.5)
                  const ks = Math.max(0.3, Math.min(
                    ({1:1.0,2:0.88,3:0.72,4:0.55}[String(m.flowability)]||0.8) *
                    Math.max(0.5, 1-(m.cohesion||0.2)/10), 1.0))
                  const lamBase = pszVal<0.5?1.8:pszVal<5?1.4:1.0
                  const lam = Math.max(0.4, Math.min(
                    0.6*(m.lambda_ref||1.0)+0.4*lamBase, 3.5))
                  return (
                    <tr key={m.id} style={ss({ borderBottom: `1px solid ${C.border}` })}
                      onMouseOver={e=>(e.currentTarget as HTMLElement).style.background='#0d1e30'}
                      onMouseOut={e=>(e.currentTarget as HTMLElement).style.background='transparent'}>
                      <TD><strong style={ss({ color: C.text })}>{m.name}</strong>{m.custom&&<CustomBadge/>}</TD>
                      <TD faint>{m.category||'—'}</TD>
                      <TD mono>{m.rho.toFixed(2)}</TD>
                      <TD mono>{lam.toFixed(2)}</TD>
                      <TD mono>{(m.fill_max*100).toFixed(0)}%</TD>
                      <TD mono>{ks.toFixed(2)}</TD>
                      <TD mono>{wc.toFixed(2)}</TD>
                      <TD faint>{m.particle_class||'—'}</TD>
                      <TD faint>{m.flowability!=null?`${m.flowability} — ${['Very Free','Free','Average','Sluggish'][m.flowability-1]||''}`:'—'}</TD>
                      <TD faint>{m.abr}</TD>
                      <TD mono>{m.aor!=null?m.aor.toFixed(1)+'°':'—'}</TD>
                      <TD mono>{m.cohesion!=null?m.cohesion.toFixed(1):'—'}</TD>
                      <TD mono>{m.cls}</TD>
                      <TD mono>{m.moist.toFixed(1)+'%'}</TD>
                      <td style={ss({ padding: '4px 8px' })}><FlagsCell flags={m.flags} /></td>
                      <td style={ss({ padding: '4px 8px', minWidth: 200 })}><AppCoverage mat={m} /></td>
                      <TD faint>{(m as any).cema_code||'—'}</TD>
                      <td style={ss({ padding: '4px 8px', whiteSpace: 'nowrap' })}>
                        <div style={ss({ display: 'flex', gap: 4 })}>
                          <button onClick={()=>{ setInp({mat:m.name}); setPage('calc') }}
                            style={ss({ fontSize:9,padding:'2px 6px',borderRadius:3,
                              border:`1px solid ${C.accent}`,background:'transparent',
                              color:C.accent,cursor:'pointer' })}>Use→</button>
                          <button onClick={()=>setModal({ mode:'edit', row:m })}
                            style={ss({ fontSize:9,padding:'2px 6px',borderRadius:3,
                              border:`1px solid ${C.blue}`,background:'transparent',
                              color:C.blue,cursor:'pointer' })}>✏️</button>
                          {m.custom&&<button onClick={()=>setDelTarget(m.name)}
                            style={ss({ fontSize:9,padding:'2px 6px',borderRadius:3,
                              border:`1px solid ${C.red}`,background:'transparent',
                              color:C.red,cursor:'pointer' })}>🗑</button>}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </TableWrap>
        </>
      )}

      {/* ══ BEARINGS ════════════════════════════════════════════════ */}
      {tab === 'process' && (
        <>
          <div style={ss({ display:'flex', justifyContent:'flex-end', flexShrink:0 })}>
            <button onClick={()=>setModal({mode:'add'})}
              style={ss({ padding:'6px 14px',borderRadius:4,border:`1px solid ${C.green}`,
                background:'rgba(31,184,110,.1)',color:C.green,cursor:'pointer',
                fontSize:11,fontWeight:700,fontFamily:'inherit' })}>+ Add Bearing</button>
          </div>
          <TableWrap loading={bL} empty={!(bearings||[]).length}>
            <table style={ss({ width:'100%', borderCollapse:'collapse' })}>
              <thead><tr>
                {['Name','Type','Bore mm','OD mm','B mm','C kN','C₀ kN','p','Speed rpm','Seal','Role','Mass kg','Note'].map(h=><TH key={h}>{h}</TH>)}
                <TH></TH>
              </tr></thead>
              <tbody>
                {(bearings||[]).map((b:any)=>(
                  <tr key={b.id} style={ss({borderBottom:`1px solid ${C.border}`})}
                    onMouseOver={e=>(e.currentTarget as HTMLElement).style.background='#0d1e30'}
                    onMouseOut={e=>(e.currentTarget as HTMLElement).style.background='transparent'}>
                    <TD><strong style={ss({color:C.text})}>{b.name}</strong>{b.custom&&<CustomBadge/>}</TD>
                    <TD faint>{b.type||'—'}</TD>
                    <TD mono>{b.bore?.toFixed(0)||'—'}</TD>
                    <TD mono>{b.od?.toFixed(0)||'—'}</TD>
                    <TD mono>{b.B?.toFixed(0)||'—'}</TD>
                    <TD mono>{b.C?.toFixed(1)||'—'}</TD>
                    <TD mono>{b.C0?.toFixed(1)||'—'}</TD>
                    <TD mono>{b.p?.toFixed(0)||'—'}</TD>
                    <TD mono>{b.speed_g?.toLocaleString()||'—'}</TD>
                    <TD faint>{b.seal||'—'}</TD>
                    <TD faint>{b.role||'—'}</TD>
                    <TD mono>{b.mass_kg?.toFixed(1)||'—'}</TD>
                    <TD faint>{b.note||''}</TD>
                    <td style={ss({padding:'4px 8px'})}>
                      <ActionBtns isCustom={!!b.custom} onEdit={()=>setModal({mode:'edit',row:b})}
                        onDelete={b.custom?()=>setDelTarget(b.name):undefined}/>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        </>
      )}

      {/* ══ GEARBOXES ═══════════════════════════════════════════════ */}
      {tab === 'gearboxes' && (
        <>
          <div style={ss({ display:'flex', justifyContent:'flex-end', flexShrink:0 })}>
            <button onClick={()=>setModal({mode:'add'})}
              style={ss({ padding:'6px 14px',borderRadius:4,border:`1px solid ${C.green}`,
                background:'rgba(31,184,110,.1)',color:C.green,cursor:'pointer',
                fontSize:11,fontWeight:700,fontFamily:'inherit' })}>+ Add Gearbox</button>
          </div>
          <TableWrap loading={gL} empty={!(gearboxes||[]).length}>
            <table style={ss({ width:'100%', borderCollapse:'collapse' })}>
              <thead><tr>
                {['Model','Type','Stages','Rated Torque Nm','Power kW','Ratio min','Ratio max','η %','Mount','IP','Mass kg','Note'].map(h=><TH key={h}>{h}</TH>)}
                <TH></TH>
              </tr></thead>
              <tbody>
                {(gearboxes||[]).map((g:any)=>(
                  <tr key={g.id} style={ss({borderBottom:`1px solid ${C.border}`})}
                    onMouseOver={e=>(e.currentTarget as HTMLElement).style.background='#0d1e30'}
                    onMouseOut={e=>(e.currentTarget as HTMLElement).style.background='transparent'}>
                    <TD><strong style={ss({color:C.text})}>{g.model}</strong>{g.custom&&<CustomBadge/>}</TD>
                    <TD faint>{g.type||'—'}</TD>
                    <TD mono>{g.stages||'—'}</TD>
                    <TD mono>{g.Tn?.toLocaleString()}</TD>
                    <TD mono>{g.Pkw?.toFixed(1)}</TD>
                    <TD mono>{g.ratio_min?.toFixed(1)||'—'}</TD>
                    <TD mono>{g.ratio_max?.toFixed(1)||'—'}</TD>
                    <TD mono>{g.eta?.toFixed(1)||'—'}</TD>
                    <TD faint>{g.mount||'—'}</TD>
                    <TD faint>{g.ip||'—'}</TD>
                    <TD mono>{g.mass_kg?.toFixed(1)||'—'}</TD>
                    <TD faint>{g.note||''}</TD>
                    <td style={ss({padding:'4px 8px'})}>
                      <ActionBtns isCustom={!!g.custom} onEdit={()=>setModal({mode:'edit',row:g})}
                        onDelete={g.custom?()=>setDelTarget(g.model):undefined}/>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        </>
      )}

      {/* ══ MOTORS ══════════════════════════════════════════════════ */}
      {tab === 'motors' && (
        <>
          <div style={ss({ display:'flex', justifyContent:'flex-end', flexShrink:0 })}>
            <button onClick={()=>setModal({mode:'add'})}
              style={ss({ padding:'6px 14px',borderRadius:4,border:`1px solid ${C.green}`,
                background:'rgba(31,184,110,.1)',color:C.green,cursor:'pointer',
                fontSize:11,fontWeight:700,fontFamily:'inherit' })}>+ Add Motor</button>
          </div>
          <TableWrap loading={moL} empty={!(motors||[]).length}>
            <table style={ss({ width:'100%', borderCollapse:'collapse' })}>
              <thead><tr>
                {['Model','Frame','Power kW','Poles','RPM (50Hz)','Efficiency %','IE Class','IP','Mass kg','Note'].map(h=><TH key={h}>{h}</TH>)}
                <TH></TH>
              </tr></thead>
              <tbody>
                {(motors||[]).map((m:any)=>(
                  <tr key={m.id} style={ss({borderBottom:`1px solid ${C.border}`})}
                    onMouseOver={e=>(e.currentTarget as HTMLElement).style.background='#0d1e30'}
                    onMouseOut={e=>(e.currentTarget as HTMLElement).style.background='transparent'}>
                    <TD><strong style={ss({color:C.text})}>{m.model}</strong>{m.custom&&<CustomBadge/>}</TD>
                    <TD faint>{m.frame||'—'}</TD>
                    <TD mono>{m.Pkw?.toFixed(2)}</TD>
                    <TD mono>{m.poles||'—'}</TD>
                    <TD mono>{m.rpm_50hz?.toFixed(0)||'—'}</TD>
                    <TD mono>{m.efficiency?.toFixed(1)||'—'}</TD>
                    <TD faint>{m.ie_class||'—'}</TD>
                    <TD faint>{m.ip||'—'}</TD>
                    <TD mono>{m.mass_kg?.toFixed(1)||'—'}</TD>
                    <TD faint>{m.note||''}</TD>
                    <td style={ss({padding:'4px 8px'})}>
                      <ActionBtns isCustom={!!m.custom} onEdit={()=>setModal({mode:'edit',row:m})}
                        onDelete={m.custom?()=>setDelTarget(m.model):undefined}/>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        </>
      )}

      {/* ══ DRIVES ══════════════════════════════════════════════════ */}
      {tab === 'drives' && (
        <>
          <div style={ss({ display:'flex', justifyContent:'flex-end', flexShrink:0 })}>
            <button onClick={()=>setModal({mode:'add'})}
              style={ss({ padding:'6px 14px',borderRadius:4,border:`1px solid ${C.green}`,
                background:'rgba(31,184,110,.1)',color:C.green,cursor:'pointer',
                fontSize:11,fontWeight:700,fontFamily:'inherit' })}>+ Add Drive</button>
          </div>
          <TableWrap loading={dL} empty={!(drives||[]).length}>
            <table style={ss({ width:'100%', borderCollapse:'collapse' })}>
              <thead><tr>
                {['Model','Type','Max kW','Rated V','Rated A','Overload %','Control','IP','Features','Note'].map(h=><TH key={h}>{h}</TH>)}
                <TH></TH>
              </tr></thead>
              <tbody>
                {(drives||[]).map((d:any)=>(
                  <tr key={d.id} style={ss({borderBottom:`1px solid ${C.border}`})}
                    onMouseOver={e=>(e.currentTarget as HTMLElement).style.background='#0d1e30'}
                    onMouseOut={e=>(e.currentTarget as HTMLElement).style.background='transparent'}>
                    <TD><strong style={ss({color:C.text})}>{d.model}</strong>{d.custom&&<CustomBadge/>}</TD>
                    <TD faint>{d.type||'—'}</TD>
                    <TD mono>{d.Pkw_max?.toFixed(2)||'—'}</TD>
                    <TD mono>{d.Vrated?.toFixed(0)||'—'}</TD>
                    <TD mono>{d.Irated?.toFixed(1)||'—'}</TD>
                    <TD mono>{d.overload_pct?.toFixed(0)||'—'}</TD>
                    <TD faint>{d.control||'—'}</TD>
                    <TD faint>{d.ip||'—'}</TD>
                    <TD faint>{d.features||'—'}</TD>
                    <TD faint>{d.note||''}</TD>
                    <td style={ss({padding:'4px 8px'})}>
                      <ActionBtns isCustom={!!d.custom} onEdit={()=>setModal({mode:'edit',row:d})}
                        onDelete={d.custom?()=>setDelTarget(d.model):undefined}/>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        </>
      )}

      {/* ══ COSTS ═══════════════════════════════════════════════════ */}
      {tab === 'costs' && (
        <>
          <div style={ss({ display:'flex', justifyContent:'flex-end', flexShrink:0 })}>
            <button onClick={()=>setModal({mode:'add'})}
              style={ss({ padding:'6px 14px',borderRadius:4,border:`1px solid ${C.green}`,
                background:'rgba(31,184,110,.1)',color:C.green,cursor:'pointer',
                fontSize:11,fontWeight:700,fontFamily:'inherit' })}>+ Add Cost Item</button>
          </div>
          <TableWrap loading={cL} empty={!(costs||[]).length}>
            <table style={ss({ width:'100%', borderCollapse:'collapse' })}>
              <thead><tr>
                {['Material / Item','USD / kg','Material Group','Description','Note'].map(h=><TH key={h}>{h}</TH>)}
                <TH></TH>
              </tr></thead>
              <tbody>
                {(costs||[]).map((c:any)=>(
                  <tr key={c.id} style={ss({borderBottom:`1px solid ${C.border}`})}
                    onMouseOver={e=>(e.currentTarget as HTMLElement).style.background='#0d1e30'}
                    onMouseOut={e=>(e.currentTarget as HTMLElement).style.background='transparent'}>
                    <TD><strong style={ss({color:C.text})}>{c.item}</strong>{c.custom&&<CustomBadge/>}</TD>
                    <TD mono>{c.usd?.toFixed(2)}</TD>
                    <TD faint>{c.material_group||'—'}</TD>
                    <TD faint>{c.description||'—'}</TD>
                    <TD faint>{c.note||''}</TD>
                    <td style={ss({padding:'4px 8px'})}>
                      <ActionBtns isCustom={!!c.custom} onEdit={()=>setModal({mode:'edit',row:c})}
                        onDelete={c.custom?()=>setDelTarget(c.item):undefined}/>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        </>
      )}

      {/* ── Material modal ── */}
      {modal && tab === 'materials' && (
        <MaterialFormModal
          title={modal.mode==='add' ? 'Add Custom Material' : `Edit: ${modal.row?.name}`}
          initial={modal.mode==='edit' ? {
            ...modal.row,
            rho: String(modal.row.rho||''), rho_min: String(modal.row.rho_min||''),
            rho_max: String(modal.row.rho_max||''), lambda_ref: String(modal.row.lambda_ref||''),
            fill_max: String(modal.row.fill_max||''), moist: String(modal.row.moist||''),
            aor: String(modal.row.aor||''), cohesion: String(modal.row.cohesion||''),
            temp_max: String(modal.row.temp_max||''), bridging_risk: String(modal.row.bridging_risk||''),
            flowability: String(modal.row.flowability||'2'),
            app: modal.row.app || [],
          } : undefined}
          onSave={async (d) => { await handleSave(d) }}
          onClose={() => setModal(null)}
        />
      )}

      {/* ── Generic simple edit modal for other tables ── */}
      {modal && tab !== 'materials' && (() => {
        const row = modal.row || {}
        const [form, setFormLocal] = React.useState<Record<string,string>>(
          Object.fromEntries(Object.entries(row).map(([k,v])=>[k, v==null?'':String(v)]))
        )
        const [saving, setSaving] = React.useState(false)
        const [err, setErr] = React.useState('')
        const setF = (k:string) => (v:string) => setFormLocal(p=>({...p,[k]:v}))

        const fieldDefs: Record<Tab, {k:string;label:string;type?:string}[]> = {
          materials: [],
          process: [
            {k:'name',label:'Name *'},{k:'type',label:'Type'},{k:'bore',label:'Bore mm',type:'number'},
            {k:'od',label:'OD mm',type:'number'},{k:'B',label:'B mm',type:'number'},
            {k:'C',label:'C kN',type:'number'},{k:'C0',label:'C₀ kN',type:'number'},
            {k:'p',label:'Life exp',type:'number'},{k:'speed_g',label:'Speed limit',type:'number'},
            {k:'seal',label:'Seal'},{k:'role',label:'Role'},{k:'mass_kg',label:'Mass kg',type:'number'},
            {k:'note',label:'Note'},
          ],
          gearboxes: [
            {k:'model',label:'Model *'},{k:'type',label:'Type'},{k:'stages',label:'Stages',type:'number'},
            {k:'Tn',label:'Rated Torque Nm',type:'number'},{k:'Pkw',label:'Power kW',type:'number'},
            {k:'ratio_min',label:'Ratio min',type:'number'},{k:'ratio_max',label:'Ratio max',type:'number'},
            {k:'eta',label:'Efficiency %',type:'number'},{k:'mount',label:'Mount'},
            {k:'ip',label:'IP'},{k:'mass_kg',label:'Mass kg',type:'number'},{k:'note',label:'Note'},
          ],
          motors: [
            {k:'model',label:'Model *'},{k:'frame',label:'Frame'},
            {k:'Pkw',label:'Power kW',type:'number'},{k:'poles',label:'Poles',type:'number'},
            {k:'rpm_50hz',label:'RPM 50Hz',type:'number'},{k:'efficiency',label:'Efficiency %',type:'number'},
            {k:'ie_class',label:'IE Class'},{k:'ip',label:'IP'},
            {k:'mass_kg',label:'Mass kg',type:'number'},{k:'note',label:'Note'},
          ],
          drives: [
            {k:'model',label:'Model *'},{k:'type',label:'Type'},
            {k:'Pkw_max',label:'Max kW',type:'number'},{k:'Vrated',label:'Rated V',type:'number'},
            {k:'Irated',label:'Rated A',type:'number'},{k:'overload_pct',label:'Overload %',type:'number'},
            {k:'control',label:'Control'},{k:'ip',label:'IP'},
            {k:'features',label:'Features'},{k:'note',label:'Note'},
          ],
          costs: [
            {k:'item',label:'Item Name *'},{k:'usd',label:'USD / kg',type:'number'},
            {k:'material_group',label:'Material Group'},{k:'description',label:'Description'},
            {k:'note',label:'Note'},
          ],
        }

        const fields = fieldDefs[tab] || []
        const keyField = tab==='process'?'name':tab==='gearboxes'||tab==='motors'||tab==='drives'?'model':'item'

        const doSave = async () => {
          setSaving(true); setErr('')
          const parsed: Record<string,any> = {}
          fields.forEach(({k,type})=>{
            parsed[k] = type==='number' ? (parseFloat(form[k])||null) : (form[k]||null)
          })
          try { await handleSave(parsed); } catch(e:any){ setErr(e.message); setSaving(false) }
        }

        const title = modal.mode==='add' ? `Add ${tab[0].toUpperCase()+tab.slice(1,-1)}`
                    : `Edit: ${row[keyField]}`
        return (
          <Modal title={title} icon="✏️" onClose={()=>setModal(null)}
            onSave={doSave} saving={saving} error={err}>
            {fields.map(({k,label,type})=>(
              <FInput key={k} label={label} value={form[k]||''} type={type||'text'}
                onChange={setF(k)} step={type==='number'?'0.01':undefined}/>
            ))}
          </Modal>
        )
      })()}

      {/* Delete confirmation */}
      {delTarget && (
        <DeleteConfirm name={delTarget} onConfirm={handleDelete} onCancel={()=>setDelTarget(null)}/>
      )}
    </div>
  )
}
