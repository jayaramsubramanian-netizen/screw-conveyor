import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/**
 * App.tsx — VECTRIX™ application root
 *
 * Layout:
 *   TitleBar (26px) — logo + brand + active module indicator (right side)
 *   MenuBar  (28px) — Windows-style pull-down menus
 *   <main>          — page content (NO second tab bar row)
 *
 * Each process module is an independent page/tab.
 */
import React, { useState, useCallback, useEffect } from 'react';
import TitleBar from './components/layout/TitleBar';
import MenuBar from './components/layout/MenuBar';
import ProjectDialog from './components/layout/ProjectDialog';
import AboutDialog from './components/layout/AboutDialog';
import ShortcutsDialog from './components/layout/ShortcutsDialog';
import CalcPage from './components/pages/CalcPage';
import FamilyPage from './components/pages/FamilyPage';
import MixerPage from './components/pages/MixerPage';
import DryerPage from './components/pages/DryerPage';
import CoolerPage from './components/pages/CoolerPage';
import SeparatorPage from './components/pages/SeparatorPage';
import ReactorPage from './components/pages/ReactorPage';
import CompactorPage from './components/pages/CompactorPage';
import DatabasePage from './components/pages/DatabasePage';
import ManualPage from './components/pages/ManualPage';
export const PAGE_META = {
    calc: { icon: '🔩', label: 'Screw Conveyor Designer', group: 'conveyor' },
    family: { icon: '📊', label: 'Family Designer', group: 'conveyor' },
    mixer: { icon: '🌀', label: 'Screw Mixer', group: 'process' },
    dryer: { icon: '🌡️', label: 'Screw Dryer', group: 'process' },
    cooler: { icon: '❄️', label: 'Screw Cooler', group: 'process' },
    separator: { icon: '🔀', label: 'Separator', group: 'process' },
    reactor: { icon: '⚗️', label: 'Screw Reactor', group: 'process' },
    compactor: { icon: '🗜️', label: 'Compactor', group: 'process' },
    db: { icon: '🗄️', label: 'Material Database', group: 'reference' },
    help: { icon: '📘', label: 'User Manual', group: 'reference' },
};
const DEFAULT_META = {
    project: '', tagNo: '', client: '', engineer: '',
    approved: '', rev: 'A', docNo: '', site: '', notes: '',
};
export default function App() {
    const [page, setPage] = useState('calc');
    const [projectMeta, setProjectMeta] = useState(DEFAULT_META);
    const [showProject, setShowProject] = useState(false);
    const [showAbout, setShowAbout] = useState(false);
    const [showShortcuts, setShowShortcuts] = useState(false);
    useEffect(() => {
        const handler = (e) => {
            if (e.altKey) {
                const map = {
                    '1': 'calc', '2': 'family', '3': 'mixer', '4': 'dryer',
                    '5': 'cooler', '6': 'separator', '7': 'reactor', '8': 'compactor',
                    '9': 'db', '0': 'help',
                };
                if (map[e.key]) {
                    e.preventDefault();
                    setPage(map[e.key]);
                }
            }
            if (e.key === 'Escape') {
                setShowProject(false);
                setShowAbout(false);
                setShowShortcuts(false);
            }
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, []);
    const handleNewProject = useCallback(() => setShowProject(true), []);
    const handleShowAbout = useCallback(() => setShowAbout(true), []);
    const handleShowShortcuts = useCallback(() => setShowShortcuts(true), []);
    return (_jsxs("div", { style: {
            display: 'flex', flexDirection: 'column', height: '100%',
            background: '#0b1522', color: '#ddeaf6',
            fontFamily: "'Segoe UI', system-ui, sans-serif", overflow: 'hidden',
        }, children: [_jsx(TitleBar, { page: page }), _jsx(MenuBar, { page: page, setPage: setPage, onNewProject: handleNewProject, onShowAbout: handleShowAbout, onShowShortcuts: handleShowShortcuts }), _jsxs("main", { style: { flex: 1, overflow: 'hidden', position: 'relative', display: 'flex', flexDirection: 'column', minHeight: 0 }, children: [page === 'calc' && _jsx(CalcPage, { meta: projectMeta }), page === 'family' && _jsx(FamilyPage, {}), page === 'mixer' && _jsx(MixerPage, {}), page === 'dryer' && _jsx(DryerPage, {}), page === 'cooler' && _jsx(CoolerPage, {}), page === 'separator' && _jsx(SeparatorPage, {}), page === 'reactor' && _jsx(ReactorPage, {}), page === 'compactor' && _jsx(CompactorPage, {}), page === 'db' && _jsx(DatabasePage, { setPage: setPage }), page === 'help' && _jsx(ManualPage, {})] }), showProject && _jsx(ProjectDialog, { meta: projectMeta, setMeta: setProjectMeta, onClose: () => setShowProject(false) }), showAbout && _jsx(AboutDialog, { onClose: () => setShowAbout(false) }), showShortcuts && _jsx(ShortcutsDialog, { onClose: () => setShowShortcuts(false) })] }));
}
