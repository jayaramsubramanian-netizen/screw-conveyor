import React, { useState } from 'react'
import axios from 'axios'
import { C, Field, Divider, KpiCard, ResultRow, AxialChart, RunBtn, ErrorBanner, EmptyState, ModuleShell } from './ProcessPage'

export default function DryerPage() {
  const [r, setR] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string|null>(null)

  const [inp, setInp] = useState({
    diam:0.4, len:6, speedDry:40, fillDry:0.35,
    feed:5, rho:1.2, tIn:20, mIn:18, mOut:5,
    tTr:120, U:50, d_p:0.003, k_solid:0.3, CpDry:1800,
  })
  const s = (k:string) => (v:any) => setInp(p=>({...p,[k]:v}))

  const run = async () => {
    setLoading(true); setErr(null)
    try {
      const {data} = await axios.post('/api/v1/process/dryer', inp)
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
          <div style={{fontSize:20,marginBottom:3}}>🌡️</div>
          <div style={{fontSize:12,fontWeight:800,color:C.accent,fontFamily:"'Barlow Condensed',sans-serif",letterSpacing:'0.08em'}}>SCREW DRYER</div>
          <div style={{fontSize:9,color:C.muted,marginTop:3,lineHeight:1.6}}>LMTD heat transfer · Two-phase drying kinetics · D_factor scale correction</div>
        </div>
        <Divider label="Geometry"/>
        <Field label="Diameter" value={inp.diam} setter={s('diam')} min={0.1} max={1.2} step={0.05} unit="m"/>
        <Field label="Length" value={inp.len} setter={s('len')} min={1} max={40} step={0.5} unit="m"/>
        <Divider label="Drive"/>
        <Field label="Speed" value={inp.speedDry} setter={s('speedDry')} min={5} max={120} step={1} unit="RPM"/>
        <Field label="Fill fraction" value={inp.fillDry} setter={s('fillDry')} min={0.1} max={0.6} step={0.05}/>
        <Divider label="Feed"/>
        <Field label="Feed rate" value={inp.feed} setter={s('feed')} min={0.1} max={500} step={1} unit="t/h"/>
        <Field label="Bulk density" value={inp.rho} setter={s('rho')} min={0.1} max={3} step={0.05} unit="t/m³"/>
        <Field label="Moisture in" value={inp.mIn} setter={s('mIn')} min={1} max={80} step={1} unit="% wb"/>
        <Field label="Target moisture" value={inp.mOut} setter={s('mOut')} min={0.1} max={20} step={0.5} unit="% wb"/>
        <Divider label="Thermal"/>
        <Field label="Wall temperature" value={inp.tTr} setter={s('tTr')} min={40} max={400} step={5} unit="°C"/>
        <Field label="Feed temperature" value={inp.tIn} setter={s('tIn')} min={0} max={100} step={1} unit="°C"/>
        <Field label="Overall U" value={inp.U} setter={s('U')} min={5} max={300} step={5} unit="W/m²K"/>
        <Divider label="Material"/>
        <Field label="Particle size" value={inp.d_p} setter={s('d_p')} min={0.0001} max={0.05} step={0.001} unit="m"/>
        <Field label="k solid" value={inp.k_solid} setter={s('k_solid')} min={0.05} max={2} step={0.05} unit="W/mK"/>
        <Field label="Cp dry solid" value={inp.CpDry} setter={s('CpDry')} min={200} max={4000} step={50} unit="J/kgK"/>
        <RunBtn onClick={run} loading={loading}/>
      </>}
      resultPanel={<>
        {err && <ErrorBanner msg={err}/>}
        {r && <>
          {/* KPI row */}
          <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:8}}>
            <KpiCard label="Moisture Out" value={r.mOut_actual?.toFixed(1)||'—'} unit="%" ok={r.target_met} sub={`target ≤${inp.mOut}%`}/>
            <KpiCard label="Energy Intensity" value={r.kWh_kgWater?.toFixed(3)||'—'} unit="kWh/kg" col={C.amber}/>
            <KpiCard label="Thermal Eff." value={r.eff!=null?(r.eff*100).toFixed(1):'—'} unit="%" col={C.blue}/>
            <KpiCard label="T out" value={summary?.T_out?.toFixed(0)||'—'} unit="°C" col={C.purple}/>
          </div>
          {/* Summary */}
          <div style={{background:C.panel,border:`1px solid ${C.border}`,borderRadius:8,padding:12}}>
            <div style={{fontSize:9,fontWeight:700,color:C.accent,letterSpacing:'0.10em',marginBottom:8,textTransform:'uppercase' as const,fontFamily:"'Barlow Condensed',sans-serif"}}>📊 Drying Summary</div>
            <ResultRow label="Moisture in"   value={inp.mIn+' %'}/>
            <ResultRow label="Moisture out"  value={r.mOut_actual?.toFixed(2)+' %'} ok={r.target_met}/>
            <ResultRow label="Target"        value={'≤'+inp.mOut+' %'}/>
            <ResultRow label="Water evap'd"  value={summary?.W_evap_tph?.toFixed(3)} unit="t/h"/>
            <ResultRow label="Heat duty"     value={summary?.Q_total_kW?.toFixed(1)} unit="kW"/>
            <ResultRow label="kWh/kg water"  value={r.kWh_kgWater?.toFixed(3)} unit="kWh/kg"/>
            <ResultRow label="Thermal eff."  value={(r.eff*100)?.toFixed(1)} unit="%"/>
            <ResultRow label="Residence time" value={summary?.t_res_s?.toFixed(0)} unit="s"/>
            <ResultRow label="Axial velocity" value={summary?.v_ax?.toFixed(4)} unit="m/s"/>
          </div>
          {/* Charts */}
          <AxialChart history={hist} dataKey="moisture" label="Moisture" unit="% wb" color={C.blue} refValue={inp.mOut} refLabel={`Target ${inp.mOut}%`}/>
          <AxialChart history={hist} dataKey="T" label="Temperature" unit="°C" color={C.red} refValue={inp.tTr} refLabel={`Wall ${inp.tTr}°C`}/>
          <AxialChart history={hist} dataKey="Q_cumul" label="Cumulative Heat" unit="kW·s" color={C.amber}/>
        </>}
        {!r && !loading && !err && <EmptyState icon="🌡️" name="Screw Dryer" desc="LMTD heat transfer with two-phase drying kinetics. Constant-rate phase (heat limited) and falling-rate phase (diffusion limited) tracked per segment."/>}
      </>}
    />
  )
}
