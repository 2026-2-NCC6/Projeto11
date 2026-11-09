import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_CALIBRATION as C, ROOM, project3DTo2D, floorVToZ, mouseToAim,
  createShot, sampleShot, createReturn, sampleReturn, calibrateRoomFromPose, estimateAthlete3D
} from './tennis3DPhysics.js';

const W = 800, H = 600;

test('piso: Z maior fica mais alto na tela (mais ao fundo)', () => {
  const near = project3DTo2D(0, 0, 1.2, C, W, H).v;
  const far = project3DTo2D(0, 0, 3.3, C, W, H).v;
  assert.ok(far < near);
});

test('bola a Y=1,0m em Z=2,7m fica >200px acima do piso', () => {
  const p = project3DTo2D(0, 1.0, 2.7, C, W, H);
  assert.ok(p.floorV - p.v > 200, `delta=${p.floorV - p.v}`);
});

test('inverso do piso devolve Z', () => {
  for (const z of [1.2, 1.8, 2.5, 3.2]) {
    const v = project3DTo2D(0, 0, z, C, W, H).floorV / H;
    assert.ok(Math.abs(floorVToZ(v, C) - z) < 0.01);
  }
});

test('mira: limites OUT', () => {
  assert.equal(mouseToAim(0.5, 0.6).inBounds, true);
  assert.equal(mouseToAim(0.5, 0.9).inBounds, false); // curta demais
  assert.equal(mouseToAim(0.5, 0.2).inBounds, false); // longa demais
  assert.equal(mouseToAim(0.99, 0.6).inBounds, false); // lateral fora
});

test('trajetória: quique no chão (Y=0) e apex ~1,02m', () => {
  const s = createShot(0, 0.8, 1.8);
  const b = sampleShot(s, s.bounceFrac);
  assert.ok(Math.abs(b.y) < 1e-9 && Math.abs(b.z - 1.8) < 1e-9);
  const post = sampleShot(s, s.bounceFrac + (1 - s.bounceFrac) * 0.5);
  assert.ok(Math.abs(post.y - ROOM.apexHeight) < 1e-9);
  const end = sampleShot(s, 1);
  assert.ok(Math.abs(end.y) < 1e-9 && Math.abs(end.z - ROOM.zFall) < 1e-9);
});

test('atleta a ~2,7m: bola passa entre 0,85 e 1,02m de altura', () => {
  const s = createShot(0, 0.5, 1.6);
  let ok = false;
  for (let p = 0.4; p <= 1; p += 0.005) {
    const b = sampleShot(s, p);
    if (Math.abs(b.z - 2.7) < 0.05 && b.y > 0.85) ok = true;
  }
  assert.ok(ok);
});

test('devolução termina na rede e respeita limites laterais', () => {
  const r = createReturn({ x: 1.6, y: 0.95, z: 2.7 }, 0.4);
  const e = sampleReturn(r, 1);
  assert.ok(Math.abs(e.z - ROOM.zNet) < 1e-9 && Math.abs(e.x) <= 1.55);
});

test('calibração e estimativa do atleta', () => {
  const lm = Array.from({ length: 33 }, () => [0.5, 0.5, 1]);
  lm[0] = [0.5, 0.2, 1];
  for (const i of [27, 28, 29, 30, 31, 32]) lm[i] = [0.5, 0.78, 1];
  const c = calibrateRoomFromPose(lm, W, H);
  assert.ok(c && c.calibrated && Math.abs(c.vBack - 0.78) < 1e-9);
  const a = estimateAthlete3D(lm, c);
  assert.ok(a.z >= 2.0 && a.z <= 3.3);
  assert.equal(calibrateRoomFromPose([], W, H), null);
});
