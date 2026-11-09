/**
 * Motor físico 3D métrico do TenniSync (sala de até 3,5m x 3,5m).
 * Eixos: X = largura (-1,75..+1,75 m), Y = altura acima do piso (m), Z = profundidade
 * (0 = webcam/tela, 0,6 = rede, 3,5 = parede do fundo).
 * A geometria da sala é fixa (calibração); só o atleta se move dentro dela.
 */

export const ROOM = {
  halfWidth: 1.75,
  zNet: 0.6,
  zBack: 3.5,
  zBackLine: 3.35,
  zService: 1.85,
  zBounceMin: 1.1,
  zBounceMax: 2.6,
  xInBounds: 1.6,
  zFall: 3.45,
  apexHeight: 1.02,
  serveHeight: 1.05
};

export const DEFAULT_CALIBRATION = {
  vBack: 0.80,       // linha chão/parede do fundo (fração da altura da tela)
  vFront: 0.97,      // borda frontal do piso visível (Z = rede)
  ppmBack: 0.30,     // fração da altura da tela por metro vertical em Z = 3,5 m
  halfWBack: 0.36,   // meia-largura da sala em Z = 3,5 m (fração da largura da tela)
  halfWFront: 0.62,  // meia-largura da sala em Z = rede
  calibrated: false
};

const SPREAD = 0.55; // compressão perceptiva para manter a profundidade legível

export const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
export const lerp = (a, b, t) => a + (b - a) * t;

/** Fator de perspectiva t em [0,1]: 0 na parede do fundo, 1 na rede. */
export function perspT(z) {
  const zc = clamp(z, 0.4, 3.6);
  const t = (1 / zc - 1 / ROOM.zBack) / (1 / ROOM.zNet - 1 / ROOM.zBack);
  return clamp(t, 0, 1.2);
}

export function floorV(z, c = DEFAULT_CALIBRATION) {
  return c.vBack + Math.pow(perspT(z), SPREAD) * (c.vFront - c.vBack);
}

export function pxPerMeterY(z, c = DEFAULT_CALIBRATION) {
  return c.ppmBack * Math.pow(ROOM.zBack / clamp(z, 0.4, 3.6), 0.65);
}

export function halfWidthNorm(z, c = DEFAULT_CALIBRATION) {
  return c.halfWBack + Math.pow(perspT(z), SPREAD) * (c.halfWFront - c.halfWBack);
}

/** Projeta [X,Y,Z] (metros) em pixels do canvas. */
export function project3DTo2D(x, y, z, c, width, height) {
  const vf = floorV(z, c);
  const ppm = pxPerMeterY(z, c);
  return {
    u: (0.5 + (x / ROOM.halfWidth) * halfWidthNorm(z, c)) * width,
    v: (vf - y * ppm) * height,
    floorV: vf * height,
    radiusPx: Math.max(5, ppm * height * 0.075)
  };
}

/** Inverso do piso: v normalizado (0..1) -> profundidade Z. */
export function floorVToZ(v, c = DEFAULT_CALIBRATION) {
  const tt = (v - c.vBack) / (c.vFront - c.vBack);
  if (tt <= 0) return ROOM.zBack - 0.1;
  const t = Math.pow(Math.min(tt, 1.2), 1 / SPREAD);
  return clamp(1 / (1 / ROOM.zBack + t * (1 / ROOM.zNet - 1 / ROOM.zBack)), ROOM.zNet, ROOM.zBack);
}

/** Converte u normalizado (0..1) em X métrico na profundidade Z. */
export function uToX(u, z, c = DEFAULT_CALIBRATION) {
  return ((u - 0.5) / halfWidthNorm(z, c)) * ROOM.halfWidth;
}

/** Mouse (normalizado) -> ponto de mira no piso da sala. y alto = bola mais funda. */
export function mouseToAim(mx, my) {
  const z = ROOM.zNet + ((0.92 - my) / (0.92 - 0.15)) * (ROOM.zBack - ROOM.zNet);
  const x = (mx - 0.5) * 2 * ROOM.halfWidth;
  const inBounds = Math.abs(x) <= ROOM.xInBounds && z >= ROOM.zBounceMin && z <= ROOM.zBounceMax;
  return { x: clamp(x, -ROOM.halfWidth, ROOM.halfWidth), z, inBounds };
}

