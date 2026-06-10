import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
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
import React, { useState, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer, } from 'recharts';
import { useCalcStore, useCalculate, useMaterials, useBearings, useGearboxes } from '../../hooks/useCalculator';
import * as api from '../../api/client';
// ── Colours ─────────────────────────────────────────────────────
const C = {
    panel: '#0d1c2e', border: '#162438', text: '#ddeaf6',
    muted: '#5a7a9a', faint: '#3a5470', accent: '#c8192e',
    green: '#1fb86e', red: '#e05252', amber: '#d98e00', blue: '#4a9eff',
    teal: '#2dd4bf', purple: '#a78bfa',
};
const ss = (s) => s;
// ── calcStructural (matches HTML prototype exactly) ──────────────
function calcStructural(D_m, L_m, rho, ang, fill = 0.35, abr = 'Medium', temp = 20) {
    const rk = rho * 1000, g = 9.81;
    const sa = temp > 200 ? 100e6 : temp > 150 ? 120e6 : 160e6;
    const sw = sa * 0.7, sb = 144e6;
    const fd = D_m * fill * 1.3, Ph = rk * g * fd, Pd = Ph * 1.3;
    const hs = Math.min(L_m, D_m >= 0.45 ? 3.6 : D_m >= 0.3 ? 3.0 : 2.4);
    const wm = rk * (Math.PI / 4) * D_m * D_m * fill * g;
    const wt = 22 * D_m * g * (1 + 0.1 * temp / 200);
    const ww = wm + wt;
    const Mm = ww * hs * hs / 8;
    const tb = Math.sqrt(4 * Mm / (Math.PI * D_m * sa));
    const Dm = D_m * 1000;
    const tcm = Dm < 150 ? 3 : Dm < 250 ? 4 : Dm < 400 ? 5 : Dm < 600 ? 6 : Dm < 900 ? 8 : 10;
    const wa2 = abr === 'High' || abr === 'Very High' ? 4 : abr === 'Medium' ? 3 : 2;
    const tc = Math.max(tb, Pd * D_m / (2 * sa)) * 1000;
    const PLATE = [3, 4, 5, 6, 8, 10, 12, 14, 16, 20, 25, 30];
    const tp = PLATE.find(t => t >= Math.max(Math.ceil(tc + wa2), tcm)) || 30;
    const Pc = 1200 * g / (0.06 * D_m) + 2000;
    const tcc = Math.sqrt(3 * Pc * D_m * D_m / (16 * sa)) * 1000;
    const tc2 = PLATE.find(t => t >= Math.max(tcc + 2, tcm + 1)) || 12;
    const PCD = D_m + 2 * (tp / 1000) + 0.05;
    const nb = Math.ceil(Math.ceil(Math.max(4, 4 * Math.ceil(Math.PI * PCD * 1000 / 160)) / 4) * 4);
    const bp = Math.PI * PCD * 1000 / nb;
    const Fp = Pd * (Math.PI / 4) * D_m * D_m + 2 * Math.PI * (D_m / 2) * 0.015 * 6895;
    const Fe = Fp / nb, Ab = Fe / sb;
    const dr = Math.sqrt(4 * Ab / Math.PI) * 1000;
    const BS = [{ d: 8, A: 36.6e-6 }, { d: 10, A: 58e-6 }, { d: 12, A: 84.3e-6 }, { d: 16, A: 157e-6 }, { d: 20, A: 245e-6 }, { d: 24, A: 353e-6 }];
    const bs = BS.find(b => b.d >= Math.max(dr, 8)) || BS[BS.length - 1];
    const sb_act = Fe / bs.A / 1e6;
    const ns = Math.max(2, Math.ceil(L_m / hs) + 1);
    const Rs = ww * L_m / ns;
    const wh = Math.max(3, Math.ceil(Pd * D_m / (2 * sw * 0.707) * 1000));
    const sm = Math.round(7850 * Math.PI * D_m * 0.006 * L_m + (Math.PI / 4 * D_m * D_m * L_m * fill * rk));
    const tm = Math.round(7850 * Math.PI * D_m * (tp / 1000) * L_m);
    return {
        w_total: +(ww / 1000).toFixed(3), M_max: +(Mm / 1000).toFixed(3),
        hanger_span: +hs.toFixed(2), t_plate: tp, t_cover: tc2,
        bolt_size: `M${bs.d} gr.8.8`, n_bolts: nb, bolt_pitch: +bp.toFixed(0),
        bolt_ok: sb_act <= 144, bolt_cap: +((bs.A * 144e6 * nb / 1000)).toFixed(1),
        pressure_load: +(Fe / 1000).toFixed(1), weld_size: wh,
        flange_t: PLATE.find(t => t >= Math.max(tp, 11)) || 14,
        flange_w: Math.round(Dm * 0.12 + 20), cover_bp: Math.round(Math.min(150, Dm / 3)),
        n_supports: ns, R_kN: +(Rs / 1000).toFixed(1), screw_mass: sm, trough_mass: tm,
        end_react: +((ww * L_m / 2) / 1000).toFixed(1), sigma_allow: +(sa / 1e6).toFixed(0),
        key_b: Dm >= 100 ? 28 : Dm >= 85 ? 25 : Dm >= 70 ? 20 : 16,
    };
}
// ── Shared primitives ────────────────────────────────────────────
const Lbl = ({ c, children }) => (_jsxs("div", { style: ss({ fontSize: 10, color: C.muted, fontWeight: 700, textTransform: 'uppercase',
        letterSpacing: '0.07em', marginBottom: 3 }), children: [children, c && _jsx("span", { style: ss({ marginLeft: 4, fontWeight: 400, textTransform: 'none' }), children: c })] }));
const Divider = ({ label }) => (_jsxs("div", { style: ss({ display: 'flex', alignItems: 'center', gap: 6, margin: '10px 0 7px' }), children: [label && _jsx("span", { style: ss({ fontSize: 9, color: C.faint, fontWeight: 700, letterSpacing: '0.09em', whiteSpace: 'nowrap' }), children: label }), _jsx("div", { style: ss({ flex: 1, height: 1, background: C.border }) })] }));
const SHdr = ({ icon, label, badge, col }) => (_jsxs("div", { style: ss({ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }), children: [_jsx("span", { style: ss({ fontSize: 11 }), children: icon }), _jsx("span", { style: ss({ fontSize: 10, fontWeight: 800, color: col || C.accent, letterSpacing: '0.09em', textTransform: 'uppercase', flex: 1 }), children: label }), badge] }));
const RR = ({ label, value, unit = '', ok, hl, sub }) => {
    if (value == null)
        return null;
    const col = ok === true ? C.green : ok === false ? C.red : hl ? C.accent : C.text;
    return (_jsxs("div", { style: ss({ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
            borderBottom: `1px solid ${C.border}`, padding: '4px 0', fontSize: 11, background: hl ? 'rgba(232,160,0,.04)' : 'transparent' }), children: [_jsxs("span", { style: ss({ color: C.muted }), children: [label, sub && _jsx("span", { style: ss({ fontSize: 9, color: C.faint, marginLeft: 4 }), children: sub })] }), _jsxs("span", { style: ss({ fontFamily: 'monospace', fontWeight: 700, color: col }), children: [value, unit && _jsx("span", { style: ss({ color: C.muted, fontWeight: 400, marginLeft: 3 }), children: unit })] })] }));
};
const Chip = ({ ok, label }) => (_jsx("span", { style: ss({ fontSize: 9, fontWeight: 700, padding: '2px 7px', borderRadius: 4,
        background: ok ? 'rgba(31,184,110,.15)' : 'rgba(224,82,82,.15)',
        color: ok ? C.green : C.red, border: `1px solid ${ok ? C.green : C.red}` }), children: label }));
