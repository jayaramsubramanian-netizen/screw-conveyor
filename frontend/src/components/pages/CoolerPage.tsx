import React, { useState } from 'react'
import axios from 'axios'
import { C, Field, Divider, KpiCard, ResultRow, AxialChart, RunBtn, ErrorBanner, EmptyState, ModuleShell } from './ProcessPage'

export default function CoolerPage() {
  const [r, setR] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string|null>(null)

  const [inp, setInp] = useState({
    diam:0.4, Lc:6, speedCool:40, fillC2:0.35,
    feed:5, rho:1.2, tInC:200, tTgtC:80, coolIn:20,
    U:50, Cp:900, d_p_c:0.005, k_sol_c:0.4,
  })
  const s = (k:string) => (v:any) => setInp(p=>({...p,[k]:v}))

  const run = async () => {
    setLoading(true); setErr(null)
    try {
      const {data} = await axios.post('/api/v1/process/cooler', inp)
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
          <div style={{fontSize:20,marginBottom:3}}>❄️</div>
          <div style={{fontSize:12,fontWeight:800,color:C.accent,fontFamily:"'Barlow Condensed',sans-serif",letterSpacing:'0.08em'}}>SCREW COOLER</div>
          <div style={{fontSize:9,color:C.muted,marginTop:3,lineHeight:1.6}}>NTU-effectiveness · Moving-bed correction · Composite wall resistance</div>
        </div>
        <Divider label="Geometry"/>
        <Field label="Diameter" value={inp.diam} setter={s('diam')} min={0.1} max={1.2} step={0.05} unit="m"/>
        <Field label="Length" value={inp.Lc} setter={s('Lc')} min={1} max={40} step={0.5} unit="m"/>
        <Divider label="Drive"/>
        <Field label="Speed" value={inp.speedCool} setter={s('speedCool')} min={5} max={120} step={1} unit="RPM"/>
        <Field label="Fill fraction" value={inp.fillC2} setter={s('fillC2')} min={0.1} max={0.6} step={0.05}/>
        <Divider label="Feed"/>
        <Field label="Feed rate" value={inp.feed} setter={s('feed')} min={0.1} max={500} step={1} unit="t/h"/>
        <Field label="Bulk density" value={inp.rho} setter={s('rho')} min={0.1} max={3} step={0.05} unit="t/m³"/>
        <Field label="Material temp in" value={inp.tInC} setter={s('tInC')} min={20} max={800} step={5} unit="°C"/>
        <Field label="Target temp out" value={inp.tTgtC} setter={s('tTgtC')} min={10} max={300} step={5} unit="°C"/>
        <Divider label="Cooling"/>
        <Field label="Coolant temperature" value={inp.coolIn} setter={s('coolIn')} min={-20} max={100} step={1} unit="°C"/>
        <Field label="Overall U" value={inp.U} setter={s('U')} min={5} max={300} step={5} unit="W/m²K"/>
        <Divider label="Material"/>
        <Field label="Cp solid" value={inp.Cp} setter={s('Cp')} min={200} max={4000} step={50} unit="J/kgK"/>
        <Field label="Particle size" value={inp.d_p_c} setter={s('d_p_c')} min={0.0001} max={0.05} step={0.001} unit="m"/>
        <Field label="k solid" value={inp.k_sol_c} setter={s('k_sol_c')} min={0.05} max={2} step={0.05} unit="W/mK"/>
        <RunBtn onClick={run} loading={loading}/>
      </>}
      resultPanel={<>
        {err && <ErrorBanner msg={err}/>}
        {r && <>
          <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:8}}>
            <KpiCard label="T out" value={summary?.T_out?.toFixed(0)||'—'} unit="°C" ok={r.target_met} sub={`target ≤${inp.tTgtC}°C`}/>
            <KpiCard label="ε Effectiveness" value={r.eps_actual!=null?(r.eps_actual*100).toFixed(1):'—'} unit="%" col={C.blue}/>
            <KpiCard label="Q Actual" value={r.Q_actual_kW?.toFixed(1)||'—'} unit="kW" col={C.teal}/>
            <KpiCard label="NTU" value={r.NTU?.toFixed(2)||'—'} col={C.purple}/>
          </div>
          <div style={{background:C.panel,border:`1px solid ${C.border}`,borderRadius:8,padding:12}}>
            <div style={{fontSize:9,fontWeight:700,color:C.accent,letterSpacing:'0.10em',marginBottom:8,textTransform:'uppercase' as const,fontFamily:"'Barlow Condensed',sans-serif"}}>📊 Cooling Summary</div>
            <ResultRow label="T material in"    value={inp.tInC+' °C'}/>
            <ResultRow label="T material out"   value={summary?.T_out?.toFixed(1)+' °C'} ok={r.target_met}/>
            <ResultRow label="Target"           value={'≤'+inp.tTgtC+' °C'}/>
            <ResultRow label="Q design duty"    value={r.Qd_target?.toFixed(1)} unit="kW"/>
            <ResultRow label="Q achieved"       value={r.Q_actual_kW?.toFixed(1)} unit="kW"/>
            <ResultRow label="Effectiveness ε"  value={(r.eps_actual*100)?.toFixed(1)} unit="%"/>
            <ResultRow label="NTU"              value={r.NTU?.toFixed(3)}/>
            <ResultRow label="Residence time"   value={summary?.t_res_s?.toFixed(0)} unit="s"/>
            <ResultRow label="Axial velocity"   value={summary?.v_ax?.toFixed(4)} unit="m/s"/>
          </div>
          <AxialChart history={hist} dataKey="T" label="Temperature" unit="°C" color={C.blue} refValue={inp.tTgtC} refLabel={`Target ${inp.tTgtC}°C`}/>
          <AxialChart history={hist} dataKey="Q_cumul" label="Cumulative Heat Removed" unit="kW·s" color={C.teal}/>
        </>}
        {!r && !loading && !err && <EmptyState icon="❄️" name="Screw Cooler" desc="NTU-effectiveness method with moving-bed non-ideality correction. Composite wall + particle contact resistance tracked per segment."/>}
      </>}
    />
  )
}
