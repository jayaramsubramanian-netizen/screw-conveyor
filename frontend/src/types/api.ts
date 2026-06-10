/**
 * TypeScript types mirroring Pydantic schemas exactly.
 */

export interface EngineInput {
  type:            'screw' | 'pipe'
  D:               number
  L:               number
  N:               number
  P:               number
  ang:             number
  mat:             string
  cap:             number
  surge:           number
  use_multipitch?: boolean
  P_in?:           number
  P_out?:          number
  pct_in?:         number
  pct_out?:        number
  shaft_mode?:     'auto' | 'manual'
  shtype?:         'bar' | 'pipe'
  pod?:            number
  pwall?:          number
  sallow?:         number
  prefer_pipe?:    boolean
  support_cond?:   'pinfix' | 'pinned' | 'fixed'
  ft?:             number
  wa?:             number
  temp_c?:         number
  brg?:            string
  hgr_brg?:        string
  gbx?:            string
  bload?:          number
  hangers?:        number | null
  duty?:           number
  contAFact?:      boolean
}

export interface CapResult {
  Qt: number; Qv: number; Qt_raw: number
  Qt_body: number; Qt_inlet: number; Qt_outlet: number; Qt_governing: number
  fill: number; fill_actual: number; feed_ratio: number; eta_L: number
  pipe_transport_derate: number; ok: boolean; req: number; lam_used: number
}

export interface PowerResult {
  Pe: number; Pm: number; Pi: number; Pf: number; Pf_factor: number
  Ps_ideal: number; Ps: number; Pt: number
  motor: number; motor_rated: number; motor_SF: number
}

export interface TorqueResult {
  Tr: number; Tr_max: number; Ts: number; od: number
  tau: number; tau_run: number; shOk: boolean; eff_od_mm: number
  I_m4: number; A_m2: number
}

export interface WearResult {
  v_tip: number; P_contact_kPa: number; P_factor: number
  wrate_mm_h: number; wc: number; thick_mm: number; life_h: number; life_t: number
}

export interface EffResult {
  fill_pct: number; cap_util: number; kWh_t: number
  sug_geom: { D_opt_mm: number; D_next_sm: number | null; N_opt: number; target_Qt: number }
}

export interface EngineResult {
  D: number; L: number; N: number; ang: number; is_pipe: boolean; P_eff: number
  cap: CapResult; pwr: PowerResult; tor: TorqueResult; wear: WearResult; eff: EffResult
  brg_r: Record<string,unknown>; hgr: Record<string,unknown>; gbx_r: Record<string,unknown>
  deflection: number; defl_limit: number; deflection_ok: boolean
  nc: number; nc_ratio: number; vibration_risk: number; vri_label: string
  regime: { name: string }; mat_props?: Record<string,unknown>
}

export interface AxialSegment {
  x: number; fill_pct: number; Qt: number; Qt_cap: number
  pwr_density: number; torque_pm: number; torque_cumul: number
  wear_rate: number; axial_velocity: number
  localAng: number; localPitch: number
  status: 'ok' | 'flood' | 'choke' | 'starve'; isHanger: boolean
}

export interface AxialProfileResult { segments: AxialSegment[] }

export interface FamilyPoint {
  Dmm: number; L: number; N: number; cap: number; cap_ok: boolean
  pwr: number; motor: number; tor: number; shaft_mm: number
  hgr: number; L10: number; kWh: number; cost: number; score: number
}

export interface FamilyResult { pts: FamilyPoint[] }

export interface MaterialOut {
  id: number; name: string; category: string | null; rho: number
  rho_min?: number; rho_max?: number; lambda_ref?: number; fill_max: number
  abr: string; cls: string; particle_class?: string; flowability?: number
  moist: number; aor?: number; cohesion?: number; temp_max?: number
  bridging_risk?: number; flow_regime?: string; confidence?: number
  source?: string; note?: string; cema_code?: string; flags?: string
  app?: string[]; custom: boolean
}

export interface BearingOut {
  id: number; name: string; mfr?: string; type?: string; bore?: number
  C?: number; C0?: number; p?: number; speed_g?: number
  seal?: string; role?: string; mass_kg?: number; note?: string
}

export interface GearboxOut {
  id: number; model: string; type?: string; stages?: number
  Tn: number; Pkw: number; ratio_min?: number; ratio_max?: number
  eta?: number; mount?: string; ip?: string; mass_kg?: number; note?: string
}