const Panel = ({ children, bordered = true }) => (_jsx("div", { style: ss({ background: C.panel, border: bordered ? `1px solid ${C.border}` : 'none', borderRadius: 9, padding: 12 }), children: children }));
// ── Input primitives ─────────────────────────────────────────────
const NI = ({ field, label, min, max, step = 0.01, unit }) => {
    const { inp, setInp } = useCalcStore();
    return (_jsxs("div", { style: ss({ marginBottom: 7 }), children: [_jsx(Lbl, { c: unit && `(${unit})`, children: label }), _jsx("input", { type: "number", value: inp[field] ?? '', min: min, max: max, step: step, onChange: e => setInp({ [field]: parseFloat(e.target.value) || 0 }), style: ss({ width: '100%', background: '#081321', border: `1px solid ${C.border}`, borderRadius: 4,
                    padding: '5px 8px', color: C.text, fontSize: 11, fontFamily: 'monospace', outline: 'none', boxSizing: 'border-box' }) })] }));
};
const SI = ({ field, label, options }) => {
    const { inp, setInp } = useCalcStore();
    return (_jsxs("div", { style: ss({ marginBottom: 7 }), children: [_jsx(Lbl, { children: label }), _jsx("select", { value: inp[field], onChange: e => setInp({ [field]: e.target.value }), style: ss({ width: '100%', background: '#081321', border: `1px solid ${C.border}`, borderRadius: 4,
                    padding: '5px 8px', color: C.text, fontSize: 11, fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box' }), children: options.map(o => _jsx("option", { value: o.value, children: o.label }, o.value)) })] }));
};
const Ck = ({ field, label }) => {
    const { inp, setInp } = useCalcStore();
    return (_jsxs("label", { style: ss({ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: C.muted, cursor: 'pointer', marginBottom: 5 }), children: [_jsx("input", { type: "checkbox", checked: !!inp[field], onChange: e => setInp({ [field]: e.target.checked }) }), label] }));
};
// ── Standards tab component ──────────────────────────────────────
const STD_DEFS = {
    CEMA: { lam: 1.00, flag: '🇺🇸', label: 'CEMA 7th Ed.', desc: 'CEMA resistance-factor method. λ multiplier = 1.00 (baseline).' },
    DIN: { lam: 1.01, flag: '🇩🇪', label: 'DIN 15262', desc: 'German DIN λ-coefficient method. +1% on material λ.' },
    Custom: { lam: 1.05, flag: '⚙️', label: 'Custom', desc: 'User-defined λ-multiplier. Adjust to match field data or project spec.' },
};
function StdTabs({ activeStd, setStd, customLam, setCustomLam, multiR, matLam, matName }) {
    const def = STD_DEFS[activeStd];
    const lamMult = activeStd === 'Custom' ? customLam : def?.lam || 1.0;
    const effLam = (matLam * lamMult).toFixed(3);
    return (_jsxs("div", { style: ss({ marginBottom: 12 }), children: [_jsx("div", { style: ss({ display: 'flex', gap: 0, borderBottom: `2px solid ${C.border}`, marginBottom: 12 }), children: Object.entries(STD_DEFS).map(([key, d]) => (_jsxs("button", { onClick: () => setStd(key), style: ss({ padding: '7px 18px', border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: 12,
                        background: 'transparent', fontFamily: 'inherit',
                        color: activeStd === key ? C.accent : C.muted,
                        borderBottom: activeStd === key ? `2px solid ${C.accent}` : '2px solid transparent',
                        marginBottom: -2 }), children: [d.flag, " ", key] }, key))) }), _jsxs("div", { style: ss({ background: 'rgba(74,158,255,.05)', border: '1px solid rgba(74,158,255,.15)',
                    borderRadius: 7, padding: '8px 12px', marginBottom: 10, fontSize: 9.5, color: 'rgba(221,234,246,.7)', lineHeight: 1.6 }), children: [_jsx("strong", { style: ss({ color: C.blue, fontSize: 10 }), children: "\u03BB (Lambda) \u2014 How it works: " }), "The material \u03BB (", matLam.toFixed(2), " for ", matName, ") is the CEMA flight resistance factor. The standards multiplier (", lamMult.toFixed(2), ") is a method correction factor applied on top.", ' ', _jsxs("strong", { style: ss({ color: C.accent }), children: ["Effective \u03BB used in Pm = ", matLam.toFixed(2), " \u00D7 ", lamMult.toFixed(2), " = ", effLam] }), ".", ' ', "Pm = Q_design \u00D7 L \u00D7 \u03BB_eff \u00D7 Ks / 367, where 367 = unit conversion (kg\u00B7m/min \u2192 kW)."] }), _jsxs("div", { style: ss({ background: 'rgba(232,160,0,.06)', border: '1px solid rgba(232,160,0,.2)',
                    borderRadius: 7, padding: '8px 12px', marginBottom: 10 }), children: [_jsxs("div", { style: ss({ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }), children: [_jsxs("div", { style: ss({ flex: 1 }), children: [_jsxs("p", { style: ss({ fontSize: 11, fontWeight: 700, color: C.accent }), children: [def?.flag, " ", def?.label] }), _jsx("p", { style: ss({ fontSize: 10, color: C.muted }), children: def?.desc })] }), _jsxs("div", { style: ss({ textAlign: 'right', fontSize: 10, fontFamily: 'monospace' }), children: [_jsx("span", { style: ss({ color: C.muted }), children: "mat.\u03BB " }), _jsx("strong", { style: ss({ color: C.text }), children: matLam.toFixed(2) }), _jsx("span", { style: ss({ color: C.muted, margin: '0 4px' }), children: "\u00D7" }), _jsx("span", { style: ss({ color: C.muted }), children: "SF " }), _jsx("strong", { style: ss({ color: C.accent }), children: lamMult.toFixed(3) }), _jsx("span", { style: ss({ color: C.muted, margin: '0 4px' }), children: "=" }), _jsxs("strong", { style: ss({ color: C.green, fontSize: 12 }), children: ["\u03BB_eff ", effLam] })] })] }), activeStd === 'Custom' && (_jsxs("div", { style: ss({ marginTop: 10, padding: '8px 10px', background: 'rgba(0,0,0,.2)', borderRadius: 6 }), children: [_jsx("p", { style: ss({ fontSize: 9, fontWeight: 700, color: C.accent, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }), children: "\u2699\uFE0F Custom Parameters" }), _jsxs("div", { style: ss({ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 8, alignItems: 'center' }), children: [_jsx("label", { style: ss({ fontSize: 9, color: C.muted }), children: "\u03BB Multiplier (0.80\u20132.00)" }), _jsxs("div", { style: ss({ display: 'flex', gap: 6, alignItems: 'center' }), children: [_jsx("input", { type: "number", value: customLam, step: 0.01, min: 0.8, max: 2.0, onChange: e => setCustomLam(Math.max(0.8, Math.min(2.0, parseFloat(e.target.value) || 1.05))), style: ss({ width: 70, background: '#081321', border: `1px solid ${C.accent}`, color: C.accent,
                                                    borderRadius: 4, padding: '3px 6px', fontSize: 11, fontFamily: 'monospace', fontWeight: 700 }) }), _jsx("div", { style: ss({ flex: 1, height: 6, background: 'rgba(0,0,0,.3)', borderRadius: 3, overflow: 'hidden' }), children: _jsx("div", { style: ss({ width: Math.max(0, Math.min(100, (customLam - 0.8) / 1.2 * 100)) + '%', height: '100%',
                                                        background: customLam > 1.3 ? C.red : customLam > 1.1 ? C.amber : C.green, borderRadius: 3 }) }) }), _jsx("span", { style: ss({ fontSize: 9, color: C.muted, minWidth: 70 }), children: customLam < 0.95 ? 'under-estimate' : customLam > 1.15 ? 'conservative' : 'standard' })] })] })] }))] })] }));
}
// ── Design Health ────────────────────────────────────────────────
function DesignHealth({ R, inp }) {
    if (!R)
        return null;
    const f2 = (v, d = 2) => v.toFixed(d);
    const checks = [
        { label: 'Capacity', ok: R.cap.ok, val: f2(R.cap.Qt, 1) + ' t/h', req: R.cap.req + ' t/h req' },
        { label: 'Shaft Stress', ok: R.tor.shOk, val: f2(R.tor.tau, 1) + ' MPa', req: '≤' + inp.sallow + ' MPa' },
        { label: 'Gearbox Torque', ok: R.gbx_r?.tOk, val: Math.round(R.tor.Ts) + ' Nm', req: '≤' + (R.gbx_r?.Tn_derated || R.gbx_r?.Tn || 0 | 0).toLocaleString() + ' Nm' },
        { label: 'Bearing L10', ok: R.brg_r?.ok, val: Math.round(R.brg_r?.L10 || 0).toLocaleString() + ' h', req: '≥' + (R.brg_r?.L10_target || 20000).toLocaleString() + ' h' },
        { label: 'Vibration Risk', ok: (R.vibration_risk || 0) < 3, val: R.vri_label || '—', req: 'Low target' },
        { label: 'Energy kWh/t', ok: (R.eff?.kWh_t || 9) < 1, val: f2(R.eff?.kWh_t || 0, 3), req: '<1.0 optimal' },
        { label: 'Fill φ (act)', ok: (R.cap.fill_actual || R.cap.fill || 0.3) * 100 >= 15 && (R.cap.fill_actual || R.cap.fill || 0.3) * 100 <= 45,
            val: f2((R.cap.fill_actual || R.cap.fill || 0) * 100, 1) + '%', req: '15–45% target' },
        { label: 'Utilisation', ok: (R.eff?.cap_util || 0) >= 70 && (R.eff?.cap_util || 0) <= 100,
            val: f2(R.eff?.cap_util || 0, 0) + '%', req: '70–100% target' },
        { label: 'Shaft Defl.', ok: R.deflection_ok, val: f2((R.deflection || 0) * 1000, 2) + ' mm', req: '≤' + f2((R.defl_limit || 0.01) * 1000, 2) + ' mm' },
        { label: 'Motor', ok: R.pwr.motor >= R.pwr.motor_rated, val: R.pwr.motor + ' kW', req: f2(R.pwr.motor_rated || 0, 1) + ' kW rated' },
        { label: 'Load Class', ok: true, val: 'Class ' + (R.mat?.cls || '—'), req: '' },
    ];
    const nFail = checks.filter(c => !c.ok).length;
    const col = nFail > 0 ? C.red : C.green;
    return (_jsxs("div", { style: ss({ background: 'rgba(16,30,48,.8)', border: `1px solid ${C.border}`, borderRadius: 10, padding: 14, marginBottom: 12 }), children: [_jsxs("div", { style: ss({ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }), children: [_jsx("span", { style: ss({ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: C.muted }), children: "\uD83C\uDFE5 Design Health" }), _jsx("span", { style: ss({ fontSize: 11, fontWeight: 700, color: col, background: 'rgba(0,0,0,.3)', padding: '3px 12px', borderRadius: 20, border: `1px solid ${col}` }), children: nFail > 0 ? `⛔ ${nFail} Critical` : '✅ Design OK' })] }), _jsx("div", { style: ss({ display: 'grid', gridTemplateColumns: 'repeat(6,1fr)', gap: 4 }), children: checks.map((c, i) => {
                    const cl = c.ok ? C.green : C.red;
                    return (_jsxs("div", { style: ss({ background: 'rgba(0,0,0,.25)', border: `1px solid ${cl}44`, borderRadius: 7, padding: '7px 9px' }), children: [_jsx("div", { style: ss({ fontSize: 9, fontWeight: 700, color: C.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 3 }), children: c.label }), _jsx("div", { style: ss({ fontSize: 12, fontWeight: 800, fontFamily: 'monospace', color: cl }), children: c.val }), _jsx("div", { style: ss({ fontSize: 8.5, color: 'rgba(93,125,153,.7)', marginTop: 2 }), children: c.req })] }, i));
                }) })] }));
}
// ── Efficiency Score card ────────────────────────────────────────
function EfficiencyCard({ eff }) {
    if (!eff)
        return null;
    const score = eff.score || 0;
    const col = score > 70 ? C.green : score > 45 ? C.amber : C.red;
    const bars = [
        { l: 'Loading Efficiency (40%)', v: Math.round((eff.eta_load || 0) * 100), c: C.blue, w: 40 },
        { l: 'Energy Efficiency (35%)', v: Math.round((eff.eta_energy || 0) * 100), c: C.green, w: 35 },
        { l: 'Incline Factor (25%)', v: Math.round((eff.eta_incline || 0) * 100), c: C.amber, w: 25 },
    ];
    return (_jsxs(Panel, { children: [_jsx(SHdr, { icon: "\uD83D\uDCCA", label: "Design Efficiency Score" }), _jsxs("div", { style: ss({ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 12 }), children: [_jsx("div", { style: ss({ width: 58, height: 58, borderRadius: '50%', border: `3px solid ${col}`, display: 'flex',
                            alignItems: 'center', justifyContent: 'center', flexShrink: 0 }), children: _jsx("span", { style: ss({ color: col, fontWeight: 800, fontSize: 20 }), children: score }) }), _jsxs("div", { children: [_jsx("p", { style: ss({ fontSize: 10, color: C.muted }), children: "CEMA-weighted score /100" }), _jsxs("p", { style: ss({ fontSize: 12, color: C.text, marginTop: 2, fontWeight: 700 }), children: ["Energy: ", _jsxs("span", { style: ss({ color: C.accent }), children: [(eff.kWh_t || 0).toFixed(3), " kWh/t"] })] }), _jsxs("p", { style: ss({ fontSize: 10, color: C.muted, marginTop: 1 }), children: ["Fill: ", (eff.fill_pct || 0).toFixed(1), "% \u00B7 Utilisation: ", (eff.cap_util || 0).toFixed(1), "%"] })] })] }), bars.map((b, i) => (_jsxs("div", { style: ss({ marginBottom: 6 }), children: [_jsxs("div", { style: ss({ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: C.muted, marginBottom: 2 }), children: [_jsx("span", { children: b.l }), _jsxs("span", { style: ss({ fontFamily: 'monospace' }), children: [b.v, "% \u00D7 ", b.w, "% = ", Math.round(b.v * b.w / 100)] })] }), _jsx("div", { style: ss({ height: 6, background: 'rgba(0,0,0,.3)', borderRadius: 3, overflow: 'hidden' }), children: _jsx("div", { style: ss({ width: b.v + '%', height: '100%', background: b.c, borderRadius: 3 }) }) })] }, i)))] }));
}
// ── Power Breakdown bar chart ────────────────────────────────────
function PowerBreakdown({ pwr }) {
    if (!pwr)
        return null;
    const data = [
        { name: 'Empty', kW: +(pwr.Pe || 0).toFixed(3) },
        { name: 'Material', kW: +(pwr.Pm || 0).toFixed(3) },
        { name: 'Incline', kW: +(pwr.Pi || 0).toFixed(3) },
    ];
    return (_jsxs("div", { style: ss({ marginTop: 14 }), children: [_jsx("div", { style: ss({ fontSize: 10, fontWeight: 800, color: C.accent, letterSpacing: '0.09em', marginBottom: 8, textTransform: 'uppercase' }), children: "Power Breakdown" }), _jsx("div", { style: ss({ height: 160 }), children: _jsx(ResponsiveContainer, { width: "100%", height: "100%", children: _jsxs(BarChart, { data: data, margin: { top: 5, right: 20, bottom: 20, left: 10 }, children: [_jsx(CartesianGrid, { strokeDasharray: "3 3", stroke: C.border }), _jsx(XAxis, { dataKey: "name", tick: { fill: C.muted, fontSize: 10 } }), _jsx(YAxis, { tick: { fill: C.muted, fontSize: 9 }, label: { value: 'kW', angle: -90, position: 'insideLeft', fill: C.muted, fontSize: 9 } }), _jsx(Tooltip, { contentStyle: { background: C.panel, border: `1px solid ${C.border}`, fontSize: 10 }, formatter: (v) => [v + ' kW', ''] }), _jsx(Bar, { dataKey: "kW", fill: C.accent, radius: [3, 3, 0, 0] })] }) }) })] }));
}
// ── Parametric Sweep ─────────────────────────────────────────────
function ParamSweep({ inp }) {
    const [swType, setSwType] = useState('speed');
    const [running, setRunning] = useState(false);
    const [swData, setSwData] = useState([]);
    const run = async () => {
        setRunning(true);
        const pts = [];
        try {
            let vals = [];
            if (swType === 'speed')
                vals = [10, 20, 30, 40, 50, 60, 80, 100, 120, 150].map(N => ({ x: N, field: 'N' }));
            else if (swType === 'diam')
                vals = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6].map(D => ({ x: Math.round(D * 1000), field: 'D', extra: { D, P: D } }));
            else
                vals = [3, 5, 8, 10, 12, 15, 18, 20, 25, 30].map(L => ({ x: L, field: 'L' }));
            for (const v of vals) {
                try {
                    const r = await api.calculate({ ...inp, ...(v.extra || { [v.field]: v.swType === 'diam' ? v.x / 1000 : v.x }) });
                    pts.push({ x: v.x, cap: +(r.cap.Qt).toFixed(1), pwr: +(r.pwr.Pt).toFixed(2) });
                }
                catch { }
            }
        }
        catch { }
        setSwData(pts);
        setRunning(false);
    };
    return (_jsxs("div", { style: ss({ marginTop: 14, paddingTop: 12, borderTop: `1px solid ${C.border}` }), children: [_jsx("div", { style: ss({ fontSize: 10, fontWeight: 800, color: C.accent, letterSpacing: '0.09em', marginBottom: 8, textTransform: 'uppercase' }), children: "\uD83D\uDCC8 Parametric Sweep" }), _jsxs("div", { style: ss({ display: 'flex', gap: 6, marginBottom: 8 }), children: [['speed', 'diam', 'length'].map(t => (_jsx("button", { onClick: () => setSwType(t), style: ss({ padding: '4px 12px', borderRadius: 4, border: 'none', cursor: 'pointer', fontSize: 10, fontWeight: 700, fontFamily: 'inherit',
                            background: swType === t ? C.accent : 'transparent', color: swType === t ? '#0b1522' : C.muted }), children: t === 'speed' ? '⚡ Speed' : t === 'diam' ? '⭕ Diam' : '↔️ Length' }, t))), _jsx("button", { onClick: run, disabled: running, style: ss({ padding: '4px 14px', borderRadius: 4, border: `1px solid ${C.green}`, background: 'rgba(31,184,110,.1)',
                            color: C.green, cursor: 'pointer', fontSize: 10, fontWeight: 700, fontFamily: 'inherit' }), children: running ? '⏳' : '▶ Run' })] }), swData.length > 0 && (_jsx("div", { style: ss({ height: 160 }), children: _jsx(ResponsiveContainer, { width: "100%", height: "100%", children: _jsxs(LineChart, { data: swData, margin: { top: 5, right: 20, bottom: 20, left: 10 }, children: [_jsx(CartesianGrid, { strokeDasharray: "3 3", stroke: C.border }), _jsx(XAxis, { dataKey: "x", tick: { fill: C.muted, fontSize: 9 }, label: { value: swType === 'speed' ? 'RPM' : swType === 'diam' ? 'Ø mm' : 'L (m)', position: 'insideBottom', offset: -10, fill: C.muted, fontSize: 9 } }), _jsx(YAxis, { tick: { fill: C.muted, fontSize: 9 } }), _jsx(Tooltip, { contentStyle: { background: C.panel, border: `1px solid ${C.border}`, fontSize: 10 } }), _jsx(Line, { type: "monotone", dataKey: "cap", stroke: C.green, dot: false, strokeWidth: 2, name: "Cap (t/h)" }), _jsx(Line, { type: "monotone", dataKey: "pwr", stroke: C.amber, dot: false, strokeWidth: 2, name: "Power (kW)" })] }) }) }))] }));
}
// ── Material Recommendations ─────────────────────────────────────
function MatRecs({ recs }) {
    if (!recs)
        return null;
    const secs = [
        { k: 'trough', icon: '□', l: 'Trough', col: '#60a5fa' },
        { k: 'flight', icon: '🔩', l: 'Flights', col: '#f97316' },
        { k: 'shaft', icon: '⚙️', l: 'Shaft', col: C.purple },
        { k: 'treatments', icon: '🔥', l: 'Treatments', col: '#fb923c' },
    ];
    return (_jsxs(Panel, { children: [_jsxs("div", { style: ss({ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, paddingBottom: 8, borderBottom: `1px solid ${C.border}` }), children: [_jsx("span", { style: ss({ fontSize: 14 }), children: "\uD83D\uDEE1\uFE0F" }), _jsx("span", { style: ss({ fontWeight: 700, fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#fb923c' }), children: "Material & Surface Recommendations" })] }), _jsx("div", { style: ss({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }), children: secs.map(s => (recs[s.k] || []).length > 0 && (_jsxs("div", { style: ss({ background: 'rgba(0,0,0,.2)', borderRadius: 7, padding: '9px 11px' }), children: [_jsxs("p", { style: ss({ fontSize: 10, fontWeight: 700, color: s.col, marginBottom: 5 }), children: [s.icon, " ", s.l] }), (recs[s.k] || []).map((r, i) => (_jsxs("p", { style: ss({ fontSize: 10, color: '#b0c8e0', marginBottom: 3, lineHeight: 1.4,
                                paddingLeft: 8, borderLeft: `2px solid ${s.col}33` }), children: ["\u2022 ", r] }, i)))] }, s.k))) }), (recs.notes || []).length > 0 && (_jsxs("div", { style: ss({ marginTop: 10, background: 'rgba(74,158,255,.06)', border: '1px solid rgba(74,158,255,.2)', borderRadius: 6, padding: '7px 10px' }), children: [_jsx("p", { style: ss({ fontSize: 9, fontWeight: 700, color: C.blue, marginBottom: 3, textTransform: 'uppercase', letterSpacing: '0.08em' }), children: "\u26A0 Design Notes" }), (recs.notes || []).map((n, i) => _jsxs("p", { style: ss({ fontSize: 10, color: '#93c5fd', marginBottom: 2 }), children: ["\u2022 ", n] }, i))] }))] }));
}
// ── Structural module ────────────────────────────────────────────
function StructuralModule({ R, inp }) {
    if (!R)
        return null;
    const mat = R.mat || {}, fill = R.cap?.fill_actual || R.cap?.fill || 0.30;
    const s = calcStructural(inp.D, inp.L, mat.rho || 1.2, inp.ang || 0, fill, mat.abr || 'Medium', inp.temp_c || 20);
    const hCount = R.hgr?.count || s.n_supports, hLoad = s.R_kN / Math.max(hCount, 1);
    const hOk = hLoad <= 10;
    const Sub = ({ t, i, ch }) => (_jsxs("div", { style: ss({ background: 'rgba(0,0,0,.15)', border: `1px solid ${C.border}`, borderRadius: 7, padding: 12 }), children: [_jsxs("div", { style: ss({ fontSize: 10, fontWeight: 800, color: C.accent, letterSpacing: '0.08em', marginBottom: 8 }), children: [i, " ", t] }), ch] }));
    return (_jsxs(Panel, { children: [_jsx(SHdr, { icon: "\uD83D\uDD29", label: "Structural Engineering Module \u2014 U-Trough Screw Conveyor", badge: _jsxs("span", { style: ss({ fontSize: 9, color: C.faint }), children: ["Basis: Plate bending (AISC) \u00B7 S355 steel (\u03C3_allow=", s.sigma_allow, " MPa)"] }) }), _jsxs("div", { style: ss({ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 10 }), children: [_jsx(Sub, { t: "Trough Plate", i: "\u25A1", ch: _jsxs(_Fragment, { children: [_jsx(RR, { label: "Load (mat+screw)", value: s.w_total, unit: "kN/m" }), _jsx(RR, { label: "Bending moment", value: s.M_max, unit: "N\u00B7m/m" }), _jsx(RR, { label: "Plate thickness", value: s.t_plate, unit: "mm", ok: true }), _jsx(RR, { label: "Span used", value: s.hanger_span, unit: "m" })] }) }), _jsx(Sub, { t: "Cover & Flange", i: "\u22A1", ch: _jsxs(_Fragment, { children: [_jsx(RR, { label: "Cover thickness", value: s.t_cover, unit: "mm" }), _jsx(RR, { label: "Cover bolt pitch", value: s.cover_bp, unit: "mm" }), _jsx(RR, { label: "Flange thickness", value: s.flange_t, unit: "mm" }), _jsx(RR, { label: "Flange width", value: s.flange_w, unit: "mm" }), _jsx(RR, { label: "Bolt size", value: s.bolt_size }), _jsx(RR, { label: "Bolts per flange", value: s.n_bolts, unit: "pcs" })] }) }), _jsx(Sub, { t: "Bolting", i: "\uD83D\uDD29", ch: _jsxs(_Fragment, { children: [_jsx(RR, { label: "Bolt capacity", value: s.bolt_cap, unit: "kN", ok: s.bolt_ok }), _jsx(RR, { label: "Pressure load", value: s.pressure_load, unit: "kN" }), _jsx(RR, { label: "Required bolts", value: s.n_bolts, unit: "pcs", ok: true }), _jsx(RR, { label: "Bolt spacing", value: s.bolt_pitch, unit: "mm" }), _jsx(RR, { label: "Weld size", value: s.weld_size, unit: "mm" })] }) })] }), _jsxs("div", { style: ss({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }), children: [_jsx(Sub, { t: "Hanger Loads", i: "\uD83D\uDD17", ch: _jsxs(_Fragment, { children: [_jsx(RR, { label: "Hangers", value: hCount, unit: "pcs" }), _jsx(RR, { label: "Hanger span", value: s.hanger_span, unit: "m" }), _jsx(RR, { label: "Load per hanger", value: hLoad.toFixed(1), unit: "kN", ok: hOk }), _jsx(RR, { label: "Reaction force", value: s.R_kN, unit: "kN" }), _jsx(RR, { label: "Recommended brg", value: `UC${Math.ceil(inp.D * 100 / 5) * 5 + 200}` })] }) }), _jsx(Sub, { t: "Shaft Key & System", i: "\uD83D\uDDDD\uFE0F", ch: _jsxs(_Fragment, { children: [_jsx(RR, { label: "Key width (b)", value: s.key_b, unit: "mm" }), _jsx(RR, { label: "Screw mass", value: s.screw_mass.toLocaleString(), unit: "kg" }), _jsx(RR, { label: "Trough mass (est)", value: s.trough_mass.toLocaleString(), unit: "kg" }), _jsx(RR, { label: "End support reac.", value: s.end_react, unit: "kN" })] }) })] }), _jsx("div", { style: ss({ fontSize: 9, color: C.muted, fontWeight: 700, letterSpacing: '0.07em', marginBottom: 6 }), children: "HANGER LOAD DISTRIBUTION" }), _jsx("div", { style: ss({ display: 'flex', gap: 4 }), children: Array.from({ length: hCount }, (_, i) => (_jsxs("div", { style: ss({ flex: 1, textAlign: 'center' }), children: [_jsx("div", { style: ss({ fontSize: 8, color: C.muted, marginBottom: 2 }), children: hLoad.toFixed(1) }), _jsx("div", { style: ss({ height: 16, background: hOk ? C.teal : C.amber, borderRadius: 2 }) }), _jsxs("div", { style: ss({ fontSize: 8, color: C.faint, marginTop: 2 }), children: ["H", i + 1] })] }, i))) }), _jsx("div", { style: ss({ fontSize: 9, color: C.faint, marginTop: 4 }), children: "Load in kN per hanger \u00B7 Green \u226410, Amber \u226420, Red >20" })] }));
}
function AxialProfiles({ R, inp }) {
    const [tab, setTab] = useState('Throughput');
    const [hov, setHov] = useState(null);
    const { data: profile, isLoading } = useQuery({
        queryKey: ['axial-profile', inp],
        queryFn: () => api.getAxialProfile(inp, 60),
        enabled: !!R, staleTime: 0, placeholderData: (p) => p,
    });
    if (!R)
        return null;
    const tabs = {
        Throughput: { key: 'Qt', color: C.green, unit: 't/h', req: inp.cap },
        Fill: { key: 'fill_pct', color: C.blue, unit: '%' },
        Power: { key: 'pwr_density', color: C.amber, unit: 'kW/m' },
        Torque: { key: 'torque_pm', color: C.purple, unit: 'Nm/m' },
        Cumulative: { key: 'torque_cumul', color: C.accent, unit: 'Nm' },
        Wear: { key: 'wear_rate', color: C.red, unit: 'mm/h' },
        Axial: { key: 'axial_velocity', color: C.teal, unit: 'm/s' },
    };
    const tc = tabs[tab];
    const data = Array.isArray(profile) ? profile : (profile?.segments || []);
    const hangers = data.filter((s) => s.isHanger);
    const insights = [];
    if (data.length) {
        const choke = data.filter((s) => s.status === 'choke').length;
        if (choke / data.length > 0.5)
            insights.push(`${Math.round(choke / data.length * 100)}% of length is choking — throughput limited by inlet pitch (${Math.round(inp.P * 1000)} mm). Increase inlet pitch or reduce required capacity.`);
        const mxW = Math.max(...data.map((s) => s.wear_rate));
        if (mxW > 0.01)
            insights.push(`High inlet wear (${mxW.toFixed(4)} mm/h). Consider AR-lined inlet section or reduced inlet pitch.`);
    }
    return (_jsxs(Panel, { children: [_jsx(SHdr, { icon: "\uD83D\uDCC8", label: "Axial Profiles" }), _jsx("div", { style: ss({ display: 'flex', gap: 4, marginBottom: 10 }), children: Object.keys(tabs).map(t => (_jsx("button", { onClick: () => setTab(t), style: ss({ padding: '4px 10px', borderRadius: 4, border: 'none', cursor: 'pointer', fontSize: 10, fontWeight: 700, fontFamily: 'inherit',
                        background: tab === t ? tabs[t].color : 'transparent',
                        color: tab === t ? '#0b1522' : C.muted,
                        outline: tab === t ? `1px solid ${tabs[t].color}` : 'none' }), children: t }, t))) }), isLoading && _jsx("div", { style: ss({ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.muted, fontSize: 11 }), children: "\u23F3 Building profile\u2026" }), !isLoading && data.length > 0 && (_jsx("div", { style: ss({ height: 220 }), children: _jsx(ResponsiveContainer, { width: "100%", height: "100%", children: _jsxs(LineChart, { data: data, onMouseMove: (e) => e.activePayload && setHov(e.activePayload[0]?.payload), onMouseLeave: () => setHov(null), margin: { top: 5, right: 40, bottom: 20, left: 10 }, children: [_jsx(CartesianGrid, { strokeDasharray: "3 3", stroke: C.border }), _jsx(XAxis, { dataKey: "x", label: { value: 'Length (m)', position: 'insideBottom', offset: -10, fill: C.muted, fontSize: 10 }, tick: { fill: C.muted, fontSize: 9 } }), _jsx(YAxis, { tick: { fill: C.muted, fontSize: 9 } }), _jsx(Tooltip, { contentStyle: { background: C.panel, border: `1px solid ${C.border}`, borderRadius: 6, fontSize: 10 }, labelFormatter: (v) => `x = ${v} m` }), tc.req !== undefined && _jsx(ReferenceLine, { y: tc.req, stroke: C.amber, strokeDasharray: "6 3", label: { value: `Required ${tc.req} t/h`, fill: C.amber, fontSize: 9 } }), hangers.map((h, i) => (_jsx(ReferenceLine, { x: h.x, stroke: C.blue, strokeDasharray: "3 3", strokeOpacity: 0.4 }, i))), _jsx(Line, { type: "monotone", dataKey: tc.key, stroke: tc.color, dot: false, strokeWidth: 2 })] }) }) })), _jsxs("div", { style: ss({ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 6, fontSize: 9, color: C.muted }), children: [_jsxs("span", { children: [_jsx("span", { style: ss({ color: C.blue }), children: "H\u2014 " }), "Hanger bearing"] }), _jsxs("span", { children: [_jsx("span", { style: ss({ color: C.red }), children: "\u2014 " }), "Flooding"] }), _jsxs("span", { children: [_jsx("span", { style: ss({ color: C.amber }), children: "\u2014 " }), "Choke (<req.)"] }), _jsxs("span", { children: [_jsx("span", { style: ss({ color: C.faint }), children: "\u2014 " }), "Starved (<12%)"] })] }), hov && (_jsxs("div", { style: ss({ marginTop: 8, background: '#081321', borderRadius: 6, padding: '6px 12px', fontSize: 10, display: 'flex', gap: 16, flexWrap: 'wrap' }), children: [_jsxs("span", { style: ss({ color: C.accent }), children: ["x = ", hov.x, " m"] }), _jsxs("span", { style: ss({ color: C.green }), children: ["Throughput: ", hov.Qt, " t/h"] }), _jsxs("span", { style: ss({ color: C.blue }), children: ["Fill: ", hov.fill_pct, "%"] }), _jsxs("span", { style: ss({ color: C.amber }), children: ["Pitch: ", (hov.localPitch * 1000).toFixed(0), " mm"] }), hov.status !== 'ok' && _jsxs("span", { style: ss({ color: C.red }), children: ["\u25B2 ", hov.status.toUpperCase(), " \u2014 capacity limited"] })] })), insights.map((s, i) => (_jsxs("div", { style: ss({ marginTop: 6, background: 'rgba(232,160,0,.06)', border: `1px solid ${C.amber}44`, borderRadius: 5, padding: '5px 10px', fontSize: 10, color: C.amber }), children: ["\u26A0 ", s] }, i))), _jsxs("div", { style: ss({ marginTop: 14, paddingTop: 12, borderTop: `1px solid ${C.border}` }), children: [_jsxs("div", { style: ss({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }), children: [_jsx("span", { style: ss({ fontSize: 10, fontWeight: 800, color: C.accent, letterSpacing: '0.08em' }), children: "\uD83D\uDCD0 SHAFT DEFLECTION PROFILE" }), _jsx("span", { style: ss({ fontSize: 9, color: (R.tor?.pipe ? C.purple : C.blue), fontFamily: 'monospace' }), children: R.tor?.pipe
                                    ? `Pipe Ø${Math.round(R.tor?.eff_od_mm || 70)}×${Math.round(R.tor?.eff_id_mm || 54)} mm (hollow)`
                                    : `Bar Ø${Math.round(R.tor?.eff_od_mm || R.tor?.od || 70)} mm (solid)` })] }), data.length > 0 && (() => {
                        const L_conv = inp.L || 10;
                        // R is already activeR — passed by caller
                        const span = R.hgr?.span || L_conv;
                        const mxD = (R.deflection || 0) * 1000;
                        const limitMm = (R.defl_limit || 0.01) * 1000;
                        const deflOk = R.deflection_ok;
                        // Mirror HTML prototype exactly: spans×20+1 points
                        // Each span is one arch from zero (support) to peak (mid-span) to zero (next support)
                        // hanger_count hangers = hanger_count+1 spans
                        const numSpans = Math.max(1, Math.round(L_conv / span));
                        const dp = Array.from({ length: numSpans * 20 + 1 }, (_, i) => {
                            const xFrac = i / (numSpans * 20);
                            const xInSpan = (xFrac * numSpans) % 1; // 0→1 within each span
                            const d = mxD * (Math.sin(Math.PI * xInSpan) ** 2); // sin² gives smooth arch
                            return { x: +(xFrac * L_conv).toFixed(3), d: +d.toFixed(4) };
                        });
                        // Y-axis must include the limit line — use max of deflection and limit
                        const yMax = Math.max(mxD, limitMm) * 1.15;
                        return (_jsx("div", { style: ss({ height: 140 }), children: _jsx(ResponsiveContainer, { width: "100%", height: "100%", children: _jsxs(LineChart, { data: dp, margin: { top: 5, right: 60, bottom: 20, left: 10 }, children: [_jsx(CartesianGrid, { strokeDasharray: "3 3", stroke: C.border }), _jsx(XAxis, { dataKey: "x", tick: { fill: C.muted, fontSize: 9 }, label: { value: 'Length (m)', position: 'insideBottom', offset: -10, fill: C.muted, fontSize: 9 } }), _jsx(YAxis, { tick: { fill: C.muted, fontSize: 9 }, domain: [0, yMax], label: { value: 'δ (mm)', angle: -90, position: 'insideLeft', fill: C.muted, fontSize: 9 } }), Array.from({ length: numSpans - 1 }, (_, i) => (_jsx(ReferenceLine, { x: +((i + 1) * span).toFixed(2), stroke: C.purple, strokeDasharray: "3 2", strokeOpacity: 0.7, label: { value: 'H', fill: C.purple, fontSize: 8, position: 'top' } }, i))), _jsx(ReferenceLine, { y: limitMm, stroke: C.red, strokeDasharray: "6 3", strokeWidth: 1.5, label: { value: `Limit ${limitMm.toFixed(2)} mm`, fill: C.red, fontSize: 8, position: 'insideTopRight' } }), _jsx(ReferenceLine, { y: mxD, stroke: deflOk ? C.blue : C.red, strokeDasharray: "2 4", strokeOpacity: 0.5, label: { value: `δ=${mxD.toFixed(3)} mm ${deflOk ? '✓' : '✗'}`, fill: deflOk ? C.blue : C.red, fontSize: 8, position: 'insideBottomRight' } }), _jsx(Line, { type: "monotone", dataKey: "d", stroke: R.tor?.pipe ? C.purple : C.blue, dot: false, strokeWidth: 2 })] }) }) }));
                    })(), _jsxs("div", { style: ss({ display: 'flex', alignItems: 'center', gap: 10, marginTop: 6 }), children: [_jsx("span", { style: ss({ fontSize: 9, color: C.muted, whiteSpace: 'nowrap' }), children: "Critical Speed" }), _jsx("div", { style: ss({ flex: 1, height: 10, background: C.border, borderRadius: 5, position: 'relative' }), children: _jsx("div", { style: ss({ position: 'absolute', left: 0, width: Math.min(100, (R.nc_ratio || 0) * 100) + '%', height: '100%',
                                        background: (R.nc_ratio || 0) < 0.7 ? C.green : C.amber, borderRadius: 5 }) }) }), _jsxs("span", { style: ss({ fontSize: 9, color: C.faint, whiteSpace: 'nowrap' }), children: [((R.nc_ratio || 0) * 100).toFixed(0), "% of Nc"] }), _jsxs("span", { style: ss({ fontSize: 9, color: C.muted, whiteSpace: 'nowrap' }), children: ["Nc=", Math.round(R.nc || 0), " RPM"] })] })] })] }));
}
// ── Standards Comparison table ───────────────────────────────────
function StdCompTable({ multiR, activeStd }) {
    if (!multiR)
        return null;
    const f2 = (v, d = 2) => v != null ? v.toFixed(d) : '—';
    const fN = (v) => v != null ? Math.round(v).toLocaleString() : '—';
    const rows = [
        ['Capacity (t/h)', r => f2(r.cap.Qt, 2), r => r.cap.ok],
        ['Power (kW)', r => f2(r.pwr.Pt, 3), () => null],
        ['Motor (kW)', r => String(r.pwr.motor), () => null],
        ['Running Torque (Nm)', r => Math.round(r.tor.Tr).toString(), () => null],
        ['Shaft OD (mm)', r => (r.tor.od || r.shaft_auto?.sel_mm || 0).toFixed(0) + ' std', r => r.tor.shOk],
        ['Shear Stress (MPa)', r => f2(r.tor.tau, 2), r => r.tor.shOk],
        ['Safety Factor', r => ((r.inp?.sallow || 40) / Math.max(r.tor.tau, 0.001)).toFixed(2) + ' ×', r => { const sf = (r.inp?.sallow || 40) / Math.max(r.tor.tau, 0.001); return sf >= 1.5; }],
        ['Bearing L10 (h)', r => fN(r.brg_r?.L10), r => r.brg_r?.ok],
        ['Shaft Defl. (mm)', r => f2((r.deflection || 0) * 1000, 3) + ' / ' + f2((r.defl_limit || 0.01) * 1000, 3) + ' lim', r => r.deflection_ok],
        ['Hangers', r => (r.hgr?.count || 0) + ' @ ' + f2(r.hgr?.span, 1) + 'm', () => null],
        ['kWh/t', r => f2(r.eff?.kWh_t, 3), () => null],
        ['Design Score', r => (r.eff?.score || 0) + '/100', r => (r.eff?.score || 0) > 70],
        ['Est. Cost (USD)', r => '$' + fN(r.cost?.total), () => null],
    ];
    const stds = ['CEMA', 'DIN', 'Custom'];
    return (_jsxs(Panel, { children: [_jsx(SHdr, { icon: "\uD83D\uDCCA", label: "Standards Comparison" }), _jsx("div", { style: ss({ overflowX: 'auto' }), children: _jsxs("table", { style: ss({ width: '100%', borderCollapse: 'collapse', fontSize: 11 }), children: [_jsx("thead", { children: _jsx("tr", { style: ss({ borderBottom: `1px solid ${C.border}` }), children: ['Metric', 'CEMA', 'DIN', 'Custom'].map(h => (_jsx("th", { style: ss({ padding: '4px 10px', textAlign: 'left', color: C.muted, fontWeight: 700, fontSize: 10, textTransform: 'uppercase' }), children: h }, h))) }) }), _jsx("tbody", { children: rows.map(([lb, fn, okFn]) => (_jsxs("tr", { style: ss({ borderBottom: '1px solid rgba(28,48,72,.4)' }), children: [_jsx("td", { style: ss({ padding: '4px 10px', color: C.muted, fontSize: 10 }), children: lb }), stds.map(s => {
                                        const r = multiR[s];
                                        const v = r ? fn(r) : '—';
                                        const ok = r && okFn ? okFn(r) : null;
                                        const col = ok === true ? C.green : ok === false ? C.red : s === activeStd ? C.accent : C.text;
                                        return _jsx("td", { style: ss({ padding: '4px 10px', fontFamily: 'monospace', fontWeight: 700, fontSize: 11, color: col }), children: v }, s);
                                    })] }, lb))) })] }) })] }));
}
function AutoOptModal({ inp, onApply, onClose }) {
    const { data: bearings } = useBearings();
    const { data: gearboxes } = useGearboxes();
    const PHASES = ['geometry', 'pitch', 'drive'];
    const [phase, setPhase] = useState('geometry');
    const [goals, setGoals] = useState(['efficiency']);
    const [running, setRunning] = useState(false);
    const [phaseResults, setPhaseResults] = useState({});
    const [applied, setApplied] = useState({});
    const [done, setDone] = useState(false);
    const effectiveInp = useMemo(() => ({
        ...inp, ...(applied.geometry || {}), ...(applied.pitch || {}), ...(applied.drive || {})
    }), [inp, applied]);
    const scoreCandidate = (r) => {
        if (!r?.eff)
            return 0;
        const s_eff = r.eff.score || 0;
        const s_energy = Math.max(0, 100 - (r.eff.kWh_t || 5) * 20);
        const s_cost = Math.max(0, 100 - (r.cost?.total || 99999) / 500);
        const s_life = Math.min(100, (r.wear?.life_h || 0) / 500);
        const w = { efficiency: 0.35, energy: 0.35, cost: 0.2, life: 0.1 };
        const wTotal = goals.reduce((s, g) => s + (w[g] || 0.25), 0) || 1;
        return goals.reduce((s, g) => {
            const v = g === 'efficiency' ? s_eff : g === 'energy' ? s_energy : g === 'cost' ? s_cost : s_life;
            return s + (w[g] || 0.25) * v;
        }, 0) / wTotal;
    };
    const runGeometry = async () => {
        setRunning(true);
        const base = { ...effectiveInp };
        const Ds = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60];
        const Ns = [20, 30, 40, 50, 60, 80, 100, 120];
        const PRs = [0.75, 0.875, 1.0, 1.125, 1.25];
        const candidates = [], trials = [];
        for (const D of Ds) {
            for (const N of Ns) {
                for (const pr of PRs) {
                    const P = Math.min(D * pr, 1.5);
                    try {
                        const r = await api.calculate({ ...base, D, N, P, use_multipitch: false, lam_factor: 1.0 });
                        const sc = scoreCandidate(r);
                        const c = { D, N, P, pr, score: sc, kWh: r.eff?.kWh_t || 9, cost: r.cost?.total || 0,
                            life: r.wear?.life_h || 0, defl_mm: (r.deflection || 0) * 1000,
                            L10: r.brg_r?.L10 || 0, motor: r.pwr?.motor || 0, r };
                        trials.push(c);
                        if (r.cap?.ok && r.tor?.shOk && r.deflection_ok && r.gbx_r?.tOk && r.brg_r?.ok)
                            candidates.push(c);
                    }
                    catch { }
                }
            }
        }
        const sorted = candidates.sort((a, b) => b.score - a.score);
        const partial = candidates.length === 0 && trials.length ?
            [...trials].sort((a, b) => b.score - a.score)[0] : null;
        setPhaseResults(prev => ({ ...prev, geometry: {
                top: sorted.slice(0, 6), partial, total_swept: trials.length, feasible: candidates.length
            } }));
        setRunning(false);
    };
    const runPitch = async () => {
        setRunning(true);
        const base = { ...effectiveInp };
        const inletRatios = [0.5, 0.6, 0.667, 0.75, 0.8, 0.875];
        const outletRatios = [0.667, 0.75, 0.875, 1.0];
        const pctPairs = [[10, 10], [15, 15], [20, 20], [10, 15], [15, 10]];
        const candidates = [], trials = [];
        for (const ir of inletRatios) {
            for (const or of outletRatios) {
                for (const [pi, po] of pctPairs) {
                    const P_body = base.P || base.D;
                    const P_in = P_body * ir, P_out = P_body * or;
                    try {
                        const r = await api.calculate({ ...base, P_in, P_out, pct_in: pi, pct_out: po,
                            use_multipitch: true, lam_factor: 1.0 });
                        const sc = scoreCandidate(r);
                        const c = { P_in, P_out, pct_in: pi, pct_out: po, ir, or, score: sc,
                            kWh: r.eff?.kWh_t || 9, cost: r.cost?.total || 0, life: r.wear?.life_h || 0,
                            defl_mm: (r.deflection || 0) * 1000, L10: r.brg_r?.L10 || 0, motor: r.pwr?.motor || 0, r };
                        trials.push(c);
                        if (r.cap?.ok && r.tor?.shOk && r.deflection_ok && r.gbx_r?.tOk && r.brg_r?.ok)
                            candidates.push(c);
                    }
                    catch { }
                }
            }
        }
        const sorted = candidates.sort((a, b) => b.score - a.score);
        const partial = candidates.length === 0 && trials.length ?
            [...trials].sort((a, b) => b.score - a.score)[0] : null;
        setPhaseResults(prev => ({ ...prev, pitch: {
                top: sorted.slice(0, 5), partial, total_swept: trials.length,
                feasible: candidates.length, skip_ok: true
            } }));
        setRunning(false);
    };
    const runDrive = async () => {
        setRunning(true);
        const base = { ...effectiveInp };
        const gbxList = (gearboxes || []).map((g) => g.model);
        const brgList = (bearings || []).map((b) => b.name);
        const candidates = [], trials = [];
        for (const gbx of gbxList.slice(0, 12)) {
            for (const brg of brgList.slice(0, 10)) {
                for (const hangers of [0, 1, 2, 3, 4, 6]) {
                    try {
                        const r = await api.calculate({ ...base, gbx, brg, hangers: hangers || 0, lam_factor: 1.0 });
                        const sc = scoreCandidate(r);
                        const c = { gbx, brg, hangers, score: sc, kWh: r.eff?.kWh_t || 9, cost: r.cost?.total || 0,
                            life: r.wear?.life_h || 0, defl_mm: (r.deflection || 0) * 1000,
                            L10: r.brg_r?.L10 || 0, motor: r.pwr?.motor || 0, r };
                        trials.push(c);
                        if (r.cap?.ok && r.tor?.shOk && r.deflection_ok && r.gbx_r?.tOk && r.brg_r?.ok)
                            candidates.push(c);
                    }
                    catch { }
                }
            }
        }
        const sorted = candidates.sort((a, b) => b.score - a.score);
        const partial = candidates.length === 0 && trials.length ?
            [...trials].sort((a, b) => b.score - a.score)[0] : null;
        setPhaseResults(prev => ({ ...prev, drive: {
                top: sorted.slice(0, 5), partial, total_swept: trials.length, feasible: candidates.length
            } }));
        setRunning(false);
    };
    const runPhase = () => {
        if (phase === 'geometry')
            runGeometry();
        else if (phase === 'pitch')
            runPitch();
        else
            runDrive();
    };
    const applyCandidate = (c, ph) => {
        const cfg = ph === 'geometry'
            ? { D: c.D, N: c.N, P: c.P }
            : ph === 'pitch'
                ? { P_in: c.P_in, P_out: c.P_out, pct_in: c.pct_in, pct_out: c.pct_out, use_multipitch: true }
                : { gbx: c.gbx, brg: c.brg, hangers: c.hangers };
        setApplied(prev => ({ ...prev, [ph]: cfg }));
        onApply(cfg);
    };
    const phaseCfg = {
        geometry: { icon: '⭕', label: 'Phase 1', title: 'Geometry', sub: 'D × N × Pitch' },
        pitch: { icon: '🌀', label: 'Phase 2', title: 'Pitch Pattern', sub: 'Inlet/Outlet (optional)' },
        drive: { icon: '⚙️', label: 'Phase 3', title: 'Drive & Hangers', sub: 'GBX × BRG × Hangers' },
    };
    const goalCfg = {
        efficiency: { icon: '📈', l: 'Efficiency' }, energy: { icon: '🔋', l: 'Min Energy' },
        cost: { icon: '💰', l: 'Min Cost' }, life: { icon: '⏱️', l: 'Max Life' },
    };
    const renderCand = (c, i, ph) => {
        const isApplied = !!applied[ph];
        const lab = ph === 'geometry'
            ? `Ø${(c.D * 1000).toFixed(0)}mm · ${c.N} RPM · P=${(c.P * 1000).toFixed(0)}mm`
            : ph === 'pitch'
                ? `Inlet ${(c.ir * 100).toFixed(0)}%D · Outlet ${(c.or * 100).toFixed(0)}%D · Zones ${c.pct_in}%/${c.pct_out}%`
                : `${c.gbx} · ${c.brg} · ${c.hangers} hangers`;
        return (_jsxs("div", { style: ss({ border: `1px solid ${i === 0 ? 'rgba(45,212,191,.25)' : C.border}`,
                background: i === 0 ? 'rgba(45,212,191,.05)' : 'rgba(0,0,0,.15)',
                borderRadius: 8, padding: '10px 12px', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }), children: [_jsxs("div", { style: ss({ flex: 1, minWidth: 0 }), children: [_jsx("div", { style: ss({ fontSize: 10, fontWeight: 700, color: i === 0 ? C.teal : C.text, fontFamily: 'monospace', marginBottom: 4 }), children: lab }), _jsx("div", { style: ss({ display: 'flex', gap: 10, flexWrap: 'wrap', fontSize: 9, color: C.muted }), children: [['Score', (c.score * 100 / 100).toFixed(1), C.accent],
                                ['kWh/t', c.kWh?.toFixed(3), C.green],
                                ['Motor', (c.motor || '—') + ' kW', C.purple],
                                ['Defl', (c.defl_mm || 0).toFixed(2) + 'mm', (c.defl_mm || 0) < 2 ? C.green : C.amber],
                                ['L10', ((c.L10 || 0) / 1000).toFixed(0) + 'kh', (c.L10 || 0) >= 20000 ? C.green : C.amber],
                            ].map(([l, v, col]) => _jsxs("span", { children: [l, ": ", _jsx("strong", { style: ss({ color: col }), children: v })] }, l)) })] }), _jsx("button", { onClick: () => applyCandidate(c, ph), style: ss({ padding: '5px 14px', borderRadius: 6, border: `1px solid ${C.teal}44`,
                        background: 'transparent', color: C.teal, cursor: 'pointer', fontSize: 10, fontWeight: 700, flexShrink: 0 }), children: "Apply" })] }, i));
    };
    const renderPhaseResult = (ph) => {
        const pr = phaseResults[ph];
        if (!pr)
            return null;
        return (_jsxs("div", { children: [_jsxs("div", { style: ss({ fontSize: 10, fontWeight: 700, color: pr.feasible > 0 ? C.green : C.amber, marginBottom: 8 }), children: [pr.feasible > 0
                            ? `✓ ${pr.feasible}/${pr.total_swept} feasible designs found`
                            : `⚠ 0/${pr.total_swept} — no fully feasible design`, pr.feasible === 0 && pr.skip_ok && _jsx("span", { style: ss({ fontSize: 9, color: C.muted, marginLeft: 8 }), children: "Phase 2 is optional \u2014 skip or adjust pitch manually" })] }), pr.feasible === 0 && pr.partial && (_jsxs("div", { style: ss({ background: 'rgba(217,142,0,.08)', border: `1px solid rgba(217,142,0,.3)`, borderRadius: 8, padding: '10px 12px', marginBottom: 10 }), children: [_jsx("p", { style: ss({ fontSize: 10, fontWeight: 700, color: C.amber, marginBottom: 6 }), children: "\uD83D\uDD0D Best Partial \u2014 apply as starting point, refine manually:" }), renderCand(pr.partial, 0, ph)] })), pr.top?.map((c, i) => renderCand(c, i, ph))] }));
    };
    return (_jsx("div", { style: ss({ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.85)', zIndex: 3000,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'opacity .3s', opacity: done ? 0 : 1 }), children: _jsxs("div", { style: ss({ background: C.panel, border: '1px solid #2a4a72', borderRadius: 14,
                width: 780, maxHeight: '92vh', overflowY: 'auto',
                boxShadow: '0 24px 80px rgba(0,0,0,.8)', padding: 24, display: 'flex', flexDirection: 'column', gap: 0 }), children: [_jsxs("div", { style: ss({ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
                        marginBottom: 16, paddingBottom: 12, borderBottom: `1px solid ${C.border}` }), children: [_jsxs("div", { children: [_jsx("h2", { style: ss({ fontWeight: 800, color: C.text, fontSize: 17 }), children: "\u2728 Sequential Auto-Optimiser" }), _jsx("p", { style: ss({ fontSize: 10, color: C.muted, marginTop: 3 }), children: "Three phases \u2014 run each, apply preferred result, continue. Changes update live design immediately." })] }), _jsx("button", { onClick: onClose, style: ss({ color: C.muted, fontSize: 20, background: 'none', border: 'none', cursor: 'pointer' }), children: "\u2715" })] }), _jsxs("div", { style: ss({ marginBottom: 14 }), children: [_jsx("div", { style: ss({ fontSize: 9, color: C.muted, fontWeight: 700, letterSpacing: '0.08em', marginBottom: 6 }), children: "OPTIMISATION GOALS (multi-select)" }), _jsx("div", { style: ss({ display: 'flex', gap: 6, flexWrap: 'wrap' }), children: Object.entries(goalCfg).map(([k, g]) => (_jsxs("button", { onClick: () => setGoals(prev => prev.includes(k) ? prev.filter(x => x !== k) : [...prev, k]), style: ss({ padding: '4px 12px', borderRadius: 20, border: `1px solid ${goals.includes(k) ? C.accent : C.border}`,
                                    background: goals.includes(k) ? 'rgba(232,160,0,.12)' : 'transparent',
                                    color: goals.includes(k) ? C.accent : C.muted, cursor: 'pointer', fontSize: 10, fontWeight: 700 }), children: [g.icon, " ", g.l] }, k))) })] }), _jsx("div", { style: ss({ display: 'flex', gap: 0, marginBottom: 16, borderBottom: `2px solid ${C.border}` }), children: PHASES.map(ph => {
                        const pc = phaseCfg[ph];
                        const ran = !!phaseResults[ph];
                        const app = !!applied[ph];
                        return (_jsxs("button", { onClick: () => setPhase(ph), style: ss({ padding: '8px 18px', border: 'none', cursor: 'pointer', background: 'transparent',
                                fontFamily: 'inherit', textAlign: 'left',
                                borderBottom: phase === ph ? `2px solid ${C.accent}` : '2px solid transparent', marginBottom: -2 }), children: [_jsxs("div", { style: ss({ fontSize: 10, fontWeight: 700, color: phase === ph ? C.accent : C.muted }), children: [pc.icon, " ", pc.label, ": ", pc.title, ran && _jsx("span", { style: ss({ marginLeft: 6, fontSize: 8, padding: '1px 6px', borderRadius: 4,
                                                background: 'rgba(31,184,110,.15)', color: C.green }), children: "\u2713" }), app && _jsx("span", { style: ss({ marginLeft: 4, fontSize: 8, padding: '1px 6px', borderRadius: 4,
                                                background: 'rgba(45,212,191,.15)', color: C.teal }), children: "Applied" })] }), _jsx("div", { style: ss({ fontSize: 9, color: C.faint }), children: pc.sub })] }, ph));
                    }) }), _jsxs("div", { style: ss({ background: '#081321', borderRadius: 6, padding: '7px 12px', marginBottom: 12, fontSize: 9, color: C.muted, display: 'flex', gap: 16, flexWrap: 'wrap' }), children: [_jsx("span", { style: ss({ color: C.faint }), children: "Effective design:" }), _jsxs("span", { children: ["D=", ((effectiveInp.D || 0) * 1000).toFixed(0), "mm"] }), _jsxs("span", { children: ["N=", effectiveInp.N || 0, "RPM"] }), _jsxs("span", { children: ["P=", ((effectiveInp.P || 0) * 1000).toFixed(0), "mm"] }), _jsxs("span", { children: ["L=", effectiveInp.L || 0, "m"] }), _jsx("span", { style: ss({ color: C.accent }), children: effectiveInp.mat })] }), _jsxs("div", { style: ss({ flex: 1 }), children: [renderPhaseResult(phase), !phaseResults[phase] && (_jsxs("div", { style: ss({ textAlign: 'center', color: C.faint, fontSize: 11, padding: 24 }), children: [phase === 'geometry' && 'Run Phase 1 to sweep D × N × Pitch combinations', phase === 'pitch' && 'Run Phase 1 first, then Phase 2 to optimise inlet/outlet pitch (optional)', phase === 'drive' && 'Run Phase 3 to sweep gearbox and bearing combinations'] }))] }), _jsxs("div", { style: ss({ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        marginTop: 16, paddingTop: 12, borderTop: `1px solid ${C.border}` }), children: [_jsx("div", { style: ss({ display: 'flex', gap: 6 }), children: running && _jsxs("span", { style: ss({ fontSize: 10, color: C.blue }), children: ["\u23F3 Sweeping ", phaseCfg[phase].title, "\u2026"] }) }), _jsxs("div", { style: ss({ display: 'flex', gap: 8 }), children: [_jsx("button", { onClick: onClose, style: ss({ padding: '7px 18px', borderRadius: 4, border: `1px solid ${C.border}`, background: 'transparent', color: C.muted, cursor: 'pointer', fontSize: 12 }), children: "Close" }), _jsx("button", { onClick: runPhase, disabled: running, style: ss({ padding: '7px 22px', borderRadius: 4, border: `1px solid ${C.teal}`,
                                        background: running ? 'transparent' : 'rgba(45,212,191,.12)', color: running ? C.faint : C.teal,
                                        cursor: running ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 700 }), children: running ? '⏳ Running…' : `▶ Run ${phaseCfg[phase].label}` })] })] })] }) }));
}
// ═════════════════════════════════════════════════════════════════
// MAIN CalcPage
// ═════════════════════════════════════════════════════════════════
export default function CalcPage({ _meta }) {
    const { inp, setInp } = useCalcStore();
    const { data: R, isLoading, isError, error, refetch } = useCalculate();
    const { data: mats } = useMaterials();
    const { data: bearings } = useBearings();
    const { data: gearboxes } = useGearboxes();
    // Sync default material to first DB entry if current name not found
    useEffect(() => {
        if (mats && mats.length > 0) {
            const names = mats.map((m) => m.name);
            if (!names.includes(inp.mat)) {
                setInp({ mat: names[0] });
            }
        }
    }, [mats]);
    const [activeStd, setActiveStd] = useState('CEMA');
    const [customLam, setCustomLam] = useState(1.05);
    const [showOpt, setShowOpt] = useState(false);
    // Multi-standard query
    const { data: multiR } = useQuery({
        queryKey: ['calculate-multi', inp, customLam],
        queryFn: () => api.calculateMulti({ ...inp, lam_factor: customLam }),
        enabled: !!R, staleTime: 0, placeholderData: (p) => p,
    });
    const activeR = multiR ? multiR[activeStd] : R;
    // Material lambda for display
    const matLam = useMemo(() => {
        const m = (mats || []).find(x => x.name === inp.mat);
        if (!m)
            return 1.0;
        const pszMap = { A200: 0.075, A100: 0.15, A40: 0.42, B6: 6, 'C1/2': 12, D3: 75, D7: 180 };
        const psz = pszMap[m.particle_class || 'B6'] || 6;
        const lamBase = psz < 0.5 ? 1.8 : psz < 5 ? 1.4 : 1.0;
        return Math.max(0.4, Math.min((m.lambda_ref || 1.0) * 0.6 + lamBase * 0.4, 3.5));
    }, [mats, inp.mat]);
    const matMeta = useMemo(() => {
        const m = (mats || []).find(x => x.name === inp.mat);
        return m ? `ρ ${m.rho} t/m³ · Fill: ${(m.fill_max * 100).toFixed(0)}% · λ ${(m.lambda_ref || 1.0).toFixed(1)} · Abr: ${m.abr} · CEMA: Class ${m.cls}` : '';
    }, [mats, inp.mat]);
    const f2 = (v, d = 2) => v != null ? v.toFixed(d) : '—';
    const fN = (v) => v != null ? Math.round(v).toLocaleString() : '—';
    const shAuto = R ? R.shaft_auto : null;
    return (_jsxs("div", { style: ss({ display: 'flex', height: '100%', overflow: 'hidden' }), children: [_jsxs("div", { style: ss({ width: 270, flexShrink: 0, background: C.panel, borderRight: `1px solid ${C.border}`, overflowY: 'auto', overflowX: 'hidden', padding: '10px 12px', minHeight: 0, height: '100%', boxSizing: 'border-box' }), children: [_jsx(Divider, { label: "MATERIAL & DUTY" }), _jsxs("div", { style: ss({ marginBottom: 7 }), children: [_jsx(Lbl, { children: "Incline Factor Model" }), _jsx(Ck, { field: "contAFact", label: "Continuous exp(\u2013k\u00B7\u03B8)" }), _jsx("span", { style: ss({ fontSize: 9, color: C.faint }), children: "CEMA stepped" })] }), _jsx(SI, { field: "type", label: "Conveyor Type", options: [
                            { value: 'screw', label: '🔩 Screw Conveyor (U-trough)' },
                            { value: 'pipe', label: '⭕ Pipe Conveyor' },
                        ] }), _jsxs("div", { style: ss({ marginBottom: 7 }), children: [_jsx(Lbl, { children: "Material" }), _jsxs("select", { value: inp.mat, onChange: e => setInp({ mat: e.target.value }), style: ss({ width: '100%', background: '#081321', border: `1px solid ${C.border}`, borderRadius: 4,
                                    padding: '5px 8px', color: C.text, fontSize: 11, fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box' }), children: [(mats || []).length === 0 && _jsx("option", { value: inp.mat, children: inp.mat }), (mats || []).map(m => _jsx("option", { value: m.name, children: m.name }, m.name))] }), matMeta && _jsx("div", { style: ss({ fontSize: 9, color: C.faint, marginTop: 3 }), children: matMeta })] }), _jsx(NI, { field: "cap", label: "Capacity", unit: "t/h", min: 0.1, max: 5000, step: 1 }), _jsx(NI, { field: "L", label: "Length", unit: "m", min: 0.5, max: 100, step: 0.5 }), _jsx(NI, { field: "ang", label: "Angle", unit: "\u00B0 (\u221220\u2192+45)", min: -20, max: 45, step: 1 }), _jsx(NI, { field: "surge", label: "Surge Factor", min: 1.0, max: 2.0, step: 0.05 }), _jsx(Divider, { label: "TROUGH GEOMETRY" }), _jsx(NI, { field: "D", label: "Trough \u00D8", unit: "m", min: 0.05, max: 1.2, step: 0.05 }), _jsx(NI, { field: "N", label: "Speed", unit: "RPM", min: 5, max: 300, step: 5 }), _jsx(NI, { field: "ft", label: "Flight Thick.", unit: "m", min: 0.002, max: 0.02, step: 0.001 }), _jsx(NI, { field: "wa", label: "Wear Allowance", unit: "m", min: 0.001, max: 0.01, step: 0.001 }), _jsx(Divider, { label: "FLIGHT PITCH" }), activeR && (_jsxs("div", { style: ss({ background: 'rgba(31,184,110,.06)', border: `1px solid ${C.green}33`, borderRadius: 5, padding: '6px 9px', marginBottom: 7, fontSize: 10 }), children: [_jsxs("div", { style: ss({ color: activeR.cap.ok ? C.green : C.red, fontWeight: 700 }), children: [activeR.cap.ok ? '✓' : '✗', " Pitch capacity ", activeR.cap.ok ? 'OK' : 'LOW'] }), _jsxs("div", { style: ss({ color: C.faint, marginTop: 2 }), children: ["Body ", f2(activeR.cap.Qt, 1), " t/h  P=", Math.round(inp.P * 1000), " mm =", Math.round(inp.P / inp.D * 100), "%D"] })] })), _jsxs("div", { style: ss({ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 7 }), children: [_jsx(Ck, { field: "use_multipitch", label: "Multi-Pitch" }), _jsx("span", { style: ss({ fontSize: 9, color: C.faint }), children: "Sections" })] }), _jsx(NI, { field: "P", label: "Body Pitch (m) [uniform]", min: 0.05, max: 2.0, step: 0.05 }), inp.use_multipitch && (_jsxs("div", { style: ss({ background: 'rgba(74,158,255,.05)', border: `1px solid ${C.blue}33`, borderRadius: 6, padding: 8, marginBottom: 7 }), children: [_jsx("div", { style: ss({ fontSize: 9, color: C.blue, fontWeight: 700, marginBottom: 6 }), children: "MULTI-PITCH ZONES" }), _jsxs("div", { style: ss({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }), children: [_jsx(NI, { field: "P_in", label: "Inlet Pitch (m)", min: 0.05, max: 2.0, step: 0.05 }), _jsx(NI, { field: "P_out", label: "Outlet Pitch (m)", min: 0.05, max: 2.0, step: 0.05 }), _jsx(NI, { field: "pct_in", label: "Inlet zone %", min: 5, max: 50, step: 5 }), _jsx(NI, { field: "pct_out", label: "Outlet zone %", min: 5, max: 50, step: 5 })] })] })), _jsx(Divider, { label: "SHAFT CONFIGURATION" }), _jsx(SI, { field: "shaft_mode", label: "Shaft Mode", options: [
                            { value: 'auto', label: 'Auto-size from torque' },
                            { value: 'manual', label: 'Manual override' },
                        ] }), inp.shaft_mode === 'auto' && shAuto && (_jsxs("div", { style: ss({ background: 'rgba(31,184,110,.06)', border: `1px solid ${C.green}33`, borderRadius: 5, padding: '6px 9px', marginBottom: 7, fontSize: 10 }), children: [_jsxs("div", { style: ss({ color: C.green, fontWeight: 700 }), children: ["Auto: \u00D8", shAuto.sel_mm, " mm \u25AE solid bar  ", _jsxs("span", { style: ss({ fontWeight: 400 }), children: ["req. ", f2(shAuto.req_mm, 1), " mm \u00B7 SF ", f2(shAuto.sf, 2)] })] }), _jsx("div", { style: ss({ fontSize: 9, color: C.faint, marginTop: 2 }), children: "\u26A1 Auto-selects nearest ISO standard size from startup torque." })] })), _jsxs("div", { style: ss({ display: 'flex', gap: 6, marginBottom: 8 }), children: [_jsx("button", { onClick: () => setInp({ shaft_mode: 'manual', shtype: 'bar', pod: shAuto?.sel_mm || Math.round(inp.D * 1000 * 0.25) }), style: ss({ flex: 1, padding: '5px 0', borderRadius: 4, border: `1px solid ${C.blue}`, background: 'rgba(74,158,255,.1)', color: C.blue, cursor: 'pointer', fontSize: 10, fontWeight: 700, fontFamily: 'inherit' }), children: "\uD83D\uDCCA Override as Bar \u2192" }), _jsx("button", { onClick: () => setInp({ shaft_mode: 'manual', shtype: 'pipe', pod: shAuto?.sel_mm || 80, pwall: 8 }), style: ss({ flex: 1, padding: '5px 0', borderRadius: 4, border: `1px solid ${C.purple}`, background: 'rgba(167,139,250,.1)', color: C.purple, cursor: 'pointer', fontSize: 10, fontWeight: 700, fontFamily: 'inherit' }), children: "\u2B55 Override as Pipe \u2192" })] }), inp.shaft_mode === 'manual' && (_jsx("div", { style: ss({ background: 'rgba(74,158,255,.05)', border: `1px solid ${C.blue}33`, borderRadius: 6, padding: 8, marginBottom: 7 }), children: _jsxs("div", { style: ss({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }), children: [_jsx(SI, { field: "shtype", label: "Type", options: [{ value: 'bar', label: 'Solid Bar' }, { value: 'pipe', label: 'Hollow Pipe' }] }), _jsx(NI, { field: "pod", label: "OD (mm)", min: 20, max: 300, step: 5 }), inp.shtype === 'pipe' && _jsx(NI, { field: "pwall", label: "Wall (mm)", min: 3, max: 30, step: 1 }), _jsx(NI, { field: "sallow", label: "\u03C4_allow MPa", min: 10, max: 120, step: 5 })] }) })), inp.shaft_mode === 'auto' && _jsx(NI, { field: "sallow", label: "Allowable Shear (MPa)", min: 10, max: 120, step: 5 }), _jsx(Divider, { label: "DRIVE & BEARINGS" }), _jsxs("div", { style: ss({ marginBottom: 7 }), children: [_jsx(Lbl, { children: "End Bearing (shaft ends)" }), _jsxs("select", { value: inp.brg, onChange: e => setInp({ brg: e.target.value }), style: ss({ width: '100%', background: '#081321', border: `1px solid ${C.border}`, borderRadius: 4, padding: '5px 8px', color: C.text, fontSize: 11, fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box' }), children: [(bearings || []).length === 0 && _jsx("option", { value: inp.brg, children: inp.brg }), (bearings || []).map(b => _jsx("option", { value: b.name, children: b.name }, b.name))] }), activeR && _jsxs("div", { style: ss({ fontSize: 9, color: C.faint, marginTop: 2 }), children: ["L10: ", fN(activeR.brg_r?.L10), " h", ' ', "(req \u2265", fN(activeR.brg_r?.L10_target || 20000), " h)", ' ', activeR.brg_r?.ok ? '✓ OK' : '✗'] })] }), _jsxs("div", { style: ss({ marginBottom: 7 }), children: [_jsx(Lbl, { children: "Hanger Bearing (intermediate)" }), _jsxs("select", { value: inp.hgr_brg || inp.brg, onChange: e => setInp({ hgr_brg: e.target.value }), style: ss({ width: '100%', background: '#081321', border: `1px solid ${C.border}`, borderRadius: 4, padding: '5px 8px', color: C.text, fontSize: 11, fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box' }), children: [(bearings || []).length === 0 && _jsx("option", { value: inp.hgr_brg || inp.brg, children: inp.hgr_brg || inp.brg }), (bearings || []).map(b => _jsx("option", { value: b.name, children: b.name }, b.name))] }), _jsx("div", { style: ss({ fontSize: 8, color: C.faint, marginTop: 2 }), children: "Used for hanger load distribution display only" })] }), _jsxs("div", { style: ss({ marginBottom: 7 }), children: [_jsx(Lbl, { children: "Gearbox" }), _jsxs("select", { value: inp.gbx, onChange: e => setInp({ gbx: e.target.value }), style: ss({ width: '100%', background: '#081321', border: `1px solid ${C.border}`, borderRadius: 4, padding: '5px 8px', color: C.text, fontSize: 11, fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box' }), children: [(gearboxes || []).length === 0 && _jsx("option", { value: inp.gbx, children: inp.gbx }), (gearboxes || []).map(g => _jsx("option", { value: g.model, children: g.model }, g.model))] })] }), _jsx(SI, { field: "duty", label: "Duty Cycle", options: [
                            { value: '8', label: '8 h/day — standard' },
                            { value: '16', label: '16 h/day — heavy' },
                            { value: '24', label: '24 h/day — continuous' },
                        ] }), activeR && (_jsxs("div", { style: ss({ background: 'rgba(74,158,255,.06)', border: `1px solid ${C.blue}33`, borderRadius: 5, padding: '6px 9px', marginBottom: 7, fontSize: 10 }), children: [_jsxs("div", { style: ss({ color: C.blue }), children: ["AGMA SF: ", _jsx("strong", { children: f2(activeR.gbx_r?.agma_sf, 2) }), "  Derating: ", _jsxs("span", { style: ss({ color: C.amber }), children: [Math.round((1 - 1 / (activeR.gbx_r?.agma_sf || 1.25)) * 100), "%"] })] }), _jsxs("div", { style: ss({ color: C.faint, fontSize: 9, marginTop: 2 }), children: ["Motor: ", f2(activeR.pwr.motor_rated, 3), " kW \u00B7 ", f2(activeR.pwr.motor, 3), " kW selected"] })] })), _jsx(NI, { field: "hangers", label: "Intermediate Hanger Bearings (0=auto)", min: 0, max: 20, step: 1 }), _jsxs("div", { style: ss({ fontSize: 8, color: C.faint, marginTop: -4, marginBottom: 7, lineHeight: 1.4 }), children: ["Intermediate bearings only \u2014 excludes 2 fixed end shaft bearings.", _jsx("br", {}), "N hangers = N+1 spans. Span = L / (N+1)."] }), _jsx(NI, { field: "bload", label: "Bearing Load (kN)", min: 1, max: 200, step: 1 }), _jsx(NI, { field: "temp_c", label: "Process Temp (\u00B0C)", min: -20, max: 800, step: 5 }), _jsx("button", { onClick: () => refetch(), disabled: isLoading, style: ss({ width: '100%', marginTop: 10, padding: '9px 0', borderRadius: 5, border: `1px solid ${C.accent}`,
                            background: 'rgba(232,160,0,.12)', color: C.accent, fontSize: 12, fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit', letterSpacing: '0.04em' }), children: isLoading ? '⏳ Calculating…' : '▶ Recalculate' })] }), _jsxs("div", { style: ss({ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }), children: [_jsxs("div", { style: ss({ background: '#060f1c', borderBottom: `1px solid ${C.border}`, padding: '6px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }), children: [_jsx("span", { style: ss({ fontSize: 11, fontWeight: 800, color: C.accent, letterSpacing: '0.08em' }), children: "\uD83D\uDD29 SCREW CONVEYOR DESIGNER v2.4" }), _jsxs("div", { style: ss({ display: 'flex', gap: 6 }), children: [_jsx("button", { onClick: () => setShowOpt(true), style: ss({ padding: '5px 14px', borderRadius: 4, border: `1px solid ${C.teal}`, background: 'rgba(45,212,191,.1)', color: C.teal, cursor: 'pointer', fontSize: 11, fontWeight: 700, fontFamily: 'inherit' }), children: "\u2728 Auto-Optimise" }), _jsx("button", { onClick: () => window.print(), style: ss({ padding: '5px 12px', borderRadius: 4, border: `1px solid ${C.blue}`, background: 'rgba(74,158,255,.1)', color: C.blue, cursor: 'pointer', fontSize: 11, fontFamily: 'inherit' }), children: "\uD83D\uDDA8\uFE0F Print" })] })] }), _jsxs("div", { style: ss({ flex: 1, padding: 14, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 10 }), children: [_jsx("div", { style: ss({ background: 'rgba(217,142,0,.07)', border: `1px solid ${C.amber}44`, borderRadius: 6, padding: '5px 12px', fontSize: 10, color: C.amber }), children: "\u26A0 Preliminary Engineering Estimate Only" }), isError && (_jsx("div", { style: ss({ background: 'rgba(224,82,82,.08)', border: `1px solid ${C.red}`, borderRadius: 6, padding: '10px 14px', fontSize: 11 }), children: error?.response?.status === 404
                                    ? _jsxs(_Fragment, { children: [_jsx("div", { style: ss({ color: C.red, fontWeight: 700 }), children: "\u26A0\uFE0F Material not found \u2014 run:" }), _jsx("code", { style: ss({ color: C.amber }), children: "python -m backend.db.seed" })] })
                                    : _jsxs("div", { style: ss({ color: C.red }), children: ["\u26A0\uFE0F ", error?.message] }) })), (activeR || R) && _jsx(StdTabs, { activeStd: activeStd, setStd: setActiveStd, customLam: customLam, setCustomLam: setCustomLam, multiR: multiR || null, matLam: matLam, matName: inp.mat }), activeR && _jsx(DesignHealth, { R: activeR, inp: inp }), activeR && (() => {
                                const fr = activeR.regime || { name: 'Normal Flow' };
                                const isNorm = fr.name?.includes('Normal');
                                return (_jsxs("div", { style: ss({ background: 'rgba(16,30,48,.5)', border: `1px solid ${C.border}`, borderRadius: 8, padding: '8px 14px', display: 'flex', alignItems: 'center', gap: 12 }), children: [_jsx("span", { style: ss({ background: isNorm ? C.green : C.amber, width: 14, height: 14, borderRadius: 3, flexShrink: 0, display: 'inline-block' }) }), _jsx("span", { style: ss({ fontWeight: 700, fontSize: 11, color: isNorm ? C.green : C.amber }), children: fr.name }), _jsx("span", { style: ss({ fontSize: 10, color: C.muted }), children: "Normal conveying regime" }), _jsx("div", { style: ss({ marginLeft: 'auto' }), children: _jsxs("span", { style: ss({ fontSize: 9, background: '#1c3048', padding: '2px 8px', borderRadius: 3, color: C.muted }), children: ["CEMA Class ", activeR.mat?.cls || '—'] }) })] }));
                            })(), activeR && (() => {
                                const w = activeR.warns || { crit: [], adv: [], opt: [] };
                                return [
                                    ...(w.crit || []).map((x, i) => (_jsxs("div", { style: ss({ fontSize: 11, color: C.red, padding: '5px 12px', background: 'rgba(224,82,82,.08)', border: `1px solid ${C.red}44`, borderRadius: 5 }), children: ["\u274C [CRITICAL] ", x] }, 'c' + i))),
                                    ...(w.adv || []).map((x, i) => (_jsxs("div", { style: ss({ fontSize: 11, color: C.amber, padding: '5px 12px', background: 'rgba(217,142,0,.07)', border: `1px solid ${C.amber}44`, borderRadius: 5 }), children: ["\u26A0\uFE0F [ADVISORY] ", x] }, 'a' + i))),
                                    ...(w.opt || []).map((x, i) => (_jsxs("div", { style: ss({ fontSize: 11, color: C.blue, padding: '5px 12px', background: 'rgba(74,158,255,.07)', border: `1px solid ${C.blue}44`, borderRadius: 5 }), children: ["\uD83D\uDCA1 [OPTIMISATION] ", x] }, 'o' + i))),
                                ];
                            })(), activeR && (_jsxs("div", { style: ss({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }), children: [_jsxs(Panel, { children: [_jsx(SHdr, { icon: "\uD83D\uDCCA", label: "Capacity", badge: _jsx(Chip, { ok: activeR.cap.ok, label: activeR.cap.ok ? 'OK' : 'FAIL' }) }), _jsx(RR, { label: "Achieved", value: f2(activeR.cap.Qt, 2), unit: "t/h", ok: activeR.cap.ok }), _jsx(RR, { label: "Required", value: f2(activeR.cap.req || inp.cap, 2), unit: "t/h" }), _jsx(RR, { label: "Effective Pitch", value: Math.round((activeR.P_eff || inp.P) * 1000), unit: "mm", sub: "weighted avg / zones" }), _jsx(RR, { label: "Body capacity", value: f2(activeR.cap.Qt_body, 2), unit: "t/h", ok: activeR.cap.ok }), _jsx(RR, { label: "Governing (bottleneck)", value: f2(activeR.cap.Qt_governing || activeR.cap.Qt, 2), unit: "t/h", ok: activeR.cap.ok }), _jsx(RR, { label: "Volumetric", value: f2(activeR.cap.Qv, 3), unit: "m\u00B3/h" }), _jsx(RR, { label: "Fill Fraction", value: f2((activeR.cap.fill_actual || activeR.cap.fill || 0) * 100, 1), unit: "%", sub: "mat.fill_max\u00D7f(\u03B8) CEMA" }), _jsx(RR, { label: "Fill basis", value: "Dynamic calcFill" })] }), _jsxs(Panel, { children: [_jsx(SHdr, { icon: "\u26A1", label: "Power" }), _jsx(RR, { label: "Empty Friction", value: f2(activeR.pwr.Pe, 3), unit: "kW" }), _jsx(RR, { label: "Material Transport", value: f2(activeR.pwr.Pm, 3), unit: "kW" }), _jsx(RR, { label: "Incline Component", value: f2(activeR.pwr.Pi, 3), unit: "kW" }), _jsx(RR, { label: "Shaft Total", value: f2(activeR.pwr.Ps, 3), unit: "kW", hl: true }), _jsx(RR, { label: "Motor Selected", value: activeR.pwr.motor, unit: "kW", hl: true })] })] })), activeR && (_jsxs("div", { style: ss({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }), children: [_jsx(Panel, { children: (() => {
                                            const sa = activeR.shaft_auto || {};
                                            const pOpt = sa.pipe_opt || activeR.shaft_pipe_opt || null;
                                            const isManual = (inp.shaft_mode || 'auto') === 'manual';
                                            const isPipe = activeR.tor?.pipe || false;
                                            const effOD = activeR.tor?.eff_od_mm || sa.sel_mm || 70;
                                            const effID = activeR.tor?.eff_id_mm || 0;
                                            const pwall = inp.pwall || 8;
                                            const sfActual = (inp.sallow || 40) / Math.max(activeR.tor.tau, 0.001);
                                            const sfCol = sfActual >= 2.0 ? C.green : sfActual >= 1.5 ? C.amber : C.red;
                                            return (_jsxs(_Fragment, { children: [_jsx(SHdr, { icon: "\u2699\uFE0F", label: isManual ? 'Manual Shaft Override' : 'Auto Shaft Design', col: isManual ? C.amber : C.teal, badge: _jsx(Chip, { ok: activeR.tor.shOk, label: activeR.tor.shOk ? 'PASS' : 'FAIL' }) }), isManual
                                                        ? _jsxs("div", { style: ss({ background: 'rgba(232,160,0,.06)', border: `1px solid ${C.amber}33`, borderRadius: 5, padding: '5px 9px', marginBottom: 8, fontSize: 10, color: C.amber }), children: ["\u270F\uFE0F Manual override \u2014 ", isPipe ? 'hollow pipe' : 'solid bar', " \u00D8", effOD.toFixed(0), isPipe ? ' / ' + effID.toFixed(0) + ' mm ID' : '', " mm"] })
                                                        : _jsxs("div", { style: ss({ background: 'rgba(45,212,191,.06)', border: `1px solid ${C.teal}33`, borderRadius: 5, padding: '5px 9px', marginBottom: 8, fontSize: 10, color: C.teal }), children: ["\uD83D\uDCD0 Auto-sized from running torque ", Math.round(activeR.tor.Tr), " Nm at \u03C4_allow=", inp.sallow, " MPa"] }), _jsx(RR, { label: "Required diameter", value: f2(sa.req_mm, 1), unit: "mm", sub: "from torque" }), _jsx(RR, { label: isManual ? (isPipe ? 'Pipe OD / Wall / ID' : 'Manual OD') : 'Selected standard', value: isPipe ? `${effOD.toFixed(0)} / ${pwall} / ${effID.toFixed(0)} mm`
                                                            : `${effOD.toFixed(0)} mm${isManual ? '' : ' std'}`, ok: true }), _jsx(RR, { label: "Shear stress (startup)", value: f2(activeR.tor.tau, 2), unit: "MPa", ok: activeR.tor.shOk }), _jsxs("div", { style: ss({ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                                            padding: '4px 0', borderBottom: `1px solid ${C.border}`, fontSize: 11 }), children: [_jsx("span", { style: ss({ color: C.muted }), children: "Safety factor" }), _jsxs("span", { style: ss({ fontSize: 13, fontFamily: 'monospace', fontWeight: 800, color: sfCol }), children: [sfActual.toFixed(2), " \u00D7"] })] }), _jsx(RR, { label: "Running torque", value: Math.round(activeR.tor.Tr), unit: "Nm" }), _jsx(RR, { label: "Startup torque", value: Math.round(activeR.tor.Ts), unit: "Nm" }), _jsxs("div", { style: ss({ marginTop: 6, paddingTop: 6, borderTop: `1px solid ${C.border}44` }), children: [_jsx(RR, { label: "Shaft I (bending)", value: ((activeR.tor?.I_m4 || 0) * 1e8).toFixed(4), unit: "cm\u2074", sub: "section modulus" }), _jsx(RR, { label: "Deflection @ span", value: f2((activeR.deflection || 0) * 1000, 3), unit: "mm", ok: activeR.deflection_ok, sub: `limit ${((activeR.defl_limit || 0.01) * 1000).toFixed(2)}mm · span ${f2(activeR.hgr?.span, 2)}m` })] }), pOpt && (_jsxs("div", { style: ss({ marginTop: 10, background: isPipe ? 'rgba(45,212,191,.06)' : 'rgba(74,158,255,.06)',
                                                            border: `1px solid ${isPipe ? 'rgba(45,212,191,.25)' : 'rgba(74,158,255,.2)'}`, borderRadius: 8, padding: '10px 12px' }), children: [_jsx("p", { style: ss({ fontSize: 10, fontWeight: 700, color: isPipe ? C.teal : C.blue, marginBottom: 8 }), children: isPipe
                                                                    ? '⭕ Current: Hollow Pipe — weight saving vs same-OD solid bar'
                                                                    : `⭕ Pipe Option — same OD, ${pOpt.wt_save_pct}% lighter` }), _jsx("div", { style: ss({ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 6 }), children: [
                                                                    ['OD / Wall / ID', `${pOpt.od_mm} / ${pOpt.wall_mm} / ${pOpt.id_mm} mm`],
                                                                    ['Shear stress', `${(pOpt.tau_mpa || 0).toFixed(2)} MPa`],
                                                                    ['Weight saving', `${pOpt.wt_save_pct}%`],
                                                                    ['Feasible', pOpt.ok ? 'Yes ✓' : 'No ✗'],
                                                                ].map(([l, v]) => (_jsxs("div", { children: [_jsx("p", { style: ss({ fontSize: 8.5, color: C.muted, marginBottom: 2 }), children: l }), _jsx("p", { style: ss({ fontSize: 11, fontFamily: 'monospace', fontWeight: 700,
                                                                                color: l === 'Feasible' ? (pOpt.ok ? C.green : C.red) : l === 'Weight saving' ? C.teal : C.text }), children: v })] }, l))) }), isPipe && pOpt.vs_bar_tau != null && (_jsxs("p", { style: ss({ fontSize: 9, color: C.muted, marginTop: 6 }), children: ["Equivalent solid bar: \u03C4 = ", (pOpt.vs_bar_tau || 0).toFixed(2), " MPa", ' ', "(vs pipe \u03C4 = ", (pOpt.tau_mpa || 0).toFixed(2), " MPa)"] }))] }))] }));
                                        })() }), _jsxs(Panel, { children: [_jsx(SHdr, { icon: "\uD83D\uDD17", label: "Hanger Bearing Layout", badge: _jsxs("span", { style: ss({ fontSize: 9, color: C.muted }), children: ["\u00D8", Math.round(inp.D * 1000), " mm"] }) }), _jsxs("div", { style: ss({ background: 'rgba(45,212,191,.1)', border: `1px solid ${C.teal}33`, borderRadius: 5, padding: '7px 10px', marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }), children: [_jsxs("span", { style: ss({ fontWeight: 800, fontSize: 13, color: C.teal }), children: [activeR.hgr?.count || 0, " hanger bearings"] }), _jsxs("span", { style: ss({ fontSize: 9, color: C.teal }), children: ["\u00D8", Math.round(inp.D * 1000), " mm"] })] }), _jsx(RR, { label: "CEMA max span", value: f2(activeR.hgr?.max_span, 1), unit: "m", sub: "at this D & abrasion class" }), _jsx(RR, { label: "Actual span", value: f2(activeR.hgr?.span, 1), unit: "m", ok: activeR.hgr?.span <= (activeR.hgr?.max_span || 999), sub: activeR.hgr?.user_override ? 'user-set' : 'CEMA auto' }), _jsx(RR, { label: "Total length", value: inp.L, unit: "m" }), _jsx(RR, { label: "Total supports", value: (activeR.hgr?.count || 0) + 2, unit: "pcs", sub: `${activeR.hgr?.count || 0} hangers + 2 end bearings` }), _jsx(RR, { label: "Spans created", value: (activeR.hgr?.count || 0) + 1, sub: "L / (hangers + 1)" })] })] })), activeR && (_jsxs("div", { style: ss({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }), children: [_jsxs(Panel, { children: [_jsx(SHdr, { icon: "\u2B55", label: "Bearing Life", badge: _jsx(Chip, { ok: activeR.brg_r?.ok, label: activeR.brg_r?.ok ? 'PASS' : 'FAIL' }) }), _jsx(RR, { label: "Bearing", value: activeR.brg_r?.name || inp.brg }), _jsx(RR, { label: "C Dynamic", value: f2(activeR.brg_r?.C, 0), unit: "kN" }), _jsx(RR, { label: "Bearing load", value: f2(activeR.brg_r?.load, 2), unit: "kN" }), _jsx(RR, { label: "C/P Ratio", value: f2((activeR.brg_r?.C || 43) / (activeR.brg_r?.load || 10), 2) }), _jsx(RR, { label: "Required L10", value: fN(activeR.brg_r?.L10_target || 20000), unit: "h", sub: inp.duty === '24' ? '24h/day' : inp.duty === '16' ? '16h/day' : '8h/day' }), _jsx(RR, { label: "L10 Life", value: fN(activeR.brg_r?.L10), unit: "h", ok: activeR.brg_r?.ok, hl: true }), !activeR.brg_r?.ok && activeR.brg_r?.adequate && (_jsxs("div", { style: ss({ marginTop: 6, background: 'rgba(232,160,0,.08)', border: `1px solid ${C.amber}33`, borderRadius: 4, padding: '5px 8px', fontSize: 9, color: C.amber }), children: ["\uD83D\uDCA1 Suggested: ", _jsx("strong", { children: activeR.brg_r.adequate }), " \u2014 select from dropdown to meet target"] }))] }), _jsxs(Panel, { children: [_jsx(SHdr, { icon: "\uD83D\uDD27", label: "Wear Life" }), _jsx(RR, { label: "Tip Speed", value: f2(activeR.wear?.v_tip, 2), unit: "m/s" }), _jsx(RR, { label: "Contact Pressure", value: f2(activeR.wear?.P_contact_kPa, 2), unit: "kPa" }), _jsx(RR, { label: "Wear Rate (body)", value: f2(activeR.wear?.wrate_mm_h, 4), unit: "mm/h" }), _jsx(RR, { label: "Wear Rate (inlet)", value: f2((activeR.wear?.wrate_mm_h || 0) * 3, 4), unit: "mm/h", sub: "3\u00D7 body rate" }), _jsx(RR, { label: "Usable Thickness", value: f2(activeR.wear?.thick_mm, 1), unit: "mm" }), _jsx(RR, { label: "Flight Life (body)", value: fN(activeR.wear?.life_h), unit: "h", ok: (activeR.wear?.life_h || 0) > 8000, hl: true }), _jsx(RR, { label: "Flight Life (inlet)", value: fN((activeR.wear?.life_h || 0) / 3), unit: "h", ok: (activeR.wear?.life_h || 0) / 3 > 2000 }), _jsx(RR, { label: "Throughput Life", value: fN(activeR.wear?.life_t), unit: "t" })] })] })), activeR && (_jsxs("div", { style: ss({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }), children: [_jsxs(Panel, { children: [_jsx(SHdr, { icon: "\uD83D\uDCB0", label: "Cost Estimate" }), _jsx(RR, { label: "Steel Grade", value: activeR.cost?.steel || 'Steel' }), _jsx(RR, { label: "Unit Cost", value: f2(activeR.cost?.uc, 1), unit: "USD/kg" }), _jsx(RR, { label: "Steel Mass", value: fN(activeR.cost?.mass), unit: "kg" }), _jsx(RR, { label: "Est. Cost", value: '$' + fN(activeR.cost?.total), hl: true })] }), _jsxs(Panel, { children: [_jsx(SHdr, { icon: "\u2699\uFE0F", label: "Gearbox & Motor", badge: _jsx(Chip, { ok: activeR.gbx_r?.tOk, label: activeR.gbx_r?.tOk ? 'PASS' : 'FAIL' }) }), _jsx(RR, { label: "Selected GBX", value: activeR.gbx_r?.model }), _jsx(RR, { label: "Startup Torque", value: Math.round(activeR.tor.Ts), unit: "Nm", ok: activeR.gbx_r?.tOk }), _jsx(RR, { label: "GBX Nameplate", value: fN(activeR.gbx_r?.Tn), unit: "Nm" }), _jsx(RR, { label: `GBX Derated (SF=${f2(activeR.gbx_r?.agma_sf, 2)})`, value: fN(activeR.gbx_r?.Tn_derated || activeR.gbx_r?.Tn), unit: "Nm", ok: activeR.gbx_r?.tOk, sub: "effective capacity at this duty" }), _jsx(RR, { label: "Thermal Power", value: f2(activeR.pwr.Pt, 2), unit: "kW" }), _jsx(RR, { label: "Motor", value: activeR.pwr.motor, unit: "kW", hl: true }), _jsx(RR, { label: `AGMA SF (${inp.duty || 8}h/day)`, value: f2(activeR.gbx_r?.agma_sf, 2) + ' ×', sub: "motor & GBX derating" })] })] })), activeR?.eff && _jsx(EfficiencyCard, { eff: activeR.eff }), multiR && _jsx(StdCompTable, { multiR: multiR, activeStd: activeStd }), activeR?.recs && _jsx(MatRecs, { recs: activeR.recs }), activeR && (_jsxs(Panel, { children: [_jsx("div", { style: ss({ fontSize: 9, color: C.faint, marginBottom: 4 }), children: "\u25B6 CALCULATION BASIS & METHOD TRACEABILITY \u25BC" }), _jsxs("div", { style: ss({ fontSize: 9, color: C.faint, lineHeight: 1.7 }), children: ["Capacity: CEMA \u00A73 \u2014 volumetric with inclination factor", _jsx("br", {}), "Power: CEMA \u00A74 \u2014 Pe + Pm + Pi split, Pf=(Pe+Pm)\u00D7kf", _jsx("br", {}), "Shaft: ASME B106.1M torsional section modulus", _jsx("br", {}), "Bearings: ISO 281 L10 life", _jsx("br", {}), "Wear: Archard model, K_base=", 0.006, " mm/h calibrated to CEMA Class II field data", _jsx("br", {}), "Ce=0.50 empirical friction factor (CEMA-based)"] }), _jsx(PowerBreakdown, { pwr: activeR.pwr }), _jsx(ParamSweep, { inp: inp })] })), activeR && _jsx(StructuralModule, { R: activeR, inp: inp }), activeR && (() => { try {
                                return _jsx(AxialProfiles, { R: activeR, inp: inp });
                            }
                            catch (e) {
                                return _jsx("div", { style: { color: '#e05252', padding: 12, fontSize: 11 }, children: "\u26A0 Axial profile error \u2014 check console" });
                            } })(), !R && !isLoading && !isError && (_jsx("div", { style: ss({ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.muted, fontSize: 13, minHeight: 200 }), children: "Select a material and adjust inputs \u2014 results appear automatically" }))] })] }), showOpt && _jsx(AutoOptModal, { inp: inp, onApply: p => setInp(p), onClose: () => setShowOpt(false) })] }));
}
