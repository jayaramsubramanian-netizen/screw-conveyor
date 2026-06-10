/**
 * FamilyPage.tsx — VECTRIX™ Family Designer
 * Full port of the HTML prototype: D × L × N matrix generator with
 * 5 view modes (All Designs, Meets Target, Capacity Matrix, Energy Matrix, Best per D)
 * CSV export, Apply-to-Designer, material-aware speed cap.
 */
import React, { useState, useEffect, useMemo } from 'react'
import { useMaterials, useCalcStore } from '../../hooks/useCalculator'
import * as api from '../../api/client'

const C = {
  panel:'#0d1c2e', border:'#162438', text:'#ddeaf6',
  muted:'#5d7d99', faint:'#3a5470', accent:'#c8192e',
  green:'#1fb86e', red:'#e05252', amber:'#d98e00', blue:'#4a9eff',
  teal:'#2dd4bf', purple:'#a78bfa',
}
const ss = (s: React.CSSProperties) => s

const DA = [100,150,200,250,300,350,400,450,500,600,700,800]
const LA = [3,5,8,10,12,15,18,20,25,30,35,40,45,50]

type ViewTab = 'list'|'feasible'|'matrix'|'energy'|'best'

interface Pt {
  Dmm: number; L: number; N: number; cap: number; cap_ok: boolean
  pwr: number; motor: number; tor: number; shaft_mm: number
  hgr: number; L10: number; kWh: number; cost: number; score: number
}

