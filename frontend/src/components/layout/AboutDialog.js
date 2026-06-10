import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import React from 'react';
export default function AboutDialog({ onClose }) {
    return (_jsx("div", { style: {
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,.7)', zIndex: 3000,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
        }, onClick: onClose, children: _jsxs("div", { onClick: e => e.stopPropagation(), style: {
                background: '#101e30', border: '1px solid #2a4a72', borderRadius: 8,
                padding: '28px 36px', minWidth: 380, textAlign: 'center',
                boxShadow: '0 16px 64px rgba(0,0,0,.8)',
            }, children: [_jsx("div", { style: { fontSize: 22, fontWeight: 800, color: '#e8a000', letterSpacing: '0.08em' }, children: "VECTRIX\u2122" }), _jsx("div", { style: { fontSize: 11, color: '#5d7d99', letterSpacing: '0.12em', marginTop: 2 }, children: "SCREW CONVEYOR CALCULATOR" }), _jsx("div", { style: { fontSize: 10, color: '#3a5470', marginTop: 4 }, children: "Version 2.5.0" }), _jsx("div", { style: { margin: '16px 0', height: 1, background: '#1c3048' } }), _jsxs("div", { style: { fontSize: 11, color: '#5d7d99', lineHeight: 1.8 }, children: ["A Jayveecons Engineering Platform", _jsx("br", {}), "Screw Conveyor \u00B7 Process Modules \u00B7 Material Database", _jsx("br", {}), "Powered by VECTOMEC\u2122 Engineering Intelligence"] }), _jsx("div", { style: { margin: '16px 0', height: 1, background: '#1c3048' } }), _jsxs("div", { style: { fontSize: 10, color: '#3a5470', lineHeight: 1.6 }, children: ["For engineering reference only.", _jsx("br", {}), "Verify all results before fabrication."] }), _jsx("button", { onClick: onClose, style: {
                        marginTop: 16, padding: '6px 28px', borderRadius: 4,
                        background: 'rgba(232,160,0,.12)', border: '1px solid #e8a000',
                        color: '#e8a000', cursor: 'pointer', fontSize: 12, fontWeight: 700,
                    }, children: "Close" })] }) }));
}
