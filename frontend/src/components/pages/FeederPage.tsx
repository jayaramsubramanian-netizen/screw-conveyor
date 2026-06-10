/**
 * FeederPage.tsx — Screw Feeder / Doser
 * Full port of HTML screw-process-v4.html feeder module.
 * Covers: K-factor, turndown, feed accuracy (CV%), hopper interface,
 *         flood/starve analysis, LIW load cell sizing, N vs Q calibration curve.
 */
import React, { useState } from 'react'
import axios from 'axios'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { C, Field, Divider, KpiCard, ResultRow, RunBtn, ErrorBanner, EmptyState, ModuleShell } from './ProcessPage'

const ss = (s: React.CSSProperties) => s

export default function FeederPage() {
  const [r, setR]         = useState<any>(null)
  const [loading, setL]   = useState(false)
  const [err, setErr]     = useState<string|null>(null)

  const [inp, setInp] = useState({
    fDiam: 0.15, fLen: 1.2, fPitch: 1.0, fFill: 0.45,
    fRho: 0.8, fN_min: 2, fN_max: 60, fQ_target: 0.5,
    fMat_flowability: 'easy_flowing',
    fMode: 'volumetric', fDriveType: 'servo',
    fHopperVol: 0.5, fHopperAngle: 60, fWallFriction: 0.35,
    fLIW_tare: 50,
    fDownstreamT: 0, fBatchSize: 0,
  })
  const s = (k: string) => (v: any) => setInp(p => ({ ...p, [k]: v }))

  const run = async () => {
    setL(true); setErr(null)
    try {
      const { data } = await axios.post('/api/v1/process/feeder', inp)
      setR(data)
    } catch (e: any) { setErr(e?.response?.data?.detail || e?.message || 'Error') }
    finally { setL(false) }
  }

  const accuracyColor = (cv: number) =>
    cv < 0.5 ? C.green : cv < 1.5 ? C.teal : cv < 3.0 ? C.amber : C.red

  return (
    <ModuleShell
      inputPanel={<>
        <div style={ss({ marginBottom: 10 })}>
          <div style={ss({ fontSize: 20, marginBottom: 3 })}>🎚️</div>
          <div style={ss({ fontSize: 12, fontWeight: 800, color: C.accent, fontFamily: "'Barlow Condensed',sans-serif", letterSpacing: '0.08em' })}>
            FEEDER / DOSER
          </div>
          <div style={ss({ fontSize: 9, color: C.muted, marginTop: 3, lineHeight: 1.6 })}>
            K-factor · Turndown · CV% accuracy · Hopper interface · Flood/starve · LIW sizing
          </div>
        </div>

        <Divider label="A — Screw Geometry"/>
        <div style={ss({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 })}>
          <Field label="Diameter" value={inp.fDiam} setter={s('fDiam')} min={0.05} max={0.60} step={0.01} unit="m"/>
          <Field label="Length" value={inp.fLen} setter={s('fLen')} min={0.2} max={6} step={0.1} unit="m"/>
          <Field label="Pitch ratio ×D" value={inp.fPitch} setter={s('fPitch')} min={0.3} max={1.5} step={0.1}/>
          <Field label="Fill fraction" value={inp.fFill} setter={s('fFill')} min={0.15} max={0.70} step={0.05}/>
        </div>
        {inp.fFill > 0.60 && (
          <div style={ss({ background: 'rgba(224,82,82,.08)', border: `1px solid ${C.red}44`, borderRadius: 4, padding: '5px 8px', fontSize: 9, color: C.red, marginBottom: 4 })}>
            ⚠ Fill {(inp.fFill * 100).toFixed(0)}% &gt; 60% — flood risk with free-flowing materials
          </div>
        )}

        <Divider label="B — Material & Speed Range"/>
        <div style={ss({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 })}>
          <Field label="Bulk density" value={inp.fRho} setter={s('fRho')} min={0.05} max={3} step={0.05} unit="t/m³"/>
          <Field label="Target flow" value={inp.fQ_target} setter={s('fQ_target')} min={0.001} max={500} step={0.01} unit="t/h"/>
          <Field label="N_min" value={inp.fN_min} setter={s('fN_min')} min={0.5} max={20} step={0.5} unit="RPM"/>
          <Field label="N_max" value={inp.fN_max} setter={s('fN_max')} min={5} max={200} step={1} unit="RPM"/>
        </div>
        <Field label="Material flowability" value={inp.fMat_flowability} setter={s('fMat_flowability')} options={[
          { value: 'free_flowing',  label: 'Free-flowing (K≈0.90) — sand, grain, pellets' },
          { value: 'easy_flowing',  label: 'Easy-flowing (K≈0.82) — sugar, salt, powder' },
          { value: 'cohesive',      label: 'Cohesive (K≈0.72) — flour, clay, sticky' },
          { value: 'very_cohesive', label: 'Very cohesive (K≈0.58) — wet cake, hygroscopic' },
        ]}/>

        <Divider label="C — Control Mode & Drive"/>
        <Field label="Control mode" value={inp.fMode} setter={s('fMode')} options={[
          { value: 'volumetric', label: '📦 Volumetric — RPM controls Q (±2–5%)' },
          { value: 'liw',        label: '⚖️ Loss-in-Weight — gravimetric (±0.5%)' },
        ]}/>
        <Field label="Drive type" value={inp.fDriveType} setter={s('fDriveType')} options={[
          { value: 'servo',   label: '🎯 Servo — highest accuracy' },
          { value: 'vfd',     label: '⚡ VFD/AC — standard' },
          { value: 'stepper', label: '🔩 Stepper — digital positioning' },
          { value: 'dc',      label: '🔋 DC drive — low cost' },
        ]}/>
        {inp.fMode === 'liw' && (
          <div style={ss({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 4, background: 'rgba(45,212,191,.05)', border: `1px solid ${C.teal}33`, borderRadius: 5, padding: 8 })}>
            <Field label="Tare weight" value={inp.fLIW_tare} setter={s('fLIW_tare')} min={5} max={2000} step={5} unit="kg"/>
            <Field label="Hopper vol" value={inp.fHopperVol} setter={s('fHopperVol')} min={0.01} max={50} step={0.05} unit="m³"/>
          </div>
        )}
        {inp.fMode === 'volumetric' && (
          <Field label="Hopper volume" value={inp.fHopperVol} setter={s('fHopperVol')} min={0.01} max={50} step={0.05} unit="m³"/>
        )}

        <Divider label="D — Hopper Interface (Jenike)"/>
        <div style={ss({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 })}>
          <Field label="Hopper angle" value={inp.fHopperAngle} setter={s('fHopperAngle')} min={30} max={90} step={5} unit="°"/>
          <Field label="Wall friction μ" value={inp.fWallFriction} setter={s('fWallFriction')} min={0.1} max={0.7} step={0.05}/>
        </div>

        <Divider label="E — Downstream Matching"/>
        <div style={ss({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 })}>
          <Field label="Process cycle" value={inp.fDownstreamT} setter={s('fDownstreamT')} min={0} max={3600} step={10} unit="s"/>
          <Field label="Batch size" value={inp.fBatchSize} setter={s('fBatchSize')} min={0} max={100000} step={10} unit="kg"/>
        </div>
        <RunBtn onClick={run} loading={loading}/>
      </>}

      resultPanel={<>
        {err && <ErrorBanner msg={err}/>}
        {r && <>
          {/* KPI row */}
          <div style={ss({ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 8 })}>
            <KpiCard label="Target Flow" value={r.target_achievable ? `${r.Q_actual?.toFixed(3)}` : '✗ NOT MET'}
              unit={r.target_achievable ? 't/h' : ''} ok={r.target_achievable}
              sub={`req ${inp.fQ_target} t/h`}/>
            <KpiCard label="Turndown" value={r.turndown?.toFixed(1)} unit=":1"
              col={r.turndown >= 10 ? C.green : C.amber} sub="Q_max / Q_min"/>
            <KpiCard label="Feed Accuracy" value={`CV ${r.CV_total?.toFixed(1)}`} unit="%"
              col={accuracyColor(r.CV_total)} sub={r.accuracy_class}/>
            <KpiCard label="K-factor" value={r.K_factor?.toFixed(3)} col={C.blue} sub="volumetric efficiency"/>
          </div>

          {/* Warnings */}
          {(r.warns?.crit?.length > 0 || r.warns?.adv?.length > 0) && (
            <div style={ss({ display: 'flex', flexDirection: 'column', gap: 6 })}>
              {r.warns.crit.map((w: string, i: number) => (
                <div key={i} style={ss({ background: 'rgba(224,82,82,.08)', border: `1px solid ${C.red}44`, borderRadius: 6, padding: '6px 10px', fontSize: 10, color: C.red })}>
                  ✗ [CRITICAL] {w}
                </div>
              ))}
              {r.warns.adv.map((w: string, i: number) => (
                <div key={i} style={ss({ background: 'rgba(217,142,0,.07)', border: `1px solid ${C.amber}44`, borderRadius: 6, padding: '6px 10px', fontSize: 10, color: C.amber })}>
                  ▲ [ADVISORY] {w}
                </div>
              ))}
              {r.warns.opt?.map((w: string, i: number) => (
                <div key={i} style={ss({ background: 'rgba(45,212,191,.07)', border: `1px solid ${C.teal}44`, borderRadius: 6, padding: '6px 10px', fontSize: 10, color: C.teal })}>
                  💡 {w}
                </div>
              ))}
            </div>
          )}

          {/* Main results grid */}
          <div style={ss({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 })}>
            {/* Flow range */}
            <div style={ss({ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, padding: 12 })}>
              <div style={ss({ fontSize: 9, fontWeight: 700, color: C.accent, letterSpacing: '0.10em', textTransform: 'uppercase', fontFamily: "'Barlow Condensed',sans-serif", marginBottom: 8 })}>
                📊 Flow Range
              </div>
              <ResultRow label="Q_min" value={r.Q_mass_min?.toFixed(4)} unit="t/h"/>
              <ResultRow label="Q_max" value={r.Q_mass_max?.toFixed(4)} unit="t/h"/>
              <ResultRow label="Q_target" value={inp.fQ_target} unit="t/h"/>
              <ResultRow label="Q_actual" value={r.Q_actual?.toFixed(4)} unit="t/h" ok={r.target_achievable}/>
              <ResultRow label="N_required" value={r.N_required?.toFixed(1)} unit="RPM" ok={r.target_achievable}/>
              <ResultRow label="N_operating" value={r.N_req_clamped?.toFixed(1)} unit="RPM"/>
              <ResultRow label="Qv/rev" value={r.Qv_per_rpm?.toFixed(4)} unit="L/rev"/>
              <ResultRow label="Turndown" value={r.turndown?.toFixed(1)+':1'} ok={r.turndown >= 10}/>
            </div>

            {/* K-factor & Accuracy */}
            <div style={ss({ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, padding: 12 })}>
              <div style={ss({ fontSize: 9, fontWeight: 700, color: C.accent, letterSpacing: '0.10em', textTransform: 'uppercase', fontFamily: "'Barlow Condensed',sans-serif", marginBottom: 8 })}>
                🎯 K-factor & Accuracy
              </div>
              <ResultRow label="K_base (flowability)" value={r.K_base?.toFixed(3)}/>
              <ResultRow label="K_fill (correction)"  value={r.K_fill?.toFixed(3)}/>
              <ResultRow label="K_factor (total)"     value={r.K_factor?.toFixed(3)} col={C.blue}/>
              <div style={ss({ height: 1, background: C.border, margin: '5px 0' })}/>
              <ResultRow label="CV drive"   value={r.CV_drive?.toFixed(2)} unit="%"/>
              <ResultRow label="CV material" value={r.CV_mat?.toFixed(2)} unit="%"/>
              <ResultRow label="CV mode"    value={r.CV_mode?.toFixed(2)} unit="%"/>
              <ResultRow label="CV total (RSS)" value={r.CV_total?.toFixed(2)} unit="%" col={accuracyColor(r.CV_total)}/>
              <div style={ss({ fontSize: 9, color: accuracyColor(r.CV_total), marginTop: 4, fontWeight: 700 })}>
                {r.accuracy_class}
              </div>
            </div>

            {/* Power & Drive */}
            <div style={ss({ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, padding: 12 })}>
              <div style={ss({ fontSize: 9, fontWeight: 700, color: C.accent, letterSpacing: '0.10em', textTransform: 'uppercase', fontFamily: "'Barlow Condensed',sans-serif", marginBottom: 8 })}>
                ⚡ Power & Drive
              </div>
              <ResultRow label="P friction"  value={r.P_e?.toFixed(4)} unit="kW"/>
              <ResultRow label="P material"  value={r.P_mat?.toFixed(4)} unit="kW"/>
              <ResultRow label="P shaft"     value={r.P_shaft?.toFixed(4)} unit="kW"/>
              <ResultRow label="P total"     value={r.P_total?.toFixed(3)} unit="kW"/>
              <ResultRow label="Motor"       value={r.motor_kW} unit="kW" col={C.purple}/>
              <ResultRow label="Torque"      value={r.torque_Nm?.toFixed(1)} unit="Nm"/>
              <ResultRow label="Tip speed"   value={r.tip_speed?.toFixed(3)} unit="m/s" ok={r.tip_speed <= 2}/>
              <ResultRow label="L/D ratio"   value={r.LD_ratio?.toFixed(1)} ok={r.LD_ratio <= 8}/>
            </div>

            {/* Hopper Interface */}
            <div style={ss({ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, padding: 12 })}>
              <div style={ss({ fontSize: 9, fontWeight: 700, color: C.accent, letterSpacing: '0.10em', textTransform: 'uppercase', fontFamily: "'Barlow Condensed',sans-serif", marginBottom: 8 })}>
                🪣 Hopper Interface
              </div>
              <ResultRow label="Min outlet size" value={r.outlet_min_m?.toFixed(4)} unit="m"/>
              <ResultRow label="Hopper angle"    value={inp.fHopperAngle} unit="°"/>
              <ResultRow label="Mass flow angle" value={r.mass_flow_angle?.toFixed(1)} unit="° half-angle min"/>
              <ResultRow label="Refill interval" value={r.refill_min?.toFixed(1)} unit="min" ok={r.refill_min >= 10}/>
              <ResultRow label="Surge capacity"  value={r.surge_time_min?.toFixed(1)} unit="min"/>
              <ResultRow label="Arch risk"       value={r.arch_risk_msg} ok={!r.arch_risk}/>
              <ResultRow label="Flood risk"      value={r.flood_risk ? '⚠ YES' : 'No ✓'} ok={!r.flood_risk}/>
              <ResultRow label="Starve risk"     value={r.starve_risk ? '⚠ YES' : 'No ✓'} ok={!r.starve_risk}/>
            </div>

            {/* Control & LIW */}
            <div style={ss({ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, padding: 12 })}>
              <div style={ss({ fontSize: 9, fontWeight: 700, color: C.accent, letterSpacing: '0.10em', textTransform: 'uppercase', fontFamily: "'Barlow Condensed',sans-serif", marginBottom: 8 })}>
                🎛️ Control Sizing
              </div>
              <ResultRow label="dQ/dN"           value={r.dQ_per_rpm?.toFixed(5)} unit="t/h/RPM"/>
              <ResultRow label="RPM resolution"  value={r.rpm_resolution?.toFixed(2)} unit="%/RPM" ok={r.control_ok}/>
              <ResultRow label="Control OK"      value={r.control_ok ? '✓ <2%/RPM' : '✗ >2%/RPM'} ok={r.control_ok}/>
              {inp.fMode === 'liw' && <>
                <div style={ss({ height: 1, background: C.border, margin: '5px 0' })}/>
                <div style={ss({ fontSize: 9, fontWeight: 700, color: C.teal, marginBottom: 4 })}>⚖️ LIW Load Cell</div>
                <ResultRow label="LC rating"     value={r.liw_lcell} unit="kg"/>
                <ResultRow label="LC resolution" value={r.liw_resolution?.toFixed(3)} unit="kg"/>
                <ResultRow label="Tare weight"   value={inp.fLIW_tare} unit="kg"/>
              </>}
            </div>

            {/* Downstream */}
            <div style={ss({ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, padding: 12 })}>
              <div style={ss({ fontSize: 9, fontWeight: 700, color: C.accent, letterSpacing: '0.10em', textTransform: 'uppercase', fontFamily: "'Barlow Condensed',sans-serif", marginBottom: 8 })}>
                🔁 Downstream Matching
              </div>
              <ResultRow label="V axial"         value={r.v_ax_f?.toFixed(4)} unit="m/s"/>
              <ResultRow label="Slip factor S"   value={r.S_f?.toFixed(3)??'—'}/>
              <ResultRow label="Process cycle"   value={inp.fDownstreamT || 'Continuous'} unit={inp.fDownstreamT ? 's' : ''}/>
              <ResultRow label="Batch size"      value={inp.fBatchSize || 'N/A'} unit={inp.fBatchSize ? 'kg' : ''}/>
              {inp.fBatchSize > 0 && (
                <ResultRow label="Batch fill time" value={r.batch_time_s?.toFixed(1)} unit="s" ok={r.batch_ok}/>
              )}
            </div>
          </div>

          {/* N vs Q calibration curve */}
          {r.calibCurve?.length > 0 && (
            <div style={ss({ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, padding: 12 })}>
              <div style={ss({ fontSize: 9, fontWeight: 700, color: C.accent, letterSpacing: '0.10em', textTransform: 'uppercase', fontFamily: "'Barlow Condensed',sans-serif", marginBottom: 8 })}>
                📈 N vs Q Calibration Curve
              </div>
              <div style={ss({ fontSize: 9, color: C.muted, marginBottom: 6 })}>
                Speed (RPM) → Mass flow (t/h) — linear relationship for screw feeders
              </div>
              <ResponsiveContainer width="100%" height={160}>
                <LineChart data={r.calibCurve} margin={{ top: 4, right: 40, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.border} strokeOpacity={0.5}/>
                  <XAxis dataKey="N" tick={{ fill: C.muted, fontSize: 8 }} label={{ value: 'Speed (RPM)', fill: C.muted, fontSize: 8, position: 'insideBottom', offset: -2 }}/>
                  <YAxis tick={{ fill: C.muted, fontSize: 8 }} label={{ value: 't/h', angle: -90, fill: C.muted, fontSize: 8, position: 'insideLeft' }}/>
                  <Tooltip contentStyle={{ background: '#07111e', border: `1px solid ${C.border}`, fontSize: 10 }}
                    formatter={(v: any) => [`${Number(v).toFixed(4)} t/h`, 'Q']}
                    labelFormatter={(l: any) => `N = ${l} RPM`}/>
                  <ReferenceLine y={inp.fQ_target} stroke={C.amber} strokeDasharray="5 3"
                    label={{ value: `Target ${inp.fQ_target} t/h`, fill: C.amber, fontSize: 8, position: 'right' }}/>
                  <ReferenceLine x={r.N_req_clamped} stroke={C.green} strokeDasharray="5 3"
                    label={{ value: `${r.N_req_clamped?.toFixed(0)} RPM`, fill: C.green, fontSize: 8, position: 'top' }}/>
                  <Line type="monotone" dataKey="Q" stroke={C.blue} dot={false} strokeWidth={2}/>
                </LineChart>
              </ResponsiveContainer>
              <div style={ss({ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 6, marginTop: 8 })}>
                {[0, 5, 10].map(i => {
                  const pt = r.calibCurve[i]
                  return (
                    <div key={i} style={ss({ background: '#060f1a', borderRadius: 5, padding: '5px 8px', fontSize: 9 })}>
                      <div style={ss({ color: C.muted })}>N = {pt?.N} RPM</div>
                      <div style={ss({ color: C.text, fontFamily: 'monospace', fontWeight: 700 })}>{pt?.Q?.toFixed(4)} t/h</div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </>}

        {!r && !loading && !err && (
          <EmptyState icon="🎚️" name="Screw Feeder / Doser"
            desc="K-factor volumetric efficiency · Turndown ratio · Feed accuracy (CV%) via drive+material+mode RSS · Hopper interface with Jenike arch analysis · Flood/starve assessment · N vs Q calibration curve. CEMA 7th Ed. + Jenike principles."/>
        )}
      </>}
    />
  )
}
