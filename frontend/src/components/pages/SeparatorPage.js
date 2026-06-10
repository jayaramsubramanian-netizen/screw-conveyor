import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import React, { useState } from 'react';
import axios from 'axios';
const C = {
    panel: '#101e30', border: '#1c3048', text: '#ddeaf6',
    muted: '#5d7d99', accent: '#e8a000', green: '#1fb86e', red: '#e05252',
};
function Field({ label, value, setter, min, max, step = 0.01 }) {
    return (_jsxs("div", { style: { marginBottom: 10 }, children: [_jsx("div", { style: { fontSize: 10, color: C.muted, fontWeight: 700,
                    textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 3 }, children: label }), _jsx("input", { type: 'number', value: value, min: min, max: max, step: step, onChange: e => setter(parseFloat(e.target.value) || 0), style: { width: '100%', background: '#081321', border: `1px solid ${C.border}`,
                    borderRadius: 4, padding: '5px 8px', color: C.text, fontSize: 11,
                    fontFamily: 'monospace', outline: 'none', boxSizing: 'border-box' } })] }));
}
export default function SeparatorPage() {
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [diam, setDiam] = useState(0.4);
    const [len, setLen] = useState(6);
    const [speed, setSpeed] = useState(30);
    const [fill, setFill] = useState(0.35);
    const [feed, setFeed] = useState(5);
    const [rho, setRho] = useState(1.2);
    const run = async () => {
        setLoading(true);
        setError(null);
        try {
            const { data } = await axios.post('/api/v1/process/separator', {
                diam, len, feed, rho,
                speedDry: speed, speedCool: speed, Nr: speed, speedS: speed, Nc: speed,
                fillDry: fill, fillC2: fill, fillR: fill, fill2: fill, fFill: fill,
                Lr: len, Lc: len, lenSep: len, fLen: len,
                tIn: 20, tInC: 20,
            });
            setResult(data);
        }
        catch (e) {
            setError(e?.response?.data?.detail || e?.message || 'Unknown error');
        }
        finally {
            setLoading(false);
        }
    };
    return (_jsxs("div", { style: { display: 'flex', gap: 12, padding: 12, height: '100%' }, children: [_jsxs("div", { style: { width: 260, flexShrink: 0, background: C.panel,
                    border: `1px solid ${C.border}`, borderRadius: 8, padding: 14, overflowY: 'auto' }, children: [_jsxs("div", { style: { marginBottom: 12 }, children: [_jsx("div", { style: { fontSize: 20, marginBottom: 4 }, children: "\uD83D\uDD00" }), _jsx("div", { style: { fontSize: 12, fontWeight: 800, color: C.accent }, children: "Separator" }), _jsx("div", { style: { fontSize: 10, color: C.muted, marginTop: 4, lineHeight: 1.6 }, children: "Sigmoid grade efficiency \u00B7 Stokes settling (physics validation)" })] }), _jsx("div", { style: { height: 1, background: C.border, margin: '12px 0' } }), _jsx(Field, { label: 'Diameter (m)', value: diam, setter: setDiam, min: 0.1, max: 1.2, step: 0.05 }), _jsx(Field, { label: 'Length (m)', value: len, setter: setLen, min: 0.5, max: 30, step: 0.5 }), _jsx(Field, { label: 'Speed (RPM)', value: speed, setter: setSpeed, min: 2, max: 120, step: 1 }), _jsx(Field, { label: 'Fill fraction', value: fill, setter: setFill, min: 0.1, max: 0.8, step: 0.05 }), _jsx(Field, { label: 'Feed rate (t/h)', value: feed, setter: setFeed, min: 0.1, max: 500, step: 1 }), _jsx(Field, { label: 'Bulk density (t/m\u00B3)', value: rho, setter: setRho, min: 0.1, max: 3, step: 0.05 }), _jsx("button", { onClick: run, disabled: loading, style: {
                            width: '100%', marginTop: 8, padding: '8px 0', borderRadius: 5,
                            border: `1px solid ${C.accent}`, background: 'rgba(232,160,0,0.12)',
                            color: C.accent, fontSize: 12, fontWeight: 800, cursor: 'pointer',
                            fontFamily: 'inherit',
                        }, children: loading ? 'Calculating…' : 'Run Calculation' })] }), _jsxs("div", { style: { flex: 1, display: 'flex', flexDirection: 'column', gap: 12, overflowY: 'auto' }, children: [error && (_jsxs("div", { style: { background: 'rgba(224,82,82,.08)', border: `1px solid ${C.red}`,
                            borderRadius: 6, padding: '8px 14px', fontSize: 11, color: C.red }, children: ["\u26A0\uFE0F ", error] })), result && (_jsxs(_Fragment, { children: [result.tr && (_jsxs("div", { style: { background: C.panel, border: `1px solid ${C.border}`,
                                    borderRadius: 8, padding: 12 }, children: [_jsx("div", { style: { fontSize: 10, fontWeight: 800, color: C.accent,
                                            letterSpacing: '0.08em', marginBottom: 8 }, children: "\u2699\uFE0F TRANSPORT" }), [
                                        ['v_ax ideal', result.tr?.v_ax_ideal?.toFixed(4), 'm/s'],
                                        ['v_ax process', result.tr?.v_ax?.toFixed(4), 'm/s'],
                                        ['Slip factor S', result.tr?.S?.toFixed(3), ''],
                                        ['t_res', result.tr?.t_res?.toFixed(1), 's'],
                                    ].map(([l, v, u]) => v != null && (_jsxs("div", { style: { display: 'flex', justifyContent: 'space-between',
                                            borderBottom: `1px solid ${C.border}`, padding: '3px 0', fontSize: 11 }, children: [_jsx("span", { style: { color: C.muted }, children: l }), _jsxs("span", { style: { fontFamily: 'monospace', fontWeight: 700, color: C.text }, children: [v, " ", _jsx("span", { style: { color: C.muted, fontWeight: 400 }, children: u })] })] }, l)))] })), result.summary && (_jsxs("div", { style: { background: C.panel, border: `1px solid ${C.border}`,
                                    borderRadius: 8, padding: 12 }, children: [_jsx("div", { style: { fontSize: 10, fontWeight: 800, color: C.accent,
                                            letterSpacing: '0.08em', marginBottom: 8 }, children: "\uD83D\uDCCA SUMMARY" }), Object.entries(result.summary).map(([k, v]) => (_jsxs("div", { style: { display: 'flex', justifyContent: 'space-between',
                                            borderBottom: `1px solid ${C.border}`, padding: '3px 0', fontSize: 11 }, children: [_jsx("span", { style: { color: C.muted }, children: k.replace(/_/g, ' ') }), _jsx("span", { style: { fontFamily: 'monospace', fontWeight: 700, color: C.text }, children: typeof v === 'number' ? v.toFixed(3) : String(v) })] }, k)))] })), result.history?.length > 0 && (_jsxs("div", { style: { background: C.panel, border: `1px solid ${C.border}`,
                                    borderRadius: 8, padding: 12 }, children: [_jsx("div", { style: { fontSize: 10, fontWeight: 800, color: C.accent,
                                            letterSpacing: '0.08em', marginBottom: 8 }, children: "\uD83D\uDCC8 AXIAL PROFILE \u2014 inlet / mid / outlet" }), _jsx("div", { style: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }, children: [0, Math.floor(result.history.length / 2), result.history.length - 1].map(i => {
                                            const seg = result.history[i];
                                            return (_jsxs("div", { style: { background: '#081321', borderRadius: 6, padding: 8 }, children: [_jsxs("div", { style: { fontSize: 9, color: C.muted, marginBottom: 6, fontWeight: 700 }, children: ["x = ", seg.x, " m"] }), Object.entries(seg).filter(([k]) => k !== 'x').map(([k, v]) => (_jsxs("div", { style: { display: 'flex', justifyContent: 'space-between', fontSize: 10, padding: '1px 0' }, children: [_jsx("span", { style: { color: C.muted }, children: k }), _jsx("span", { style: { fontFamily: 'monospace', color: C.text }, children: typeof v === 'number' ? v.toFixed(2) : String(v) })] }, k)))] }, i));
                                        }) })] }))] })), !result && !loading && !error && (_jsx("div", { style: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
                            color: C.muted, fontSize: 13 }, children: "Configure inputs \u2192 click Run Calculation" }))] })] }));
}
