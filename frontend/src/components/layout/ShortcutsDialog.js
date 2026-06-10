import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import React from 'react';
const SHORTCUTS = [
    ['Alt+1', 'Calculator'],
    ['Alt+2', 'Family Designer'],
    ['Alt+3', 'Process Modules'],
    ['Alt+4', 'Database'],
    ['Alt+5', 'User Manual'],
    ['Escape', 'Close dialogs'],
];
export default function ShortcutsDialog({ onClose }) {
    return (_jsx("div", { style: {
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,.7)', zIndex: 3000,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
        }, onClick: onClose, children: _jsxs("div", { onClick: e => e.stopPropagation(), style: {
                background: '#101e30', border: '1px solid #2a4a72', borderRadius: 8,
                padding: '24px 32px', minWidth: 320, boxShadow: '0 16px 64px rgba(0,0,0,.8)',
            }, children: [_jsx("div", { style: { fontSize: 13, fontWeight: 800, color: '#ddeaf6', marginBottom: 16 }, children: "Keyboard Shortcuts" }), SHORTCUTS.map(([k, d]) => (_jsxs("div", { style: {
                        display: 'flex', justifyContent: 'space-between',
                        padding: '5px 0', borderBottom: '1px solid #1c3048', gap: 24,
                    }, children: [_jsx("code", { style: {
                                fontSize: 11, color: '#e8a000', background: 'rgba(232,160,0,.08)',
                                padding: '1px 6px', borderRadius: 3, border: '1px solid rgba(232,160,0,.2)',
                            }, children: k }), _jsx("span", { style: { fontSize: 11, color: '#5d7d99' }, children: d })] }, k))), _jsx("button", { onClick: onClose, style: {
                        marginTop: 16, padding: '5px 20px', borderRadius: 4,
                        background: 'rgba(74,158,255,.1)', border: '1px solid #4a9eff',
                        color: '#4a9eff', cursor: 'pointer', fontSize: 11, fontWeight: 700,
                    }, children: "Close" })] }) }));
}
