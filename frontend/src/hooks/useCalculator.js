/**
 * useCalculator.ts
 * ─────────────────
 * Central state + server state for the VECTRIX™ calculator.
 *
 * Global store: Zustand (inp, page, setInp, setPage)
 * Server state: @tanstack/react-query v5 (useQuery)
 *
 * All components read from this hook — nothing fetches directly.
 */
import { create } from 'zustand';
import { useQuery } from '@tanstack/react-query';
import * as api from '../api/client';
// ── Default inputs (mirrors JS DEF object exactly) ────────────────
export const DEFAULT_INPUT = {
    type: 'screw',
    mat: 'Portland cement dry',
    cap: 30,
    L: 20,
    ang: 0,
    surge: 1.2,
    D: 0.3,
    P: 0.3,
    N: 60,
    use_multipitch: false,
    P_in: 0.15,
    P_out: 0.15,
    pct_in: 10,
    pct_out: 10,
    ft: 0.008,
    wa: 0.003,
    shaft_mode: 'auto',
    shtype: 'bar',
    pod: 80,
    pwall: 8,
    prefer_pipe: false,
    brg: 'UC210',
    bload: 10,
    gbx: 'GB-40k',
    sallow: 40,
    hangers: 0, // 0 = auto-select
    duty: 8,
    temp_c: 20,
    contAFact: false,
    support_cond: 'pinfix',
};
export const useCalcStore = create((set) => ({
    inp: DEFAULT_INPUT,
    setInp: (patch) => set((s) => ({ inp: { ...s.inp, ...patch } })),
    applyDesign: (patch) => set((s) => ({ inp: { ...s.inp, ...patch } })),
}));
// ── Server state hooks (react-query v5) ──────────────────────────
/** Main calculation — runs whenever inp changes */
export function useCalculate() {
    const inp = useCalcStore((s) => s.inp);
    return useQuery({
        queryKey: ['calculate', inp],
        queryFn: () => api.calculate(inp),
        placeholderData: (prev) => prev, // v5: replaces keepPreviousData
        staleTime: 0,
        retry: 1,
    });
}
/** Axial profile — on-demand */
export function useAxialProfile(segments = 60) {
    const inp = useCalcStore((s) => s.inp);
    return useQuery({
        queryKey: ['axial-profile', inp, segments],
        queryFn: () => api.getAxialProfile(inp, segments),
        placeholderData: (prev) => prev,
        staleTime: 0,
    });
}
/** Materials list with optional filters */
export function useMaterials(params) {
    return useQuery({
        queryKey: ['materials', params],
        queryFn: () => api.getMaterials(params),
        staleTime: 5 * 60 * 1000,
    });
}
/** Category list */
export function useCategories() {
    return useQuery({
        queryKey: ['categories'],
        queryFn: api.getCategories,
        staleTime: 10 * 60 * 1000,
    });
}
/** Bearings */
export function useBearings(params) {
    return useQuery({
        queryKey: ['bearings', params],
        queryFn: () => api.getBearings(params),
        staleTime: 10 * 60 * 1000,
    });
}
/** Gearboxes */
export function useGearboxes(params) {
    return useQuery({
        queryKey: ['gearboxes', params],
        queryFn: () => api.getGearboxes(params),
        staleTime: 10 * 60 * 1000,
    });
}
/** Family design — triggered manually */
export function useFamily(payload) {
    return useQuery({
        queryKey: ['family', payload],
        queryFn: () => api.getFamily(payload),
        enabled: false, // call refetch() to run
    });
}
