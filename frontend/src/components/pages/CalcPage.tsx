/**
 * CalcPage.tsx — VECTRIX™ Screw Conveyor Designer v2.4
 *
 * Full feature parity with HTML prototype including:
 *   CEMA | DIN | Custom standards tabs (top of results)
 *   Standards Comparison table (all three results side by side)
 *   Design Health dashboard
 *   Auto Shaft Design card + Pipe Option
 *   Bearing Life card + Wear Life card + Cost Estimate card
 *   Design Efficiency Score card + Gearbox & Motor card
 *   Material & Surface Recommendations
 *   Power Breakdown bar chart + Parametric Sweep
 *   Structural Engineering Module
 *   Axial Profiles (7 tabs) + Shaft Deflection
 *   Auto-Optimise | Explain | Print toolbar
 */
import React, { useState, useMemo, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer,
} from 'recharts'
import { useCalcStore, useCalculate, useMaterials, useBearings, useGearboxes } from '../../hooks/useCalculator'
import * as api from '../../api/client'
import type { ProjectMeta } from '../../App'

// ── Colours ─────────────────────────────────────────────────────
const C = {
  panel:'#0d1c2e', border:'#162438', text:'#ddeaf6',
  muted:'#5a7a9a', faint:'#3a5470', accent:'#c8192e',
  green:'#1fb86e', red:'#e05252', amber:'#d98e00', blue:'#4a9eff',
  teal:'#2dd4bf', purple:'#a78bfa',
}
const ss = (s: React.CSSProperties) => s

// ── calcStructural (matches HTML prototype exactly) ──────────────
function calcStructural(D_m:number, L_m:number, rho:number, ang:number, fill=0.35, abr='Medium', temp=20){
  const rk=rho*1000, g=9.81
  const sa=temp>200?100e6:temp>150?120e6:160e6
  const sw=sa*0.7, sb=144e6
  const fd=D_m*fill*1.3, Ph=rk*g*fd, Pd=Ph*1.3
  const hs=Math.min(L_m, D_m>=0.45?3.6:D_m>=0.3?3.0:2.4)
  const wm=rk*(Math.PI/4)*D_m*D_m*fill*g
  const wt=22*D_m*g*(1+0.1*temp/200)
  const ww=wm+wt
  const Mm=ww*hs*hs/8
  const tb=Math.sqrt(4*Mm/(Math.PI*D_m*sa))
  const Dm=D_m*1000
  const tcm=Dm<150?3:Dm<250?4:Dm<400?5:Dm<600?6:Dm<900?8:10
  const wa2=abr==='High'||abr==='Very High'?4:abr==='Medium'?3:2
  const tc=Math.max(tb,Pd*D_m/(2*sa))*1000
  const PLATE=[3,4,5,6,8,10,12,14,16,20,25,30]
  const tp=PLATE.find(t=>t>=Math.max(Math.ceil(tc+wa2),tcm))||30
  const Pc=1200*g/(0.06*D_m)+2000
  const tcc=Math.sqrt(3*Pc*D_m*D_m/(16*sa))*1000
  const tc2=PLATE.find(t=>t>=Math.max(tcc+2,tcm+1))||12
  const PCD=D_m+2*(tp/1000)+0.05
  const nb=Math.ceil(Math.ceil(Math.max(4,4*Math.ceil(Math.PI*PCD*1000/160))/4)*4)
  const bp=Math.PI*PCD*1000/nb
  const Fp=Pd*(Math.PI/4)*D_m*D_m+2*Math.PI*(D_m/2)*0.015*6895
  const Fe=Fp/nb, Ab=Fe/sb
  const dr=Math.sqrt(4*Ab/Math.PI)*1000
  const BS=[{d:8,A:36.6e-6},{d:10,A:58e-6},{d:12,A:84.3e-6},{d:16,A:157e-6},{d:20,A:245e-6},{d:24,A:353e-6}]
  const bs=BS.find(b=>b.d>=Math.max(dr,8))||BS[BS.length-1]
  const sb_act=Fe/bs.A/1e6
  const ns=Math.max(2,Math.ceil(L_m/hs)+1)
  const Rs=ww*L_m/ns
  const wh=Math.max(3,Math.ceil(Pd*D_m/(2*sw*0.707)*1000))
  const sm=Math.round(7850*Math.PI*D_m*0.006*L_m+(Math.PI/4*D_m*D_m*L_m*fill*rk))
  const tm=Math.round(7850*Math.PI*D_m*(tp/1000)*L_m)
  return{
    w_total:+(ww/1000).toFixed(3), M_max:+(Mm/1000).toFixed(3),
    hanger_span:+hs.toFixed(2), t_plate:tp, t_cover:tc2,
    bolt_size:`M${bs.d} gr.8.8`, n_bolts:nb, bolt_pitch:+bp.toFixed(0),
    bolt_ok:sb_act<=144, bolt_cap:+((bs.A*144e6*nb/1000)).toFixed(1),
    pressure_load:+(Fe/1000).toFixed(1), weld_size:wh,
    flange_t:PLATE.find(t=>t>=Math.max(tp,11))||14,
    flange_w:Math.round(Dm*0.12+20), cover_bp:Math.round(Math.min(150,Dm/3)),
    n_supports:ns, R_kN:+(Rs/1000).toFixed(1), screw_mass:sm, trough_mass:tm,
    end_react:+((ww*L_m/2)/1000).toFixed(1), sigma_allow:+(sa/1e6).toFixed(0),
    key_b:Dm>=100?28:Dm>=85?25:Dm>=70?20:16,
  }
}

// ── Shared primitives ────────────────────────────────────────────
const Lbl=({c,children}:{c?:React.ReactNode,children:React.ReactNode})=>(
  <div style={ss({fontSize:10,color:C.muted,fontWeight:700,textTransform:'uppercase',
    letterSpacing:'0.07em',marginBottom:3})}>{children}{c&&<span style={ss({marginLeft:4,fontWeight:400,textTransform:'none'})}>{c}</span>}</div>
)
const Divider=({label}:{label?:string})=>(
  <div style={ss({display:'flex',alignItems:'center',gap:6,margin:'10px 0 7px'})}>
    {label&&<span style={ss({fontSize:9,color:C.faint,fontWeight:700,letterSpacing:'0.09em',whiteSpace:'nowrap'})}>{label}</span>}
    <div style={ss({flex:1,height:1,background:C.border})}/>
  </div>
)
const SHdr=({icon,label,badge,col}:{icon:string,label:string,badge?:React.ReactNode,col?:string})=>(
  <div style={ss({display:'flex',alignItems:'center',gap:6,marginBottom:8})}>
    <span style={ss({fontSize:11})}>{icon}</span>
    <span style={ss({fontSize:9,fontWeight:700,color:col||C.accent,letterSpacing:'0.09em',textTransform:'uppercase',flex:1})}>{label}</span>
    {badge}
  </div>
)
const RR=({label,value,unit='',ok,hl,sub}:{label:string,value?:string|number,unit?:string,ok?:boolean,hl?:boolean,sub?:string})=>{
  if(value==null)return null
  const col=ok===true?C.green:ok===false?C.red:hl?C.accent:C.text
  return(
    <div style={ss({display:'flex',justifyContent:'space-between',alignItems:'baseline',
      borderBottom:`1px solid ${C.border}`,padding:'4px 0',fontSize:11,background:hl?'rgba(232,160,0,.04)':'transparent'})}>
      <span style={ss({color:C.muted})}>{label}{sub&&<span style={ss({fontSize:9,color:C.faint,marginLeft:4})}>{sub}</span>}</span>
      <span style={ss({fontFamily:'monospace',fontWeight:700,color:col})}>
        {value}{unit&&<span style={ss({color:C.muted,fontWeight:400,marginLeft:3})}>{unit}</span>}
      </span>
    </div>
  )
}
const Chip=({ok,label}:{ok:boolean,label:string})=>(
  <span style={ss({fontSize:9,fontWeight:700,padding:'2px 7px',borderRadius:4,
    background:ok?'rgba(31,184,110,.15)':'rgba(224,82,82,.15)',
    color:ok?C.green:C.red,border:`1px solid ${ok?C.green:C.red}`})}>{label}</span>
)
const Panel=({children,bordered=true}:{children:React.ReactNode,bordered?:boolean})=>(
  <div style={ss({background:C.panel,border:bordered?`1px solid ${C.border}`:'none',borderRadius:9,padding:12})}>{children}</div>
)

