import test from 'node:test';
import assert from 'node:assert/strict';
import { logger, LOG_LEVELS } from './logger.js';

test('TenniSync Logger - Níveis e Configuração', () => {
  logger.clearHistory();
  logger.setLevel('WARN');
  assert.equal(logger.getLevel(), LOG_LEVELS.WARN);

  logger.debug('BALL-3D', 'Mensagem de debug - não deve entrar no console mas grava no buffer');
  logger.info('PRESENCE', 'Mensagem de info');
  logger.warn('GAME-MISS', 'Mensagem de warn');
  logger.error('RUNTIME-ERROR', 'Mensagem de error');

  const history = logger.getHistory();
  assert.equal(history.length, 5); // 1 do setLevel + 4 das mensagens
  assert.equal(history[history.length - 1].tag, 'RUNTIME-ERROR');
  assert.equal(history[history.length - 1].level, 'ERROR');

  logger.setLevel('DEBUG');
});

test('TenniSync Logger - Filtro por Tag e Ring Buffer', () => {
  logger.clearHistory();
  logger.info('BALL-3D', 'Bola lançada');
  logger.info('BOT-AI', 'Bot calculando');
  logger.info('BALL-3D', 'Bola quicou');

  const ballLogs = logger.getHistory('BALL-3D');
  assert.equal(ballLogs.length, 2);
  assert.equal(ballLogs[0].message, 'Bola lançada');
  assert.equal(ballLogs[1].message, 'Bola quicou');

  const botLogs = logger.getHistory('BOT-AI');
  assert.equal(botLogs.length, 1);
  assert.equal(botLogs[0].message, 'Bot calculando');

  const dumped = logger.dump();
  assert.ok(dumped.includes('Bola lançada'));
  assert.ok(dumped.includes('Bot calculando'));
});

test('TenniSync Logger - Amostragem periódica (sampling)', () => {
  logger.clearHistory();
  
  // Primeira chamada: deve emitir
  const first = logger.sample('test_key', 1000, 'DEBUG', 'SPATIAL', 'Coord 1');
  assert.equal(first, true);

  // Segunda chamada imediata: deve ser throttled (retorna false)
  const second = logger.sample('test_key', 1000, 'DEBUG', 'SPATIAL', 'Coord 2');
  assert.equal(second, false);

  const logs = logger.getHistory('SPATIAL');
  assert.equal(logs.length, 1);
  assert.equal(logs[0].message, 'Coord 1');
});

test('TenniSync Logger - fetchWithLog captura erros de conexão graciosamente', async () => {
  logger.clearHistory();

  // URL inválida para simular falha de rede sem quebrar a execução
  const res = await logger.fetchWithLog('http://127.0.0.1:59999/invalid-route-for-test', { method: 'POST' }, 'API-HTTP');
  assert.equal(res, null);

  const errorLogs = logger.getHistory('API-HTTP');
  assert.ok(errorLogs.length >= 1);
  assert.equal(errorLogs[0].level, 'ERROR');
  assert.ok(errorLogs[0].message.includes('Erro de rede'));
});
