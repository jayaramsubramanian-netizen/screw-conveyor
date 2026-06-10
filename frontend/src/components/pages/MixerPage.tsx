import React, { useState } from 'react'
import axios from 'axios'
import { C, Field, Divider, KpiCard, ResultRow, RunBtn, ErrorBanner, EmptyState, ModuleShell } from './ProcessPage'

export default function MixerPage() {
  const [r, setR] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string|null>(null)

  const [inp, setInp] = useState({
    D:0.4, L:4, N:40, rho:1.2, fill:0.45, pr:1.0,
    mtype:'ribbon', mode:'continuous', shaft_mode:'single',
    psz:1.0, psz2:1.0,
  })
  const s = (k:string) => (v:any) => setInp(p=>({...p,[k]:v}))

  const run = async () => {
    setLoading(true); setErr(null)
    try {
      const {data} = await axios.post('/api/v1/process/mixer', inp)
      setR(data)
    } catch(e:any) { setErr(e?.response?.data?.detail||e?.message||'Error') }
    finally { setLoading(false) }
  }

  const laceyColor = (M:number) => M>=0.9?C.green:M>=0.75?C.teal:M>=0.5?C.amber:C.red
  const laceyLabel = (M:number) => M>=0.9?'Excellent':M>=0.75?'Good':M>=0.5?'Moderate':'Poor'

  return (
    <ModuleShell
      inputPanel={<>
        <div style={{marginBottom:10}}>
          <div style={{fontSize:20,marginBottom:3}}>🌀</div>
          <div style={{fontSize:12,fontWeight:800,color:C.accent,fontFamily:"'Barlow Condensed',sans-serif",letterSpacing:'0.08em'}}>SCREW MIXER</div>
          <div style={{fontSize:9,color:C.muted,marginTop:3,lineHeight:1.6}}>Newton number · Lacey index · Axial Dispersion Model · Flow regime</div>
        </div>
        <Divider label="Geometry"/>
        <Field label="Diameter" value={inp.D} setter={s('D')} min={0.1} max={1.5} step={0.05} unit="m"/>
        <Field label="Length" value={inp.L} setter={s('L')} min={0.5} max={40} step={0.5} unit="m"/>
        <Field label="Pitch ratio P/D" value={inp.pr} setter={s('pr')} min={0.3} max={2} step={0.1}/>
        <Divider label="Drive"/>
        <Field label="Speed" value={inp.N} setter={s('N')} min={2} max={200} step={1} unit="RPM"/>
        <Field label="Fill fraction" value={inp.fill} setter={s('fill')} min={0.1} max={0.9} step={0.05}/>
        <Divider label="Material"/>
        <Field label="Bulk density" value={inp.rho} setter={s('rho')} min={0.1} max={3} step={0.05} unit="t/m³"/>
        <Field label="Particle size 1" value={inp.psz} setter={s('psz')} min={0.01} max={50} step={0.1} unit="mm"/>
        <Field label="Particle size 2" value={inp.psz2} setter={s('psz2')} min={0.01} max={50} step={0.1} unit="mm"/>
        <Divider label="Configuration"/>
        <Field label="Mixer type" value={inp.mtype} setter={s('mtype')} options={[
          {value:'ribbon',label:'🎗️ Ribbon — axial transport'},
          {value:'paddle',label:'🏓 Paddle — radial mixing'},
          {value:'plough',label:'🔱 Plough/Shovel — intensive'},
          {value:'screw', label:'🔩 Screw — conveying'},
        ]}/>
        <Field label="Operation mode" value={inp.mode} setter={s('mode')} options={[
          {value:'continuous',label:'Continuous'},
          {value:'batch',     label:'Batch'},
        ]}/>
        <Field label="Shaft configuration" value={inp.shaft_mode} setter={s('shaft_mode')} options={[
          {value:'single',       label:'Single shaft'},
          {value:'twin_co',      label:'Twin co-rotating'},
          {value:'twin_counter', label:'Twin counter-rotating'},
          {value:'multi_3',      label:'Triple shaft'},
        ]}/>
        <RunBtn onClick={run} loading={loading}/>
      </>}
      resultPanel={<>
        {err && <ErrorBanner msg={err}/>}
        {r && <>
          <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:8}}>
            <KpiCard label="Lacey M" value={(r.M_adm*100)?.toFixed(1)||'—'} unit="%"
              col={laceyColor(r.M_adm||0)} sub={laceyLabel(r.M_adm||0)}/>
            <KpiCard label="Flow Regime" value={r.regime||'—'}
              col={r.regime==='Rolling'?C.green:r.regime==='Cascading'?C.amber:C.red}/>
            <KpiCard label="Power" value={r.P_mix_kW?.toFixed(2)||'—'} unit="kW" col={C.purple}/>
            <KpiCard label="Froude Fr" value={r.Fr?.toFixed(4)||'—'} col={C.blue} sub="Fr<0.5 = rolling"/>
          </div>

          {/* Quality band */}
          <div style={{background:C.panel,border:`1px solid ${C.border}33`,borderRadius:8,padding:'10px 14px',
            borderLeft:`4px solid ${laceyColor(r.M_adm||0)}`}}>
            <div style={{display:'flex',alignItems:'center',gap:10}}>
              <div style={{fontSize:20,fontWeight:800,fontFamily:'monospace',color:laceyColor(r.M_adm||0)}}>
                M = {((r.M_adm||0)*100).toFixed(1)}%
              </div>
              <div>
                <div style={{fontSize:11,fontWeight:700,color:laceyColor(r.M_adm||0)}}>{laceyLabel(r.M_adm||0)} mixing quality</div>
                <div style={{fontSize:9,color:C.muted}}>Lacey index via ADM correction · Pe = {r.Pe?.toFixed(1)} · k_eff = {r.k_eff?.toFixed(4)} 1/s</div>
              </div>
            </div>
          </div>

          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:10}}>
            <div style={{background:C.panel,border:`1px solid ${C.border}`,borderRadius:8,padding:12}}>
              <div style={{fontSize:9,fontWeight:700,color:C.accent,letterSpacing:'0.10em',marginBottom:8,textTransform:'uppercase' as const,fontFamily:"'Barlow Condensed',sans-serif"}}>⚙️ Mixing Kinetics</div>
              <ResultRow label="k_eff (mixing rate)" value={r.k_eff?.toFixed(5)} unit="1/s"/>
              <ResultRow label="Lacey M (classical)" value={((r.M_lacey||0)*100).toFixed(1)} unit="%"/>
              <ResultRow label="Lacey M (ADM)"       value={((r.M_adm||0)*100).toFixed(1)} unit="%" ok={(r.M_adm||0)>=0.75}/>
              <ResultRow label="Peclet Pe"           value={r.Pe?.toFixed(2)}/>
              <ResultRow label="t_mix 95%"           value={r.t_mix_s?.toFixed(0)} unit="s"/>
              <ResultRow label="t_res"               value={r.t_res_s?.toFixed(0)} unit="s"/>
            </div>
            <div style={{background:C.panel,border:`1px solid ${C.border}`,borderRadius:8,padding:12}}>
              <div style={{fontSize:9,fontWeight:700,color:C.accent,letterSpacing:'0.10em',marginBottom:8,textTransform:'uppercase' as const,fontFamily:"'Barlow Condensed',sans-serif"}}>💡 Power & Structure</div>
              <ResultRow label="Power"         value={r.P_mix_kW?.toFixed(3)} unit="kW"/>
              <ResultRow label="Torque"        value={r.Tr_Nm?.toFixed(0)} unit="Nm"/>
              <ResultRow label="Newton Ne"     value={r.Ne?.toFixed(2)}/>
              <ResultRow label="Froude Fr"     value={r.Fr?.toFixed(4)}/>
              <ResultRow label="Shear rate"    value={r.shear_rate?.toFixed(1)} unit="1/s"/>
              <ResultRow label="Tip speed"     value={(Math.PI*inp.D*inp.N/60).toFixed(3)} unit="m/s"/>
            </div>
          </div>

          <div style={{background:C.panel,border:`1px solid ${C.border}`,borderRadius:8,padding:12}}>
            <div style={{fontSize:9,fontWeight:700,color:C.accent,letterSpacing:'0.10em',marginBottom:8,textTransform:'uppercase' as const,fontFamily:"'Barlow Condensed',sans-serif"}}>📋 Design Check</div>
            <ResultRow label="Fill vs max" value={`${(inp.fill*100).toFixed(0)}% / ${((r.fill_max||0)*100).toFixed(0)}% max`} ok={r.fill_ok}/>
            <ResultRow label="Regime"      value={r.regime} ok={r.regime_ok}/>
            <ResultRow label="Mode"        value={r.mode}/>
            <ResultRow label="Shafts"      value={r.ns}/>
            <ResultRow label="v_axial"     value={r.v_axial?.toFixed(4)} unit="m/s"/>
            <ResultRow label="Slip S"      value={r.slip_S?.toFixed(3)}/>
          </div>
        </>}
        {!r && !loading && !err && <EmptyState icon="🌀" name="Screw Mixer" desc="Newton number power model with Lacey mixing index and axial dispersion RTD correction. Supports ribbon, paddle, plough, and screw types. Single, twin, and triple shaft configurations."/>}
      </>}
    />
  )
}