export default function FamilyPage() {
  const { inp: calcInp, setInp } = useCalcStore()
  const { data: mats } = useMaterials()

  const [cfg, setCfg] = useState({
    mat: calcInp.mat || 'Portland cement dry',
    ang: calcInp.ang ?? 0,
    surge: calcInp.surge || 1.2,
    cap: calcInp.cap || 30,
    L: calcInp.L || 10,
    Ds: [150, 200, 250, 300, 400, 500] as number[],
    Ls: [5, 10, 15, 20, 25, 30] as number[],
  })

  // Sync from CalcPage whenever calcInp changes
  useEffect(() => {
    setCfg(prev => ({
      ...prev,
      mat: calcInp.mat || prev.mat,
      ang: calcInp.ang ?? prev.ang,
      surge: calcInp.surge || prev.surge,
      cap: calcInp.cap || prev.cap,
    }))
  }, [calcInp.mat, calcInp.ang, calcInp.surge, calcInp.cap])

  const [res, setRes] = useState<{ pts: Pt[] } | null>(null)
  const [vt, setVt] = useState<ViewTab>('list')
  const [running, setRunning] = useState(false)
  const [picked, setPicked] = useState<Pt | null>(null)

  const c = (k: string) => (v: any) => setCfg(prev => ({ ...prev, [k]: v }))
  const toggleArr = (key: 'Ds'|'Ls', val: number) =>
    setCfg(prev => ({
      ...prev,
      [key]: prev[key].includes(val)
        ? prev[key].filter((x: number) => x !== val)
        : [...prev[key], val].sort((a, b) => a - b)
    }))

  const generate = async () => {
    setRunning(true)
    setRes(null)
    try {
      const result = await api.getFamily({
        mat: cfg.mat, ang: cfg.ang, surge: cfg.surge,
        cap: cfg.cap, L: cfg.L,
        Ds: cfg.Ds.map(d => d), // send as mm — backend divides by 1000
        Ls: cfg.Ls,
      })
      // getFamily returns {pts:[...]} from backend
      const pts: Pt[] = (result as any).pts || []
      setRes({ pts })
    } catch (e) {
      console.error('Family generation failed', e)
    }
    setRunning(false)
    setPicked(null)
  }

  const applyDesign = (p: Pt) => {
    setPicked(p)
    setInp({
      D: p.Dmm / 1000,
      N: p.N,
      P: p.Dmm / 1000,
      L: p.L,
      mat: cfg.mat,
      ang: cfg.ang,
      surge: cfg.surge,
    })
  }

  const exportCSV = () => {
    if (!res) return
    const hdr = ['D(mm)','L(m)','N(RPM)','Cap(t/h)','Feasible','Power(kW)','Motor(kW)','Torque(Nm)','Shaft(mm)','Hangers','L10(h)','kWh/t','Cost(USD)','Score']
    const rows = res.pts.map(p => [p.Dmm,p.L,p.N,p.cap.toFixed(1),p.cap_ok?'Yes':'No',p.pwr.toFixed(2),p.motor,p.tor.toFixed(0),p.shaft_mm,p.hgr,p.L10.toFixed(0),p.kWh.toFixed(3),p.cost.toFixed(0),p.score.toFixed(1)])
    const csv = [hdr, ...rows].map(r => r.join(',')).join('\n')
    const a = document.createElement('a')
    a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv)
    a.download = 'screw_family.csv'; a.click()
  }

  const feasible   = res?.pts.filter(p => p.cap_ok) || []
  const infeasible = res?.pts.filter(p => !p.cap_ok) || []

  // Best per D (minimum kWh/t among feasible for each diameter)
  const bestPerD = useMemo(() => {
    const byD: Record<number, Pt> = {}
    for (const p of feasible) {
      if (!byD[p.Dmm] || p.kWh < byD[p.Dmm].kWh) byD[p.Dmm] = p
    }
    return Object.values(byD).sort((a, b) => a.Dmm - b.Dmm)
  }, [feasible])

  // Capacity heat matrix: rows=D, cols=L, cells=max cap at best N
  const capMatrix = useMemo(() => {
    const Ds = [...new Set(res?.pts.map(p => p.Dmm) || [])].sort((a, b) => a - b)
    const Ls = [...new Set(res?.pts.map(p => p.L) || [])].sort((a, b) => a - b)
    const cell = (D: number, L: number) => {
      const group = res?.pts.filter(p => p.Dmm === D && p.L === L) || []
      if (!group.length) return null
      return group.sort((a, b) => b.cap - a.cap)[0]
    }
    return { Ds, Ls, cell }
  }, [res])

  const okCol = (ok: boolean) => ok ? C.green : C.red

  // ── Table header cell
  const TH = ({ children, right }: { children: React.ReactNode; right?: boolean }) => (
    <th style={ss({ padding:'5px 8px', textAlign: right ? 'right' : 'left', color:'#93c5fd',
      fontWeight:700, fontSize:9, textTransform:'uppercase', letterSpacing:'0.06em',
      background:'rgba(0,0,0,.4)', borderBottom:`2px solid ${C.border}`,
      whiteSpace:'nowrap', position:'sticky', top:0, zIndex:2 })}>
      {children}
    </th>
  )
  const TD = ({ children, right, col, mono }: { children: React.ReactNode; right?: boolean; col?: string; mono?: boolean }) => (
    <td style={ss({ padding:'4px 8px', textAlign: right ? 'right' : 'left', color: col || C.text,
      fontSize:10, fontFamily: mono ? 'monospace' : 'inherit', borderBottom:`1px solid ${C.border}33` })}>
      {children}
    </td>
  )

  const renderTableRows = (pts: Pt[]) => pts.slice(0, 200).map((p, i) => (
    <tr key={i} style={ss({ background: i % 2 === 0 ? 'transparent' : 'rgba(0,0,0,.12)',
      cursor:'pointer' })}
      onClick={() => applyDesign(p)}>
      <TD mono col={C.accent}>{p.Dmm}</TD>
      <TD mono>{p.L}</TD>
      <TD mono>{p.N}</TD>
      <TD mono col={okCol(p.cap_ok)}>{p.cap.toFixed(1)}</TD>
      <TD><span style={ss({ fontSize:9, fontWeight:700, padding:'1px 6px', borderRadius:3,
        background: p.cap_ok ? 'rgba(31,184,110,.15)' : 'rgba(224,82,82,.15)',
        color: p.cap_ok ? C.green : C.red, border:`1px solid ${okCol(p.cap_ok)}` })}>
        {p.cap_ok ? '✓' : '✗'}
      </span></TD>
      <TD mono right>{p.pwr.toFixed(2)}</TD>
      <TD mono right>{p.motor}</TD>
      <TD mono right>{p.tor.toFixed(0)}</TD>
      <TD mono right>{p.shaft_mm}</TD>
      <TD mono right>{p.hgr}</TD>
      <TD mono right col={p.L10 >= 20000 ? C.green : C.amber}>{(p.L10/1000).toFixed(0)}k</TD>
      <TD mono right col={p.kWh < 1 ? C.green : p.kWh < 2 ? C.amber : C.red}>{p.kWh.toFixed(3)}</TD>
      <TD mono right>${p.cost.toFixed(0)}</TD>
      <TD mono right col={p.score > 70 ? C.green : p.score > 45 ? C.amber : C.red}>{p.score.toFixed(0)}</TD>
      <TD>
        <button onClick={e => { e.stopPropagation(); applyDesign(p) }}
          style={ss({ padding:'2px 8px', borderRadius:4, border:`1px solid ${C.teal}44`,
            background:'transparent', color: C.teal, cursor:'pointer', fontSize:9, fontWeight:700 })}>
          Apply
        </button>
      </TD>
    </tr>
  ))

  const heatColor = (val: number, min: number, max: number, invert = false) => {
    const t = max === min ? 0.5 : (val - min) / (max - min)
    const tt = invert ? 1 - t : t
    const r = Math.round(224 * (1 - tt) + 31 * tt)
    const g = Math.round(82 * (1 - tt) + 184 * tt)
    const b = Math.round(82 * (1 - tt) + 110 * tt)
    return `rgb(${r},${g},${b})`
  }

  return (
    <div style={ss({ display:'flex', flexDirection:'column', gap:10, height:'100%', overflowY:'auto', padding:14 })}>

      {/* ── Config panel ─────────────────────────────── */}
      <div style={ss({ background:'rgba(16,30,48,.8)', border:`1px solid ${C.border}`, borderRadius:10, padding:16, flexShrink:0 })}>
        <div style={ss({ fontSize:11, fontWeight:700, textTransform:'uppercase', color:C.accent, letterSpacing:'0.08em', marginBottom:12 })}>
          ⚙️ Family Configuration
          <span style={ss({ fontSize:9, fontWeight:400, color:C.muted, marginLeft:8 })}>synced from Screw Conveyor Designer tab</span>
        </div>

        {/* Row 1: shared params */}
        <div style={ss({ display:'grid', gridTemplateColumns:'2fr 1fr 1fr 1fr', gap:10, marginBottom:12 })}>
          {/* Material */}
          <div>
            <div style={ss({ fontSize:9, color:C.muted, marginBottom:3, textTransform:'uppercase', letterSpacing:'0.06em' })}>Material</div>
            <select value={cfg.mat} onChange={e => c('mat')(e.target.value)}
              style={ss({ width:'100%', background:'#081321', border:`1px solid ${C.border}`, color:C.text, borderRadius:5, padding:'5px 8px', fontSize:11 })}>
              {(mats || []).map(m => <option key={m.name} value={m.name}>{m.name}</option>)}
            </select>
          </div>
          {[['Required Cap (t/h)', 'cap'], ['Angle (°)', 'ang'], ['Surge Factor', 'surge']].map(([lbl, key]) => (
            <div key={key}>
              <div style={ss({ fontSize:9, color:C.muted, marginBottom:3, textTransform:'uppercase', letterSpacing:'0.06em' })}>{lbl}</div>
              <input type="number" value={(cfg as any)[key]}
                onChange={e => c(key)(parseFloat(e.target.value) || 0)}
                style={ss({ width:'100%', background:'#081321', border:`1px solid ${C.border}`, color:C.text, borderRadius:5, padding:'5px 8px', fontSize:11, fontFamily:'monospace', boxSizing:'border-box' })} />
            </div>
          ))}
        </div>

        {/* Row 2: D/L toggles */}
        <div style={ss({ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16, marginBottom:12 })}>
          {([
            ['Diameter options (mm)', 'Ds', DA, C.accent, 'rgba(232,160,0,.18)'],
            ['Length options (m)',    'Ls', LA, C.green,  'rgba(31,184,110,.18)'],
          ] as [string, 'Ds'|'Ls', number[], string, string][]).map(([lbl, key, arr, col, bg]) => (
            <div key={key}>
              <div style={ss({ fontSize:10, fontWeight:700, color:C.muted, marginBottom:5, textTransform:'uppercase', letterSpacing:'0.08em' })}>{lbl}</div>
              <div style={ss({ display:'flex', flexWrap:'wrap', gap:4 })}>
                {arr.map(v => (
                  <button key={v} onClick={() => toggleArr(key, v)}
                    style={ss({ padding:'3px 9px', borderRadius:4, fontSize:11, fontWeight:700, cursor:'pointer', fontFamily:'monospace',
                      border:`1px solid ${cfg[key].includes(v) ? col : C.border}`,
                      background: cfg[key].includes(v) ? bg : 'transparent',
                      color: cfg[key].includes(v) ? col : C.muted })}>
                    {v}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Generate + export */}
        <div style={ss({ display:'flex', gap:10, alignItems:'center', flexWrap:'wrap' })}>
          <button onClick={generate} disabled={running}
            style={ss({ padding:'9px 24px', borderRadius:8, border:'none',
              background: running ? C.faint : 'rgba(45,212,191,.9)',
              color:'#0b1522', fontWeight:800, fontSize:13, cursor: running ? 'wait' : 'pointer' })}>
            {running ? '⏳ Generating…' : '▶ Generate Family'}
          </button>
          {res && (
            <>
              <span style={ss({ fontSize:10, color:C.muted })}>
                {feasible.length} feasible / {res.pts.length} total · {cfg.mat} · {cfg.ang}° · ≥{cfg.cap} t/h
              </span>
              <button onClick={exportCSV}
                style={ss({ marginLeft:'auto', padding:'5px 12px', borderRadius:6, border:`1px solid ${C.green}`, background:'transparent', color:C.green, cursor:'pointer', fontSize:10, fontWeight:700 })}>
                ⬇ CSV
              </button>
            </>
          )}
        </div>
      </div>

      {/* Applied banner */}
      {picked && (
        <div style={ss({ background:'rgba(45,212,191,.08)', border:'1px solid rgba(45,212,191,.3)', borderRadius:8, padding:'10px 14px', display:'flex', alignItems:'center', gap:12, flexShrink:0 })}>
          <span style={ss({ fontSize:16 })}>✅</span>
          <div>
            <p style={ss({ fontSize:11, fontWeight:700, color:C.teal })}>Design applied to Screw Conveyor Designer tab</p>
            <p style={ss({ fontSize:10, color:C.muted })}>Ø{picked.Dmm}mm · {picked.N}rpm · L={picked.L}m · {picked.cap.toFixed(1)} t/h · {picked.kWh.toFixed(3)} kWh/t</p>
          </div>
        </div>
      )}

      {/* ── Results ─────────────────────────────────── */}
      {res && (
        <div style={ss({ background:'rgba(16,30,48,.8)', border:`1px solid ${C.border}`, borderRadius:10, overflow:'hidden', display:'flex', flexDirection:'column' })}>
          {/* View tabs */}
          <div style={ss({ display:'flex', gap:2, padding:'8px 12px', background:'rgba(0,0,0,.2)', borderBottom:`1px solid ${C.border}`, flexWrap:'wrap', alignItems:'center' })}>
            {([
              ['list',     '📋 All Designs'],
              ['feasible', '✓ Meets Target'],
              ['matrix',   '📊 Capacity Matrix'],
              ['energy',   '🔋 Energy Matrix'],
              ['best',     '⭐ Best per D'],
            ] as [ViewTab, string][]).map(([id, lb]) => (
              <button key={id} onClick={() => setVt(id)}
                style={ss({ padding:'4px 10px', borderRadius:5, fontSize:10, fontWeight:700, cursor:'pointer',
                  border:`1px solid ${vt === id ? C.accent : C.border}`,
                  background: vt === id ? 'rgba(232,160,0,.12)' : 'transparent',
                  color: vt === id ? C.accent : C.muted })}>
                {lb}
              </button>
            ))}
          </div>

          {/* List / Feasible table */}
          {(vt === 'list' || vt === 'feasible') && (
            <div style={ss({ overflowX:'auto', overflowY:'auto', maxHeight:480 })}>
              <table style={ss({ width:'100%', borderCollapse:'collapse', fontSize:11, tableLayout:'auto' })}>
                <thead>
                  <tr>
                    {['D(mm)','L(m)','N','Cap(t/h)','✓','Pwr(kW)','Motor','Torque','Shaft','Hgr','L10','kWh/t','Cost','Score',''].map(h => (
                      <TH key={h} right={['Cap(t/h)','Pwr(kW)','Motor','Torque','Shaft','Hgr','L10','kWh/t','Cost','Score'].includes(h)}>{h}</TH>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {renderTableRows(vt === 'feasible' ? feasible : res.pts)}
                </tbody>
              </table>
              {vt === 'feasible' && feasible.length === 0 && (
                <div style={ss({ padding:24, textAlign:'center', color:C.muted, fontSize:11 })}>
                  No designs meet the ≥{cfg.cap} t/h target. Try larger diameters or higher speeds.
                </div>
              )}
            </div>
          )}

          {/* Capacity heat matrix */}
          {vt === 'matrix' && (
            <div style={ss({ overflowX:'auto', padding:12 })}>
              <p style={ss({ fontSize:10, color:C.muted, marginBottom:8 })}>Max capacity (t/h) at best N for each D × L combination. Click cell to apply.</p>
              <table style={ss({ borderCollapse:'collapse', fontSize:10 })}>
                <thead>
                  <tr>
                    <th style={ss({ padding:'4px 10px', color:C.muted, fontSize:9 })}>D \ L(m)</th>
                    {capMatrix.Ls.map(L => <th key={L} style={ss({ padding:'4px 10px', color:C.blue, fontSize:9, fontWeight:700 })}>{L}m</th>)}
                  </tr>
                </thead>
                <tbody>
                  {capMatrix.Ds.map(D => {
                    const cells = capMatrix.Ls.map(L => capMatrix.cell(D, L))
                    const vals = cells.filter(Boolean).map(c => c!.cap)
                    const minV = Math.min(...vals), maxV = Math.max(...vals)
                    return (
                      <tr key={D}>
                        <td style={ss({ padding:'4px 10px', color:C.accent, fontWeight:700, fontFamily:'monospace', fontSize:10 })}>Ø{D}mm</td>
                        {cells.map((cell, i) => (
                          <td key={i} onClick={() => cell && applyDesign(cell)}
                            style={ss({ padding:'4px 8px', textAlign:'center', fontFamily:'monospace', fontSize:10, fontWeight:700, cursor: cell ? 'pointer' : 'default',
                              background: cell ? heatColor(cell.cap, minV, maxV) + '66' : 'transparent',
                              color: cell ? (cell.cap_ok ? C.green : C.amber) : C.faint,
                              border:`1px solid ${C.border}33` })}>
                            {cell ? cell.cap.toFixed(1) : '—'}
                          </td>
                        ))}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Energy heat matrix */}
          {vt === 'energy' && (
            <div style={ss({ overflowX:'auto', padding:12 })}>
              <p style={ss({ fontSize:10, color:C.muted, marginBottom:8 })}>Energy intensity (kWh/t) at best N — greener = more efficient. Click cell to apply.</p>
              <table style={ss({ borderCollapse:'collapse', fontSize:10 })}>
                <thead>
                  <tr>
                    <th style={ss({ padding:'4px 10px', color:C.muted, fontSize:9 })}>D \ L(m)</th>
                    {capMatrix.Ls.map(L => <th key={L} style={ss({ padding:'4px 10px', color:C.blue, fontSize:9, fontWeight:700 })}>{L}m</th>)}
                  </tr>
                </thead>
                <tbody>
                  {capMatrix.Ds.map(D => {
                    const cells = capMatrix.Ls.map(L => capMatrix.cell(D, L))
                    const vals = cells.filter(Boolean).map(c => c!.kWh)
                    const minV = Math.min(...vals), maxV = Math.max(...vals)
                    return (
                      <tr key={D}>
                        <td style={ss({ padding:'4px 10px', color:C.accent, fontWeight:700, fontFamily:'monospace', fontSize:10 })}>Ø{D}mm</td>
                        {cells.map((cell, i) => (
                          <td key={i} onClick={() => cell && applyDesign(cell)}
                            style={ss({ padding:'4px 8px', textAlign:'center', fontFamily:'monospace', fontSize:10, fontWeight:700, cursor: cell ? 'pointer' : 'default',
                              background: cell ? heatColor(cell.kWh, minV, maxV, true) + '66' : 'transparent',
                              color: cell ? (cell.kWh < 1 ? C.green : cell.kWh < 2 ? C.amber : C.red) : C.faint,
                              border:`1px solid ${C.border}33` })}>
                            {cell ? cell.kWh.toFixed(3) : '—'}
                          </td>
                        ))}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Best per D */}
          {vt === 'best' && (
            <div style={ss({ padding:12 })}>
              <p style={ss({ fontSize:10, color:C.muted, marginBottom:8 })}>Most energy-efficient feasible design at each diameter.</p>
              {bestPerD.length === 0 && (
                <div style={ss({ padding:24, textAlign:'center', color:C.muted, fontSize:11 })}>No feasible designs found. Try larger diameter selection.</div>
              )}
              <div style={ss({ display:'flex', flexDirection:'column', gap:6 })}>
                {bestPerD.map((p, i) => (
                  <div key={i} style={ss({ background: i === 0 ? 'rgba(45,212,191,.08)' : 'rgba(0,0,0,.15)', border:`1px solid ${i === 0 ? 'rgba(45,212,191,.3)' : C.border}`, borderRadius:8, padding:'10px 14px', display:'flex', alignItems:'center', gap:12, cursor:'pointer' })}
                    onClick={() => applyDesign(p)}>
                    <span style={ss({ fontSize:11, fontWeight:800, color: i === 0 ? C.teal : C.accent, fontFamily:'monospace', minWidth:60 })}>Ø{p.Dmm}mm</span>
                    <div style={ss({ display:'flex', gap:16, flexWrap:'wrap', flex:1, fontSize:10 })}>
                      {[
                        ['N', `${p.N} RPM`, C.text],
                        ['Cap', `${p.cap.toFixed(1)} t/h`, p.cap_ok ? C.green : C.red],
                        ['Motor', `${p.motor} kW`, C.purple],
                        ['kWh/t', p.kWh.toFixed(3), p.kWh < 1 ? C.green : C.amber],
                        ['L10', `${(p.L10/1000).toFixed(0)}kh`, p.L10 >= 20000 ? C.green : C.amber],
                        ['Score', p.score.toFixed(0), p.score > 70 ? C.green : C.amber],
                        ['Cost', `$${p.cost.toFixed(0)}`, C.accent],
                      ].map(([lbl, val, col]) => (
                        <span key={lbl as string} style={ss({ color:C.muted })}>
                          {lbl}: <strong style={ss({ color: col as string })}>{val as string}</strong>
                        </span>
                      ))}
                    </div>
                    <button onClick={e => { e.stopPropagation(); applyDesign(p) }}
                      style={ss({ padding:'5px 14px', borderRadius:6, border:`1px solid ${C.teal}`, background:'transparent', color:C.teal, cursor:'pointer', fontSize:10, fontWeight:700 })}>
                      Apply →
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!res && !running && (
        <div style={ss({ flex:1, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', color:C.muted, gap:8, paddingTop:40 })}>
          <div style={ss({ fontSize:32 })}>📊</div>
          <div style={ss({ fontSize:12, color:C.muted })}>Select diameters and lengths, then click Generate Family</div>
          <div style={ss({ fontSize:10, color:C.faint })}>Results are auto-scored and sorted by feasibility then energy efficiency</div>
        </div>
      )}
    </div>
  )
}
