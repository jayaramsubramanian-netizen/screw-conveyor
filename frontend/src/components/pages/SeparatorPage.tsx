import React, { useState } from 'react'
import axios from 'axios'
import { C, Field, Divider, KpiCard, ResultRow, AxialChart, RunBtn, ErrorBanner, EmptyState, ModuleShell } from './ProcessPage'

export default function SeparatorPage() {
  const [r, setR] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string|null>(null)

  const [inp, setInp] = useState({
    diam:0.3, lenSep:3, speedS:30, fill2:0.35,
    feed:5, rho:1.2, rhoA:1.5, d_p:2,
    d50:2.0, k_sep:1.5, sep_mode:'engineering', v_ref:0.15,
  })
  const s = (k:string) => (v:any) => setInp(p=>({...p,[k]:v}))

  const run = async () => {
    setLoading(true); setErr(null)
    try {
      const {data} = await axios.post('/api/v1/process/separator', {...inp,len:inp.lenSep})
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
          <div style={{fontSize:20,marginBottom:3}}>⚖️</div>
          <div style={{fontSize:12,fontWeight:800,color:C.accent,fontFamily:"'Barlow Condensed',sans-serif",letterSpacing:'0.08em'}}>SCREW SEPARATOR</div>
          <div style={{fontSize:9,color:C.muted,marginTop:3,lineHeight:1.6}}>Sigmoid grade efficiency · Stokes settling · PSD axial tracking</div>
        </div>
        <Divider label="Geometry"/>
        <Field label="Diameter" value={inp.diam} setter={s('diam')} min={0.1} max={1.2} step={0.05} unit="m"/>
        <Field label="Length" value={inp.lenSep} setter={s('lenSep')} min={0.5} max={20} step={0.5} unit="m"/>
        <Divider label="Drive"/>
        <Field label="Speed" value={inp.speedS} setter={s('speedS')} min={2} max={120} step={1} unit="RPM"/>
        <Field label="Fill fraction" value={inp.fill2} setter={s('fill2')} min={0.1} max={0.6} step={0.05}/>
        <Divider label="Feed"/>
        <Field label="Feed rate" value={inp.feed} setter={s('feed')} min={0.1} max={500} step={1} unit="t/h"/>
        <Field label="Bulk density" value={inp.rho} setter={s('rho')} min={0.1} max={3} step={0.05} unit="t/m³"/>
        <Field label="Particle density" value={inp.rhoA} setter={s('rhoA')} min={0.5} max={5} step={0.05} unit="t/m³"/>
        <Field label="Mean particle size" value={inp.d_p} setter={s('d_p')} min={0.01} max={100} step={0.5} unit="mm"/>
        <Divider label="Separation"/>
        <Field label="Model" value={inp.sep_mode} setter={s('sep_mode')} options={[
          {value:'engineering',label:'Engineering (sigmoid grade curve)'},
          {value:'physics',label:'Physics (Stokes settling)'},
        ]}/>
        <Field label="Cut size d₅₀" value={inp.d50} setter={s('d50')} min={0.01} max={50} step={0.1} unit="mm"/>
        <Field label="Slope factor k" value={inp.k_sep} setter={s('k_sep')} min={0.1} max={5} step={0.1}/>
        <Field label="Reference velocity" value={inp.v_ref} setter={s('v_ref')} min={0.01} max={1} step={0.01} unit="m/s"/>
        <RunBtn onClick={run} loading={loading}/>
      </>}
      resultPanel={<>
        {err && <ErrorBanner msg={err}/>}
        {r && <>
          <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:8}}>
            <KpiCard label="Sep. Efficiency" value={r.sep?.toFixed(1)||'—'} unit="%" col={r.sep>85?C.green:r.sep>60?C.amber:C.red}/>
            <KpiCard label="d50 out" value={summary?.d50_out_mm?.toFixed(2)||'—'} unit="mm" col={C.blue}/>
            <KpiCard label="η rotation" value={r.eta_rot!=null?(r.eta_rot*100).toFixed(0):'—'} unit="%" col={C.teal}/>
            <KpiCard label="t_res" value={summary?.t_res_s?.toFixed(0)||'—'} unit="s" col={C.purple}/>
          </div>
          <div style={{background:C.panel,border:`1px solid ${C.border}`,borderRadius:8,padding:12}}>
            <div style={{fontSize:9,fontWeight:700,color:C.accent,letterSpacing:'0.10em',marginBottom:8,textTransform:'uppercase' as const,fontFamily:"'Barlow Condensed',sans-serif"}}>📊 Separation Summary</div>
            <ResultRow label="Separation eff."  value={r.sep?.toFixed(1)+' %'} ok={r.sep>70}/>
            <ResultRow label="d10 out"          value={summary?.d10_out_mm?.toFixed(2)} unit="mm"/>
            <ResultRow label="d50 out"          value={summary?.d50_out_mm?.toFixed(2)} unit="mm"/>
            <ResultRow label="d90 out"          value={summary?.d90_out_mm?.toFixed(2)} unit="mm"/>
            <ResultRow label="Fines fraction"   value={((summary?.fines_frac||0)*100).toFixed(1)+' %'}/>
            <ResultRow label="η rotation"       value={(r.eta_rot*100)?.toFixed(1)+' %'}/>
            <ResultRow label="η fill"           value={(r.eta_fill*100)?.toFixed(1)+' %'}/>
            <ResultRow label="η time"           value={(r.eta_time*100)?.toFixed(1)+' %'}/>
            <ResultRow label="Residence time"   value={summary?.t_res_s?.toFixed(0)} unit="s"/>
          </div>
          <AxialChart history={hist} dataKey="d50" label="d50 Particle Size" unit="mm" color={C.blue} refValue={inp.d50} refLabel={`Cut ${inp.d50}mm`}/>
          <AxialChart history={hist} dataKey="mass_flow" label="Mass Flow" unit="t/h" color={C.amber}/>
        </>}
        {!r && !loading && !err && <EmptyState icon="⚖️" name="Screw Separator" desc="Sigmoid grade efficiency curve (engineering) or Stokes settling (physics). PSD tracked axially. Set d50 cut size and slope k for grade efficiency."/>}
      </>}
    />
  )
}
