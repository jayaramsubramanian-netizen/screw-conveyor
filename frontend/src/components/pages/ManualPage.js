import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import React, { useState } from 'react';
const MANUAL_URL = '/manual.html'; // served from public/ in production; proxy in dev
export default function ManualPage() {
    const [loaded, setLoaded] = useState(false);
    return (_jsxs("div", { style: { height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column', background: '#0b1522' }, children: [!loaded && (_jsxs("div", { style: { display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flex: 1, background: '#0b1522', gap: 12 }, children: [_jsx("div", { style: { width: 22, height: 22, border: '3px solid #e8a000',
                            borderTopColor: 'transparent', borderRadius: '50%',
                            animation: 'spin 0.8s linear infinite' } }), _jsx("span", { style: { color: '#5d7d99', fontSize: 12 }, children: "Loading VECTRIX\u2122 Manual\u2026" }), _jsx("style", { children: `@keyframes spin{to{transform:rotate(360deg)}}` })] })), _jsx("iframe", { src: MANUAL_URL, onLoad: () => setLoaded(true), style: { flex: 1, border: 'none', width: '100%', height: '100%',
                    display: loaded ? 'block' : 'none' }, title: "VECTRIX\u2122 Engineering Manual" })] }));
}