// ── Input primitives ─────────────────────────────────────────────
const NI=({field,label,min,max,step=0.01,unit}:{field:string,label:string,min?:number,max?:number,step?:number,unit?:string})=>{
  const{inp,setInp}=useCalcStore()
  return(
    <div style={ss({marginBottom:7})}>
      <Lbl c={unit&&`(${unit})`}>{label}</Lbl>
      <input type="number" value={(inp as any)[field] ?? ''} min={min} max={max} step={step}
        onChange={e=>setInp({[field]:parseFloat(e.target.value)||0})}
        style={ss({width:'100%',background:'#081321',border:`1px solid ${C.border}`,borderRadius:4,
          padding:'5px 8px',color:C.text,fontSize:11,fontFamily:'monospace',outline:'none',boxSizing:'border-box'})}/>
    </div>
  )
}
const SI=({field,label,options}:{field:string,label:string,options:{value:string,label:string}[]})=>{
  const{inp,setInp}=useCalcStore()
  return(
    <div style={ss({marginBottom:7})}>
      <Lbl>{label}</Lbl>
      <select value={(inp as any)[field]} onChange={e=>setInp({[field]:e.target.value})}
        style={ss({width:'100%',background:'#081321',border:`1px solid ${C.border}`,borderRadius:4,
          padding:'5px 8px',color:C.text,fontSize:11,fontFamily:'inherit',outline:'none',boxSizing:'border-box'})}>
        {options.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  )
}
const Ck=({field,label}:{field:string,label:string})=>{
  const{inp,setInp}=useCalcStore()
  return(
    <label style={ss({display:'flex',alignItems:'center',gap:6,fontSize:11,color:C.muted,cursor:'pointer',marginBottom:5})}>
      <input type="checkbox" checked={!!(inp as any)[field]} onChange={e=>setInp({[field]:e.target.checked})}/>
      {label}
    </label>
  )
}

// ── Standards tab component ──────────────────────────────────────
const STD_DEFS: Record<string, {lam:number, flag:string, label:string, desc:string}> = {
  CEMA:   {lam:1.00, flag:'🇺🇸', label:'CEMA 7th Ed.',  desc:'CEMA resistance-factor method. λ multiplier = 1.00 (baseline).'},
  DIN:    {lam:1.01, flag:'🇩🇪', label:'DIN 15262',     desc:'German DIN λ-coefficient method. +1% on material λ.'},
  Custom: {lam:1.05, flag:'⚙️',  label:'Custom',        desc:'User-defined λ-multiplier. Adjust to match field data or project spec.'},
}

function StdTabs({activeStd, setStd, customLam, setCustomLam, multiR, matLam, matName}:{
  activeStd:string, setStd:(s:string)=>void,
  customLam:number, setCustomLam:(v:number)=>void,
  multiR:Record<string,any>|null, matLam:number, matName:string
}){
  const def = STD_DEFS[activeStd]
  const lamMult = activeStd==='Custom' ? customLam : def?.lam || 1.0
  const effLam  = (matLam * lamMult).toFixed(3)
  return(
    <div style={ss({marginBottom:12})}>
      {/* Tab buttons */}
      <div style={ss({display:'flex',gap:0,borderBottom:`2px solid ${C.border}`,marginBottom:12})}>
        {Object.entries(STD_DEFS).map(([key,d])=>(
          <button key={key} onClick={()=>setStd(key)}
            style={ss({padding:'7px 18px',border:'none',cursor:'pointer',fontWeight:700,fontSize:12,
              background:'transparent',fontFamily:'inherit',
              color:activeStd===key?C.accent:C.muted,
              borderBottom:activeStd===key?`2px solid ${C.accent}`:'2px solid transparent',
              marginBottom:-2})}>
            {d.flag} {key}
          </button>
        ))}
      </div>

      {/* Lambda explanation */}
      <div style={ss({background:'rgba(74,158,255,.05)',border:'1px solid rgba(74,158,255,.15)',
        borderRadius:7,padding:'8px 12px',marginBottom:10,fontSize:9.5,color:'rgba(221,234,246,.7)',lineHeight:1.6})}>
        <strong style={ss({color:C.blue,fontSize:10})}>λ (Lambda) — How it works: </strong>
        The material λ ({matLam.toFixed(2)} for {matName}) is the CEMA flight resistance factor.
        The standards multiplier ({lamMult.toFixed(2)}) is a method correction factor applied on top.{' '}
        <strong style={ss({color:C.accent})}>Effective λ used in Pm = {matLam.toFixed(2)} × {lamMult.toFixed(2)} = {effLam}</strong>.
        {' '}Pm = Q_design × L × λ_eff × Ks / 367, where 367 = unit conversion (kg·m/min → kW).
      </div>

      {/* Active standard label */}
      <div style={ss({background:'rgba(232,160,0,.06)',border:'1px solid rgba(232,160,0,.2)',
        borderRadius:7,padding:'8px 12px',marginBottom:10})}>
        <div style={ss({display:'flex',alignItems:'center',gap:10,flexWrap:'wrap'})}>
          <div style={ss({flex:1})}>
            <p style={ss({fontSize:11,fontWeight:700,color:C.accent})}>{def?.flag} {def?.label}</p>
            <p style={ss({fontSize:10,color:C.muted})}>{def?.desc}</p>
          </div>
          <div style={ss({textAlign:'right',fontSize:10,fontFamily:'monospace'})}>
            <span style={ss({color:C.muted})}>mat.λ </span><strong style={ss({color:C.text})}>{matLam.toFixed(2)}</strong>
            <span style={ss({color:C.muted,margin:'0 4px'})}>×</span>
            <span style={ss({color:C.muted})}>SF </span><strong style={ss({color:C.accent})}>{lamMult.toFixed(3)}</strong>
            <span style={ss({color:C.muted,margin:'0 4px'})}>=</span>
            <strong style={ss({color:C.green,fontSize:12})}>λ_eff {effLam}</strong>
          </div>
        </div>

        {/* Custom controls */}
        {activeStd==='Custom'&&(
          <div style={ss({marginTop:10,padding:'8px 10px',background:'rgba(0,0,0,.2)',borderRadius:6})}>
            <p style={ss({fontSize:9,fontWeight:700,color:C.accent,textTransform:'uppercase',letterSpacing:'0.07em',marginBottom:6})}>⚙️ Custom Parameters</p>
            <div style={ss({display:'grid',gridTemplateColumns:'1fr 2fr',gap:8,alignItems:'center'})}>
              <label style={ss({fontSize:9,color:C.muted})}>λ Multiplier (0.80–2.00)</label>
              <div style={ss({display:'flex',gap:6,alignItems:'center'})}>
                <input type="number" value={customLam} step={0.01} min={0.8} max={2.0}
                  onChange={e=>setCustomLam(Math.max(0.8,Math.min(2.0,parseFloat(e.target.value)||1.05)))}
                  style={ss({width:70,background:'#081321',border:`1px solid ${C.accent}`,color:C.accent,
                    borderRadius:4,padding:'3px 6px',fontSize:11,fontFamily:'monospace',fontWeight:700})}/>
                <div style={ss({flex:1,height:6,background:'rgba(0,0,0,.3)',borderRadius:3,overflow:'hidden'})}>
                  <div style={ss({width:Math.max(0,Math.min(100,(customLam-0.8)/1.2*100))+'%',height:'100%',
                    background:customLam>1.3?C.red:customLam>1.1?C.amber:C.green,borderRadius:3})}/>
                </div>
                <span style={ss({fontSize:9,color:C.muted,minWidth:70})}>
                  {customLam<0.95?'under-estimate':customLam>1.15?'conservative':'standard'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Design Health ────────────────────────────────────────────────
function DesignHealth({R,inp}:{R:any,inp:any}){
  if(!R)return null
  const f2=(v:number|undefined|null,d=2)=>v!=null?Number(v).toFixed(d):'—'
  const checks=[
    {label:'Capacity',    ok:R.cap.ok,         val:f2(R.cap.Qt,1)+' t/h',       req:R.cap.req+' t/h req'},
    {label:'Shaft Stress',ok:R.tor.shOk,        val:f2(R.tor.tau,1)+' MPa',      req:'≤'+inp.sallow+' MPa'},
    {label:'Gearbox Torque',ok:R.gbx_r?.tOk,   val:Math.round(R.tor.Ts)+' Nm',  req:'≤'+(R.gbx_r?.Tn_derated||R.gbx_r?.Tn||0|0).toLocaleString()+' Nm'},
    {label:'Bearing L10', ok:R.brg_r?.ok,       val:Math.round(R.brg_r?.L10||0).toLocaleString()+' h', req:'≥'+(R.brg_r?.L10_target||20000).toLocaleString()+' h'},
    {label:'Vibration Risk',ok:(R.vibration_risk||0)<3,val:R.vri_label||'—',    req:'Low target'},
    {label:'Energy kWh/t',ok:(R.eff?.kWh_t||9)<1,val:f2(R.eff?.kWh_t||0,3),   req:'<1.0 optimal'},
    {label:'Fill φ (act)',ok:(R.cap.fill_actual||R.cap.fill||0.3)*100>=15&&(R.cap.fill_actual||R.cap.fill||0.3)*100<=45,
      val:f2((R.cap.fill_actual||R.cap.fill||0)*100,1)+'%',req:'15–45% target'},
    {label:'Utilisation', ok:(R.eff?.cap_util||0)>=70&&(R.eff?.cap_util||0)<=100,
      val:f2(R.eff?.cap_util||0,0)+'%',req:'70–100% target'},
    {label:'Shaft Defl.',  ok:R.deflection_ok,  val:f2((R.deflection||0)*1000,2)+' mm', req:'≤'+f2((R.defl_limit||0.01)*1000,2)+' mm'},
    {label:'Motor',        ok:R.pwr.motor>=R.pwr.motor_rated,val:R.pwr.motor+' kW',req:f2(R.pwr.motor_rated||0,1)+' kW rated'},
    {label:'Load Class',   ok:true,              val:'Class '+(R.mat?.cls||'—'),   req:''},
  ]
  const nFail=checks.filter(c=>!c.ok).length
  const col=nFail>0?C.red:C.green
  return(
    <div style={ss({background:'rgba(16,30,48,.8)',border:`1px solid ${C.border}`,borderRadius:10,padding:14,marginBottom:12})}>
      <div style={ss({display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:10})}>
        <span style={ss({fontSize:11,fontWeight:700,textTransform:'uppercase',letterSpacing:'0.08em',color:C.muted})}>🏥 Design Health</span>
        <span style={ss({fontSize:11,fontWeight:700,color:col,background:'rgba(0,0,0,.3)',padding:'3px 12px',borderRadius:20,border:`1px solid ${col}`})}>
          {nFail>0?`⛔ ${nFail} Critical`:'✅ Design OK'}
        </span>
      </div>
      <div style={ss({display:'grid',gridTemplateColumns:'repeat(6,1fr)',gap:4})}>
        {checks.map((c,i)=>{
          const cl=c.ok?C.green:C.red
          return(
            <div key={i} style={ss({background:'rgba(0,0,0,.25)',border:`1px solid ${cl}44`,borderRadius:7,padding:'7px 9px'})}>
              <div style={ss({fontSize:9,fontWeight:700,color:C.muted,textTransform:'uppercase',letterSpacing:'0.07em',marginBottom:3})}>{c.label}</div>
              <div style={ss({fontSize:12,fontWeight:800,fontFamily:'monospace',color:cl})}>{c.val}</div>
              <div style={ss({fontSize:8.5,color:'rgba(93,125,153,.7)',marginTop:2})}>{c.req}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Efficiency Score card ────────────────────────────────────────
function EfficiencyCard({eff}:{eff:any}){
  if(!eff)return null
  const score=eff.score||0
  const col=score>70?C.green:score>45?C.amber:C.red
  const bars=[
    {l:'Loading Efficiency (40%)',v:Math.round((eff.eta_load||0)*100),c:C.blue,w:40},
    {l:'Energy Efficiency (35%)',v:Math.round((eff.eta_energy||0)*100),c:C.green,w:35},
    {l:'Incline Factor (25%)',v:Math.round((eff.eta_incline||0)*100),c:C.amber,w:25},
  ]
  return(
    <Panel>
      <SHdr icon="📊" label="Design Efficiency Score"/>
      <div style={ss({display:'flex',alignItems:'center',gap:14,marginBottom:12})}>
        <div style={ss({width:58,height:58,borderRadius:'50%',border:`3px solid ${col}`,display:'flex',
          alignItems:'center',justifyContent:'center',flexShrink:0})}>
          <span style={ss({color:col,fontWeight:800,fontSize:20})}>{score}</span>
        </div>
        <div>
          <p style={ss({fontSize:10,color:C.muted})}>CEMA-weighted score /100</p>
          <p style={ss({fontSize:12,color:C.text,marginTop:2,fontWeight:700})}>Energy: <span style={ss({color:C.accent})}>{(eff.kWh_t||0).toFixed(3)} kWh/t</span></p>
          <p style={ss({fontSize:10,color:C.muted,marginTop:1})}>Fill: {(eff.fill_pct||0).toFixed(1)}% · Utilisation: {(eff.cap_util||0).toFixed(1)}%</p>
        </div>
      </div>
      {bars.map((b,i)=>(
        <div key={i} style={ss({marginBottom:6})}>
          <div style={ss({display:'flex',justifyContent:'space-between',fontSize:9,color:C.muted,marginBottom:2})}>
            <span>{b.l}</span>
            <span style={ss({fontFamily:'monospace'})}>{b.v}% × {b.w}% = {Math.round(b.v*b.w/100)}</span>
          </div>
          <div style={ss({height:6,background:'rgba(0,0,0,.3)',borderRadius:3,overflow:'hidden'})}>
            <div style={ss({width:b.v+'%',height:'100%',background:b.c,borderRadius:3})}/>
          </div>
        </div>
      ))}
    </Panel>
  )
}

// ── Power Breakdown bar chart ────────────────────────────────────
function PowerBreakdown({pwr}:{pwr:any}){
  if(!pwr)return null
  const data=[
    {name:'Empty', kW:+(pwr.Pe||0).toFixed(3)},
    {name:'Material', kW:+(pwr.Pm||0).toFixed(3)},
    {name:'Incline', kW:+(pwr.Pi||0).toFixed(3)},
  ]
  return(
    <div style={ss({marginTop:14})}>
      <div style={ss({fontSize:10,fontWeight:800,color:C.accent,letterSpacing:'0.09em',marginBottom:8,textTransform:'uppercase'})}>Power Breakdown</div>
      <div style={ss({height:160})}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{top:5,right:20,bottom:20,left:10}}>
            <CartesianGrid strokeDasharray="3 3" stroke={C.border}/>
            <XAxis dataKey="name" tick={{fill:C.muted,fontSize:10}}/>
            <YAxis tick={{fill:C.muted,fontSize:9}} label={{value:'kW',angle:-90,position:'insideLeft',fill:C.muted,fontSize:9}}/>
            <Tooltip contentStyle={{background:C.panel,border:`1px solid ${C.border}`,fontSize:10}} formatter={(v:any)=>[v+' kW','']}/>
            <Bar dataKey="kW" fill={C.accent} radius={[3,3,0,0]}/>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// ── Parametric Sweep ─────────────────────────────────────────────
function ParamSweep({inp}:{inp:any}){
  const[swType, setSwType]=useState<'speed'|'diam'|'length'>('speed')
  const[running, setRunning]=useState(false)
  const[swData, setSwData]=useState<any[]>([])

  const run=async()=>{
    setRunning(true)
    const pts: any[]=[]
    try{
      let vals: {x:number,field:string,extra?:any}[]=[]
      if(swType==='speed') vals=[10,20,30,40,50,60,80,100,120,150].map(N=>({x:N,field:'N'}))
      else if(swType==='diam') vals=[0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.45,0.5,0.6].map(D=>({x:Math.round(D*1000),field:'D',extra:{D,P:D}}))
      else vals=[3,5,8,10,12,15,18,20,25,30].map(L=>({x:L,field:'L'}))
      for(const v of vals){
        try{
          const r=await api.calculate({...inp, ...(v.extra||{[v.field]:v.swType==='diam'?v.x/1000:v.x})})
          pts.push({x:v.x, cap:+(r.cap.Qt).toFixed(1), pwr:+(r.pwr.Pt).toFixed(2)})
        }catch{}
      }
    }catch{}
    setSwData(pts)
    setRunning(false)
  }

  return(
    <div style={ss({marginTop:14,paddingTop:12,borderTop:`1px solid ${C.border}`})}>
      <div style={ss({fontSize:10,fontWeight:800,color:C.accent,letterSpacing:'0.09em',marginBottom:8,textTransform:'uppercase'})}>📈 Parametric Sweep</div>
      <div style={ss({display:'flex',gap:6,marginBottom:8})}>
        {(['speed','diam','length'] as const).map(t=>(
          <button key={t} onClick={()=>setSwType(t)}
            style={ss({padding:'4px 12px',borderRadius:4,border:'none',cursor:'pointer',fontSize:10,fontWeight:700,fontFamily:'inherit',
              background:swType===t?C.accent:'transparent',color:swType===t?'#0b1522':C.muted})}>
            {t==='speed'?'⚡ Speed':t==='diam'?'⭕ Diam':'↔️ Length'}
          </button>
        ))}
        <button onClick={run} disabled={running}
          style={ss({padding:'4px 14px',borderRadius:4,border:`1px solid ${C.green}`,background:'rgba(31,184,110,.1)',
            color:C.green,cursor:'pointer',fontSize:10,fontWeight:700,fontFamily:'inherit'})}>
          {running?'⏳':'▶ Run'}
        </button>
      </div>
      {swData.length>0&&(
        <div style={ss({height:160})}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={swData} margin={{top:5,right:20,bottom:20,left:10}}>
              <CartesianGrid strokeDasharray="3 3" stroke={C.border}/>
              <XAxis dataKey="x" tick={{fill:C.muted,fontSize:9}}
                label={{value:swType==='speed'?'RPM':swType==='diam'?'Ø mm':'L (m)',position:'insideBottom',offset:-10,fill:C.muted,fontSize:9}}/>
              <YAxis tick={{fill:C.muted,fontSize:9}}/>
              <Tooltip contentStyle={{background:C.panel,border:`1px solid ${C.border}`,fontSize:10}}/>
              <Line type="monotone" dataKey="cap" stroke={C.green} dot={false} strokeWidth={2} name="Cap (t/h)"/>
              <Line type="monotone" dataKey="pwr" stroke={C.amber} dot={false} strokeWidth={2} name="Power (kW)"/>
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

// ── Material Recommendations ─────────────────────────────────────
function MatRecs({recs}:{recs:any}){
  if(!recs)return null
  const secs=[
    {k:'trough',icon:'□',l:'Trough',col:'#60a5fa'},
    {k:'flight',icon:'🔩',l:'Flights',col:'#f97316'},
    {k:'shaft',icon:'⚙️',l:'Shaft',col:C.purple},
    {k:'treatments',icon:'🔥',l:'Treatments',col:'#fb923c'},
  ]
  return(
    <Panel>
      <div style={ss({display:'flex',alignItems:'center',gap:8,marginBottom:10,paddingBottom:8,borderBottom:`1px solid ${C.border}`})}>
        <span style={ss({fontSize:14})}>🛡️</span>
        <span style={ss({fontWeight:700,fontSize:11,letterSpacing:'0.08em',textTransform:'uppercase',color:'#fb923c'})}>Material & Surface Recommendations</span>
      </div>
      <div style={ss({display:'grid',gridTemplateColumns:'1fr 1fr',gap:10})}>
        {secs.map(s=>(recs[s.k]||[]).length>0&&(
          <div key={s.k} style={ss({background:'rgba(0,0,0,.2)',borderRadius:7,padding:'9px 11px'})}>
            <p style={ss({fontSize:10,fontWeight:700,color:s.col,marginBottom:5})}>{s.icon} {s.l}</p>
            {(recs[s.k]||[]).map((r:string,i:number)=>(
              <p key={i} style={ss({fontSize:10,color:'#b0c8e0',marginBottom:3,lineHeight:1.4,
                paddingLeft:8,borderLeft:`2px solid ${s.col}33`})}>• {r}</p>
            ))}
          </div>
        ))}
      </div>
      {(recs.notes||[]).length>0&&(
        <div style={ss({marginTop:10,background:'rgba(74,158,255,.06)',border:'1px solid rgba(74,158,255,.2)',borderRadius:6,padding:'7px 10px'})}>
          <p style={ss({fontSize:9,fontWeight:700,color:C.blue,marginBottom:3,textTransform:'uppercase',letterSpacing:'0.08em'})}>⚠ Design Notes</p>
          {(recs.notes||[]).map((n:string,i:number)=><p key={i} style={ss({fontSize:10,color:'#93c5fd',marginBottom:2})}>• {n}</p>)}
        </div>
      )}
    </Panel>
  )
}

// ── Structural module ────────────────────────────────────────────
function StructuralModule({R,inp}:{R:any,inp:any}){
  if(!R)return null
  const mat=R.mat||{}, fill=R.cap?.fill_actual||R.cap?.fill||0.30
  const s=calcStructural(inp.D,inp.L,mat.rho||1.2,inp.ang||0,fill,mat.abr||'Medium',inp.temp_c||20)
  const hCount=R.hgr?.count||s.n_supports, hLoad=s.R_kN/Math.max(hCount,1)
  const hOk=hLoad<=10
  const Sub=({t,i,ch}:{t:string,i:string,ch:React.ReactNode})=>(
    <div style={ss({background:'rgba(0,0,0,.15)',border:`1px solid ${C.border}`,borderRadius:7,padding:12})}>
      <div style={ss({fontSize:10,fontWeight:800,color:C.accent,letterSpacing:'0.08em',marginBottom:8})}>{i} {t}</div>
      {ch}
    </div>
  )
  return(
    <Panel>
      <SHdr icon="🔩" label="Structural Engineering Module — U-Trough Screw Conveyor"
        badge={<span style={ss({fontSize:9,color:C.faint})}>Basis: Plate bending (AISC) · S355 steel (σ_allow={s.sigma_allow} MPa)</span>}/>
      <div style={ss({display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:10,marginBottom:10})}>
        <Sub t="Trough Plate" i="□" ch={<>
          <RR label="Load (mat+screw)" value={s.w_total} unit="kN/m"/>
          <RR label="Bending moment"   value={s.M_max}   unit="N·m/m"/>
          <RR label="Plate thickness"  value={s.t_plate}  unit="mm" ok/>
          <RR label="Span used"        value={s.hanger_span} unit="m"/>
        </>}/>
        <Sub t="Cover & Flange" i="⊡" ch={<>
          <RR label="Cover thickness"  value={s.t_cover}   unit="mm"/>
          <RR label="Cover bolt pitch" value={s.cover_bp}  unit="mm"/>
          <RR label="Flange thickness" value={s.flange_t}  unit="mm"/>
          <RR label="Flange width"     value={s.flange_w}  unit="mm"/>
          <RR label="Bolt size"        value={s.bolt_size}/>
          <RR label="Bolts per flange" value={s.n_bolts}   unit="pcs"/>
        </>}/>
        <Sub t="Bolting" i="🔩" ch={<>
          <RR label="Bolt capacity"    value={s.bolt_cap}       unit="kN" ok={s.bolt_ok}/>
          <RR label="Pressure load"    value={s.pressure_load}  unit="kN"/>
          <RR label="Required bolts"   value={s.n_bolts}        unit="pcs" ok/>
          <RR label="Bolt spacing"     value={s.bolt_pitch}     unit="mm"/>
          <RR label="Weld size"        value={s.weld_size}      unit="mm"/>
        </>}/>
      </div>
      <div style={ss({display:'grid',gridTemplateColumns:'1fr 1fr',gap:10,marginBottom:10})}>
        <Sub t="Hanger Loads" i="🔗" ch={<>
          <RR label="Hangers"            value={hCount}               unit="pcs"/>
          <RR label="Hanger span"        value={s.hanger_span}        unit="m"/>
          <RR label="Load per hanger"    value={hLoad.toFixed(1)}     unit="kN" ok={hOk}/>
          <RR label="Reaction force"     value={s.R_kN}               unit="kN"/>
          <RR label="Recommended brg"    value={`UC${Math.ceil(inp.D*100/5)*5+200}`}/>
        </>}/>
        <Sub t="Shaft Key & System" i="🗝️" ch={<>
          <RR label="Key width (b)"      value={s.key_b}              unit="mm"/>
          <RR label="Screw mass"         value={s.screw_mass.toLocaleString()} unit="kg"/>
          <RR label="Trough mass (est)"  value={s.trough_mass.toLocaleString()} unit="kg"/>
          <RR label="End support reac."  value={s.end_react}          unit="kN"/>
        </>}/>
      </div>
      {/* Hanger distribution */}
      <div style={ss({fontSize:9,color:C.muted,fontWeight:700,letterSpacing:'0.07em',marginBottom:6})}>HANGER LOAD DISTRIBUTION</div>
      <div style={ss({display:'flex',gap:4})}>
        {Array.from({length:hCount},(_,i)=>(
          <div key={i} style={ss({flex:1,textAlign:'center'})}>
            <div style={ss({fontSize:8,color:C.muted,marginBottom:2})}>{hLoad.toFixed(1)}</div>
            <div style={ss({height:16,background:hOk?C.teal:C.amber,borderRadius:2})}/>
            <div style={ss({fontSize:8,color:C.faint,marginTop:2})}>H{i+1}</div>
          </div>
        ))}
      </div>
      <div style={ss({fontSize:9,color:C.faint,marginTop:4})}>Load in kN per hanger · Green ≤10, Amber ≤20, Red &gt;20</div>
    </Panel>
  )
}

// ── Axial Profiles ───────────────────────────────────────────────
type AxTab='Throughput'|'Fill'|'Power'|'Torque'|'Cumulative'|'Wear'|'Axial'
function AxialProfiles({R,inp}:{R:any,inp:any}){
  const[tab,setTab]=useState<AxTab>('Throughput')
  const[hov,setHov]=useState<any>(null)
  const{data:profile,isLoading}=useQuery({
    queryKey:['axial-profile',inp],
    queryFn:()=>api.getAxialProfile(inp,60),
    enabled:!!R, staleTime:0, placeholderData:(p:any)=>p,
  })
  if(!R)return null
  const tabs:Record<AxTab,{key:string,color:string,unit:string,req?:number}>={
    Throughput:{key:'Qt',color:C.green,unit:'t/h',req:inp.cap},
    Fill:      {key:'fill_pct',color:C.blue,unit:'%'},
    Power:     {key:'pwr_density',color:C.amber,unit:'kW/m'},
    Torque:    {key:'torque_pm',color:C.purple,unit:'Nm/m'},
    Cumulative:{key:'torque_cumul',color:C.accent,unit:'Nm'},
    Wear:      {key:'wear_rate',color:C.red,unit:'mm/h'},
    Axial:     {key:'axial_velocity',color:C.teal,unit:'m/s'},
  }
  const tc=tabs[tab]
  const data: any[] = Array.isArray(profile) ? profile : ((profile as any)?.segments || [])
  const hangers=data.filter((s:any)=>s.isHanger)
  const insights:string[]=[]
  if(data.length){
    const choke=data.filter((s:any)=>s.status==='choke').length
    if(choke/data.length>0.5) insights.push(`${Math.round(choke/data.length*100)}% of length is choking — throughput limited by inlet pitch (${Math.round(inp.P*1000)} mm). Increase inlet pitch or reduce required capacity.`)
    const mxW=Math.max(...data.map((s:any)=>s.wear_rate))
    if(mxW>0.01) insights.push(`High inlet wear (${mxW.toFixed(4)} mm/h). Consider AR-lined inlet section or reduced inlet pitch.`)
  }
  return(
    <Panel>
      <SHdr icon="📈" label="Axial Profiles"/>
      <div style={ss({display:'flex',gap:4,marginBottom:10})}>
        {(Object.keys(tabs) as AxTab[]).map(t=>(
          <button key={t} onClick={()=>setTab(t)}
            style={ss({padding:'4px 10px',borderRadius:4,border:'none',cursor:'pointer',fontSize:10,fontWeight:700,fontFamily:'inherit',
              background:tab===t?tabs[t].color:'transparent',
              color:tab===t?'#0b1522':C.muted,
              outline:tab===t?`1px solid ${tabs[t].color}`:'none'})}>
            {t}
          </button>
        ))}
      </div>
      {isLoading&&<div style={ss({height:200,display:'flex',alignItems:'center',justifyContent:'center',color:C.muted,fontSize:11})}>⏳ Building profile…</div>}
      {!isLoading&&data.length>0&&(
        <div style={ss({height:220})}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} onMouseMove={(e:any)=>e.activePayload&&setHov(e.activePayload[0]?.payload)}
              onMouseLeave={()=>setHov(null)} margin={{top:5,right:40,bottom:20,left:10}}>
              <CartesianGrid strokeDasharray="3 3" stroke={C.border}/>
              <XAxis dataKey="x" label={{value:'Length (m)',position:'insideBottom',offset:-10,fill:C.muted,fontSize:10}} tick={{fill:C.muted,fontSize:9}}/>
              <YAxis tick={{fill:C.muted,fontSize:9}}/>
              <Tooltip contentStyle={{background:C.panel,border:`1px solid ${C.border}`,borderRadius:6,fontSize:10}}
                labelFormatter={(v:any)=>`x = ${v} m`}/>
              {tc.req!==undefined&&<ReferenceLine y={tc.req} stroke={C.amber} strokeDasharray="6 3"
                label={{value:`Required ${tc.req} t/h`,fill:C.amber,fontSize:9}}/>}
              {hangers.map((h:any,i:number)=>(
                <ReferenceLine key={i} x={h.x} stroke={C.blue} strokeDasharray="3 3" strokeOpacity={0.4}/>
              ))}
              <Line type="monotone" dataKey={tc.key} stroke={tc.color} dot={false} strokeWidth={2}/>
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      <div style={ss({display:'flex',gap:12,flexWrap:'wrap',marginTop:6,fontSize:9,color:C.muted})}>
        <span><span style={ss({color:C.blue})}>H— </span>Hanger bearing</span>
        <span><span style={ss({color:C.red})}>— </span>Flooding</span>
        <span><span style={ss({color:C.amber})}>— </span>Choke (&lt;req.)</span>
        <span><span style={ss({color:C.faint})}>— </span>Starved (&lt;12%)</span>
      </div>
      {hov&&(
        <div style={ss({marginTop:8,background:'#081321',borderRadius:6,padding:'6px 12px',fontSize:10,display:'flex',gap:16,flexWrap:'wrap'})}>
          <span style={ss({color:C.accent})}>x = {hov.x} m</span>
          <span style={ss({color:C.green})}>Throughput: {hov.Qt} t/h</span>
          <span style={ss({color:C.blue})}>Fill: {hov.fill_pct}%</span>
          <span style={ss({color:C.amber})}>Pitch: {(hov.localPitch*1000).toFixed(0)} mm</span>
          {hov.status!=='ok'&&<span style={ss({color:C.red})}>▲ {hov.status.toUpperCase()} — capacity limited</span>}
        </div>
      )}
      {insights.map((s,i)=>(
        <div key={i} style={ss({marginTop:6,background:'rgba(232,160,0,.06)',border:`1px solid ${C.amber}44`,borderRadius:5,padding:'5px 10px',fontSize:10,color:C.amber})}>⚠ {s}</div>
      ))}
      {/* Shaft deflection */}
      <div style={ss({marginTop:14,paddingTop:12,borderTop:`1px solid ${C.border}`})}>
        <div style={ss({display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:6})}>
          <span style={ss({fontSize:10,fontWeight:800,color:C.accent,letterSpacing:'0.08em'})}>📐 SHAFT DEFLECTION PROFILE</span>
          <span style={ss({fontSize:9,color:(R.tor?.pipe?C.purple:C.blue),fontFamily:'monospace'})}>
            {R.tor?.pipe
              ? `Pipe Ø${Math.round(R.tor?.eff_od_mm||70)}×${Math.round(R.tor?.eff_id_mm||54)} mm (hollow)`
              : `Bar Ø${Math.round(R.tor?.eff_od_mm||R.tor?.od||70)} mm (solid)`}
          </span>
        </div>
        {data.length>0&&(()=>{
          const L_conv=inp.L||10
          // R is already the correct standard (activeR passed by caller)
          const span=Math.max(R.hgr?.span||L_conv, 0.1)
          const mxD=Math.max((R.deflection||0)*1000, 0)
          const limitMm=(R.defl_limit||0.01)*1000
          const deflOk=R.deflection_ok
          // Mirror HTML prototype exactly: spans×20+1 points
          // Each span is one arch from zero (support) to peak (mid-span) to zero (next support)
          // hanger_count hangers = hanger_count+1 spans
          const numSpans=Math.max(1,Math.round(L_conv/Math.max(span,0.1)))
          const dp=Array.from({length:numSpans*20+1},(_:any,i:number)=>{
            const xFrac=i/(numSpans*20)
            const xInSpan=(xFrac*numSpans)%1   // 0→1 within each span
            const d=mxD*(Math.sin(Math.PI*xInSpan)**2)  // sin² gives smooth arch
            return{x:+(xFrac*L_conv).toFixed(3), d:+d.toFixed(4)}
          })
          // Y-axis must include the limit line — use max of deflection and limit
          const yMax=Math.max(mxD,limitMm,0.001)*1.15
          return(
            <div style={ss({height:140})}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={dp} margin={{top:5,right:60,bottom:20,left:10}}>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.border}/>
                  <XAxis dataKey="x" tick={{fill:C.muted,fontSize:9}} label={{value:'Length (m)',position:'insideBottom',offset:-10,fill:C.muted,fontSize:9}}/>
                  <YAxis tick={{fill:C.muted,fontSize:9}} domain={[0,yMax]} label={{value:'δ (mm)',angle:-90,position:'insideLeft',fill:C.muted,fontSize:9}}/>
                  {/* Hanger bearing markers — one per internal hanger (not end bearings) */}
                  {Array.from({length:numSpans-1},(_:any,i:number)=>(
                    <ReferenceLine key={i} x={+((i+1)*span).toFixed(2)} stroke={C.purple}
                      strokeDasharray="3 2" strokeOpacity={0.7}
                      label={{value:'H',fill:C.purple,fontSize:8,position:'top'}}/>
                  ))}
                  <ReferenceLine y={limitMm} stroke={C.red} strokeDasharray="6 3" strokeWidth={1.5}
                    label={{value:`Limit ${limitMm.toFixed(2)} mm`,fill:C.red,fontSize:8,position:'insideTopRight'}}/>
                  <ReferenceLine y={mxD} stroke={deflOk?C.blue:C.red} strokeDasharray="2 4" strokeOpacity={0.5}
                    label={{value:`δ=${mxD.toFixed(3)} mm ${deflOk?'✓':'✗'}`,fill:deflOk?C.blue:C.red,fontSize:8,position:'insideBottomRight'}}/>
                  <Line type="monotone" dataKey="d" stroke={R.tor?.pipe?C.purple:C.blue} dot={false} strokeWidth={2}/>
                </LineChart>
              </ResponsiveContainer>
            </div>
          )
        })()}
        <div style={ss({display:'flex',alignItems:'center',gap:10,marginTop:6})}>
          <span style={ss({fontSize:9,color:C.muted,whiteSpace:'nowrap'})}>Critical Speed</span>
          <div style={ss({flex:1,height:10,background:C.border,borderRadius:5,position:'relative'})}>
            <div style={ss({position:'absolute',left:0,width:Math.min(100,(R.nc_ratio||0)*100)+'%',height:'100%',
              background:(R.nc_ratio||0)<0.7?C.green:C.amber,borderRadius:5})}/>
          </div>
          <span style={ss({fontSize:9,color:C.faint,whiteSpace:'nowrap'})}>{((R.nc_ratio||0)*100).toFixed(0)}% of Nc</span>
          <span style={ss({fontSize:9,color:C.muted,whiteSpace:'nowrap'})}>Nc={Math.round(R.nc||0)} RPM</span>
        </div>
      </div>
    </Panel>
  )
}

// ── Standards Comparison table ───────────────────────────────────
function StdCompTable({multiR,activeStd}:{multiR:Record<string,any>|null,activeStd:string}){
  if(!multiR) return null
  const f2=(v?:number,d=2)=>v!=null?v.toFixed(d):'—'
  const fN=(v?:number)=>v!=null?Math.round(v).toLocaleString():'—'
  const rows:[string,(r:any)=>string,(r:any)=>boolean|null][]=[
    ['Capacity (t/h)',   r=>f2(r.cap.Qt,2),              r=>r.cap.ok],
    ['Power (kW)',       r=>f2(r.pwr.Pt,3),              ()=>null],
    ['Motor (kW)',       r=>String(r.pwr.motor),         ()=>null],
    ['Running Torque (Nm)', r=>Math.round(r.tor.Tr).toString(), ()=>null],
    ['Shaft OD (mm)',    r=>(r.tor.od||r.shaft_auto?.sel_mm||0).toFixed(0)+' std', r=>r.tor.shOk],
    ['Shear Stress (MPa)',r=>f2(r.tor.tau,2),            r=>r.tor.shOk],
    ['Safety Factor',   r=>((r.inp?.sallow||40)/Math.max(r.tor.tau,0.001)).toFixed(2)+' ×', r=>{const sf=(r.inp?.sallow||40)/Math.max(r.tor.tau,0.001);return sf>=1.5;}],
    ['Bearing L10 (h)', r=>fN(r.brg_r?.L10),            r=>r.brg_r?.ok],
    ['Shaft Defl. (mm)',r=>f2((r.deflection||0)*1000,3)+' / '+f2((r.defl_limit||0.01)*1000,3)+' lim', r=>r.deflection_ok],
    ['Hangers',         r=>(r.hgr?.count||0)+' @ '+f2(r.hgr?.span,1)+'m', ()=>null],
    ['kWh/t',           r=>f2(r.eff?.kWh_t,3),          ()=>null],
    ['Design Score',    r=>(r.eff?.score||0)+'/100',     r=>( r.eff?.score||0)>70],
    ['Est. Cost (USD)', r=>'$'+fN(r.cost?.total),       ()=>null],
  ]
  const stds=['CEMA','DIN','Custom']
  return(
    <Panel>
      <SHdr icon="📊" label="Standards Comparison"/>
      <div style={ss({overflowX:'auto'})}>
        <table style={ss({width:'100%',borderCollapse:'collapse',fontSize:11})}>
          <thead>
            <tr style={ss({borderBottom:`1px solid ${C.border}`})}>
              {['Metric','CEMA','DIN','Custom'].map(h=>(
                <th key={h} style={ss({padding:'4px 10px',textAlign:'left',color:C.muted,fontWeight:700,fontSize:10,textTransform:'uppercase'})}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(([lb,fn,okFn])=>(
              <tr key={lb} style={ss({borderBottom:'1px solid rgba(28,48,72,.4)'})}>
                <td style={ss({padding:'4px 10px',color:C.muted,fontSize:10})}>{lb}</td>
                {stds.map(s=>{
                  const r=multiR[s]
                  const v=r?fn(r):'—'
                  const ok=r&&okFn?okFn(r):null
                  const col=ok===true?C.green:ok===false?C.red:s===activeStd?C.accent:C.text
                  return<td key={s} style={ss({padding:'4px 10px',fontFamily:'monospace',fontWeight:700,fontSize:11,color:col})}>{v}</td>
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}

// ── Auto-Optimise modal — 3-Phase Sequential ─────────────────────
type OptPhase = 'geometry'|'pitch'|'drive'

function AutoOptModal({inp,onApply,onClose}:{inp:any,onApply:(v:any)=>void,onClose:()=>void}){
  const{data:bearings}=useBearings()
  const{data:gearboxes}=useGearboxes()
  const PHASES:OptPhase[]=['geometry','pitch','drive']
  const[phase,setPhase]=useState<OptPhase>('geometry')
  const[goals,setGoals]=useState<string[]>(['efficiency'])
  const[running,setRunning]=useState(false)
  const[phaseResults,setPhaseResults]=useState<Record<string,any>>({})
  const[applied,setApplied]=useState<Record<string,any>>({})
  const[done,setDone]=useState(false)

  const effectiveInp=useMemo(()=>({
    ...inp,...(applied.geometry||{}),...(applied.pitch||{}),...(applied.drive||{})
  }),[inp,applied])

  const scoreCandidate=(r:any)=>{
    if(!r?.eff)return 0
    const s_eff=r.eff.score||0
    const s_energy=Math.max(0,100-(r.eff.kWh_t||5)*20)
    const s_cost=Math.max(0,100-(r.cost?.total||99999)/500)
    const s_life=Math.min(100,(r.wear?.life_h||0)/500)
    const w:Record<string,number>={efficiency:0.35,energy:0.35,cost:0.2,life:0.1}
    const wTotal=goals.reduce((s,g)=>s+(w[g]||0.25),0)||1
    return goals.reduce((s,g)=>{
      const v=g==='efficiency'?s_eff:g==='energy'?s_energy:g==='cost'?s_cost:s_life
      return s+(w[g]||0.25)*v
    },0)/wTotal
  }

  const runGeometry=async()=>{
    setRunning(true)
    const base={...effectiveInp}
    const Ds=[0.20,0.25,0.30,0.35,0.40,0.45,0.50,0.60]
    const Ns=[20,30,40,50,60,80,100,120]
    const PRs=[0.75,0.875,1.0,1.125,1.25]
    const candidates:any[]=[],trials:any[]=[]
    for(const D of Ds){
      for(const N of Ns){
        for(const pr of PRs){
          const P=Math.min(D*pr,1.5)
          try{
            const r=await api.calculate({...base,D,N,P,use_multipitch:false,lam_factor:1.0})
            const sc=scoreCandidate(r)
            const c={D,N,P,pr,score:sc,kWh:r.eff?.kWh_t||9,cost:r.cost?.total||0,
              life:r.wear?.life_h||0,defl_mm:(r.deflection||0)*1000,
              L10:r.brg_r?.L10||0,motor:r.pwr?.motor||0,r}
            trials.push(c)
            if(r.cap?.ok&&r.tor?.shOk&&r.deflection_ok&&r.gbx_r?.tOk&&r.brg_r?.ok)
              candidates.push(c)
          }catch{}
        }
      }
    }
    const sorted=candidates.sort((a,b)=>b.score-a.score)
    const partial=candidates.length===0&&trials.length?
      [...trials].sort((a,b)=>b.score-a.score)[0]:null
    setPhaseResults(prev=>({...prev,geometry:{
      top:sorted.slice(0,6),partial,total_swept:trials.length,feasible:candidates.length
    }}))
    setRunning(false)
  }

  const runPitch=async()=>{
    setRunning(true)
    const base={...effectiveInp}
    const inletRatios=[0.5,0.6,0.667,0.75,0.8,0.875]
    const outletRatios=[0.667,0.75,0.875,1.0]
    const pctPairs=[[10,10],[15,15],[20,20],[10,15],[15,10]]
    const candidates:any[]=[],trials:any[]=[]
    for(const ir of inletRatios){
      for(const or of outletRatios){
        for(const[pi,po] of pctPairs){
          const P_body=base.P||base.D
          const P_in=P_body*ir, P_out=P_body*or
          try{
            const r=await api.calculate({...base,P_in,P_out,pct_in:pi,pct_out:po,
              use_multipitch:true,lam_factor:1.0})
            const sc=scoreCandidate(r)
            const c={P_in,P_out,pct_in:pi,pct_out:po,ir,or,score:sc,
              kWh:r.eff?.kWh_t||9,cost:r.cost?.total||0,life:r.wear?.life_h||0,
              defl_mm:(r.deflection||0)*1000,L10:r.brg_r?.L10||0,motor:r.pwr?.motor||0,r}
            trials.push(c)
            if(r.cap?.ok&&r.tor?.shOk&&r.deflection_ok&&r.gbx_r?.tOk&&r.brg_r?.ok)
              candidates.push(c)
          }catch{}
        }
      }
    }
    const sorted=candidates.sort((a,b)=>b.score-a.score)
    const partial=candidates.length===0&&trials.length?
      [...trials].sort((a,b)=>b.score-a.score)[0]:null
    setPhaseResults(prev=>({...prev,pitch:{
      top:sorted.slice(0,5),partial,total_swept:trials.length,
      feasible:candidates.length,skip_ok:true
    }}))
    setRunning(false)
  }

  const runDrive=async()=>{
    setRunning(true)
    const base={...effectiveInp}
    const gbxList=(gearboxes||[]).map((g:any)=>g.model)
    const brgList=(bearings||[]).map((b:any)=>b.name)
    const candidates:any[]=[],trials:any[]=[]
    for(const gbx of gbxList.slice(0,12)){
      for(const brg of brgList.slice(0,10)){
        for(const hangers of [0,1,2,3,4,6]){
          try{
            const r=await api.calculate({...base,gbx,brg,hangers:hangers||0,lam_factor:1.0})
            const sc=scoreCandidate(r)
            const c={gbx,brg,hangers,score:sc,kWh:r.eff?.kWh_t||9,cost:r.cost?.total||0,
              life:r.wear?.life_h||0,defl_mm:(r.deflection||0)*1000,
              L10:r.brg_r?.L10||0,motor:r.pwr?.motor||0,r}
            trials.push(c)
            if(r.cap?.ok&&r.tor?.shOk&&r.deflection_ok&&r.gbx_r?.tOk&&r.brg_r?.ok)
              candidates.push(c)
          }catch{}
        }
      }
    }
    const sorted=candidates.sort((a,b)=>b.score-a.score)
    const partial=candidates.length===0&&trials.length?
      [...trials].sort((a,b)=>b.score-a.score)[0]:null
    setPhaseResults(prev=>({...prev,drive:{
      top:sorted.slice(0,5),partial,total_swept:trials.length,feasible:candidates.length
    }}))
    setRunning(false)
  }

  const runPhase=()=>{
    if(phase==='geometry')runGeometry()
    else if(phase==='pitch')runPitch()
    else runDrive()
  }

  const applyCandidate=(c:any,ph:OptPhase)=>{
    const cfg=ph==='geometry'
      ?{D:c.D,N:c.N,P:c.P}
      :ph==='pitch'
      ?{P_in:c.P_in,P_out:c.P_out,pct_in:c.pct_in,pct_out:c.pct_out,use_multipitch:true}
      :{gbx:c.gbx,brg:c.brg,hangers:c.hangers}
    setApplied(prev=>({...prev,[ph]:cfg}))
    onApply(cfg)
  }

  const phaseCfg:{[k in OptPhase]:{icon:string,label:string,title:string,sub:string}}={
    geometry:{icon:'⭕',label:'Phase 1',title:'Geometry',sub:'D × N × Pitch'},
    pitch:   {icon:'🌀',label:'Phase 2',title:'Pitch Pattern',sub:'Inlet/Outlet (optional)'},
    drive:   {icon:'⚙️',label:'Phase 3',title:'Drive & Hangers',sub:'GBX × BRG × Hangers'},
  }
  const goalCfg:{[k:string]:{icon:string,l:string}}={
    efficiency:{icon:'📈',l:'Efficiency'},energy:{icon:'🔋',l:'Min Energy'},
    cost:{icon:'💰',l:'Min Cost'},life:{icon:'⏱️',l:'Max Life'},
  }

  const renderCand=(c:any,i:number,ph:OptPhase)=>{
    const isApplied=!!applied[ph]
    const lab=ph==='geometry'
      ?`Ø${(c.D*1000).toFixed(0)}mm · ${c.N} RPM · P=${(c.P*1000).toFixed(0)}mm`
      :ph==='pitch'
      ?`Inlet ${(c.ir*100).toFixed(0)}%D · Outlet ${(c.or*100).toFixed(0)}%D · Zones ${c.pct_in}%/${c.pct_out}%`
      :`${c.gbx} · ${c.brg} · ${c.hangers} hangers`
    return(
      <div key={i} style={ss({border:`1px solid ${i===0?'rgba(45,212,191,.25)':C.border}`,
        background:i===0?'rgba(45,212,191,.05)':'rgba(0,0,0,.15)',
        borderRadius:8,padding:'10px 12px',marginBottom:6,display:'flex',alignItems:'center',gap:8})}>
        <div style={ss({flex:1,minWidth:0})}>
          <div style={ss({fontSize:10,fontWeight:700,color:i===0?C.teal:C.text,fontFamily:'monospace',marginBottom:4})}>{lab}</div>
          <div style={ss({display:'flex',gap:10,flexWrap:'wrap',fontSize:9,color:C.muted})}>
            {[['Score',(c.score*100/100).toFixed(1),C.accent],
              ['kWh/t',c.kWh?.toFixed(3),C.green],
              ['Motor',(c.motor||'—')+' kW',C.purple],
              ['Defl',(c.defl_mm||0).toFixed(2)+'mm',(c.defl_mm||0)<2?C.green:C.amber],
              ['L10',((c.L10||0)/1000).toFixed(0)+'kh',(c.L10||0)>=20000?C.green:C.amber],
            ].map(([l,v,col])=><span key={l as string}>{l as string}: <strong style={ss({color:col as string})}>{v as string}</strong></span>)}
          </div>
        </div>
        <button onClick={()=>applyCandidate(c,ph)}
          style={ss({padding:'5px 14px',borderRadius:6,border:`1px solid ${C.teal}44`,
            background:'transparent',color:C.teal,cursor:'pointer',fontSize:10,fontWeight:700,flexShrink:0})}>
          Apply
        </button>
      </div>
    )
  }

  const renderPhaseResult=(ph:OptPhase)=>{
    const pr=phaseResults[ph]
    if(!pr)return null
    return(
      <div>
        <div style={ss({fontSize:10,fontWeight:700,color:pr.feasible>0?C.green:C.amber,marginBottom:8})}>
          {pr.feasible>0
            ?`✓ ${pr.feasible}/${pr.total_swept} feasible designs found`
            :`⚠ 0/${pr.total_swept} — no fully feasible design`}
          {pr.feasible===0&&pr.skip_ok&&<span style={ss({fontSize:9,color:C.muted,marginLeft:8})}>Phase 2 is optional — skip or adjust pitch manually</span>}
        </div>
        {pr.feasible===0&&pr.partial&&(
          <div style={ss({background:'rgba(217,142,0,.08)',border:`1px solid rgba(217,142,0,.3)`,borderRadius:8,padding:'10px 12px',marginBottom:10})}>
            <p style={ss({fontSize:10,fontWeight:700,color:C.amber,marginBottom:6})}>🔍 Best Partial — apply as starting point, refine manually:</p>
            {renderCand(pr.partial,0,ph)}
          </div>
        )}
        {pr.top?.map((c:any,i:number)=>renderCand(c,i,ph))}
      </div>
    )
  }

  return(
    <div style={ss({position:'fixed',inset:0,background:'rgba(0,0,0,.85)',zIndex:3000,
      display:'flex',alignItems:'center',justifyContent:'center',
      transition:'opacity .3s',opacity:done?0:1})}>
      <div style={ss({background:C.panel,border:'1px solid #2a4a72',borderRadius:14,
        width:780,maxHeight:'92vh',overflowY:'auto',
        boxShadow:'0 24px 80px rgba(0,0,0,.8)',padding:24,display:'flex',flexDirection:'column',gap:0})}>

        {/* Header */}
        <div style={ss({display:'flex',justifyContent:'space-between',alignItems:'flex-start',
          marginBottom:16,paddingBottom:12,borderBottom:`1px solid ${C.border}`})}>
          <div>
            <h2 style={ss({fontWeight:800,color:C.text,fontSize:17})}>✨ Sequential Auto-Optimiser</h2>
            <p style={ss({fontSize:10,color:C.muted,marginTop:3})}>
              Three phases — run each, apply preferred result, continue. Changes update live design immediately.
            </p>
          </div>
          <button onClick={onClose} style={ss({color:C.muted,fontSize:20,background:'none',border:'none',cursor:'pointer'})}>✕</button>
        </div>

        {/* Optimisation goals */}
        <div style={ss({marginBottom:14})}>
          <div style={ss({fontSize:9,color:C.muted,fontWeight:700,letterSpacing:'0.08em',marginBottom:6})}>OPTIMISATION GOALS (multi-select)</div>
          <div style={ss({display:'flex',gap:6,flexWrap:'wrap'})}>
            {Object.entries(goalCfg).map(([k,g])=>(
              <button key={k} onClick={()=>setGoals(prev=>prev.includes(k)?prev.filter(x=>x!==k):[...prev,k])}
                style={ss({padding:'4px 12px',borderRadius:20,border:`1px solid ${goals.includes(k)?C.accent:C.border}`,
                  background:goals.includes(k)?'rgba(232,160,0,.12)':'transparent',
                  color:goals.includes(k)?C.accent:C.muted,cursor:'pointer',fontSize:10,fontWeight:700})}>
                {g.icon} {g.l}
              </button>
            ))}
          </div>
        </div>

        {/* Phase tabs */}
        <div style={ss({display:'flex',gap:0,marginBottom:16,borderBottom:`2px solid ${C.border}`})}>
          {PHASES.map(ph=>{
            const pc=phaseCfg[ph]
            const ran=!!phaseResults[ph]
            const app=!!applied[ph]
            return(
              <button key={ph} onClick={()=>setPhase(ph)}
                style={ss({padding:'8px 18px',border:'none',cursor:'pointer',background:'transparent',
                  fontFamily:'inherit',textAlign:'left',
                  borderBottom:phase===ph?`2px solid ${C.accent}`:'2px solid transparent',marginBottom:-2})}>
                <div style={ss({fontSize:10,fontWeight:700,color:phase===ph?C.accent:C.muted})}>
                  {pc.icon} {pc.label}: {pc.title}
                  {ran&&<span style={ss({marginLeft:6,fontSize:8,padding:'1px 6px',borderRadius:4,
                    background:'rgba(31,184,110,.15)',color:C.green})}>✓</span>}
                  {app&&<span style={ss({marginLeft:4,fontSize:8,padding:'1px 6px',borderRadius:4,
                    background:'rgba(45,212,191,.15)',color:C.teal})}>Applied</span>}
                </div>
                <div style={ss({fontSize:9,color:C.faint})}>{pc.sub}</div>
              </button>
            )
          })}
        </div>

        {/* Effective design summary */}
        <div style={ss({background:'#081321',borderRadius:6,padding:'7px 12px',marginBottom:12,fontSize:9,color:C.muted,display:'flex',gap:16,flexWrap:'wrap'})}>
          <span style={ss({color:C.faint})}>Effective design:</span>
          <span>D={((effectiveInp.D||0)*1000).toFixed(0)}mm</span>
          <span>N={effectiveInp.N||0}RPM</span>
          <span>P={((effectiveInp.P||0)*1000).toFixed(0)}mm</span>
          <span>L={effectiveInp.L||0}m</span>
          <span style={ss({color:C.accent})}>{effectiveInp.mat}</span>
        </div>

        {/* Phase content */}
        <div style={ss({flex:1})}>
          {renderPhaseResult(phase)}
          {!phaseResults[phase]&&(
            <div style={ss({textAlign:'center',color:C.faint,fontSize:11,padding:24})}>
              {phase==='geometry'&&'Run Phase 1 to sweep D × N × Pitch combinations'}
              {phase==='pitch'&&'Run Phase 1 first, then Phase 2 to optimise inlet/outlet pitch (optional)'}
              {phase==='drive'&&'Run Phase 3 to sweep gearbox and bearing combinations'}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={ss({display:'flex',justifyContent:'space-between',alignItems:'center',
          marginTop:16,paddingTop:12,borderTop:`1px solid ${C.border}`})}>
          <div style={ss({display:'flex',gap:6})}>
            {running&&<span style={ss({fontSize:10,color:C.blue})}>⏳ Sweeping {phaseCfg[phase].title}…</span>}
          </div>
          <div style={ss({display:'flex',gap:8})}>
            <button onClick={onClose}
              style={ss({padding:'7px 18px',borderRadius:4,border:`1px solid ${C.border}`,background:'transparent',color:C.muted,cursor:'pointer',fontSize:12})}>
              Close
            </button>
            <button onClick={runPhase} disabled={running}
              style={ss({padding:'7px 22px',borderRadius:4,border:`1px solid ${C.teal}`,
                background:running?'transparent':'rgba(45,212,191,.12)',color:running?C.faint:C.teal,
                cursor:running?'not-allowed':'pointer',fontSize:12,fontWeight:700})}>
              {running?'⏳ Running…':`▶ Run ${phaseCfg[phase].label}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════
// MAIN CalcPage
// ═════════════════════════════════════════════════════════════════
export default function CalcPage({_meta}:{_meta?:ProjectMeta}){
  const{inp,setInp}=useCalcStore()
  const{data:R,isLoading,isError,error,refetch}=useCalculate()
  const{data:mats}=useMaterials()
  const{data:bearings}=useBearings()
  const{data:gearboxes}=useGearboxes()

  // Sync default material to first DB entry if current name not found
  useEffect(()=>{
    if(mats && mats.length > 0){
      const names = mats.map((m:any)=>m.name)
      if(!names.includes(inp.mat)){
        setInp({mat: names[0]})
      }
    }
  },[mats])

  const[activeStd,setActiveStd]=useState('CEMA')
  const[customLam,setCustomLam]=useState(1.05)
  const[showOpt,setShowOpt]=useState(false)

  // Multi-standard query
  const{data:multiR}=useQuery({
    queryKey:['calculate-multi',inp,customLam],
    queryFn:()=>api.calculateMulti({...inp,lam_factor:customLam}),
    enabled:!!R, staleTime:0, placeholderData:(p:any)=>p,
  })

  const activeR=multiR?multiR[activeStd]:R

  // Material lambda for display
  const matLam=useMemo(()=>{
    const m=(mats||[]).find(x=>x.name===inp.mat)
    if(!m)return 1.0
    const pszMap:Record<string,number>={A200:0.075,A100:0.15,A40:0.42,B6:6,'C1/2':12,D3:75,D7:180}
    const psz=pszMap[m.particle_class||'B6']||6
    const lamBase=psz<0.5?1.8:psz<5?1.4:1.0
    return Math.max(0.4,Math.min((m.lambda_ref||1.0)*0.6+lamBase*0.4,3.5))
  },[mats,inp.mat])

  const matMeta=useMemo(()=>{
    const m=(mats||[]).find(x=>x.name===inp.mat)
    return m?`ρ ${m.rho} t/m³ · Fill: ${(m.fill_max*100).toFixed(0)}% · λ ${(m.lambda_ref||1.0).toFixed(1)} · Abr: ${m.abr} · CEMA: Class ${m.cls}`:''
  },[mats,inp.mat])

  const f2=(v?:number,d=2)=>v!=null?v.toFixed(d):'—'
  const fN=(v?:number)=>v!=null?Math.round(v).toLocaleString():'—'
  const shAuto=R?(R as any).shaft_auto:null

  return(
    <div style={ss({display:'flex',height:'100%',overflow:'hidden'})}>

      {/* ══ INPUT PANEL ══ */}
      <div style={ss({width:270,flexShrink:0,background:C.panel,borderRight:`1px solid ${C.border}`,overflowY:'auto',overflowX:'hidden',padding:'10px 12px',minHeight:0,height:'100%',boxSizing:'border-box'})}>
        <Divider label="MATERIAL & DUTY"/>
        <div style={ss({marginBottom:7})}>
          <Lbl>Incline Factor Model</Lbl>
          <Ck field="contAFact" label="Continuous exp(–k·θ)"/><span style={ss({fontSize:9,color:C.faint})}>CEMA stepped</span>
        </div>
        <SI field="type" label="Conveyor Type" options={[
          {value:'screw',label:'🔩 Screw Conveyor (U-trough)'},
          {value:'pipe', label:'⭕ Pipe Conveyor'},
        ]}/>
        <div style={ss({marginBottom:7})}>
          <Lbl>Material</Lbl>
          <select value={inp.mat} onChange={e=>setInp({mat:e.target.value})}
            style={ss({width:'100%',background:'#081321',border:`1px solid ${C.border}`,borderRadius:4,
              padding:'5px 8px',color:C.text,fontSize:11,fontFamily:'inherit',outline:'none',boxSizing:'border-box'})}>
            {(mats||[]).length===0&&<option value={inp.mat}>{inp.mat}</option>}
            {(mats||[]).map(m=><option key={m.name} value={m.name}>{m.name}</option>)}
          </select>
          {matMeta&&<div style={ss({fontSize:9,color:C.faint,marginTop:3})}>{matMeta}</div>}
        </div>
        <NI field="cap"   label="Capacity"  unit="t/h"        min={0.1} max={5000} step={1}/>
        <NI field="L"     label="Length"    unit="m"          min={0.5} max={100}  step={0.5}/>
        <NI field="ang"   label="Angle"     unit="° (−20→+45)" min={-20} max={45}  step={1}/>
        <NI field="surge" label="Surge Factor"                 min={1.0} max={2.0} step={0.05}/>
        <Divider label="TROUGH GEOMETRY"/>
        <NI field="D"  label="Trough Ø"      unit="m"  min={0.05} max={1.2}  step={0.05}/>
        <NI field="N"  label="Speed"         unit="RPM" min={5}   max={300}  step={5}/>
        <NI field="ft" label="Flight Thick." unit="m"  min={0.002} max={0.02} step={0.001}/>
        <NI field="wa" label="Wear Allowance" unit="m"  min={0.001} max={0.01} step={0.001}/>
        <Divider label="FLIGHT PITCH"/>
        {activeR&&(
          <div style={ss({background:'rgba(31,184,110,.06)',border:`1px solid ${C.green}33`,borderRadius:5,padding:'6px 9px',marginBottom:7,fontSize:10})}>
            <div style={ss({color:activeR.cap.ok?C.green:C.red,fontWeight:700})}>{activeR.cap.ok?'✓':'✗'} Pitch capacity {activeR.cap.ok?'OK':'LOW'}</div>
            <div style={ss({color:C.faint,marginTop:2})}>Body {f2(activeR.cap.Qt,1)} t/h  P={Math.round(inp.P*1000)} mm ={Math.round(inp.P/inp.D*100)}%D</div>
          </div>
        )}
        <div style={ss({display:'flex',alignItems:'center',gap:8,marginBottom:7})}>
          <Ck field="use_multipitch" label="Multi-Pitch"/>
          <span style={ss({fontSize:9,color:C.faint})}>Sections</span>
        </div>
        <NI field="P" label="Body Pitch (m) [uniform]" min={0.05} max={2.0} step={0.05}/>
        {inp.use_multipitch&&(
          <div style={ss({background:'rgba(74,158,255,.05)',border:`1px solid ${C.blue}33`,borderRadius:6,padding:8,marginBottom:7})}>
            <div style={ss({fontSize:9,color:C.blue,fontWeight:700,marginBottom:6})}>MULTI-PITCH ZONES</div>
            <div style={ss({display:'grid',gridTemplateColumns:'1fr 1fr',gap:6})}>
              <NI field="P_in"    label="Inlet Pitch (m)"  min={0.05} max={2.0} step={0.05}/>
              <NI field="P_out"   label="Outlet Pitch (m)" min={0.05} max={2.0} step={0.05}/>
              <NI field="pct_in"  label="Inlet zone %"     min={5}    max={50}  step={5}/>
              <NI field="pct_out" label="Outlet zone %"    min={5}    max={50}  step={5}/>
            </div>
          </div>
        )}
        <Divider label="SHAFT CONFIGURATION"/>
        <SI field="shaft_mode" label="Shaft Mode" options={[
          {value:'auto',   label:'Auto-size from torque'},
          {value:'manual', label:'Manual override'},
        ]}/>
        {inp.shaft_mode==='auto'&&shAuto&&(
          <div style={ss({background:'rgba(31,184,110,.06)',border:`1px solid ${C.green}33`,borderRadius:5,padding:'6px 9px',marginBottom:7,fontSize:10})}>
            <div style={ss({color:C.green,fontWeight:700})}>Auto: Ø{shAuto.sel_mm} mm ▮ solid bar  <span style={ss({fontWeight:400})}>req. {f2(shAuto.req_mm,1)} mm · SF {f2(shAuto.sf,2)}</span></div>
            <div style={ss({fontSize:9,color:C.faint,marginTop:2})}>⚡ Auto-selects nearest ISO standard size from startup torque.</div>
          </div>
        )}
        <div style={ss({display:'flex',gap:6,marginBottom:8})}>
          <button onClick={()=>setInp({shaft_mode:'manual',shtype:'bar',pod:shAuto?.sel_mm||Math.round(inp.D*1000*0.25)})}
            style={ss({flex:1,padding:'5px 0',borderRadius:4,border:`1px solid ${C.blue}`,background:'rgba(74,158,255,.1)',color:C.blue,cursor:'pointer',fontSize:10,fontWeight:700,fontFamily:'inherit'})}>
            📊 Override as Bar →
          </button>
          <button onClick={()=>setInp({shaft_mode:'manual',shtype:'pipe',pod:shAuto?.sel_mm||80,pwall:8})}
            style={ss({flex:1,padding:'5px 0',borderRadius:4,border:`1px solid ${C.purple}`,background:'rgba(167,139,250,.1)',color:C.purple,cursor:'pointer',fontSize:10,fontWeight:700,fontFamily:'inherit'})}>
            ⭕ Override as Pipe →
          </button>
        </div>
        {inp.shaft_mode==='manual'&&(
          <div style={ss({background:'rgba(74,158,255,.05)',border:`1px solid ${C.blue}33`,borderRadius:6,padding:8,marginBottom:7})}>
            <div style={ss({display:'grid',gridTemplateColumns:'1fr 1fr',gap:6})}>
              <SI field="shtype" label="Type" options={[{value:'bar',label:'Solid Bar'},{value:'pipe',label:'Hollow Pipe'}]}/>
              <NI field="pod"    label="OD (mm)"     min={20}  max={300} step={5}/>
              {inp.shtype==='pipe'&&<NI field="pwall" label="Wall (mm)" min={3} max={30} step={1}/>}
              <NI field="sallow" label="τ_allow MPa"  min={10}  max={120} step={5}/>
            </div>
          </div>
        )}
        {inp.shaft_mode==='auto'&&<NI field="sallow" label="Allowable Shear (MPa)" min={10} max={120} step={5}/>}
        <Divider label="DRIVE & BEARINGS"/>
        <div style={ss({marginBottom:7})}>
          <Lbl>End Bearing (shaft ends)</Lbl>
          <select value={inp.brg} onChange={e=>setInp({brg:e.target.value})}
            style={ss({width:'100%',background:'#081321',border:`1px solid ${C.border}`,borderRadius:4,padding:'5px 8px',color:C.text,fontSize:11,fontFamily:'inherit',outline:'none',boxSizing:'border-box'})}>
            {(bearings||[]).length===0&&<option value={inp.brg}>{inp.brg}</option>}
            {(bearings||[]).map(b=><option key={b.name} value={b.name}>{b.name}</option>)}
          </select>
          {activeR&&<div style={ss({fontSize:9,color:C.faint,marginTop:2})}>
            L10: {fN(activeR.brg_r?.L10)} h
            {' '}(req ≥{fN(activeR.brg_r?.L10_target||20000)} h)
            {' '}{activeR.brg_r?.ok?'✓ OK':'✗'}
          </div>}
        </div>
        <div style={ss({marginBottom:7})}>
          <Lbl>Hanger Bearing (intermediate)</Lbl>
          <select value={inp.hgr_brg||inp.brg} onChange={e=>setInp({hgr_brg:e.target.value})}
            style={ss({width:'100%',background:'#081321',border:`1px solid ${C.border}`,borderRadius:4,padding:'5px 8px',color:C.text,fontSize:11,fontFamily:'inherit',outline:'none',boxSizing:'border-box'})}>
            {(bearings||[]).length===0&&<option value={inp.hgr_brg||inp.brg}>{inp.hgr_brg||inp.brg}</option>}
            {(bearings||[]).map(b=><option key={b.name} value={b.name}>{b.name}</option>)}
          </select>
          <div style={ss({fontSize:8,color:C.faint,marginTop:2})}>Used for hanger load distribution display only</div>
        </div>
        <div style={ss({marginBottom:7})}>
          <Lbl>Gearbox</Lbl>
          <select value={inp.gbx} onChange={e=>setInp({gbx:e.target.value})}
            style={ss({width:'100%',background:'#081321',border:`1px solid ${C.border}`,borderRadius:4,padding:'5px 8px',color:C.text,fontSize:11,fontFamily:'inherit',outline:'none',boxSizing:'border-box'})}>
            {(gearboxes||[]).length===0&&<option value={inp.gbx}>{inp.gbx}</option>}
            {(gearboxes||[]).map(g=><option key={g.model} value={g.model}>{g.model}</option>)}
          </select>
        </div>
        <SI field="duty" label="Duty Cycle" options={[
          {value:'8', label:'8 h/day — standard'},
          {value:'16',label:'16 h/day — heavy'},
          {value:'24',label:'24 h/day — continuous'},
        ]}/>
        {activeR&&(
          <div style={ss({background:'rgba(74,158,255,.06)',border:`1px solid ${C.blue}33`,borderRadius:5,padding:'6px 9px',marginBottom:7,fontSize:10})}>
            <div style={ss({color:C.blue})}>AGMA SF: <strong>{f2(activeR.gbx_r?.agma_sf,2)}</strong>  Derating: <span style={ss({color:C.amber})}>{Math.round((1-1/(activeR.gbx_r?.agma_sf||1.25))*100)}%</span></div>
            <div style={ss({color:C.faint,fontSize:9,marginTop:2})}>Motor: {f2(activeR.pwr.motor_rated,3)} kW · {f2(activeR.pwr.motor,3)} kW selected</div>
          </div>
        )}
        <NI field="hangers"  label="Intermediate Hanger Bearings (0=auto)" min={0}   max={20}  step={1}/>
        <div style={ss({fontSize:8,color:C.faint,marginTop:-4,marginBottom:7,lineHeight:1.4})}>
          Intermediate bearings only — excludes 2 fixed end shaft bearings.<br/>
          N hangers = N+1 spans. Span = L / (N+1).
        </div>
        <NI field="bload"    label="Bearing Load (kN)"         min={1}   max={200} step={1}/>
        <NI field="temp_c"   label="Process Temp (°C)"         min={-20} max={800} step={5}/>
        <button onClick={()=>refetch()} disabled={isLoading}
          style={ss({width:'100%',marginTop:10,padding:'9px 0',borderRadius:5,border:`1px solid ${C.accent}`,
            background:'rgba(200,25,46,.12)',color:C.accent,fontSize:11,fontWeight:800,
            fontFamily:"'Barlow Condensed',sans-serif",letterSpacing:'0.08em',textTransform:'uppercase',cursor:'pointer',fontFamily:'inherit',letterSpacing:'0.04em'})}>
          {isLoading?'⏳ Calculating…':'▶ Recalculate'}
        </button>
      </div>

      {/* ══ RESULTS PANEL ══ */}
      <div style={ss({flex:1,overflowY:'auto',display:'flex',flexDirection:'column'})}>
        {/* Top bar */}
        <div style={ss({background:'#060f1c',borderBottom:`1px solid ${C.border}`,padding:'6px 14px',display:'flex',alignItems:'center',justifyContent:'space-between',flexShrink:0})}>
          <span style={ss({fontSize:11,fontWeight:800,color:C.accent,letterSpacing:'0.08em'})}>🔩 SCREW CONVEYOR DESIGNER v2.4</span>
          <div style={ss({display:'flex',gap:6})}>
            <button onClick={()=>setShowOpt(true)}
              style={ss({padding:'5px 14px',borderRadius:4,border:`1px solid ${C.teal}`,background:'rgba(45,212,191,.1)',color:C.teal,cursor:'pointer',fontSize:11,fontWeight:700,fontFamily:'inherit'})}>
              ✨ Auto-Optimise
            </button>
            <button onClick={()=>window.print()}
              style={ss({padding:'5px 12px',borderRadius:4,border:`1px solid ${C.blue}`,background:'rgba(74,158,255,.1)',color:C.blue,cursor:'pointer',fontSize:11,fontFamily:'inherit'})}>
              🖨️ Print
            </button>
          </div>
        </div>

        <div style={ss({flex:1,padding:14,overflowY:'auto',display:'flex',flexDirection:'column',gap:10})}>
          <div style={ss({background:'rgba(217,142,0,.07)',border:`1px solid ${C.amber}44`,borderRadius:6,padding:'5px 12px',fontSize:10,color:C.amber})}>
            ⚠ Preliminary Engineering Estimate Only
          </div>
          {isError&&(
            <div style={ss({background:'rgba(224,82,82,.08)',border:`1px solid ${C.red}`,borderRadius:6,padding:'10px 14px',fontSize:11})}>
              {(error as any)?.response?.status===404
                ?<><div style={ss({color:C.red,fontWeight:700})}>⚠️ Material not found — run:</div><code style={ss({color:C.amber})}>python -m backend.db.seed</code></>
                :<div style={ss({color:C.red})}>⚠️ {(error as Error)?.message}</div>}
            </div>
          )}

          {/* Standards tabs */}
          {(activeR||R)&&<StdTabs activeStd={activeStd} setStd={setActiveStd}
            customLam={customLam} setCustomLam={setCustomLam}
            multiR={multiR||null} matLam={matLam} matName={inp.mat}/>}

          {/* Design Health */}
          {activeR&&<DesignHealth R={activeR} inp={inp}/>}

          {/* Flow regime */}
          {activeR&&(()=>{
            const fr=activeR.regime||{name:'Normal Flow'}
            const isNorm=fr.name?.includes('Normal')
            return(
              <div style={ss({background:'rgba(16,30,48,.5)',border:`1px solid ${C.border}`,borderRadius:8,padding:'8px 14px',display:'flex',alignItems:'center',gap:12})}>
                <span style={ss({background:isNorm?C.green:C.amber,width:14,height:14,borderRadius:3,flexShrink:0,display:'inline-block'})}/>
                <span style={ss({fontWeight:700,fontSize:11,color:isNorm?C.green:C.amber})}>{fr.name}</span>
                <span style={ss({fontSize:10,color:C.muted})}>Normal conveying regime</span>
                <div style={ss({marginLeft:'auto'})}>
                  <span style={ss({fontSize:9,background:'#1c3048',padding:'2px 8px',borderRadius:3,color:C.muted})}>CEMA Class {activeR.mat?.cls||'—'}</span>
                </div>
              </div>
            )
          })()}

          {/* Engineering checks (warns) */}
          {activeR&&(()=>{
            const w=(activeR as any).warns||{crit:[],adv:[],opt:[]}
            return[
              ...(w.crit||[]).map((x:string,i:number)=>(
                <div key={'c'+i} style={ss({fontSize:11,color:C.red,padding:'5px 12px',background:'rgba(224,82,82,.08)',border:`1px solid ${C.red}44`,borderRadius:5})}>❌ [CRITICAL] {x}</div>
              )),
              ...(w.adv||[]).map((x:string,i:number)=>(
                <div key={'a'+i} style={ss({fontSize:11,color:C.amber,padding:'5px 12px',background:'rgba(217,142,0,.07)',border:`1px solid ${C.amber}44`,borderRadius:5})}>⚠️ [ADVISORY] {x}</div>
              )),
              ...(w.opt||[]).map((x:string,i:number)=>(
                <div key={'o'+i} style={ss({fontSize:11,color:C.blue,padding:'5px 12px',background:'rgba(74,158,255,.07)',border:`1px solid ${C.blue}44`,borderRadius:5})}>💡 [OPTIMISATION] {x}</div>
              )),
            ]
          })()}

          {/* Capacity + Power cards */}
          {activeR&&(
            <div style={ss({display:'grid',gridTemplateColumns:'1fr 1fr',gap:10})}>
              <Panel>
                <SHdr icon="📊" label="Capacity" badge={<Chip ok={activeR.cap.ok} label={activeR.cap.ok?'OK':'FAIL'}/>}/>
                <RR label="Achieved"         value={f2(activeR.cap.Qt,2)}          unit="t/h"   ok={activeR.cap.ok}/>
                <RR label="Required"         value={f2(activeR.cap.req||inp.cap,2)}unit="t/h"/>
                <RR label="Effective Pitch"  value={Math.round((activeR.P_eff||inp.P)*1000)} unit="mm" sub="weighted avg / zones"/>
                <RR label="Body capacity"    value={f2(activeR.cap.Qt_body,2)}     unit="t/h"   ok={activeR.cap.ok}/>
                <RR label="Governing (bottleneck)" value={f2(activeR.cap.Qt_governing||activeR.cap.Qt,2)} unit="t/h" ok={activeR.cap.ok}/>
                <RR label="Volumetric"       value={f2(activeR.cap.Qv,3)}          unit="m³/h"/>
                <RR label="Fill Fraction"    value={f2((activeR.cap.fill_actual||activeR.cap.fill||0)*100,1)} unit="%" sub="mat.fill_max×f(θ) CEMA"/>
                <RR label="Fill basis"       value="Dynamic calcFill"/>
              </Panel>
              <Panel>
                <SHdr icon="⚡" label="Power"/>
                <RR label="Empty Friction"   value={f2(activeR.pwr.Pe,3)}   unit="kW"/>
                <RR label="Material Transport" value={f2(activeR.pwr.Pm,3)} unit="kW"/>
                <RR label="Incline Component" value={f2(activeR.pwr.Pi,3)}  unit="kW"/>
                <RR label="Shaft Total"      value={f2(activeR.pwr.Ps,3)}   unit="kW" hl/>
                <RR label="Motor Selected"   value={activeR.pwr.motor}      unit="kW" hl/>
              </Panel>
            </div>
          )}

          {/* Auto Shaft + Hanger Layout cards */}
          {activeR&&(
            <div style={ss({display:'grid',gridTemplateColumns:'1fr 1fr',gap:10})}>
              <Panel>
                {(()=>{
                  const sa  = (activeR as any).shaft_auto || {}
                  const pOpt= sa.pipe_opt || (activeR as any).shaft_pipe_opt || null
                  const isManual = (inp.shaft_mode||'auto') === 'manual'
                  const isPipe   = activeR.tor?.pipe || false
                  const effOD    = activeR.tor?.eff_od_mm || sa.sel_mm || 70
                  const effID    = activeR.tor?.eff_id_mm || 0
                  const pwall    = inp.pwall || 8
                  const sfActual = (inp.sallow||40) / Math.max(activeR.tor?.tau, 0.001)
                  const sfCol    = sfActual >= 2.0 ? C.green : sfActual >= 1.5 ? C.amber : C.red
                  return(<>
                    <SHdr icon="⚙️"
                      label={isManual ? 'Manual Shaft Override' : 'Auto Shaft Design'}
                      col={isManual ? C.amber : C.teal}
                      badge={<Chip ok={activeR.tor?.shOk} label={activeR.tor?.shOk?'PASS':'FAIL'}/>}/>
                    {/* Mode banner */}
                    {isManual
                      ? <div style={ss({background:'rgba(232,160,0,.06)',border:`1px solid ${C.amber}33`,borderRadius:5,padding:'5px 9px',marginBottom:8,fontSize:10,color:C.amber})}>
                          ✏️ Manual override — {isPipe?'hollow pipe':'solid bar'} Ø{effOD.toFixed(0)}{isPipe?' / '+effID.toFixed(0)+' mm ID':''} mm
                        </div>
                      : <div style={ss({background:'rgba(45,212,191,.06)',border:`1px solid ${C.teal}33`,borderRadius:5,padding:'5px 9px',marginBottom:8,fontSize:10,color:C.teal})}>
                          📐 Auto-sized from running torque {Math.round(activeR.tor?.Tr)} Nm at τ_allow={inp.sallow} MPa
                        </div>
                    }
                    <RR label="Required diameter"     value={f2(sa.req_mm,1)}    unit="mm" sub="from torque"/>
                    <RR label={isManual ? (isPipe?'Pipe OD / Wall / ID':'Manual OD') : 'Selected standard'}
                        value={isPipe ? `${effOD.toFixed(0)} / ${pwall} / ${effID.toFixed(0)} mm`
                                      : `${effOD.toFixed(0)} mm${isManual?'':' std'}`} ok/>
                    <RR label="Shear stress (startup)" value={f2(activeR.tor?.tau,2)} unit="MPa" ok={activeR.tor?.shOk}/>
                    <div style={ss({display:'flex',justifyContent:'space-between',alignItems:'center',
                      padding:'4px 0',borderBottom:`1px solid ${C.border}`,fontSize:11})}>
                      <span style={ss({color:C.muted})}>Safety factor</span>
                      <span style={ss({fontSize:13,fontFamily:'monospace',fontWeight:800,color:sfCol})}>{sfActual.toFixed(2)} ×</span>
                    </div>
                    <RR label="Running torque"  value={Math.round(activeR.tor?.Tr)} unit="Nm"/>
                    <RR label="Startup torque"  value={Math.round(activeR.tor?.Ts)} unit="Nm"/>
                    <div style={ss({marginTop:6,paddingTop:6,borderTop:`1px solid ${C.border}44`})}>
                      <RR label="Shaft I (bending)"  value={((activeR.tor?.I_m4||0)*1e8).toFixed(4)} unit="cm⁴" sub="section modulus"/>
                      <RR label="Deflection @ span"  value={f2((activeR.deflection||0)*1000,3)} unit="mm"
                        ok={activeR.deflection_ok}
                        sub={`limit ${((activeR.defl_limit||0.01)*1000).toFixed(2)}mm · span ${f2(activeR.hgr?.span,2)}m`}/>
                    </div>
                    {/* Pipe option — shows for BOTH modes */}
                    {pOpt&&(
                      <div style={ss({marginTop:10,background:isPipe?'rgba(45,212,191,.06)':'rgba(74,158,255,.06)',
                        border:`1px solid ${isPipe?'rgba(45,212,191,.25)':'rgba(74,158,255,.2)'}`,borderRadius:8,padding:'10px 12px'})}>
                        <p style={ss({fontSize:10,fontWeight:700,color:isPipe?C.teal:C.blue,marginBottom:8})}>
                          {isPipe
                            ? '⭕ Current: Hollow Pipe — weight saving vs same-OD solid bar'
                            : `⭕ Pipe Option — same OD, ${pOpt.wt_save_pct}% lighter`}
                        </p>
                        <div style={ss({display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:6})}>
                          {[
                            ['OD / Wall / ID', `${pOpt.od_mm} / ${pOpt.wall_mm} / ${pOpt.id_mm} mm`],
                            ['Shear stress',   `${(pOpt.tau_mpa||0).toFixed(2)} MPa`],
                            ['Weight saving',  `${pOpt.wt_save_pct}%`],
                            ['Feasible',       pOpt.ok ? 'Yes ✓' : 'No ✗'],
                          ].map(([l,v])=>(
                            <div key={l}>
                              <p style={ss({fontSize:8.5,color:C.muted,marginBottom:2})}>{l}</p>
                              <p style={ss({fontSize:11,fontFamily:'monospace',fontWeight:700,
                                color:l==='Feasible'?(pOpt.ok?C.green:C.red):l==='Weight saving'?C.teal:C.text})}>
                                {v}
                              </p>
                            </div>
                          ))}
                        </div>
                        {isPipe&&pOpt.vs_bar_tau!=null&&(
                          <p style={ss({fontSize:9,color:C.muted,marginTop:6})}>
                            Equivalent solid bar: τ = {(pOpt.vs_bar_tau||0).toFixed(2)} MPa
                            {' '}(vs pipe τ = {(pOpt.tau_mpa||0).toFixed(2)} MPa)
                          </p>
                        )}
                      </div>
                    )}
                  </>)
                })()}
              </Panel>
              <Panel>
                <SHdr icon="🔗" label="Hanger Bearing Layout"
                  badge={<span style={ss({fontSize:9,color:C.muted})}>Ø{Math.round(inp.D*1000)} mm</span>}/>
                <div style={ss({background:'rgba(45,212,191,.1)',border:`1px solid ${C.teal}33`,borderRadius:5,padding:'7px 10px',marginBottom:8,display:'flex',justifyContent:'space-between',alignItems:'center'})}>
                  <span style={ss({fontWeight:800,fontSize:13,color:C.teal})}>{activeR.hgr?.count||0} hanger bearings</span>
                  <span style={ss({fontSize:9,color:C.teal})}>Ø{Math.round(inp.D*1000)} mm</span>
                </div>
                <RR label="CEMA max span"  value={f2(activeR.hgr?.max_span,1)} unit="m" sub="at this D & abrasion class"/>
                <RR label="Actual span"    value={f2(activeR.hgr?.span,1)} unit="m"
                  ok={activeR.hgr?.span<=(activeR.hgr?.max_span||999)}
                  sub={activeR.hgr?.user_override?'user-set':'CEMA auto'}/>
                <RR label="Total length"   value={inp.L} unit="m"/>
                <RR label="Total supports" value={(activeR.hgr?.count||0)+2} unit="pcs" sub={`${activeR.hgr?.count||0} hangers + 2 end bearings`}/>
                <RR label="Spans created"  value={(activeR.hgr?.count||0)+1} sub="L / (hangers + 1)"/>
              </Panel>
            </div>
          )}

          {/* Bearing Life + Wear Life cards */}
          {activeR&&(
            <div style={ss({display:'grid',gridTemplateColumns:'1fr 1fr',gap:10})}>
              <Panel>
                <SHdr icon="⭕" label="Bearing Life" badge={<Chip ok={activeR.brg_r?.ok} label={activeR.brg_r?.ok?'PASS':'FAIL'}/>}/>
                <RR label="Bearing"       value={activeR.brg_r?.name||inp.brg}/>
                <RR label="C Dynamic"     value={f2(activeR.brg_r?.C,0)} unit="kN"/>
                <RR label="Bearing load"  value={f2(activeR.brg_r?.load,2)} unit="kN"/>
                <RR label="C/P Ratio"     value={f2((activeR.brg_r?.C||43)/(activeR.brg_r?.load||10),2)}/>
                <RR label="Required L10"  value={fN(activeR.brg_r?.L10_target||20000)} unit="h" sub={inp.duty==='24'?'24h/day':inp.duty==='16'?'16h/day':'8h/day'}/>
                <RR label="L10 Life"      value={fN(activeR.brg_r?.L10)} unit="h" ok={activeR.brg_r?.ok} hl/>
                {!activeR.brg_r?.ok&&activeR.brg_r?.adequate&&(
                  <div style={ss({marginTop:6,background:'rgba(232,160,0,.08)',border:`1px solid ${C.amber}33`,borderRadius:4,padding:'5px 8px',fontSize:9,color:C.amber})}>
                    💡 Suggested: <strong>{activeR.brg_r.adequate}</strong> — select from dropdown to meet target
                  </div>
                )}
              </Panel>
              <Panel>
                <SHdr icon="🔧" label="Wear Life"/>
                <RR label="Tip Speed"           value={f2(activeR.wear?.v_tip,2)}           unit="m/s"/>
                <RR label="Contact Pressure"    value={f2(activeR.wear?.P_contact_kPa,2)}   unit="kPa"/>
                <RR label="Wear Rate (body)"    value={f2(activeR.wear?.wrate_mm_h,4)}       unit="mm/h"/>
                <RR label="Wear Rate (inlet)"   value={f2((activeR.wear?.wrate_mm_h||0)*3,4)}unit="mm/h" sub="3× body rate"/>
                <RR label="Usable Thickness"    value={f2(activeR.wear?.thick_mm,1)}         unit="mm"/>
                <RR label="Flight Life (body)"  value={fN(activeR.wear?.life_h)}             unit="h" ok={(activeR.wear?.life_h||0)>8000} hl/>
                <RR label="Flight Life (inlet)" value={fN((activeR.wear?.life_h||0)/3)}      unit="h" ok={(activeR.wear?.life_h||0)/3>2000}/>
                <RR label="Throughput Life"     value={fN(activeR.wear?.life_t)}             unit="t"/>
              </Panel>
            </div>
          )}

          {/* Cost Estimate + Design Efficiency + Gearbox & Motor */}
          {activeR&&(
            <div style={ss({display:'grid',gridTemplateColumns:'1fr 1fr',gap:10})}>
              <Panel>
                <SHdr icon="💰" label="Cost Estimate"/>
                <RR label="Steel Grade" value={activeR.cost?.steel||'Steel'}/>
                <RR label="Unit Cost"   value={f2(activeR.cost?.uc,1)} unit="USD/kg"/>
                <RR label="Steel Mass"  value={fN(activeR.cost?.mass)} unit="kg"/>
                <RR label="Est. Cost"   value={'$'+fN(activeR.cost?.total)} hl/>
              </Panel>
              <Panel>
                <SHdr icon="⚙️" label="Gearbox & Motor" badge={<Chip ok={activeR.gbx_r?.tOk} label={activeR.gbx_r?.tOk?'PASS':'FAIL'}/>}/>
                <RR label="Selected GBX"         value={activeR.gbx_r?.model}/>
                <RR label="Startup Torque"        value={Math.round(activeR.tor?.Ts)} unit="Nm" ok={activeR.gbx_r?.tOk}/>
                <RR label="GBX Nameplate"         value={fN(activeR.gbx_r?.Tn)} unit="Nm"/>
                <RR label={`GBX Derated (SF=${f2(activeR.gbx_r?.agma_sf,2)})`} value={fN(activeR.gbx_r?.Tn_derated||activeR.gbx_r?.Tn)} unit="Nm" ok={activeR.gbx_r?.tOk} sub="effective capacity at this duty"/>
                <RR label="Thermal Power"         value={f2(activeR.pwr.Pt,2)} unit="kW"/>
                <RR label="Motor"                 value={activeR.pwr.motor} unit="kW" hl/>
                <RR label={`AGMA SF (${inp.duty||8}h/day)`} value={f2(activeR.gbx_r?.agma_sf,2)+' ×'} sub="motor & GBX derating"/>
              </Panel>
            </div>
          )}

          {/* Efficiency score */}
          {activeR?.eff&&<EfficiencyCard eff={activeR.eff}/>}

          {/* Standards Comparison table */}
          {multiR&&<StdCompTable multiR={multiR} activeStd={activeStd}/>}

          {/* Material Recommendations */}
          {activeR?.recs&&<MatRecs recs={activeR.recs}/>}

          {/* Calc basis + Power Breakdown + Parametric Sweep in one panel */}
          {activeR&&(
            <Panel>
              <div style={ss({fontSize:9,color:C.faint,marginBottom:4})}>
                ▶ CALCULATION BASIS & METHOD TRACEABILITY ▼
              </div>
              <div style={ss({fontSize:9,color:C.faint,lineHeight:1.7})}>
                Capacity: CEMA §3 — volumetric with inclination factor<br/>
                Power: CEMA §4 — Pe + Pm + Pi split, Pf=(Pe+Pm)×kf<br/>
                Shaft: ASME B106.1M torsional section modulus<br/>
                Bearings: ISO 281 L10 life<br/>
                Wear: Archard model, K_base={0.006} mm/h calibrated to CEMA Class II field data<br/>
                Ce=0.50 empirical friction factor (CEMA-based)
              </div>
              <PowerBreakdown pwr={activeR.pwr}/>
              <ParamSweep inp={inp}/>
            </Panel>
          )}

          {/* Structural Module */}
          {activeR&&<StructuralModule R={activeR} inp={inp}/>}

          {/* Axial profiles + shaft deflection */}
          {activeR&&(() => { try { return <AxialProfiles R={activeR} inp={inp}/> } catch(e) { return <div style={{color:'#e05252',padding:12,fontSize:11}}>⚠ Axial profile error — check console</div> } })()}

          {!R&&!isLoading&&!isError&&(
            <div style={ss({flex:1,display:'flex',alignItems:'center',justifyContent:'center',color:C.muted,fontSize:13,minHeight:200})}>
              Select a material and adjust inputs — results appear automatically
            </div>
          )}
        </div>
      </div>

      {showOpt&&<AutoOptModal inp={inp} onApply={p=>setInp(p)} onClose={()=>setShowOpt(false)}/>}
    </div>
  )
}
