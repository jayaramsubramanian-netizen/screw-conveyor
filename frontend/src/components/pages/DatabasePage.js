import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
/**
 * DatabasePage.tsx — Full 6-tab database with CRUD on every table.
 *
 * Tabs: Materials | Process Apps | Gearboxes | Motors | Drives | Costs
 *
 * KEY FEATURE: Applications column on Materials shows module coverage.
 * Each app badge is GREEN if the material has the required fields for that module,
 * AMBER if partial, RED/grey if missing critical fields.
 * This tells the user which modules will work for this material,
 * and which need the material record to be completed first.
 */
import React, { useState } from 'react';
import axios from 'axios';
import { useQueryClient, useQuery } from '@tanstack/react-query';
import { useMaterials, useCategories, useBearings, useGearboxes, useCalcStore } from '../../hooks/useCalculator';
const C = {
    panel: '#101e30', border: '#1c3048', text: '#ddeaf6',
    muted: '#5d7d99', faint: '#3a5470', accent: '#e8a000',
    green: '#1fb86e', red: '#e05252', amber: '#d98e00', blue: '#4a9eff',
    teal: '#2dd4bf', purple: '#a78bfa',
};
const ss = (s) => s;
// ── Application module definitions and required fields ────────────
const APP_DEFS = {
    conv: { label: 'Conveyor', icon: '🔩', col: C.blue,
        required: ['rho', 'fill_max', 'lambda_ref'],
        recommended: ['flowability', 'abr', 'cls', 'moist'] },
    dry: { label: 'Dryer', icon: '🌡️', col: '#e8a000',
        required: ['rho', 'moist', 'temp_max'],
        recommended: ['fill_max', 'flowability'] },
    cool: { label: 'Cooler', icon: '❄️', col: C.teal,
        required: ['rho', 'temp_max'],
        recommended: ['fill_max'] },
    mix: { label: 'Mixer', icon: '🌀', col: C.purple,
        required: ['rho', 'fill_max'],
        recommended: ['flowability', 'particle_class'] },
    sep: { label: 'Separator', icon: '🔀', col: C.green,
        required: ['rho', 'particle_class'],
        recommended: ['flowability'] },
    react: { label: 'Reactor', icon: '⚗️', col: '#a78bfa',
        required: ['rho', 'temp_max'],
        recommended: ['fill_max', 'flowability'] },
    compact: { label: 'Compactor', icon: '🗜️', col: C.red,
        required: ['rho', 'bridging_risk'],
        recommended: ['fill_max', 'flowability'] },
    feed: { label: 'Feeder', icon: '⚖️', col: '#d98e00',
        required: ['rho', 'fill_max', 'flowability'],
        recommended: ['bridging_risk', 'cohesion'] },
};
function AppCoverage({ mat }) {
    const apps = mat.app || [];
    if (apps.length === 0)
        return _jsx("span", { style: ss({ color: C.faint, fontSize: 9 }), children: "\u2014" });
    return (_jsx("div", { style: ss({ display: 'flex', flexWrap: 'wrap', gap: 2 }), children: apps.map(appId => {
            const def = APP_DEFS[appId];
            if (!def)
                return null;
            const missingReq = def.required.filter(f => mat[f] == null || mat[f] === '');
            const missingRec = def.recommended.filter(f => mat[f] == null || mat[f] === '');
            const status = missingReq.length > 0 ? 'missing' : missingRec.length > 0 ? 'partial' : 'ok';
            const bgCol = status === 'ok' ? def.col + '22'
                : status === 'partial' ? C.amber + '22'
                    : C.red + '22';
            const borderCol = status === 'ok' ? def.col + '88'
                : status === 'partial' ? C.amber + '88'
                    : C.red + '88';
            const textCol = status === 'ok' ? def.col
                : status === 'partial' ? C.amber
                    : C.red;
            const tooltip = status === 'ok'
                ? `${def.label}: all required fields present`
                : status === 'partial'
                    ? `${def.label}: recommended fields missing: ${missingRec.join(', ')}`
                    : `${def.label}: REQUIRED fields missing: ${missingReq.join(', ')}`;
            return (_jsxs("span", { title: tooltip, style: ss({
                    display: 'inline-flex', alignItems: 'center', gap: 2,
                    padding: '1px 5px', borderRadius: 3, fontSize: 9, fontWeight: 700,
                    background: bgCol, border: `1px solid ${borderCol}`, color: textCol,
                    cursor: 'default', whiteSpace: 'nowrap',
                }), children: [def.icon, " ", def.label, status === 'missing' && _jsx("span", { style: ss({ fontSize: 8 }), children: "\u26A0" })] }, appId));
        }) }));
}
// ── Flags column ──────────────────────────────────────────────────
const FLAG_META = {
    L: { label: 'Lumpy', col: C.amber },
    M: { label: 'Moist', col: C.blue },
    O: { label: 'Oily', col: '#d98e00' },
    U: { label: 'Dusty', col: C.purple },
    X: { label: 'Explosive', col: C.red },
};
function FlagsCell({ flags }) {
    if (!flags)
        return _jsx("span", { style: ss({ color: C.faint, fontSize: 9 }), children: "\u2014" });
    return (_jsx("div", { style: ss({ display: 'flex', gap: 2 }), children: flags.split('').map(f => {
            const meta = FLAG_META[f];
            return meta ? (_jsx("span", { title: meta.label, style: ss({
                    display: 'inline-block', padding: '1px 4px', borderRadius: 3,
                    fontSize: 9, fontWeight: 800, background: meta.col + '22',
                    border: `1px solid ${meta.col}55`, color: meta.col,
                }), children: f }, f)) : null;
        }) }));
}
// ── Shared form field ─────────────────────────────────────────────
function FInput({ label, value, onChange, type = 'text', step, placeholder }) {
    return (_jsxs("div", { style: ss({ marginBottom: 8 }), children: [_jsx("div", { style: ss({ fontSize: 10, color: C.muted, fontWeight: 700,
                    textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 3 }), children: label }), _jsx("input", { type: type, value: value, step: step, placeholder: placeholder, onChange: e => onChange(e.target.value), style: ss({ width: '100%', background: '#081321', border: `1px solid ${C.border}`,
                    borderRadius: 4, padding: '5px 8px', color: C.text, fontSize: 11,
                    fontFamily: type === 'number' ? 'monospace' : 'inherit',
                    outline: 'none', boxSizing: 'border-box' }) })] }));
}
function FSelect({ label, value, onChange, options }) {
    return (_jsxs("div", { style: ss({ marginBottom: 8 }), children: [_jsx("div", { style: ss({ fontSize: 10, color: C.muted, fontWeight: 700,
                    textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 3 }), children: label }), _jsx("select", { value: value, onChange: e => onChange(e.target.value), style: ss({ width: '100%', background: '#081321', border: `1px solid ${C.border}`,
                    borderRadius: 4, padding: '5px 8px', color: C.text, fontSize: 11,
                    fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box' }), children: options.map(o => _jsx("option", { value: o, children: o }, o)) })] }));
}
// ── Generic modal wrapper ─────────────────────────────────────────
function Modal({ title, icon, onClose, onSave, saving, error, children }) {
    return (_jsx("div", { style: ss({ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.75)',
            zIndex: 3000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }), children: _jsxs("div", { style: ss({ background: C.panel, border: '1px solid #2a4a72', borderRadius: 8,
                width: '100%', maxWidth: 620, maxHeight: '90vh', display: 'flex', flexDirection: 'column',
                boxShadow: '0 24px 80px rgba(0,0,0,.8)' }), children: [_jsxs("div", { style: ss({ display: 'flex', alignItems: 'center', gap: 10,
                        padding: '14px 20px', borderBottom: `1px solid ${C.border}` }), children: [_jsx("span", { style: ss({ fontSize: 16 }), children: icon }), _jsx("span", { style: ss({ fontWeight: 800, fontSize: 13, color: C.text, flex: 1 }), children: title }), _jsx("button", { onClick: onClose, style: ss({ padding: '4px 10px', borderRadius: 4,
                                border: `1px solid ${C.border}`, background: 'transparent',
                                color: C.muted, cursor: 'pointer', fontSize: 11 }), children: "\u2715" })] }), _jsx("div", { style: ss({ overflowY: 'auto', padding: '16px 20px',
                        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }), children: children }), error && (_jsx("div", { style: ss({ margin: '0 20px', padding: '5px 10px', fontSize: 11,
                        color: C.red, background: 'rgba(224,82,82,.08)', borderRadius: 4 }), children: error })), _jsxs("div", { style: ss({ display: 'flex', justifyContent: 'flex-end', gap: 8,
                        padding: '12px 20px', borderTop: `1px solid ${C.border}` }), children: [_jsx("button", { onClick: onClose, style: ss({ padding: '7px 20px', borderRadius: 4,
                                border: `1px solid ${C.border}`, background: 'transparent',
                                color: C.muted, cursor: 'pointer', fontSize: 12 }), children: "Cancel" }), _jsx("button", { onClick: onSave, disabled: saving, style: ss({ padding: '7px 24px', borderRadius: 4,
                                border: `1px solid ${C.accent}`, background: 'rgba(232,160,0,.12)',
                                color: C.accent, cursor: 'pointer', fontSize: 12, fontWeight: 700 }), children: saving ? 'Saving…' : '✓ Save' })] })] }) }));
}
// ── Delete confirm ────────────────────────────────────────────────
function DeleteConfirm({ name, onConfirm, onCancel }) {
    return (_jsx("div", { style: ss({ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.7)',
            zIndex: 3000, display: 'flex', alignItems: 'center', justifyContent: 'center' }), children: _jsxs("div", { style: ss({ background: C.panel, border: '1px solid #2a4a72', borderRadius: 8,
                padding: '24px 32px', minWidth: 340, boxShadow: '0 16px 64px rgba(0,0,0,.8)' }), children: [_jsx("div", { style: ss({ fontSize: 13, fontWeight: 800, color: C.text, marginBottom: 8 }), children: "Confirm Delete" }), _jsxs("div", { style: ss({ fontSize: 11, color: C.muted, marginBottom: 20 }), children: ["Remove ", _jsx("strong", { style: ss({ color: C.text }), children: name }), "? This cannot be undone."] }), _jsxs("div", { style: ss({ display: 'flex', gap: 8, justifyContent: 'flex-end' }), children: [_jsx("button", { onClick: onCancel, style: ss({ padding: '6px 20px', borderRadius: 4,
                                border: `1px solid ${C.border}`, background: 'transparent',
                                color: C.muted, cursor: 'pointer', fontSize: 12 }), children: "Cancel" }), _jsx("button", { onClick: onConfirm, style: ss({ padding: '6px 20px', borderRadius: 4,
                                border: `1px solid ${C.red}`, background: 'rgba(224,82,82,.12)',
                                color: C.red, cursor: 'pointer', fontSize: 12, fontWeight: 700 }), children: "Delete" })] })] }) }));
}
// ── Table header ──────────────────────────────────────────────────
function TH({ children }) {
    return _jsx("th", { style: ss({ padding: '6px 10px', textAlign: 'left', color: C.muted,
            fontWeight: 700, borderBottom: `1px solid ${C.border}`, whiteSpace: 'nowrap',
            fontSize: 11, background: '#081321' }), children: children });
}
function TD({ children, mono = false, faint = false }) {
    return _jsx("td", { style: ss({ padding: '5px 10px', fontFamily: mono ? 'monospace' : 'inherit',
            color: faint ? C.faint : C.text, fontSize: 11 }), children: children });
}
function CustomBadge() {
    return _jsx("span", { style: ss({ marginLeft: 5, fontSize: 8, color: C.blue,
            background: 'rgba(74,158,255,.12)', border: '1px solid rgba(74,158,255,.3)',
            borderRadius: 3, padding: '1px 4px' }), children: "CUSTOM" });
}
function ActionBtns({ isCustom, onEdit, onDelete }) {
    return (_jsxs("div", { style: ss({ display: 'flex', gap: 4 }), children: [_jsx("button", { onClick: onEdit, style: ss({ fontSize: 9, padding: '2px 7px', borderRadius: 3,
                    border: `1px solid ${C.blue}`, background: 'transparent',
                    color: C.blue, cursor: 'pointer' }), children: "\u270F\uFE0F Edit" }), isCustom && onDelete && (_jsx("button", { onClick: onDelete, style: ss({ fontSize: 9, padding: '2px 7px', borderRadius: 3,
                    border: `1px solid ${C.red}`, background: 'transparent',
                    color: C.red, cursor: 'pointer' }), children: "\uD83D\uDDD1" }))] }));
}
// ═════════════════════════════════════════════════════════════════
// MATERIAL FORM
// ═════════════════════════════════════════════════════════════════
const EMPTY_MAT = {
    name: '', category: '', rho: '', rho_min: '', rho_max: '',
    lambda_ref: '', fill_max: '', abr: 'Low', cls: 'I',
    particle_class: 'B6', flowability: '2',
    moist: '', aor: '', cohesion: '', temp_max: '', bridging_risk: '',
    flags: '', note: '',
    app: [],
};
function MaterialFormModal({ initial, onSave, onClose, title }) {
    const [form, setForm] = useState({ ...EMPTY_MAT, ...(initial || {}) });
    const [saving, setSaving] = useState(false);
    const [err, setErr] = useState('');
    const set = (k) => (v) => setForm(p => ({ ...p, [k]: v }));
    const toggleApp = (id) => setForm(p => ({
        ...p,
        app: p.app.includes(id) ? p.app.filter(a => a !== id) : [...p.app, id],
    }));
    const handleSave = async () => {
        if (!form.name) {
            setErr('Name is required');
            return;
        }
        setSaving(true);
        setErr('');
        try {
            await onSave({
                name: form.name, category: form.category || null,
                rho: parseFloat(form.rho) || 1.0,
                rho_min: parseFloat(form.rho_min) || null,
                rho_max: parseFloat(form.rho_max) || null,
                lambda_ref: parseFloat(form.lambda_ref) || null,
                fill_max: parseFloat(form.fill_max) || 0.30,
                abr: form.abr, cls: form.cls,
                particle_class: form.particle_class || null,
                flowability: parseInt(form.flowability) || null,
                moist: parseFloat(form.moist) || 0,
                aor: parseFloat(form.aor) || null,
                cohesion: parseFloat(form.cohesion) || null,
                temp_max: parseFloat(form.temp_max) || null,
                bridging_risk: parseFloat(form.bridging_risk) || null,
                flags: form.flags || null,
                app: form.app,
                note: form.note || null,
            });
        }
        catch (e) {
            setErr(e?.response?.data?.detail || e?.message || 'Save failed');
        }
        finally {
            setSaving(false);
        }
    };
    return (_jsx(Modal, { title: title, icon: "\uD83E\uDDEA", onClose: onClose, onSave: handleSave, saving: saving, error: err, children: _jsxs("div", { style: ss({ gridColumn: '1/-1', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }), children: [_jsx(FInput, { label: "Name *", value: form.name, onChange: set('name') }), _jsx(FInput, { label: "Category", value: form.category, onChange: set('category') }), _jsx(FInput, { label: "Bulk Density \u03C1 (t/m\u00B3)", value: form.rho, onChange: set('rho'), type: "number", step: "0.01" }), _jsx(FInput, { label: "\u03C1_min", value: form.rho_min, onChange: set('rho_min'), type: "number", step: "0.01" }), _jsx(FInput, { label: "\u03C1_max", value: form.rho_max, onChange: set('rho_max'), type: "number", step: "0.01" }), _jsx(FInput, { label: "\u03BB_ref", value: form.lambda_ref, onChange: set('lambda_ref'), type: "number", step: "0.01" }), _jsx(FInput, { label: "Fill max", value: form.fill_max, onChange: set('fill_max'), type: "number", step: "0.01" }), _jsx(FInput, { label: "Moisture %", value: form.moist, onChange: set('moist'), type: "number", step: "0.1" }), _jsx(FInput, { label: "Angle of Repose \u00B0", value: form.aor, onChange: set('aor'), type: "number", step: "1" }), _jsx(FInput, { label: "Cohesion (kPa)", value: form.cohesion, onChange: set('cohesion'), type: "number", step: "0.1" }), _jsx(FInput, { label: "Max Temp \u00B0C", value: form.temp_max, onChange: set('temp_max'), type: "number", step: "5" }), _jsx(FInput, { label: "Bridging Risk (0\u20131)", value: form.bridging_risk, onChange: set('bridging_risk'), type: "number", step: "0.05" }), _jsx(FInput, { label: "Flags (e.g. OUX)", value: form.flags, onChange: set('flags') }), _jsx(FInput, { label: "Note", value: form.note, onChange: set('note') }), _jsx(FSelect, { label: "Abrasiveness", value: form.abr, onChange: set('abr'), options: ['Low', 'Medium', 'High', 'Very High'] }), _jsx(FSelect, { label: "CEMA Class", value: form.cls, onChange: set('cls'), options: ['I', 'II', 'III', 'IV'] }), _jsx(FSelect, { label: "Particle Class", value: form.particle_class, onChange: set('particle_class'), options: ['A200', 'A100', 'A40', 'B6', 'C1/2', 'D3', 'D7'] }), _jsx(FSelect, { label: "Flowability", value: form.flowability, onChange: set('flowability'), options: ['1', '2', '3', '4'] }), _jsxs("div", { style: ss({ gridColumn: '1/-1', marginBottom: 8 }), children: [_jsx("div", { style: ss({ fontSize: 10, color: C.muted, fontWeight: 700,
                                textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }), children: "Applications (tick modules this material is validated for)" }), _jsx("div", { style: ss({ display: 'flex', flexWrap: 'wrap', gap: 6 }), children: Object.entries(APP_DEFS).map(([id, def]) => {
                                const active = form.app.includes(id);
                                return (_jsxs("button", { onClick: () => toggleApp(id), type: "button", style: ss({
                                        padding: '4px 10px', borderRadius: 4, cursor: 'pointer', fontSize: 10,
                                        fontFamily: 'inherit', fontWeight: 700,
                                        border: `1px solid ${active ? def.col : C.border}`,
                                        background: active ? def.col + '22' : 'transparent',
                                        color: active ? def.col : C.muted,
                                    }), children: [def.icon, " ", def.label] }, id));
                            }) })] })] }) }));
}
export default function DatabasePage({ setPage }) {
    const [tab, setTab] = useState('materials');
    const [search, setSearch] = useState('');
    const [cat, setCat] = useState('');
    const [modal, setModal] = useState(null);
    const [delTarget, setDelTarget] = useState(null);
    const [msg, setMsg] = useState(null);
    const { data: cats } = useCategories();
    const { data: mats, isLoading: mL } = useMaterials({ search: search || undefined, category: cat || undefined });
    const { data: bearings, isLoading: bL } = useBearings();
    const { data: gearboxes, isLoading: gL } = useGearboxes();
    const { data: motors, isLoading: moL } = useQuery({ queryKey: ['motors'], queryFn: () => axios.get('/api/v1/motors').then(r => r.data), staleTime: 60000 });
    const { data: drives, isLoading: dL } = useQuery({ queryKey: ['drives'], queryFn: () => axios.get('/api/v1/drives').then(r => r.data), staleTime: 60000 });
    const { data: costs, isLoading: cL } = useQuery({ queryKey: ['costs'], queryFn: () => axios.get('/api/v1/costs').then(r => r.data), staleTime: 60000 });
    const { setInp } = useCalcStore();
    const qc = useQueryClient();
    const flash = (text, ok = true) => { setMsg({ text, ok }); setTimeout(() => setMsg(null), 3500); };
    const inv = (key) => qc.invalidateQueries({ queryKey: [key] });
    // ── Generic save dispatcher ────────────────────────────────────
    const handleSave = async (data) => {
        const isEdit = modal?.mode === 'edit';
        try {
            if (tab === 'materials') {
                if (isEdit)
                    await axios.put(`/api/v1/materials/${encodeURIComponent(modal.row.name)}`, data);
                else
                    await axios.post('/api/v1/materials', data);
                inv('materials');
            }
            else if (tab === 'gearboxes') {
                if (isEdit)
                    await axios.put(`/api/v1/gearboxes/${encodeURIComponent(modal.row.model)}`, data);
                else
                    await axios.post('/api/v1/gearboxes', data);
                inv('gearboxes');
            }
            else if (tab === 'motors') {
                if (isEdit)
                    await axios.put(`/api/v1/motors/${encodeURIComponent(modal.row.model)}`, data);
                else
                    await axios.post('/api/v1/motors', data);
                inv('motors');
            }
            else if (tab === 'drives') {
                if (isEdit)
                    await axios.put(`/api/v1/drives/${encodeURIComponent(modal.row.model)}`, data);
                else
                    await axios.post('/api/v1/drives', data);
                inv('drives');
            }
            else if (tab === 'costs') {
                if (isEdit)
                    await axios.put(`/api/v1/costs/${encodeURIComponent(modal.row.item)}`, data);
                else
                    await axios.post('/api/v1/costs', data);
                inv('costs');
            }
            else if (tab === 'process' || tab === 'materials') {
                // bearings (shown in process tab)
                if (isEdit)
                    await axios.put(`/api/v1/bearings/${encodeURIComponent(modal.row.name)}`, data);
                else
                    await axios.post('/api/v1/bearings', data);
                inv('bearings');
            }
            flash(`✓ ${isEdit ? 'Updated' : 'Added'} successfully`);
            setModal(null);
        }
        catch (e) {
            throw new Error(e?.response?.data?.detail || e?.message || 'Save failed');
        }
    };
    // ── Generic delete dispatcher ──────────────────────────────────
    const handleDelete = async () => {
        if (!delTarget)
            return;
        try {
            if (tab === 'materials')
                await axios.delete(`/api/v1/materials/${encodeURIComponent(delTarget)}`);
            else if (tab === 'gearboxes')
                await axios.delete(`/api/v1/gearboxes/${encodeURIComponent(delTarget)}`);
            else if (tab === 'motors')
                await axios.delete(`/api/v1/motors/${encodeURIComponent(delTarget)}`);
            else if (tab === 'drives')
                await axios.delete(`/api/v1/drives/${encodeURIComponent(delTarget)}`);
            else if (tab === 'costs')
                await axios.delete(`/api/v1/costs/${encodeURIComponent(delTarget)}`);
            else if (tab === 'process')
                await axios.delete(`/api/v1/bearings/${encodeURIComponent(delTarget)}`);
            const keys = { materials: 'materials', process: 'bearings',
                gearboxes: 'gearboxes', motors: 'motors', drives: 'drives', costs: 'costs' };
            inv(keys[tab]);
            flash(`✓ Deleted '${delTarget}'`);
        }
        catch (e) {
            flash(e?.response?.data?.detail || 'Delete failed', false);
        }
        setDelTarget(null);
    };
    // ── Tab button ─────────────────────────────────────────────────
    const Tb = (id, label) => (_jsx("button", { onClick: () => setTab(id), style: ss({
            padding: '6px 14px', border: 'none',
            borderBottom: tab === id ? `2px solid ${C.accent}` : '2px solid transparent',
            background: tab === id ? '#101e30' : 'transparent',
            color: tab === id ? C.accent : C.muted,
            fontWeight: tab === id ? 800 : 600, fontSize: 11,
            cursor: 'pointer', fontFamily: 'inherit', letterSpacing: '0.04em', whiteSpace: 'nowrap',
        }), children: label }, id));
    // ── Shared table wrapper ───────────────────────────────────────
    const TableWrap = ({ loading, empty, children }) => (_jsxs("div", { style: ss({ flex: 1, overflowY: 'auto', border: `1px solid ${C.border}`, borderRadius: 6 }), children: [loading && _jsx("div", { style: ss({ padding: 16, color: C.muted, fontSize: 11 }), children: "Loading\u2026" }), !loading && empty && (_jsxs("div", { style: ss({ padding: 24, textAlign: 'center', color: C.muted, fontSize: 11 }), children: ["No records found. Run ", _jsx("code", { children: "python -m backend.db.seed" })] })), !loading && !empty && children] }));
    return (_jsxs("div", { style: ss({ display: 'flex', flexDirection: 'column', height: '100%', padding: 12, gap: 8 }), children: [_jsxs("div", { style: ss({ display: 'flex', borderBottom: `1px solid ${C.border}`, gap: 0, flexShrink: 0 }), children: [Tb('materials', '🧪 Materials'), Tb('process', '⚙️ Bearings'), Tb('gearboxes', '🔧 Gearboxes'), Tb('motors', '🔌 Motors'), Tb('drives', '🎛️ Drives'), Tb('costs', '💰 Costs')] }), msg && (_jsx("div", { style: ss({ fontSize: 11, padding: '6px 12px', borderRadius: 4, flexShrink: 0,
                    background: msg.ok ? 'rgba(31,184,110,.1)' : 'rgba(224,82,82,.1)',
                    border: `1px solid ${msg.ok ? C.green : C.red}`,
                    color: msg.ok ? C.green : C.red }), children: msg.text })), tab === 'materials' && (_jsxs(_Fragment, { children: [_jsxs("div", { style: ss({ display: 'flex', gap: 8, flexShrink: 0 }), children: [_jsx("input", { value: search, onChange: e => setSearch(e.target.value), placeholder: "Search name / CEMA code / note\u2026", style: ss({ flex: 1, background: '#081321', border: `1px solid ${C.border}`, borderRadius: 4,
                                    padding: '6px 10px', color: C.text, fontSize: 11, fontFamily: 'inherit', outline: 'none' }) }), _jsxs("select", { value: cat, onChange: e => setCat(e.target.value), style: ss({ background: '#081321', border: `1px solid ${C.border}`, borderRadius: 4,
                                    padding: '6px 10px', color: C.text, fontSize: 11, fontFamily: 'inherit', outline: 'none' }), children: [_jsx("option", { value: "", children: "All Categories" }), (cats || []).map(c => _jsx("option", { value: c, children: c }, c))] }), _jsx("button", { onClick: () => setModal({ mode: 'add' }), style: ss({ padding: '6px 14px', borderRadius: 4, border: `1px solid ${C.green}`,
                                    background: 'rgba(31,184,110,.1)', color: C.green,
                                    cursor: 'pointer', fontSize: 11, fontWeight: 700, fontFamily: 'inherit', whiteSpace: 'nowrap' }), children: "+ Add Material" })] }), _jsx(TableWrap, { loading: mL, empty: !(mats || []).length, children: _jsxs("table", { style: ss({ width: '100%', borderCollapse: 'collapse' }), children: [_jsx("thead", { children: _jsxs("tr", { children: [['Material Name', 'Category', 'ρ t/m³', 'λ (computed)', 'Fill max', 'Ks', 'Wc', 'Particle', 'Flow', 'Abrasiveness', 'AoR °', 'Cohesion kPa', 'Cls', 'Moist%', 'Flags', 'Applications', 'CEMA C…'].map(h => (_jsx(TH, { children: h }, h))), _jsx(TH, {})] }) }), _jsx("tbody", { children: (mats || []).map(m => {
                                        // Compute lambda/Ks/Wc client-side for display (mirrors Python engine)
                                        const psz = { A200: 0.075, A100: 0.15, A40: 0.42, B6: 6, 'C1/2': 12, D3: 75, D7: 180 };
                                        const pszVal = psz[m.particle_class || 'B6'] || 6;
                                        const wc = Math.min(Math.max(({ Low: 0.25, Medium: 0.70, High: 1.40, 'Very High': 2.30 }[m.abr] || 0.5) * (1 + pszVal / 100), 0.1), 4.5);
                                        const ks = Math.max(0.3, Math.min(({ 1: 1.0, 2: 0.88, 3: 0.72, 4: 0.55 }[String(m.flowability)] || 0.8) *
                                            Math.max(0.5, 1 - (m.cohesion || 0.2) / 10), 1.0));
                                        const lamBase = pszVal < 0.5 ? 1.8 : pszVal < 5 ? 1.4 : 1.0;
                                        const lam = Math.max(0.4, Math.min(0.6 * (m.lambda_ref || 1.0) + 0.4 * lamBase, 3.5));
                                        return (_jsxs("tr", { style: ss({ borderBottom: `1px solid ${C.border}` }), onMouseOver: e => e.currentTarget.style.background = '#0d1e30', onMouseOut: e => e.currentTarget.style.background = 'transparent', children: [_jsxs(TD, { children: [_jsx("strong", { style: ss({ color: C.text }), children: m.name }), m.custom && _jsx(CustomBadge, {})] }), _jsx(TD, { faint: true, children: m.category || '—' }), _jsx(TD, { mono: true, children: m.rho.toFixed(2) }), _jsx(TD, { mono: true, children: lam.toFixed(2) }), _jsxs(TD, { mono: true, children: [(m.fill_max * 100).toFixed(0), "%"] }), _jsx(TD, { mono: true, children: ks.toFixed(2) }), _jsx(TD, { mono: true, children: wc.toFixed(2) }), _jsx(TD, { faint: true, children: m.particle_class || '—' }), _jsx(TD, { faint: true, children: m.flowability != null ? `${m.flowability} — ${['Very Free', 'Free', 'Average', 'Sluggish'][m.flowability - 1] || ''}` : '—' }), _jsx(TD, { faint: true, children: m.abr }), _jsx(TD, { mono: true, children: m.aor != null ? m.aor.toFixed(1) + '°' : '—' }), _jsx(TD, { mono: true, children: m.cohesion != null ? m.cohesion.toFixed(1) : '—' }), _jsx(TD, { mono: true, children: m.cls }), _jsx(TD, { mono: true, children: m.moist.toFixed(1) + '%' }), _jsx("td", { style: ss({ padding: '4px 8px' }), children: _jsx(FlagsCell, { flags: m.flags }) }), _jsx("td", { style: ss({ padding: '4px 8px', minWidth: 200 }), children: _jsx(AppCoverage, { mat: m }) }), _jsx(TD, { faint: true, children: m.cema_code || '—' }), _jsx("td", { style: ss({ padding: '4px 8px', whiteSpace: 'nowrap' }), children: _jsxs("div", { style: ss({ display: 'flex', gap: 4 }), children: [_jsx("button", { onClick: () => { setInp({ mat: m.name }); setPage('calc'); }, style: ss({ fontSize: 9, padding: '2px 6px', borderRadius: 3,
                                                                    border: `1px solid ${C.accent}`, background: 'transparent',
                                                                    color: C.accent, cursor: 'pointer' }), children: "Use\u2192" }), _jsx("button", { onClick: () => setModal({ mode: 'edit', row: m }), style: ss({ fontSize: 9, padding: '2px 6px', borderRadius: 3,
                                                                    border: `1px solid ${C.blue}`, background: 'transparent',
                                                                    color: C.blue, cursor: 'pointer' }), children: "\u270F\uFE0F" }), m.custom && _jsx("button", { onClick: () => setDelTarget(m.name), style: ss({ fontSize: 9, padding: '2px 6px', borderRadius: 3,
                                                                    border: `1px solid ${C.red}`, background: 'transparent',
                                                                    color: C.red, cursor: 'pointer' }), children: "\uD83D\uDDD1" })] }) })] }, m.id));
                                    }) })] }) })] })), tab === 'process' && (_jsxs(_Fragment, { children: [_jsx("div", { style: ss({ display: 'flex', justifyContent: 'flex-end', flexShrink: 0 }), children: _jsx("button", { onClick: () => setModal({ mode: 'add' }), style: ss({ padding: '6px 14px', borderRadius: 4, border: `1px solid ${C.green}`,
                                background: 'rgba(31,184,110,.1)', color: C.green, cursor: 'pointer',
                                fontSize: 11, fontWeight: 700, fontFamily: 'inherit' }), children: "+ Add Bearing" }) }), _jsx(TableWrap, { loading: bL, empty: !(bearings || []).length, children: _jsxs("table", { style: ss({ width: '100%', borderCollapse: 'collapse' }), children: [_jsx("thead", { children: _jsxs("tr", { children: [['Name', 'Type', 'Bore mm', 'OD mm', 'B mm', 'C kN', 'C₀ kN', 'p', 'Speed rpm', 'Seal', 'Role', 'Mass kg', 'Note'].map(h => _jsx(TH, { children: h }, h)), _jsx(TH, {})] }) }), _jsx("tbody", { children: (bearings || []).map((b) => (_jsxs("tr", { style: ss({ borderBottom: `1px solid ${C.border}` }), onMouseOver: e => e.currentTarget.style.background = '#0d1e30', onMouseOut: e => e.currentTarget.style.background = 'transparent', children: [_jsxs(TD, { children: [_jsx("strong", { style: ss({ color: C.text }), children: b.name }), b.custom && _jsx(CustomBadge, {})] }), _jsx(TD, { faint: true, children: b.type || '—' }), _jsx(TD, { mono: true, children: b.bore?.toFixed(0) || '—' }), _jsx(TD, { mono: true, children: b.od?.toFixed(0) || '—' }), _jsx(TD, { mono: true, children: b.B?.toFixed(0) || '—' }), _jsx(TD, { mono: true, children: b.C?.toFixed(1) || '—' }), _jsx(TD, { mono: true, children: b.C0?.toFixed(1) || '—' }), _jsx(TD, { mono: true, children: b.p?.toFixed(0) || '—' }), _jsx(TD, { mono: true, children: b.speed_g?.toLocaleString() || '—' }), _jsx(TD, { faint: true, children: b.seal || '—' }), _jsx(TD, { faint: true, children: b.role || '—' }), _jsx(TD, { mono: true, children: b.mass_kg?.toFixed(1) || '—' }), _jsx(TD, { faint: true, children: b.note || '' }), _jsx("td", { style: ss({ padding: '4px 8px' }), children: _jsx(ActionBtns, { isCustom: !!b.custom, onEdit: () => setModal({ mode: 'edit', row: b }), onDelete: b.custom ? () => setDelTarget(b.name) : undefined }) })] }, b.id))) })] }) })] })), tab === 'gearboxes' && (_jsxs(_Fragment, { children: [_jsx("div", { style: ss({ display: 'flex', justifyContent: 'flex-end', flexShrink: 0 }), children: _jsx("button", { onClick: () => setModal({ mode: 'add' }), style: ss({ padding: '6px 14px', borderRadius: 4, border: `1px solid ${C.green}`,
                                background: 'rgba(31,184,110,.1)', color: C.green, cursor: 'pointer',
                                fontSize: 11, fontWeight: 700, fontFamily: 'inherit' }), children: "+ Add Gearbox" }) }), _jsx(TableWrap, { loading: gL, empty: !(gearboxes || []).length, children: _jsxs("table", { style: ss({ width: '100%', borderCollapse: 'collapse' }), children: [_jsx("thead", { children: _jsxs("tr", { children: [['Model', 'Type', 'Stages', 'Rated Torque Nm', 'Power kW', 'Ratio min', 'Ratio max', 'η %', 'Mount', 'IP', 'Mass kg', 'Note'].map(h => _jsx(TH, { children: h }, h)), _jsx(TH, {})] }) }), _jsx("tbody", { children: (gearboxes || []).map((g) => (_jsxs("tr", { style: ss({ borderBottom: `1px solid ${C.border}` }), onMouseOver: e => e.currentTarget.style.background = '#0d1e30', onMouseOut: e => e.currentTarget.style.background = 'transparent', children: [_jsxs(TD, { children: [_jsx("strong", { style: ss({ color: C.text }), children: g.model }), g.custom && _jsx(CustomBadge, {})] }), _jsx(TD, { faint: true, children: g.type || '—' }), _jsx(TD, { mono: true, children: g.stages || '—' }), _jsx(TD, { mono: true, children: g.Tn?.toLocaleString() }), _jsx(TD, { mono: true, children: g.Pkw?.toFixed(1) }), _jsx(TD, { mono: true, children: g.ratio_min?.toFixed(1) || '—' }), _jsx(TD, { mono: true, children: g.ratio_max?.toFixed(1) || '—' }), _jsx(TD, { mono: true, children: g.eta?.toFixed(1) || '—' }), _jsx(TD, { faint: true, children: g.mount || '—' }), _jsx(TD, { faint: true, children: g.ip || '—' }), _jsx(TD, { mono: true, children: g.mass_kg?.toFixed(1) || '—' }), _jsx(TD, { faint: true, children: g.note || '' }), _jsx("td", { style: ss({ padding: '4px 8px' }), children: _jsx(ActionBtns, { isCustom: !!g.custom, onEdit: () => setModal({ mode: 'edit', row: g }), onDelete: g.custom ? () => setDelTarget(g.model) : undefined }) })] }, g.id))) })] }) })] })), tab === 'motors' && (_jsxs(_Fragment, { children: [_jsx("div", { style: ss({ display: 'flex', justifyContent: 'flex-end', flexShrink: 0 }), children: _jsx("button", { onClick: () => setModal({ mode: 'add' }), style: ss({ padding: '6px 14px', borderRadius: 4, border: `1px solid ${C.green}`,
                                background: 'rgba(31,184,110,.1)', color: C.green, cursor: 'pointer',
                                fontSize: 11, fontWeight: 700, fontFamily: 'inherit' }), children: "+ Add Motor" }) }), _jsx(TableWrap, { loading: moL, empty: !(motors || []).length, children: _jsxs("table", { style: ss({ width: '100%', borderCollapse: 'collapse' }), children: [_jsx("thead", { children: _jsxs("tr", { children: [['Model', 'Frame', 'Power kW', 'Poles', 'RPM (50Hz)', 'Efficiency %', 'IE Class', 'IP', 'Mass kg', 'Note'].map(h => _jsx(TH, { children: h }, h)), _jsx(TH, {})] }) }), _jsx("tbody", { children: (motors || []).map((m) => (_jsxs("tr", { style: ss({ borderBottom: `1px solid ${C.border}` }), onMouseOver: e => e.currentTarget.style.background = '#0d1e30', onMouseOut: e => e.currentTarget.style.background = 'transparent', children: [_jsxs(TD, { children: [_jsx("strong", { style: ss({ color: C.text }), children: m.model }), m.custom && _jsx(CustomBadge, {})] }), _jsx(TD, { faint: true, children: m.frame || '—' }), _jsx(TD, { mono: true, children: m.Pkw?.toFixed(2) }), _jsx(TD, { mono: true, children: m.poles || '—' }), _jsx(TD, { mono: true, children: m.rpm_50hz?.toFixed(0) || '—' }), _jsx(TD, { mono: true, children: m.efficiency?.toFixed(1) || '—' }), _jsx(TD, { faint: true, children: m.ie_class || '—' }), _jsx(TD, { faint: true, children: m.ip || '—' }), _jsx(TD, { mono: true, children: m.mass_kg?.toFixed(1) || '—' }), _jsx(TD, { faint: true, children: m.note || '' }), _jsx("td", { style: ss({ padding: '4px 8px' }), children: _jsx(ActionBtns, { isCustom: !!m.custom, onEdit: () => setModal({ mode: 'edit', row: m }), onDelete: m.custom ? () => setDelTarget(m.model) : undefined }) })] }, m.id))) })] }) })] })), tab === 'drives' && (_jsxs(_Fragment, { children: [_jsx("div", { style: ss({ display: 'flex', justifyContent: 'flex-end', flexShrink: 0 }), children: _jsx("button", { onClick: () => setModal({ mode: 'add' }), style: ss({ padding: '6px 14px', borderRadius: 4, border: `1px solid ${C.green}`,
                                background: 'rgba(31,184,110,.1)', color: C.green, cursor: 'pointer',
                                fontSize: 11, fontWeight: 700, fontFamily: 'inherit' }), children: "+ Add Drive" }) }), _jsx(TableWrap, { loading: dL, empty: !(drives || []).length, children: _jsxs("table", { style: ss({ width: '100%', borderCollapse: 'collapse' }), children: [_jsx("thead", { children: _jsxs("tr", { children: [['Model', 'Type', 'Max kW', 'Rated V', 'Rated A', 'Overload %', 'Control', 'IP', 'Features', 'Note'].map(h => _jsx(TH, { children: h }, h)), _jsx(TH, {})] }) }), _jsx("tbody", { children: (drives || []).map((d) => (_jsxs("tr", { style: ss({ borderBottom: `1px solid ${C.border}` }), onMouseOver: e => e.currentTarget.style.background = '#0d1e30', onMouseOut: e => e.currentTarget.style.background = 'transparent', children: [_jsxs(TD, { children: [_jsx("strong", { style: ss({ color: C.text }), children: d.model }), d.custom && _jsx(CustomBadge, {})] }), _jsx(TD, { faint: true, children: d.type || '—' }), _jsx(TD, { mono: true, children: d.Pkw_max?.toFixed(2) || '—' }), _jsx(TD, { mono: true, children: d.Vrated?.toFixed(0) || '—' }), _jsx(TD, { mono: true, children: d.Irated?.toFixed(1) || '—' }), _jsx(TD, { mono: true, children: d.overload_pct?.toFixed(0) || '—' }), _jsx(TD, { faint: true, children: d.control || '—' }), _jsx(TD, { faint: true, children: d.ip || '—' }), _jsx(TD, { faint: true, children: d.features || '—' }), _jsx(TD, { faint: true, children: d.note || '' }), _jsx("td", { style: ss({ padding: '4px 8px' }), children: _jsx(ActionBtns, { isCustom: !!d.custom, onEdit: () => setModal({ mode: 'edit', row: d }), onDelete: d.custom ? () => setDelTarget(d.model) : undefined }) })] }, d.id))) })] }) })] })), tab === 'costs' && (_jsxs(_Fragment, { children: [_jsx("div", { style: ss({ display: 'flex', justifyContent: 'flex-end', flexShrink: 0 }), children: _jsx("button", { onClick: () => setModal({ mode: 'add' }), style: ss({ padding: '6px 14px', borderRadius: 4, border: `1px solid ${C.green}`,
                                background: 'rgba(31,184,110,.1)', color: C.green, cursor: 'pointer',
                                fontSize: 11, fontWeight: 700, fontFamily: 'inherit' }), children: "+ Add Cost Item" }) }), _jsx(TableWrap, { loading: cL, empty: !(costs || []).length, children: _jsxs("table", { style: ss({ width: '100%', borderCollapse: 'collapse' }), children: [_jsx("thead", { children: _jsxs("tr", { children: [['Material / Item', 'USD / kg', 'Material Group', 'Description', 'Note'].map(h => _jsx(TH, { children: h }, h)), _jsx(TH, {})] }) }), _jsx("tbody", { children: (costs || []).map((c) => (_jsxs("tr", { style: ss({ borderBottom: `1px solid ${C.border}` }), onMouseOver: e => e.currentTarget.style.background = '#0d1e30', onMouseOut: e => e.currentTarget.style.background = 'transparent', children: [_jsxs(TD, { children: [_jsx("strong", { style: ss({ color: C.text }), children: c.item }), c.custom && _jsx(CustomBadge, {})] }), _jsx(TD, { mono: true, children: c.usd?.toFixed(2) }), _jsx(TD, { faint: true, children: c.material_group || '—' }), _jsx(TD, { faint: true, children: c.description || '—' }), _jsx(TD, { faint: true, children: c.note || '' }), _jsx("td", { style: ss({ padding: '4px 8px' }), children: _jsx(ActionBtns, { isCustom: !!c.custom, onEdit: () => setModal({ mode: 'edit', row: c }), onDelete: c.custom ? () => setDelTarget(c.item) : undefined }) })] }, c.id))) })] }) })] })), modal && tab === 'materials' && (_jsx(MaterialFormModal, { title: modal.mode === 'add' ? 'Add Custom Material' : `Edit: ${modal.row?.name}`, initial: modal.mode === 'edit' ? {
                    ...modal.row,
                    rho: String(modal.row.rho || ''), rho_min: String(modal.row.rho_min || ''),
                    rho_max: String(modal.row.rho_max || ''), lambda_ref: String(modal.row.lambda_ref || ''),
                    fill_max: String(modal.row.fill_max || ''), moist: String(modal.row.moist || ''),
                    aor: String(modal.row.aor || ''), cohesion: String(modal.row.cohesion || ''),
                    temp_max: String(modal.row.temp_max || ''), bridging_risk: String(modal.row.bridging_risk || ''),
                    flowability: String(modal.row.flowability || '2'),
                    app: modal.row.app || [],
                } : undefined, onSave: async (d) => { await handleSave(d); }, onClose: () => setModal(null) })), modal && tab !== 'materials' && (() => {
                const row = modal.row || {};
                const [form, setFormLocal] = React.useState(Object.fromEntries(Object.entries(row).map(([k, v]) => [k, v == null ? '' : String(v)])));
                const [saving, setSaving] = React.useState(false);
                const [err, setErr] = React.useState('');
                const setF = (k) => (v) => setFormLocal(p => ({ ...p, [k]: v }));
                const fieldDefs = {
                    materials: [],
                    process: [
                        { k: 'name', label: 'Name *' }, { k: 'type', label: 'Type' }, { k: 'bore', label: 'Bore mm', type: 'number' },
                        { k: 'od', label: 'OD mm', type: 'number' }, { k: 'B', label: 'B mm', type: 'number' },
                        { k: 'C', label: 'C kN', type: 'number' }, { k: 'C0', label: 'C₀ kN', type: 'number' },
                        { k: 'p', label: 'Life exp', type: 'number' }, { k: 'speed_g', label: 'Speed limit', type: 'number' },
                        { k: 'seal', label: 'Seal' }, { k: 'role', label: 'Role' }, { k: 'mass_kg', label: 'Mass kg', type: 'number' },
                        { k: 'note', label: 'Note' },
                    ],
                    gearboxes: [
                        { k: 'model', label: 'Model *' }, { k: 'type', label: 'Type' }, { k: 'stages', label: 'Stages', type: 'number' },
                        { k: 'Tn', label: 'Rated Torque Nm', type: 'number' }, { k: 'Pkw', label: 'Power kW', type: 'number' },
                        { k: 'ratio_min', label: 'Ratio min', type: 'number' }, { k: 'ratio_max', label: 'Ratio max', type: 'number' },
                        { k: 'eta', label: 'Efficiency %', type: 'number' }, { k: 'mount', label: 'Mount' },
                        { k: 'ip', label: 'IP' }, { k: 'mass_kg', label: 'Mass kg', type: 'number' }, { k: 'note', label: 'Note' },
                    ],
                    motors: [
                        { k: 'model', label: 'Model *' }, { k: 'frame', label: 'Frame' },
                        { k: 'Pkw', label: 'Power kW', type: 'number' }, { k: 'poles', label: 'Poles', type: 'number' },
                        { k: 'rpm_50hz', label: 'RPM 50Hz', type: 'number' }, { k: 'efficiency', label: 'Efficiency %', type: 'number' },
                        { k: 'ie_class', label: 'IE Class' }, { k: 'ip', label: 'IP' },
                        { k: 'mass_kg', label: 'Mass kg', type: 'number' }, { k: 'note', label: 'Note' },
                    ],
                    drives: [
                        { k: 'model', label: 'Model *' }, { k: 'type', label: 'Type' },
                        { k: 'Pkw_max', label: 'Max kW', type: 'number' }, { k: 'Vrated', label: 'Rated V', type: 'number' },
                        { k: 'Irated', label: 'Rated A', type: 'number' }, { k: 'overload_pct', label: 'Overload %', type: 'number' },
                        { k: 'control', label: 'Control' }, { k: 'ip', label: 'IP' },
                        { k: 'features', label: 'Features' }, { k: 'note', label: 'Note' },
                    ],
                    costs: [
                        { k: 'item', label: 'Item Name *' }, { k: 'usd', label: 'USD / kg', type: 'number' },
                        { k: 'material_group', label: 'Material Group' }, { k: 'description', label: 'Description' },
                        { k: 'note', label: 'Note' },
                    ],
                };
                const fields = fieldDefs[tab] || [];
                const keyField = tab === 'process' ? 'name' : tab === 'gearboxes' || tab === 'motors' || tab === 'drives' ? 'model' : 'item';
                const doSave = async () => {
                    setSaving(true);
                    setErr('');
                    const parsed = {};
                    fields.forEach(({ k, type }) => {
                        parsed[k] = type === 'number' ? (parseFloat(form[k]) || null) : (form[k] || null);
                    });
                    try {
                        await handleSave(parsed);
                    }
                    catch (e) {
                        setErr(e.message);
                        setSaving(false);
                    }
                };
                const title = modal.mode === 'add' ? `Add ${tab[0].toUpperCase() + tab.slice(1, -1)}`
                    : `Edit: ${row[keyField]}`;
                return (_jsx(Modal, { title: title, icon: "\u270F\uFE0F", onClose: () => setModal(null), onSave: doSave, saving: saving, error: err, children: fields.map(({ k, label, type }) => (_jsx(FInput, { label: label, value: form[k] || '', type: type || 'text', onChange: setF(k), step: type === 'number' ? '0.01' : undefined }, k))) }));
            })(), delTarget && (_jsx(DeleteConfirm, { name: delTarget, onConfirm: handleDelete, onCancel: () => setDelTarget(null) }))] }));
}
