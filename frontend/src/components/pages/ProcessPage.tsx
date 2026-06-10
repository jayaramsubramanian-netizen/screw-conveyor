/**
 * ProcessPage.tsx — Shared layout component for all process modules.
 * Each module renders its own input panel + result cards.
 * Called from individual page files (MixerPage, DryerPage, etc.)
 */
import React from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'

export const C = {
  panel:'#0d1c2e', border:'#162438', text:'#ddeaf6',
  muted:'#5a7a9a', faint:'#3a5470', accent:'#c8192e',
  green:'#1fb86e', red:'#e05252', amber:'#d98e00', blue:'#4a9eff',
  teal:'#2dd4bf', purple:'#a78bfa', bg:'#07111e',
}

const ss = (s: React.CSSProperties) => s

export function Field({
  label, value, setter, min, max, step=0.01, unit='', options
}: {
  label:string; value:number|string; setter:(v:any)=>void;
  min?:number; max?:number; step?:number; unit?:string; options?:{value:string,label:string}[]
}) {
  return (
    <div style={ss({marginBottom:8})}>
      <div style={ss({fontSize:8.5,color:C.muted,fontWeight:700,textTransform:'uppercase',
        letterSpacing:'0.08em',marginBottom:2})}>
        {label}{unit?<span style={ss({color:C.faint,fontWeight:400,marginLeft:4,letterSpacing:0})}>{unit}</span>:''}
      </div>
      {options
        ? <select value={value as string} onChange={e=>setter(e.target.value)}
            style={ss({width:'100%',background:'#060f1a',border:`1px solid ${C.border}`,
              borderRadius:4,padding:'5px 8px',color:C.text,fontSize:11,fontFamily:'monospace',
              outline:'none',boxSizing:'border-box'})}>
            {options.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        : <input type='number' value={value as number} min={min} max={max} step={step}
            onChange={e=>setter(parseFloat(e.target.value)||0)}
            style={ss({width:'100%',background:'#060f1a',border:`1px solid ${C.border}`,
              borderRadius:4,padding:'5px 8px',color:C.text,fontSize:11,fontFamily:'monospace',
              outline:'none',boxSizing:'border-box'})}/>
      }
    </div>
  )
}

export function Divider({label}:{label:string}) {
  return (
    <div style={ss({display:'flex',alignItems:'center',gap:8,margin:'12px 0 6px'})}>
      <span style={ss({fontSize:8,fontWeight:700,color:C.accent,textTransform:'uppercase',
        letterSpacing:'0.12em',whiteSpace:'nowrap',fontFamily:"'Barlow Condensed',sans-serif"})}>
        <span style={ss({display:'inline-block',width:12,height:2,background:C.accent,
          borderRadius:1,marginRight:5,verticalAlign:'middle'})}/>
        {label}
      </span>
      <div style={ss({flex:1,height:1,background:C.border})}/>
    </div>
  )
}

export function KpiCard({
  label, value, unit, ok, sub, col
}:{label:string,value:string|number,unit?:string,ok?:boolean,sub?:string,col?:string}) {
  const color = ok===true ? C.green : ok===false ? C.red : col || C.teal
  return (
    <div style={ss({background:C.panel,border:`1px solid ${C.border}`,borderRadius:8,
      padding:'10px 14px',display:'flex',flexDirection:'column',gap:2})}>
      <div style={ss({fontSize:8.5,fontWeight:700,color:C.muted,textTransform:'uppercase',
        letterSpacing:'0.10em'})}>{label}</div>
      <div style={ss({fontSize:18,fontWeight:800,fontFamily:'monospace',color,lineHeight:1.1})}>
        {value}{unit&&<span style={ss({fontSize:12,fontWeight:400,color:C.muted,marginLeft:3})}>{unit}</span>}
      </div>
      {sub&&<div style={ss({fontSize:9,color:C.faint})}>{sub}</div>}
    </div>
  )
}

export function ResultRow({label,value,unit,sub,ok}:{
  label:string,value:any,unit?:string,sub?:string,ok?:boolean
}) {
  const col = ok===true?C.green:ok===false?C.red:C.text
  return (
    <div style={ss({display:'flex',justifyContent:'space-between',alignItems:'center',
      borderBottom:`1px solid ${C.border}33`,padding:'3px 0',fontSize:11})}>
      <span style={ss({color:C.muted})}>{label}</span>
      <span style={ss({fontFamily:'monospace',fontWeight:700,color:col})}>
        {value!=null?value:'—'}{unit&&<span style={ss({color:C.muted,fontWeight:400,marginLeft:3})}>{unit}</span>}
      </span>
    </div>
  )
}

export function AxialChart({
  history, dataKey, label, unit, color, refValue, refLabel
}:{
  history:any[],dataKey:string,label:string,unit:string,color:string,
  refValue?:number,refLabel?:string
}) {
  if(!history?.length) return null
  return (
    <div style={ss({background:C.panel,border:`1px solid ${C.border}`,borderRadius:8,padding:12})}>
      <div style={ss({fontSize:9,fontWeight:700,color:C.accent,textTransform:'uppercase',
        letterSpacing:'0.10em',marginBottom:8})}>{label} axial profile</div>
      <ResponsiveContainer width='100%' height={160}>
        <LineChart data={history} margin={{top:4,right:12,left:0,bottom:0}}>
          <CartesianGrid strokeDasharray='3 3' stroke={C.border} strokeOpacity={0.5}/>
          <XAxis dataKey='x' tick={{fill:C.muted,fontSize:8}} label={{value:'Length (m)',fill:C.muted,fontSize:8,position:'insideBottom',offset:-2}}/>
          <YAxis tick={{fill:C.muted,fontSize:8}} label={{value:unit,angle:-90,fill:C.muted,fontSize:8,position:'insideLeft'}}/>
          <Tooltip contentStyle={{background:C.bg,border:`1px solid ${C.border}`,fontSize:10}}
            labelStyle={{color:C.muted}} itemStyle={{color}}/>
          {refValue!=null&&(
            <ReferenceLine y={refValue} stroke={C.amber} strokeDasharray='5 3'
              label={{value:refLabel||'',fill:C.amber,fontSize:8,position:'right'}}/>
          )}
          <Line type='monotone' dataKey={dataKey} stroke={color} dot={false} strokeWidth={2}/>
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function RunBtn({onClick,loading}:{onClick:()=>void,loading:boolean}) {
  return (
    <button onClick={onClick} disabled={loading} style={ss({
      width:'100%',marginTop:10,padding:'9px 0',borderRadius:5,border:'none',
      background:loading?C.faint:'rgba(200,25,46,.85)',color:'#fff',
      fontSize:11,fontWeight:800,cursor:loading?'not-allowed':'pointer',
      fontFamily:"'Barlow Condensed',sans-serif",letterSpacing:'0.08em',
      textTransform:'uppercase' as const
    })}>
      {loading?'⏳ Calculating…':'▶ Run Calculation'}
    </button>
  )
}

export function ErrorBanner({msg}:{msg:string}) {
  return (
    <div style={ss({background:'rgba(224,82,82,.08)',border:`1px solid ${C.red}`,
      borderRadius:6,padding:'8px 14px',fontSize:11,color:C.red})}>
      ⚠️ {msg}
    </div>
  )
}

export function EmptyState({icon,name,desc}:{icon:string,name:string,desc:string}) {
  return (
    <div style={ss({flex:1,display:'flex',flexDirection:'column',alignItems:'center',
      justifyContent:'center',color:C.muted,gap:8,padding:40})}>
      <div style={ss({fontSize:36})}>{icon}</div>
      <div style={ss({fontSize:12,fontWeight:700,color:C.accent})}>{name}</div>
      <div style={ss({fontSize:10,color:C.muted,textAlign:'center',maxWidth:340,lineHeight:1.6})}>{desc}</div>
      <div style={ss({fontSize:10,color:C.faint,marginTop:4})}>Configure inputs → click Run Calculation</div>
    </div>
  )
}

export function ModuleShell({
  inputPanel, resultPanel
}:{inputPanel:React.ReactNode, resultPanel:React.ReactNode}) {
  return (
    <div style={ss({display:'flex',gap:12,padding:12,height:'100%',overflow:'hidden'})}>
      <div style={ss({width:260,flexShrink:0,background:C.panel,border:`1px solid ${C.border}`,
        borderRadius:8,padding:12,overflowY:'auto',height:'100%'})}>
        {inputPanel}
      </div>
      <div style={ss({flex:1,display:'flex',flexDirection:'column',gap:10,overflowY:'auto'})}>
        {resultPanel}
      </div>
    </div>
  )
}
