const BASE = import.meta.env.VITE_API_URL || '/api'

async function req(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } }
  if (body !== undefined) opts.body = JSON.stringify(body)
  const r = await fetch(BASE + path, opts)
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || JSON.stringify(err))
  }
  return r.json()
}

export const api = {
  // DB
  getMaterials: (search = '') => req('GET', `/db/materials${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  getMaterial: (name) => req('GET', `/db/materials/${encodeURIComponent(name)}`),
  createMaterial: (data) => req('POST', '/db/materials', data),
  updateMaterial: (name, data) => req('PUT', `/db/materials/${encodeURIComponent(name)}`, data),
  deleteMaterial: (name) => req('DELETE', `/db/materials/${encodeURIComponent(name)}`),

  getBearings: () => req('GET', '/db/bearings'),
  createBearing: (data) => req('POST', '/db/bearings', data),
  updateBearing: (name, data) => req('PUT', `/db/bearings/${encodeURIComponent(name)}`, data),
  deleteBearing: (name) => req('DELETE', `/db/bearings/${encodeURIComponent(name)}`),

  getGearboxes: () => req('GET', '/db/gearboxes'),
  createGearbox: (data) => req('POST', '/db/gearboxes', data),
  updateGearbox: (model, data) => req('PUT', `/db/gearboxes/${encodeURIComponent(model)}`, data),
  deleteGearbox: (model) => req('DELETE', `/db/gearboxes/${encodeURIComponent(model)}`),

  getCosts: () => req('GET', '/db/costs'),
  updateCost: (item, data) => req('PUT', `/db/costs/${encodeURIComponent(item)}`, data),

  getMotors: () => req('GET', '/db/motors'),
  addMotor: (kW) => req('POST', `/db/motors?kW=${kW}`),

  // Calculations
  calculate: (data) => req('POST', '/calculate', data),
  calculateAll: (data) => req('POST', '/calculate/all', data),
  sweepSpeed: (data) => req('POST', '/sweep/speed', data),
  sweepDiameter: (data) => req('POST', '/sweep/diameter', data),
  sweepLength: (data) => req('POST', '/sweep/length', data),

  // Family
  familyDesign: (data) => req('POST', '/family/design', data),
  familyMatrix: (data) => req('POST', '/family/matrix', data),

  // Process
  calcMixer: (data) => req('POST', '/process/mixer', data),
  calcDryer: (data) => req('POST', '/process/dryer', data),
  calcCooler: (data) => req('POST', '/process/cooler', data),
  calcSeparator: (data) => req('POST', '/process/separator', data),
  calcReactor: (data) => req('POST', '/process/reactor', data),
  calcCompactor: (data) => req('POST', '/process/compactor', data),
}

// Alias for pages that import { client }
export const client = {
  ...api,
  calculate:    (data) => api.calculate(data),
  familyDesign: (data) => req('POST', '/family/design', data),
};
