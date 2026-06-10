import React, { useRef, useEffect, useState } from 'react'
const MANUAL_URL = '/manual.html'   // served from public/ in production; proxy in dev
export default function ManualPage() {
  const [loaded, setLoaded] = useState(false)
  return (
    <div style={{ height: '100%', overflow: 'hidden', display:'flex', flexDirection:'column', background:'#0b1522' }}>
      {!loaded && (
        <div style={{ display:'flex', alignItems:'center', justifyContent:'center',
          flex:1, background:'#0b1522', gap:12 }}>
          <div style={{ width:22, height:22, border:'3px solid #e8a000',
            borderTopColor:'transparent', borderRadius:'50%',
            animation:'spin 0.8s linear infinite' }}/>
          <span style={{ color:'#5d7d99', fontSize:12 }}>Loading VECTRIX™ Manual…</span>
          <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
        </div>
      )}
      <iframe
        src={MANUAL_URL}
        onLoad={() => setLoaded(true)}
        style={{ flex:1, border:'none', width:'100%', height:'100%',
          display: loaded ? 'block' : 'none' }}
        title="VECTRIX™ Engineering Manual"
      />
    </div>
  )
}
