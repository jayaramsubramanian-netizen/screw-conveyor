import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/**
 * MenuBar.tsx — Windows-style pull-down menu bar.
 * All navigation lives here. No second tab row anywhere.
 * Active page highlighted in the menu labels.
 */
import React, { useState, useRef, useEffect } from 'react';
import { PAGE_META } from '../../App';
export default function MenuBar({ page, setPage, onNewProject, onShowAbout, onShowShortcuts }) {
    const [open, setOpen] = useState(null);
    const ref = useRef(null);
    useEffect(() => {
        const h = (e) => {
            if (ref.current && !ref.current.contains(e.target))
                setOpen(null);
        };
        document.addEventListener('mousedown', h);
        return () => document.removeEventListener('mousedown', h);
    }, []);
    const toggle = (id) => setOpen(o => o === id ? null : id);
    const close = () => setOpen(null);
    // Styled menu item button
    const Item = ({ pageId, label, action, disabled = false, }) => {
        const isActive = pageId !== undefined && page === pageId;
        return (_jsxs("button", { disabled: disabled, onClick: () => { action(); close(); }, style: {
                display: 'flex', alignItems: 'center', gap: 8,
                width: '100%', textAlign: 'left',
                padding: '5px 16px', background: isActive ? 'rgba(232,160,0,0.10)' : 'transparent',
                border: 'none', fontSize: 12, cursor: disabled ? 'default' : 'pointer',
                fontFamily: 'inherit', whiteSpace: 'nowrap',
                color: disabled ? '#3a5470' : isActive ? '#e8a000' : '#ddeaf6',
                borderLeft: isActive ? '2px solid #e8a000' : '2px solid transparent',
            }, onMouseOver: e => { if (!disabled)
                e.currentTarget.style.background = '#17304d'; }, onMouseOut: e => {
                e.currentTarget.style.background = isActive ? 'rgba(232,160,0,0.10)' : 'transparent';
            }, children: [pageId && _jsx("span", { style: { fontSize: 12, width: 16 }, children: PAGE_META[pageId].icon }), _jsx("span", { children: label }), isActive && _jsx("span", { style: { marginLeft: 'auto', fontSize: 9, color: '#e8a000', paddingLeft: 12 }, children: "\u25CF" })] }));
    };
    const Div = () => _jsx("div", { style: { height: 1, background: '#1c3048', margin: '3px 0' } });
    const Menu = ({ id, label, children }) => (_jsxs("div", { style: { position: 'relative' }, children: [_jsx("button", { onClick: () => toggle(id), style: {
                    padding: '3px 10px',
                    background: open === id ? '#17304d' : 'transparent',
                    border: 'none', color: '#ddeaf6', fontSize: 12,
                    cursor: 'pointer', fontFamily: 'inherit', borderRadius: 2,
                }, onMouseOver: () => { if (open && open !== id)
                    setOpen(id); }, children: label }), open === id && (_jsx("div", { style: {
                    position: 'absolute', top: '100%', left: 0, minWidth: 240,
                    zIndex: 2000, background: '#101e30',
                    border: '1px solid #2a4a72', borderRadius: 4,
                    boxShadow: '0 8px 32px rgba(0,0,0,.6)', padding: '4px 0',
                }, children: children }))] }));
    return (_jsxs("div", { ref: ref, style: {
            display: 'flex', alignItems: 'center', gap: 2,
            background: '#081321', borderBottom: '1px solid #1c3048',
            padding: '2px 8px', flexShrink: 0, height: 28,
        }, children: [_jsxs(Menu, { id: "file", label: "File", children: [_jsx(Item, { label: "New Design / Project\u2026", action: onNewProject }), _jsx(Item, { label: "Clear & Reload", action: () => { if (confirm('Clear and reload?'))
                            window.location.reload(); } }), _jsx(Div, {}), _jsx(Item, { label: "Print Report\u2026", action: () => window.print() }), _jsx(Div, {}), _jsx(Item, { label: "Close", action: () => { if (confirm('Close?'))
                            window.close(); } })] }), _jsxs(Menu, { id: "conveyor", label: "Conveyor", children: [_jsx(Item, { pageId: "calc", label: "Screw Conveyor Calculator", action: () => setPage('calc') }), _jsx(Item, { pageId: "family", label: "Family Designer", action: () => setPage('family') })] }), _jsxs(Menu, { id: "process", label: "Process", children: [_jsx(Item, { pageId: "mixer", label: "Screw Mixer", action: () => setPage('mixer') }), _jsx(Item, { pageId: "dryer", label: "Screw Dryer", action: () => setPage('dryer') }), _jsx(Item, { pageId: "cooler", label: "Screw Cooler", action: () => setPage('cooler') }), _jsx(Item, { pageId: "separator", label: "Separator", action: () => setPage('separator') }), _jsx(Item, { pageId: "reactor", label: "Screw Reactor", action: () => setPage('reactor') }), _jsx(Item, { pageId: "compactor", label: "Compactor", action: () => setPage('compactor') })] }), _jsxs(Menu, { id: "data", label: "Database", children: [_jsx(Item, { pageId: "db", label: "Material Database", action: () => setPage('db') }), _jsx(Item, { pageId: "help", label: "User Manual", action: () => setPage('help') })] }), _jsxs(Menu, { id: "help", label: "Help", children: [_jsx(Item, { label: "Keyboard Shortcuts", action: onShowShortcuts }), _jsx(Div, {}), _jsx(Item, { label: "About VECTRIX\u2122", action: onShowAbout })] })] }));
}
