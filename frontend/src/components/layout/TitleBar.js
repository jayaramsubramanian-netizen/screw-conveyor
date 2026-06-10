import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/**
 * TitleBar.tsx
 * Top strip (26px). Shows:
 *   Left:  VECTRIX™ logo + brand
 *   Centre: active module name with icon (replaces the old second tab row)
 *   Right: v2.5.0
 */
import React from 'react';
import { PAGE_META } from '../../App';
function VectrixLogo() {
    return (_jsxs("svg", { width: "20", height: "20", viewBox: "0 0 22 22", fill: "none", style: { flexShrink: 0 }, children: [_jsx("circle", { cx: "11", cy: "11", r: "10", stroke: "#e8a000", strokeWidth: "1.5", fill: "none" }), _jsx("path", { d: "M5 11 L11 5 L17 11 L11 17 Z", fill: "#e8a000", fillOpacity: "0.15", stroke: "#e8a000", strokeWidth: "1.2" }), _jsx("circle", { cx: "11", cy: "11", r: "3.5", fill: "#e8a000" }), [[-10, 0], [10, 0], [0, -10], [0, 10]].map(([dx, dy], i) => (_jsx("line", { x1: 11, y1: 11, x2: 11 + dx, y2: 11 + dy, stroke: "#e8a000", strokeWidth: "1.2", opacity: "0.6" }, i)))] }));
}
export default function TitleBar({ page }) {
    const meta = PAGE_META[page];
    return (_jsxs("div", { style: {
            display: 'flex', alignItems: 'center', gap: 10,
            background: '#060f1c', borderBottom: '1px solid #0d1e30',
            padding: '0 12px', flexShrink: 0, height: 26, userSelect: 'none',
        }, children: [_jsx(VectrixLogo, {}), _jsx("span", { style: { fontSize: 11, fontWeight: 800, color: '#e8a000', letterSpacing: '0.10em' }, children: "VECTRIX\u2122" }), _jsx("span", { style: { color: '#1c3048', fontSize: 11, flexShrink: 0 }, children: "|" }), _jsx("span", { style: { fontSize: 10, color: '#3a5470', letterSpacing: '0.06em', flexShrink: 0 }, children: "A Jayveecons Engineering Platform" }), _jsx("div", { style: { flex: 1 } }), _jsxs("div", { style: {
                    display: 'flex', alignItems: 'center', gap: 6,
                    background: 'rgba(232,160,0,0.07)', border: '1px solid rgba(232,160,0,0.18)',
                    borderRadius: 4, padding: '0 10px', height: 18,
                }, children: [_jsx("span", { style: { fontSize: 11 }, children: meta.icon }), _jsx("span", { style: { fontSize: 10, fontWeight: 700, color: '#e8a000', letterSpacing: '0.06em' }, children: meta.label })] }), _jsx("div", { style: { width: 16 } }), _jsx("span", { style: { fontSize: 9, color: '#3a5470', letterSpacing: '0.06em', flexShrink: 0 }, children: "v2.5.0" })] }));
}