export function describeDepth(z) {
  if (z < ROOM.zBounceMin) return 'OUT (curta demais)';
  if (z < 1.6) return 'CURTA';
  if (z < 2.1) return 'MÉDIA';
  if (z <= ROOM.zBounceMax) return 'FUNDO';
  return 'OUT (longa demais)';
}

/**
 * Calibra a sala a partir de uma pose com o atleta encostado na parede do fundo (Z = 3,5 m).
 * landmarks: [[x,y,vis]...] normalizados. Retorna null se a pose for insuficiente.
 */
export function calibrateRoomFromPose(landmarks, width, height) {
  if (!landmarks || landmarks.length < 33) return null;
  let footY = 0;
  for (const i of [27, 28, 29, 30, 31, 32]) {
    const lm = landmarks[i];
    if (lm && (lm[2] === undefined || lm[2] > 0.35)) footY = Math.max(footY, lm[1]);
  }
  const nose = landmarks[0];
  if (!nose || footY <= 0.3 || footY >= 0.98 || footY - nose[1] < 0.2) return null;
  const ppmBack = (footY - nose[1]) / 1.62; // nariz ~1,62 m para adulto de 1,75 m
  return {
    ...DEFAULT_CALIBRATION,
    vBack: footY,
    ppmBack,
    halfWBack: clamp((ROOM.halfWidth * ppmBack * height) / width, 0.2, 0.48),
    calibrated: true
  };
}

/** Posição 3D do atleta (metros) a partir dos landmarks. */
export function estimateAthlete3D(landmarks, c = DEFAULT_CALIBRATION) {
  if (!landmarks || landmarks.length < 33) return null;
  let footY = 0;
  for (const i of [27, 28, 29, 30, 31, 32]) {
    const lm = landmarks[i];
    if (lm && (lm[2] === undefined || lm[2] > 0.35)) footY = Math.max(footY, lm[1]);
  }
  if (footY <= 0.3) return null;
  const z = clamp(floorVToZ(footY, c), 2.0, 3.3);
  const hip = landmarks[23] && landmarks[24] ? (landmarks[23][0] + landmarks[24][0]) / 2 : 0.5;
  const w15 = landmarks[15], w16 = landmarks[16];
  const wrist = Math.abs((w15?.[0] ?? hip) - hip) > Math.abs((w16?.[0] ?? hip) - hip) ? w15 : w16;
  const wristU = wrist ? wrist[0] : hip;
  return { x: uToX(hip, z, c), z, wristX: uToX(wristU, z, c), swing: wristU - hip, footV: footY };
}

/** Cria um lance do mouse: sai da rede, quica em (x1,z1) e sobe em direção ao atleta. */
export function createShot(x0, x1, z1) {
  const x2 = clamp(x1 + (x1 - x0) * 0.35, -1.65, 1.65);
  return { x0, x1, z1, x2, bounceFrac: 0.4 };
}

/**
 * Avalia o lance em p (0..1+). Parábola 1: rede -> 1º quique (Y=0). Parábola 2: quique -> fundo,
 * com apex 1,02 m; se o atleta não rebater cai (Y=0) em Z=3,45 m.
 */
export function sampleShot(shot, p) {
  const bf = shot.bounceFrac;
  if (p < bf) {
    const u = clamp(p / bf, 0, 1);
    return {
      phase: 'pre',
      x: lerp(shot.x0, shot.x1, u),
      z: lerp(ROOM.zNet, shot.z1, u),
      y: ROOM.serveHeight * (1 - u * u) + 0.6 * u * (1 - u),
      bounced: false
    };
  }
  const v = clamp((p - bf) / (1 - bf), 0, 1.0);
  return {
    phase: 'post',
    x: lerp(shot.x1, shot.x2, v),
    z: lerp(shot.z1, ROOM.zFall, v),
    y: 4 * ROOM.apexHeight * v * (1 - v),
    bounced: true,
    v
  };
}

/** Devolução: do ponto de impacto até a altura da rede, em direção ao mouse. */
export function createReturn(impact, swing) {
  const xRet = clamp(-impact.x * 0.65 + swing * 3.0, -1.55, 1.55);
  return { x0: impact.x, y0: impact.y, z0: impact.z, x1: xRet };
}

export function sampleReturn(ret, p) {
  const q = clamp(p, 0, 1);
  return {
    x: lerp(ret.x0, ret.x1, q),
    z: lerp(ret.z0, ROOM.zNet, q),
    y: lerp(ret.y0, 1.0, q) + 0.4 * 4 * q * (1 - q)
  };
}
