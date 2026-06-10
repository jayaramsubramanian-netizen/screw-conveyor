import React, { useState } from 'react'
import axios from 'axios'
import { C, Field, Divider, KpiCard, ResultRow, AxialChart, RunBtn, ErrorBanner, EmptyState, ModuleShell } from './ProcessPage'

export default function CompactorPage() {
  const [r, setR] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string|null>(null)

  const [inp, setInp] = useState({
    diam:0.3, fLen:2, Nc:20, fFill:0.60,
    feed:3, fRho:0.4, tgtR:0.85,
    mu_wall:0.35, k_lat:0.45, alpha_c:0.005,
  })
  const s = (k:string) => (v:any) => setInp(p=>({...p,[k]:v}))

  const run = async () => {
    setLoading(true); setErr(null)
    try {
      const {data} = await axios.post('/api/v1/process/compactor', {...inp,len:inp.fLen})
      setR(data)
    } catch(e:any) { setErr(e?.response?.data?.detail||e?.message||'Error') }
    finally { setLoading(false) }
  }

  const summary = r?.summary
  const hist    = r?.history||[]

  return (
    <ModuleShell
      inputPanel={<>
        <div style={{marginBottom:10}}>
          <div style={{fontSize:20,marginBottom:3}}>🗜️</div>
          <div style={{fontSize:12,fontWeight:800,color:C.accent,fontFamily:"'Barlow Condensed',sans-serif",letterSpacing:'0.08em'}}>SCREW COMPACTOR</div>
          <div style={{fontSize:9,color:C.muted,marginTop:3,lineHeight:1.6}}>Janssen back-pressure · Power-law compaction · Plug risk assessment</div>
        </div>
        <Divider label="Geometry"/>
        <Field label="Diameter" value={inp.diam} setter={s('diam')} min={0.1} max={1.2} step={0.05} unit="m"/>
        <Field label="Length" value={inp.fLen} setter={s('fLen')} min={0.2} max={10} step={0.1} unit="m"/>
        <Divider label="Drive"/>
        <Field label="Speed" value={inp.Nc} setter={s('Nc')} min={1} max={60} step={1} unit="RPM"/>
        <Field label="Fill fraction" value={inp.fFill} setter={s('fFill')} min={0.3} max={0.95} step={0.05}/>
        <Divider label="Material"/>
        <Field label="Feed rate" value={inp.feed} setter={s('feed')} min={0.1} max={200} step={0.5} unit="t/h"/>
        <Field label="Bulk density in" value={inp.fRho} setter={s('fRho')} min={0.05} max={2} step={0.05} unit="t/m³"/>
        <Field label="Target density out" value={inp.tgtR} setter={s('tgtR')} min={0.1} max={4} step={0.05} unit="t/m³"/>
        <Divider label="Janssen Parameters"/>
        <Field label="Wall friction μ" value={inp.mu_wall} setter={s('mu_wall')} min={0.1} max={0.8} step={0.05}/>
        <Field label="Lateral pressure k" value={inp.k_lat} setter={s('k_lat')} min={0.1} max={0.8} step={0.05}/>
        <Field label="Compaction coeff α" value={inp.alpha_c} setter={s('alpha_c')} min={0.001} max={0.05} step={0.001}/>
        <RunBtn onClick={run} loading={loading}/>
      </>}
      resultPanel={<>
        {err && <ErrorBanner msg={err}/>}
        {r && <>
          <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:8}}>
            <KpiCard label="ρ out" value={r.rho_out?.toFixed(3)||'—'} unit="t/m³" ok={r.rho_out>=inp.tgtR*0.95} sub={`target ${inp.tgtR}`}/>
            <KpiCard label="CR" value={r.CR?.toFixed(2)||'—'} col={C.blue} sub="compression ratio"/>
            <KpiCard label="σ Janssen" value={r.sigma_janssen?.toFixed(1)||'—'} unit="kPa" col={r.plugging?C.red:C.amber}/>
            <KpiCard label="Plug Risk" value={r.plugging?'⚠ HIGH':'✓ OK'} ok={!r.plugging}/>
          </div>
          <div style={{background:C.panel,border:`1px solid ${C.border}`,borderRadius:8,padding:12}}>
            <div style={{fontSize:9,fontWeight:700,color:C.accent,letterSpacing:'0.10em',marginBottom:8,textTransform:'uppercase' as const,fontFamily:"'Barlow Condensed',sans-serif"}}>📊 Compaction Summary</div>
            <ResultRow label="ρ in"             value={inp.fRho+' t/m³'}/>
            <ResultRow label="ρ out"            value={r.rho_out?.toFixed(3)+' t/m³'} ok={r.rho_out>=inp.tgtR*0.95}/>
            <ResultRow label="CR"               value={r.CR?.toFixed(3)}/>
            <ResultRow label="σ Janssen"        value={r.sigma_janssen?.toFixed(1)+' kPa'} ok={!r.plugging}/>
            <ResultRow label="τ shear"          value={summary?.tau_shear_kPa?.toFixed(2)+' kPa'}/>
            <ResultRow label="Torque"           value={summary?.torque_Nm?.toFixed(0)} unit="Nm"/>
            <ResultRow label="Plugging risk"    value={r.plugging?'HIGH — reduce speed/fill':'OK'} ok={!r.plugging}/>
            <ResultRow label="Axial velocity"   value={r?.tr?.v_ax?.toFixed(4)} unit="m/s"/>
          </div>
          <AxialChart history={hist} dataKey="sigma" label="Back Pressure σ" unit="kPa" color={C.amber}/>
          <AxialChart history={hist} dataKey="rho" label="Bulk Density" unit="t/m³" color={C.blue} refValue={inp.tgtR} refLabel={`Target ${inp.tgtR}`}/>
        </>}
        {!r && !loading && !err && <EmptyState icon="🗜️" name="Screw Compactor" desc="Janssen back-pressure model with power-law stress-density compaction. Plug risk assessment at σ>200kPa. Conservative preliminary design."/>}
      </>}
    />
  )
}
