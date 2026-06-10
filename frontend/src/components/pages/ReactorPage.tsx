import React, { useState } from 'react'
import axios from 'axios'
import { C, Field, Divider, KpiCard, ResultRow, AxialChart, RunBtn, ErrorBanner, EmptyState, ModuleShell } from './ProcessPage'

export default function ReactorPage() {
  const [r, setR] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string|null>(null)

  const [inp, setInp] = useState({
    diam:0.3, Lr:4, Nr:30, fillR:0.35,
    feed:3, rho:1.2, tIn:20, tProc:150,
    rxn:'thermal', Ea_kJ:0, k0:0.08, dHrxn:0, CpR:1000,
    D_ax:0.005, resReq:15,
  })
  const s = (k:string) => (v:any) => setInp(p=>({...p,[k]:v}))

  const run = async () => {
    setLoading(true); setErr(null)
    try {
      const {data} = await axios.post('/api/v1/process/reactor', {...inp,len:inp.Lr})
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
          <div style={{fontSize:20,marginBottom:3}}>⚗️</div>
          <div style={{fontSize:12,fontWeight:800,color:C.accent,fontFamily:"'Barlow Condensed',sans-serif",letterSpacing:'0.08em'}}>SCREW REACTOR</div>
          <div style={{fontSize:9,color:C.muted,marginTop:3,lineHeight:1.6}}>Arrhenius kinetics · Damköhler number · ADM RTD correction</div>
        </div>
        <Divider label="Geometry"/>
        <Field label="Diameter" value={inp.diam} setter={s('diam')} min={0.1} max={1.2} step={0.05} unit="m"/>
        <Field label="Length" value={inp.Lr} setter={s('Lr')} min={1} max={40} step={0.5} unit="m"/>
        <Divider label="Drive"/>
        <Field label="Speed" value={inp.Nr} setter={s('Nr')} min={2} max={120} step={1} unit="RPM"/>
        <Field label="Fill fraction" value={inp.fillR} setter={s('fillR')} min={0.1} max={0.6} step={0.05}/>
        <Divider label="Feed"/>
        <Field label="Feed rate" value={inp.feed} setter={s('feed')} min={0.1} max={500} step={1} unit="t/h"/>
        <Field label="Bulk density" value={inp.rho} setter={s('rho')} min={0.1} max={3} step={0.05} unit="t/m³"/>
        <Field label="Feed temperature" value={inp.tIn} setter={s('tIn')} min={0} max={500} step={5} unit="°C"/>
        <Divider label="Kinetics"/>
        <Field label="Reaction type" value={inp.rxn} setter={s('rxn')} options={[
          {value:'thermal',label:'Thermal decomposition'},
          {value:'chemical',label:'Chemical reaction'},
          {value:'biological',label:'Biological/enzymatic'},
          {value:'calcination',label:'Calcination'},
        ]}/>
        <Field label="Activation energy Ea" value={inp.Ea_kJ} setter={s('Ea_kJ')} min={0} max={200} step={5} unit="kJ/mol"/>
        <Field label="Rate constant k₀ (Ea=0: use as k)" value={inp.k0} setter={s('k0')} min={0.0001} max={10} step={0.001} unit="1/s"/>
        <Field label="Heat of reaction ΔH" value={inp.dHrxn} setter={s('dHrxn')} min={-500} max={500} step={10} unit="kJ/mol"/>
        <Field label="Cp solid" value={inp.CpR} setter={s('CpR')} min={200} max={4000} step={50} unit="J/kgK"/>
        <Divider label="RTD"/>
        <Field label="Axial dispersion D_ax" value={inp.D_ax} setter={s('D_ax')} min={0.0001} max={0.1} step={0.001} unit="m²/s"/>
        <Field label="Min residence required" value={inp.resReq} setter={s('resReq')} min={1} max={300} step={1} unit="min"/>
        <RunBtn onClick={run} loading={loading}/>
      </>}
      resultPanel={<>
        {err && <ErrorBanner msg={err}/>}
        {r && <>
          <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:8}}>
            <KpiCard label="Conversion X" value={r.conv?.toFixed(1)||'—'} unit="%" col={r.conv>80?C.green:r.conv>50?C.amber:C.red}/>
            <KpiCard label="Damköhler Da" value={r.Da?.toFixed(2)||'—'} ok={r.Da>=1} sub="Da≥1 = reaction limited"/>
            <KpiCard label="Peclet Pe" value={r.Pe_r?.toFixed(1)||'—'} col={C.purple} sub="Pe>10 = plug flow"/>
            <KpiCard label="t_res" value={r.res_min?.toFixed(1)||'—'} unit="min" ok={r.ok} sub={`req ≥${inp.resReq}min`}/>
          </div>
          <div style={{background:C.panel,border:`1px solid ${C.border}`,borderRadius:8,padding:12}}>
            <div style={{fontSize:9,fontWeight:700,color:C.accent,letterSpacing:'0.10em',marginBottom:8,textTransform:'uppercase' as const,fontFamily:"'Barlow Condensed',sans-serif"}}>📊 Reactor Summary</div>
            <ResultRow label="Conversion X"     value={r.conv?.toFixed(2)+' %'} ok={r.conv>=80}/>
            <ResultRow label="Damköhler Da"     value={r.Da?.toFixed(3)} ok={r.Da>=1}/>
            <ResultRow label="Peclet number"    value={r.Pe_r?.toFixed(1)}/>
            <ResultRow label="Residence time"   value={r.res_min?.toFixed(2)+' min'} ok={r.ok}/>
            <ResultRow label="Required"         value={'≥'+inp.resReq+' min'}/>
            <ResultRow label="T outlet"         value={summary?.T_out?.toFixed(1)} unit="°C"/>
            <ResultRow label="Axial velocity"   value={summary?.v_ax?.toFixed(4)} unit="m/s"/>
          </div>
          <AxialChart history={hist} dataKey="X_conv" label="Conversion X" unit="%" color={C.green}/>
          <AxialChart history={hist} dataKey="T" label="Temperature" unit="°C" color={C.red}/>
        </>}
        {!r && !loading && !err && <EmptyState icon="⚗️" name="Screw Reactor" desc="Arrhenius kinetics with Damköhler and Peclet analysis. Axial dispersion model (ADM) Danckwerts RTD correction. Set Ea=0 to use k₀ as direct rate constant."/>}
      </>}
    />
  )
}
