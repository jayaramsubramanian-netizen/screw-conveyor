/**
 * API client — all backend communication goes through here.
 */
import axios from 'axios';
const BASE = '/api/v1';
const http = axios.create({ baseURL: BASE, headers: { 'Content-Type': 'application/json' } });
// ── CALCULATE ────────────────────────────────────────────────────
export async function calculate(inp) {
    const { data } = await http.post('/calculate', inp);
    return data;
}
export async function getAxialProfile(inp, segments = 60) {
    const { data } = await http.post('/axial-profile', { inp, segments });
    return data;
}
export async function getFamily(payload) {
    const { data } = await http.post('/family', payload);
    return data;
}
// ── MATERIALS ────────────────────────────────────────────────────
export async function getMaterials(params) {
    const { data } = await http.get('/materials', { params });
    return data;
}
export async function getMaterial(name) {
    const { data } = await http.get(`/materials/${encodeURIComponent(name)}`);
    return data;
}
export async function getCategories() {
    const { data } = await http.get('/materials/categories');
    return data;
}
export async function createMaterial(m) {
    const { data } = await http.post('/materials', m);
    return data;
}
export async function updateMaterial(name, m) {
    const { data } = await http.put(`/materials/${encodeURIComponent(name)}`, m);
    return data;
}
export async function deleteMaterial(name) {
    await http.delete(`/materials/${encodeURIComponent(name)}`);
}
// ── BEARINGS ─────────────────────────────────────────────────────
export async function getBearings(params) {
    const { data } = await http.get('/bearings', { params });
    return data;
}
export async function createBearing(m) {
    const { data } = await http.post('/bearings', m);
    return data;
}
export async function updateBearing(name, m) {
    const { data } = await http.put(`/bearings/${encodeURIComponent(name)}`, m);
    return data;
}
export async function deleteBearing(name) {
    await http.delete(`/bearings/${encodeURIComponent(name)}`);
}
// ── GEARBOXES ─────────────────────────────────────────────────────
export async function getGearboxes(params) {
    const { data } = await http.get('/gearboxes', { params });
    return data;
}
export async function createGearbox(m) {
    const { data } = await http.post('/gearboxes', m);
    return data;
}
export async function updateGearbox(model, m) {
    const { data } = await http.put(`/gearboxes/${encodeURIComponent(model)}`, m);
    return data;
}
export async function deleteGearbox(model) {
    await http.delete(`/gearboxes/${encodeURIComponent(model)}`);
}
// ── MOTORS ────────────────────────────────────────────────────────
export async function getMotors() {
    const { data } = await http.get('/motors');
    return data;
}
export async function createMotor(m) {
    const { data } = await http.post('/motors', m);
    return data;
}
export async function updateMotor(model, m) {
    const { data } = await http.put(`/motors/${encodeURIComponent(model)}`, m);
    return data;
}
export async function deleteMotor(model) {
    await http.delete(`/motors/${encodeURIComponent(model)}`);
}
// ── DRIVES ────────────────────────────────────────────────────────
export async function getDrives() {
    const { data } = await http.get('/drives');
    return data;
}
export async function createDrive(m) {
    const { data } = await http.post('/drives', m);
    return data;
}
export async function updateDrive(model, m) {
    const { data } = await http.put(`/drives/${encodeURIComponent(model)}`, m);
    return data;
}
export async function deleteDrive(model) {
    await http.delete(`/drives/${encodeURIComponent(model)}`);
}
// ── COSTS ────────────────────────────────────────────────────────
export async function getCosts() {
    const { data } = await http.get('/costs');
    return data;
}
export async function createCost(m) {
    const { data } = await http.post('/costs', m);
    return data;
}
export async function updateCost(item, m) {
    const { data } = await http.put(`/costs/${encodeURIComponent(item)}`, m);
    return data;
}
export async function deleteCost(item) {
    await http.delete(`/costs/${encodeURIComponent(item)}`);
}
// ── HEALTH ───────────────────────────────────────────────────────
export async function getHealth() {
    const { data } = await http.get('/health');
    return data;
}
// ── MULTI-STANDARD CALCULATE ──────────────────────────────────────
export async function calculateMulti(inp) {
    const { data } = await http.post('/calculate-multi', inp);
    return data;
}
