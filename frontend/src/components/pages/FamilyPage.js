import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
/**
 * FamilyPage.tsx — VECTRIX™ Family Designer
 * Full port of the HTML prototype: D × L × N matrix generator with
 * 5 view modes (All Designs, Meets Target, Capacity Matrix, Energy Matrix, Best per D)
 * CSV export, Apply-to-Designer, material-aware speed cap.
 */
import React, { useState, useEffect, useMemo } from 'react';
import { useMaterials, useCalcStore } from '../../hooks/useCalculator';
import * as api from '../../api/client';
const C = {
    panel: '#101e30', border: '#1c3048', text: '#ddeaf6',
    muted: '#5d7d99', faint: '#3a5470', accent: '#e8a000',
    green: '#1fb86e', red: '#e05252', amber: '#d98e00', blue: '#4a9eff',
    teal: '#2dd4bf', purple: '#a78bfa',
};
const ss = (s) => s;
const DA = [100, 150, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800];
const LA = [3, 5, 8, 10, 12, 15, 18, 20, 25, 30, 35, 40, 45, 50];
export default function FamilyPage() {
    const { inp: calcInp, setInp } = useCalcStore();
    const { data: mats } = useMaterials();
    const [cfg, setCfg] = useState({
        mat: calcInp.mat || 'Portland cement dry',
        ang: calcInp.ang ?? 0,
        surge: calcInp.surge || 1.2,
        cap: calcInp.cap || 30,
        L: calcInp.L || 10,
        Ds: [150, 200, 250, 300, 400, 500],
        Ls: [5, 10, 15, 20, 25, 30],
    });
    // Sync from CalcPage whenever calcInp changes
    useEffect(() => {
        setCfg(prev => ({
            ...prev,
            mat: calcInp.mat || prev.mat,
            ang: calcInp.ang ?? prev.ang,
            surge: calcInp.surge || prev.surge,
            cap: calcInp.cap || prev.cap,
        }));
    }, [calcInp.mat, calcInp.ang, calcInp.surge, calcInp.cap]);
    const [res, setRes] = useState(null);
    const [vt, setVt] = useState('list');
    const [running, setRunning] = useState(false);
    const [picked, setPicked] = useState(null);
    const c = (k) => (v) => setCfg(prev => ({ ...prev, [k]: v }));
    const toggleArr = (key, val) => setCfg(prev => ({
        ...prev,
        [key]: prev[key].includes(val)
            ? prev[key].filter((x) => x !== val)
            : [...prev[key], val].sort((a, b) => a - b)
    }));
    const generate = async () => {
        setRunning(true);
        setRes(null);
        try {
            const result = await api.getFamily({
                mat: cfg.mat, ang: cfg.ang, surge: cfg.surge,
                cap: cfg.cap, L: cfg.L,
                Ds: cfg.Ds.map(d => d), // send as mm — backend divides by 1000
                Ls: cfg.Ls,
            });
            // getFamily returns {pts:[...]} from backend
            const pts = result.pts || [];
            setRes({ pts });
        }
        catch (e) {
            console.error('Family generation failed', e);
        }
        setRunning(false);
        setPicked(null);
    };
    const applyDesign = (p) => {
        setPicked(p);
        setInp({
            D: p.Dmm / 1000,
            N: p.N,
            P: p.Dmm / 1000,
            L: p.L,
            mat: cfg.mat,
            ang: cfg.ang,
            surge: cfg.surge,
        });
    };
    const exportCSV = () => {
        if (!res)
            return;
        const hdr = ['D(mm)', 'L(m)', 'N(RPM)', 'Cap(t/h)', 'Feasible', 'Power(kW)', 'Motor(kW)', 'Torque(Nm)', 'Shaft(mm)', 'Hangers', 'L10(h)', 'kWh/t', 'Cost(USD)', 'Score'];
        const rows = res.pts.map(p => [p.Dmm, p.L, p.N, p.cap.toFixed(1), p.cap_ok ? 'Yes' : 'No', p.pwr.toFixed(2), p.motor, p.tor.toFixed(0), p.shaft_mm, p.hgr, p.L10.toFixed(0), p.kWh.toFixed(3), p.cost.toFixed(0), p.score.toFixed(1)]);
        const csv = [hdr, ...rows].map(r => r.join(',')).join('\n');
        const a = document.createElement('a');
        a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
        a.download = 'screw_family.csv';
        a.click();
    };
    const feasible = res?.pts.filter(p => p.cap_ok) || [];
    const infeasible = res?.pts.filter(p => !p.cap_ok) || [];
    // Best per D (minimum kWh/t among feasible for each diameter)
    const bestPerD = useMemo(() => {
        const byD = {};
        for (const p of feasible) {
            if (!byD[p.Dmm] || p.kWh < byD[p.Dmm].kWh)
                byD[p.Dmm] = p;
        }
        return Object.values(byD).sort((a, b) => a.Dmm - b.Dmm);
    }, [feasible]);
    // Capacity heat matrix: rows=D, cols=L, cells=max cap at best N
    const capMatrix = useMemo(() => {
        const Ds = [...new Set(res?.pts.map(p => p.Dmm) || [])].sort((a, b) => a - b);
        const Ls = [...new Set(res?.pts.map(p => p.L) || [])].sort((a, b) => a - b);
        const cell = (D, L) => {
            const group = res?.pts.filter(p => p.Dmm === D && p.L === L) || [];
            if (!group.length)
                return null;
            return group.sort((a, b) => b.cap - a.cap)[0];
        };
        return { Ds, Ls, cell };
    }, [res]);
    const okCol = (ok) => ok ? C.green : C.red;
    // ── Table header cell
    const TH = ({ children, right }) => (_jsx("th", { style: ss({ padding: '5px 8px', textAlign: right ? 'right' : 'left', color: '#93c5fd',
            fontWeight: 700, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.06em',
            background: 'rgba(0,0,0,.4)', borderBottom: `2px solid ${C.border}`,
            whiteSpace: 'nowrap', position: 'sticky', top: 0, zIndex: 2 }), children: children }));
    const TD = ({ children, right, col, mono }) => (_jsx("td", { style: ss({ padding: '4px 8px', textAlign: right ? 'right' : 'left', color: col || C.text,
            fontSize: 10, fontFamily: mono ? 'monospace' : 'inherit', borderBottom: `1px solid ${C.border}33` }), children: children }));
    const renderTableRows = (pts) => pts.slice(0, 200).map((p, i) => (_jsxs("tr", { style: ss({ background: i % 2 === 0 ? 'transparent' : 'rgba(0,0,0,.12)',
            cursor: 'pointer' }), onClick: () => applyDesign(p), children: [_jsx(TD, { mono: true, col: C.accent, children: p.Dmm }), _jsx(TD, { mono: true, children: p.L }), _jsx(TD, { mono: true, children: p.N }), _jsx(TD, { mono: true, col: okCol(p.cap_ok), children: p.cap.toFixed(1) }), _jsx(TD, { children: _jsx("span", { style: ss({ fontSize: 9, fontWeight: 700, padding: '1px 6px', borderRadius: 3,
                        background: p.cap_ok ? 'rgba(31,184,110,.15)' : 'rgba(224,82,82,.15)',
                        color: p.cap_ok ? C.green : C.red, border: `1px solid ${okCol(p.cap_ok)}` }), children: p.cap_ok ? '✓' : '✗' }) }), _jsx(TD, { mono: true, right: true, children: p.pwr.toFixed(2) }), _jsx(TD, { mono: true, right: true, children: p.motor }), _jsx(TD, { mono: true, right: true, children: p.tor.toFixed(0) }), _jsx(TD, { mono: true, right: true, children: p.shaft_mm }), _jsx(TD, { mono: true, right: true, children: p.hgr }), _jsxs(TD, { mono: true, right: true, col: p.L10 >= 20000 ? C.green : C.amber, children: [(p.L10 / 1000).toFixed(0), "k"] }), _jsx(TD, { mono: true, right: true, col: p.kWh < 1 ? C.green : p.kWh < 2 ? C.amber : C.red, children: p.kWh.toFixed(3) }), _jsxs(TD, { mono: true, right: true, children: ["$", p.cost.toFixed(0)] }), _jsx(TD, { mono: true, right: true, col: p.score > 70 ? C.green : p.score > 45 ? C.amber : C.red, children: p.score.toFixed(0) }), _jsx(TD, { children: _jsx("button", { onClick: e => { e.stopPropagation(); applyDesign(p); }, style: ss({ padding: '2px 8px', borderRadius: 4, border: `1px solid ${C.teal}44`,
                        background: 'transparent', color: C.teal, cursor: 'pointer', fontSize: 9, fontWeight: 700 }), children: "Apply" }) })] }, i)));
    const heatColor = (val, min, max, invert = false) => {
        const t = max === min ? 0.5 : (val - min) / (max - min);
        const tt = invert ? 1 - t : t;
        const r = Math.round(224 * (1 - tt) + 31 * tt);
        const g = Math.round(82 * (1 - tt) + 184 * tt);
        const b = Math.round(82 * (1 - tt) + 110 * tt);
        return `rgb(${r},${g},${b})`;
    };
    return (_jsxs("div", { style: ss({ display: 'flex', flexDirection: 'column', gap: 10, height: '100%', overflowY: 'auto', padding: 14 }), children: [_jsxs("div", { style: ss({ background: 'rgba(16,30,48,.8)', border: `1px solid ${C.border}`, borderRadius: 10, padding: 16, flexShrink: 0 }), children: [_jsxs("div", { style: ss({ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: C.accent, letterSpacing: '0.08em', marginBottom: 12 }), children: ["\u2699\uFE0F Family Configuration", _jsx("span", { style: ss({ fontSize: 9, fontWeight: 400, color: C.muted, marginLeft: 8 }), children: "synced from Screw Conveyor Designer tab" })] }), _jsxs("div", { style: ss({ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: 10, marginBottom: 12 }), children: [_jsxs("div", { children: [_jsx("div", { style: ss({ fontSize: 9, color: C.muted, marginBottom: 3, textTransform: 'uppercase', letterSpacing: '0.06em' }), children: "Material" }), _jsx("select", { value: cfg.mat, onChange: e => c('mat')(e.target.value), style: ss({ width: '100%', background: '#081321', border: `1px solid ${C.border}`, color: C.text, borderRadius: 5, padding: '5px 8px', fontSize: 11 }), children: (mats || []).map(m => _jsx("option", { value: m.name, children: m.name }, m.name)) })] }), [['Required Cap (t/h)', 'cap'], ['Angle (°)', 'ang'], ['Surge Factor', 'surge']].map(([lbl, key]) => (_jsxs("div", { children: [_jsx("div", { style: ss({ fontSize: 9, color: C.muted, marginBottom: 3, textTransform: 'uppercase', letterSpacing: '0.06em' }), children: lbl }), _jsx("input", { type: "number", value: cfg[key], onChange: e => c(key)(parseFloat(e.target.value) || 0), style: ss({ width: '100%', background: '#081321', border: `1px solid ${C.border}`, color: C.text, borderRadius: 5, padding: '5px 8px', fontSize: 11, fontFamily: 'monospace', boxSizing: 'border-box' }) })] }, key)))] }), _jsx("div", { style: ss({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 12 }), children: [
                            ['Diameter options (mm)', 'Ds', DA, C.accent, 'rgba(232,160,0,.18)'],
                            ['Length options (m)', 'Ls', LA, C.green, 'rgba(31,184,110,.18)'],
                        ].map(([lbl, key, arr, col, bg]) => (_jsxs("div", { children: [_jsx("div", { style: ss({ fontSize: 10, fontWeight: 700, color: C.muted, marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.08em' }), children: lbl }), _jsx("div", { style: ss({ display: 'flex', flexWrap: 'wrap', gap: 4 }), children: arr.map(v => (_jsx("button", { onClick: () => toggleArr(key, v), style: ss({ padding: '3px 9px', borderRadius: 4, fontSize: 11, fontWeight: 700, cursor: 'pointer', fontFamily: 'monospace',
                                            border: `1px solid ${cfg[key].includes(v) ? col : C.border}`,
                                            background: cfg[key].includes(v) ? bg : 'transparent',
                                            color: cfg[key].includes(v) ? col : C.muted }), children: v }, v))) })] }, key))) }), _jsxs("div", { style: ss({ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }), children: [_jsx("button", { onClick: generate, disabled: running, style: ss({ padding: '9px 24px', borderRadius: 8, border: 'none',
                                    background: running ? C.faint : 'rgba(45,212,191,.9)',
                                    color: '#0b1522', fontWeight: 800, fontSize: 13, cursor: running ? 'wait' : 'pointer' }), children: running ? '⏳ Generating…' : '▶ Generate Family' }), res && (_jsxs(_Fragment, { children: [_jsxs("span", { style: ss({ fontSize: 10, color: C.muted }), children: [feasible.length, " feasible / ", res.pts.length, " total \u00B7 ", cfg.mat, " \u00B7 ", cfg.ang, "\u00B0 \u00B7 \u2265", cfg.cap, " t/h"] }), _jsx("button", { onClick: exportCSV, style: ss({ marginLeft: 'auto', padding: '5px 12px', borderRadius: 6, border: `1px solid ${C.green}`, background: 'transparent', color: C.green, cursor: 'pointer', fontSize: 10, fontWeight: 700 }), children: "\u2B07 CSV" })] }))] })] }), picked && (_jsxs("div", { style: ss({ background: 'rgba(45,212,191,.08)', border: '1px solid rgba(45,212,191,.3)', borderRadius: 8, padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }), children: [_jsx("span", { style: ss({ fontSize: 16 }), children: "\u2705" }), _jsxs("div", { children: [_jsx("p", { style: ss({ fontSize: 11, fontWeight: 700, color: C.teal }), children: "Design applied to Screw Conveyor Designer tab" }), _jsxs("p", { style: ss({ fontSize: 10, color: C.muted }), children: ["\u00D8", picked.Dmm, "mm \u00B7 ", picked.N, "rpm \u00B7 L=", picked.L, "m \u00B7 ", picked.cap.toFixed(1), " t/h \u00B7 ", picked.kWh.toFixed(3), " kWh/t"] })] })] })), res && (_jsxs("div", { style: ss({ background: 'rgba(16,30,48,.8)', border: `1px solid ${C.border}`, borderRadius: 10, overflow: 'hidden', display: 'flex', flexDirection: 'column' }), children: [_jsx("div", { style: ss({ display: 'flex', gap: 2, padding: '8px 12px', background: 'rgba(0,0,0,.2)', borderBottom: `1px solid ${C.border}`, flexWrap: 'wrap', alignItems: 'center' }), children: [
                            ['list', '📋 All Designs'],
                            ['feasible', '✓ Meets Target'],
                            ['matrix', '📊 Capacity Matrix'],
                            ['energy', '🔋 Energy Matrix'],
                            ['best', '⭐ Best per D'],
                        ].map(([id, lb]) => (_jsx("button", { onClick: () => setVt(id), style: ss({ padding: '4px 10px', borderRadius: 5, fontSize: 10, fontWeight: 700, cursor: 'pointer',
                                border: `1px solid ${vt === id ? C.accent : C.border}`,
                                background: vt === id ? 'rgba(232,160,0,.12)' : 'transparent',
                                color: vt === id ? C.accent : C.muted }), children: lb }, id))) }), (vt === 'list' || vt === 'feasible') && (_jsxs("div", { style: ss({ overflowX: 'auto', overflowY: 'auto', maxHeight: 480 }), children: [_jsxs("table", { style: ss({ width: '100%', borderCollapse: 'collapse', fontSize: 11, tableLayout: 'auto' }), children: [_jsx("thead", { children: _jsx("tr", { children: ['D(mm)', 'L(m)', 'N', 'Cap(t/h)', '✓', 'Pwr(kW)', 'Motor', 'Torque', 'Shaft', 'Hgr', 'L10', 'kWh/t', 'Cost', 'Score', ''].map(h => (_jsx(TH, { right: ['Cap(t/h)', 'Pwr(kW)', 'Motor', 'Torque', 'Shaft', 'Hgr', 'L10', 'kWh/t', 'Cost', 'Score'].includes(h), children: h }, h))) }) }), _jsx("tbody", { children: renderTableRows(vt === 'feasible' ? feasible : res.pts) })] }), vt === 'feasible' && feasible.length === 0 && (_jsxs("div", { style: ss({ padding: 24, textAlign: 'center', color: C.muted, fontSize: 11 }), children: ["No designs meet the \u2265", cfg.cap, " t/h target. Try larger diameters or higher speeds."] }))] })), vt === 'matrix' && (_jsxs("div", { style: ss({ overflowX: 'auto', padding: 12 }), children: [_jsx("p", { style: ss({ fontSize: 10, color: C.muted, marginBottom: 8 }), children: "Max capacity (t/h) at best N for each D \u00D7 L combination. Click cell to apply." }), _jsxs("table", { style: ss({ borderCollapse: 'collapse', fontSize: 10 }), children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { style: ss({ padding: '4px 10px', color: C.muted, fontSize: 9 }), children: "D \\ L(m)" }), capMatrix.Ls.map(L => _jsxs("th", { style: ss({ padding: '4px 10px', color: C.blue, fontSize: 9, fontWeight: 700 }), children: [L, "m"] }, L))] }) }), _jsx("tbody", { children: capMatrix.Ds.map(D => {
                                            const cells = capMatrix.Ls.map(L => capMatrix.cell(D, L));
                                            const vals = cells.filter(Boolean).map(c => c.cap);
                                            const minV = Math.min(...vals), maxV = Math.max(...vals);
                                            return (_jsxs("tr", { children: [_jsxs("td", { style: ss({ padding: '4px 10px', color: C.accent, fontWeight: 700, fontFamily: 'monospace', fontSize: 10 }), children: ["\u00D8", D, "mm"] }), cells.map((cell, i) => (_jsx("td", { onClick: () => cell && applyDesign(cell), style: ss({ padding: '4px 8px', textAlign: 'center', fontFamily: 'monospace', fontSize: 10, fontWeight: 700, cursor: cell ? 'pointer' : 'default',
                                                            background: cell ? heatColor(cell.cap, minV, maxV) + '66' : 'transparent',
                                                            color: cell ? (cell.cap_ok ? C.green : C.amber) : C.faint,
                                                            border: `1px solid ${C.border}33` }), children: cell ? cell.cap.toFixed(1) : '—' }, i)))] }, D));
                                        }) })] })] })), vt === 'energy' && (_jsxs("div", { style: ss({ overflowX: 'auto', padding: 12 }), children: [_jsx("p", { style: ss({ fontSize: 10, color: C.muted, marginBottom: 8 }), children: "Energy intensity (kWh/t) at best N \u2014 greener = more efficient. Click cell to apply." }), _jsxs("table", { style: ss({ borderCollapse: 'collapse', fontSize: 10 }), children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { style: ss({ padding: '4px 10px', color: C.muted, fontSize: 9 }), children: "D \\ L(m)" }), capMatrix.Ls.map(L => _jsxs("th", { style: ss({ padding: '4px 10px', color: C.blue, fontSize: 9, fontWeight: 700 }), children: [L, "m"] }, L))] }) }), _jsx("tbody", { children: capMatrix.Ds.map(D => {
                                            const cells = capMatrix.Ls.map(L => capMatrix.cell(D, L));
                                            const vals = cells.filter(Boolean).map(c => c.kWh);
                                            const minV = Math.min(...vals), maxV = Math.max(...vals);
                                            return (_jsxs("tr", { children: [_jsxs("td", { style: ss({ padding: '4px 10px', color: C.accent, fontWeight: 700, fontFamily: 'monospace', fontSize: 10 }), children: ["\u00D8", D, "mm"] }), cells.map((cell, i) => (_jsx("td", { onClick: () => cell && applyDesign(cell), style: ss({ padding: '4px 8px', textAlign: 'center', fontFamily: 'monospace', fontSize: 10, fontWeight: 700, cursor: cell ? 'pointer' : 'default',
                                                            background: cell ? heatColor(cell.kWh, minV, maxV, true) + '66' : 'transparent',
                                                            color: cell ? (cell.kWh < 1 ? C.green : cell.kWh < 2 ? C.amber : C.red) : C.faint,
                                                            border: `1px solid ${C.border}33` }), children: cell ? cell.kWh.toFixed(3) : '—' }, i)))] }, D));
                                        }) })] })] })), vt === 'best' && (_jsxs("div", { style: ss({ padding: 12 }), children: [_jsx("p", { style: ss({ fontSize: 10, color: C.muted, marginBottom: 8 }), children: "Most energy-efficient feasible design at each diameter." }), bestPerD.length === 0 && (_jsx("div", { style: ss({ padding: 24, textAlign: 'center', color: C.muted, fontSize: 11 }), children: "No feasible designs found. Try larger diameter selection." })), _jsx("div", { style: ss({ display: 'flex', flexDirection: 'column', gap: 6 }), children: bestPerD.map((p, i) => (_jsxs("div", { style: ss({ background: i === 0 ? 'rgba(45,212,191,.08)' : 'rgba(0,0,0,.15)', border: `1px solid ${i === 0 ? 'rgba(45,212,191,.3)' : C.border}`, borderRadius: 8, padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer' }), onClick: () => applyDesign(p), children: [_jsxs("span", { style: ss({ fontSize: 11, fontWeight: 800, color: i === 0 ? C.teal : C.accent, fontFamily: 'monospace', minWidth: 60 }), children: ["\u00D8", p.Dmm, "mm"] }), _jsx("div", { style: ss({ display: 'flex', gap: 16, flexWrap: 'wrap', flex: 1, fontSize: 10 }), children: [
                                                ['N', `${p.N} RPM`, C.text],
                                                ['Cap', `${p.cap.toFixed(1)} t/h`, p.cap_ok ? C.green : C.red],
                                                ['Motor', `${p.motor} kW`, C.purple],
                                                ['kWh/t', p.kWh.toFixed(3), p.kWh < 1 ? C.green : C.amber],
                                                ['L10', `${(p.L10 / 1000).toFixed(0)}kh`, p.L10 >= 20000 ? C.green : C.amber],
                                                ['Score', p.score.toFixed(0), p.score > 70 ? C.green : C.amber],
                                                ['Cost', `$${p.cost.toFixed(0)}`, C.accent],
                                            ].map(([lbl, val, col]) => (_jsxs("span", { style: ss({ color: C.muted }), children: [lbl, ": ", _jsx("strong", { style: ss({ color: col }), children: val })] }, lbl))) }), _jsx("button", { onClick: e => { e.stopPropagation(); applyDesign(p); }, style: ss({ padding: '5px 14px', borderRadius: 6, border: `1px solid ${C.teal}`, background: 'transparent', color: C.teal, cursor: 'pointer', fontSize: 10, fontWeight: 700 }), children: "Apply \u2192" })] }, i))) })] }))] })), !res && !running && (_jsxs("div", { style: ss({ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: C.muted, gap: 8, paddingTop: 40 }), children: [_jsx("div", { style: ss({ fontSize: 32 }), children: "\uD83D\uDCCA" }), _jsx("div", { style: ss({ fontSize: 12, color: C.muted }), children: "Select diameters and lengths, then click Generate Family" }), _jsx("div", { style: ss({ fontSize: 10, color: C.faint }), children: "Results are auto-scored and sorted by feasibility then energy efficiency" })] }))] }));
}
