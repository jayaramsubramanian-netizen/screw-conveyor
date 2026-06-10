/**
 * API client — all backend communication goes through here.
 */
import axios from 'axios'
import type {
  EngineInput, EngineResult, AxialProfileResult, FamilyResult,
  MaterialOut, BearingOut, GearboxOut,
} from '../types/api'

const BASE = '/api/v1'
const http = axios.create({ baseURL: BASE, headers: { 'Content-Type': 'application/json' } })

// ── CALCULATE ────────────────────────────────────────────────────
export async function calculate(inp: EngineInput): Promise<EngineResult> {
  const { data } = await http.post<EngineResult>('/calculate', inp); return data
}
export async function getAxialProfile(inp: EngineInput, segments = 60): Promise<AxialProfileResult> {
  const { data } = await http.post<AxialProfileResult>('/axial-profile', { inp, segments }); return data
}
export async function getFamily(payload: any): Promise<FamilyResult> {
  const { data } = await http.post<FamilyResult>('/family', payload); return data
}

// ── MATERIALS ────────────────────────────────────────────────────
export async function getMaterials(params?: any): Promise<MaterialOut[]> {
  const { data } = await http.get<MaterialOut[]>('/materials', { params }); return data
}
export async function getMaterial(name: string): Promise<MaterialOut> {
  const { data } = await http.get<MaterialOut>(`/materials/${encodeURIComponent(name)}`); return data
}
export async function getCategories(): Promise<string[]> {
  const { data } = await http.get<string[]>('/materials/categories'); return data
}
export async function createMaterial(m: any): Promise<MaterialOut> {
  const { data } = await http.post<MaterialOut>('/materials', m); return data
}
export async function updateMaterial(name: string, m: any): Promise<MaterialOut> {
  const { data } = await http.put<MaterialOut>(`/materials/${encodeURIComponent(name)}`, m); return data
}
export async function deleteMaterial(name: string): Promise<void> {
  await http.delete(`/materials/${encodeURIComponent(name)}`)
}

// ── BEARINGS ─────────────────────────────────────────────────────
export async function getBearings(params?: any): Promise<BearingOut[]> {
  const { data } = await http.get<BearingOut[]>('/bearings', { params }); return data
}
export async function createBearing(m: any): Promise<BearingOut> {
  const { data } = await http.post<BearingOut>('/bearings', m); return data
}
export async function updateBearing(name: string, m: any): Promise<BearingOut> {
  const { data } = await http.put<BearingOut>(`/bearings/${encodeURIComponent(name)}`, m); return data
}
export async function deleteBearing(name: string): Promise<void> {
  await http.delete(`/bearings/${encodeURIComponent(name)}`)
}

// ── GEARBOXES ─────────────────────────────────────────────────────
export async function getGearboxes(params?: any): Promise<GearboxOut[]> {
  const { data } = await http.get<GearboxOut[]>('/gearboxes', { params }); return data
}
export async function createGearbox(m: any): Promise<GearboxOut> {
  const { data } = await http.post<GearboxOut>('/gearboxes', m); return data
}
export async function updateGearbox(model: string, m: any): Promise<GearboxOut> {
  const { data } = await http.put<GearboxOut>(`/gearboxes/${encodeURIComponent(model)}`, m); return data
}
export async function deleteGearbox(model: string): Promise<void> {
  await http.delete(`/gearboxes/${encodeURIComponent(model)}`)
}

// ── MOTORS ────────────────────────────────────────────────────────
export async function getMotors(): Promise<any[]> {
  const { data } = await http.get<any[]>('/motors'); return data
}
export async function createMotor(m: any): Promise<any> {
  const { data } = await http.post('/motors', m); return data
}
export async function updateMotor(model: string, m: any): Promise<any> {
  const { data } = await http.put(`/motors/${encodeURIComponent(model)}`, m); return data
}
export async function deleteMotor(model: string): Promise<void> {
  await http.delete(`/motors/${encodeURIComponent(model)}`)
}

// ── DRIVES ────────────────────────────────────────────────────────
export async function getDrives(): Promise<any[]> {
  const { data } = await http.get<any[]>('/drives'); return data
}
export async function createDrive(m: any): Promise<any> {
  const { data } = await http.post('/drives', m); return data
}
export async function updateDrive(model: string, m: any): Promise<any> {
  const { data } = await http.put(`/drives/${encodeURIComponent(model)}`, m); return data
}
export async function deleteDrive(model: string): Promise<void> {
  await http.delete(`/drives/${encodeURIComponent(model)}`)
}

// ── COSTS ────────────────────────────────────────────────────────
export async function getCosts(): Promise<any[]> {
  const { data } = await http.get<any[]>('/costs'); return data
}
export async function createCost(m: any): Promise<any> {
  const { data } = await http.post('/costs', m); return data
}
export async function updateCost(item: string, m: any): Promise<any> {
  const { data } = await http.put(`/costs/${encodeURIComponent(item)}`, m); return data
}
export async function deleteCost(item: string): Promise<void> {
  await http.delete(`/costs/${encodeURIComponent(item)}`)
}

// ── HEALTH ───────────────────────────────────────────────────────
export async function getHealth() {
  const { data } = await http.get('/health'); return data
}

// ── MULTI-STANDARD CALCULATE ──────────────────────────────────────
export async function calculateMulti(inp: any): Promise<Record<string, any>> {
  const { data } = await http.post<Record<string, any>>('/calculate-multi', inp)
  return data
}
