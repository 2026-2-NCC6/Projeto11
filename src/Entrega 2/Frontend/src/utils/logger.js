// Frontend/src/utils/logger.js
// Sistema unificado de logging, diagnóstico e captura de falhas do TenniSync.

export const LOG_LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
  NONE: 4
};

let currentLogLevel = LOG_LEVELS.DEBUG;
const MAX_RING_BUFFER_SIZE = 500;
const ringBuffer = [];
let nextLogId = 1;
const sampleTimestamps = new Map();

export const TAG_STYLES = {
  'BALL-3D':       'background: #0284c7; color: #ffffff; font-weight: bold; padding: 2px 6px; border-radius: 4px;',
  'BOT-AI':        'background: #9333ea; color: #ffffff; font-weight: bold; padding: 2px 6px; border-radius: 4px;',
  'PRESENCE':      'background: #059669; color: #ffffff; font-weight: bold; padding: 2px 6px; border-radius: 4px;',
  'STROKE-HIT':    'background: #16a34a; color: #ffffff; font-weight: bold; padding: 2px 6px; border-radius: 4px;',
  'STROKE-REJECT': 'background: #d97706; color: #ffffff; font-weight: bold; padding: 2px 6px; border-radius: 4px;',
  'GAME-MISS':     'background: #dc2626; color: #ffffff; font-weight: bold; padding: 2px 6px; border-radius: 4px;',
  'SPATIAL':       'background: #ca8a04; color: #ffffff; font-weight: bold; padding: 2px 6px; border-radius: 4px;',
  'WEBSOCKET':     'background: #0891b2; color: #ffffff; font-weight: bold; padding: 2px 6px; border-radius: 4px;',
  'API-HTTP':      'background: #2563eb; color: #ffffff; font-weight: bold; padding: 2px 6px; border-radius: 4px;',
  'RUNTIME-ERROR': 'background: #b91c1c; color: #ffffff; font-weight: bold; padding: 2px 6px; border-radius: 4px;',
  'SYSTEM':        'background: #475569; color: #ffffff; font-weight: bold; padding: 2px 6px; border-radius: 4px;'
};

const isBrowser = typeof window !== 'undefined' && typeof window.document !== 'undefined';

function formatTimestamp(d = new Date()) {
  const pad = (n, w = 2) => String(n).padStart(w, '0');
  const hh = pad(d.getHours());
  const mm = pad(d.getMinutes());
  const ss = pad(d.getSeconds());
  const ms = pad(d.getMilliseconds(), 3);
  return `${hh}:${mm}:${ss}.${ms}`;
}

function addToRingBuffer(levelName, tag, message, data) {
  const now = new Date();
  const entry = {
    id: nextLogId++,
    timestamp: now.getTime(),
    timeStr: formatTimestamp(now),
    level: levelName,
    tag,
    message,
    data: data !== null && data !== undefined ? data : null
  };

  if (ringBuffer.length >= MAX_RING_BUFFER_SIZE) {
    ringBuffer.shift();
  }
  ringBuffer.push(entry);
}

function emitLog(levelNum, levelName, tag, message, data = null) {
  addToRingBuffer(levelName, tag, message, data);

  if (currentLogLevel > levelNum) return;

  const time = formatTimestamp();
  const tagStyle = TAG_STYLES[tag] || TAG_STYLES.SYSTEM;

  if (isBrowser) {
    let msgStyle = 'color: #94a3b8;';
    if (levelName === 'INFO') msgStyle = 'color: #f8fafc; font-weight: 500;';
    if (levelName === 'WARN') msgStyle = 'color: #facc15; font-weight: bold;';
    if (levelName === 'ERROR') msgStyle = 'color: #ef4444; font-weight: bold;';

    const prefix = `%c${time}%c %c${tag}%c ${message}`;
    const args = [
      prefix,
      'color: #64748b; font-size: 11px;',
      '',
      tagStyle,
      msgStyle
    ];

    if (data !== null && data !== undefined) {
      args.push(data);
    }

    if (levelName === 'DEBUG') console.debug(...args);
    else if (levelName === 'INFO') console.log(...args);
    else if (levelName === 'WARN') console.warn(...args);
    else if (levelName === 'ERROR') console.error(...args);
  } else {
    // Node.js / CLI mode (test runner)
    const dataStr = data !== null && data !== undefined ? ` ${JSON.stringify(data)}` : '';
    console.log(`[${time}] [${levelName}] [${tag}] ${message}${dataStr}`);
  }
}

export const logger = {
  LEVELS: LOG_LEVELS,

  setLevel: (level) => {
    if (typeof level === 'string') {
      const upper = level.toUpperCase();
      if (LOG_LEVELS[upper] !== undefined) {
        currentLogLevel = LOG_LEVELS[upper];
        emitLog(LOG_LEVELS.INFO, 'INFO', 'SYSTEM', `Nível de log ajustado para: ${upper}`);
        return true;
      }
    } else if (typeof level === 'number' && level >= 0 && level <= 4) {
      currentLogLevel = level;
      return true;
    }
    return false;
  },

  getLevel: () => currentLogLevel,

  debug: (tag, message, data = null) => emitLog(LOG_LEVELS.DEBUG, 'DEBUG', tag, message, data),
  info:  (tag, message, data = null) => emitLog(LOG_LEVELS.INFO,  'INFO',  tag, message, data),
  warn:  (tag, message, data = null) => emitLog(LOG_LEVELS.WARN,  'WARN',  tag, message, data),
  error: (tag, message, data = null) => emitLog(LOG_LEVELS.ERROR, 'ERROR', tag, message, data),

  /**
   * Log com amostragem periódica (evita flood em loops de 60 FPS).
   */
  sample: (key, intervalMs, levelName, tag, message, data = null) => {
    const now = Date.now();
    const last = sampleTimestamps.get(key) || 0;
    if (now - last >= intervalMs) {
      sampleTimestamps.set(key, now);
      const lvl = String(levelName || 'DEBUG').toUpperCase();
      const num = LOG_LEVELS[lvl] !== undefined ? LOG_LEVELS[lvl] : LOG_LEVELS.DEBUG;
      emitLog(num, lvl, tag, message, data);
      return true;
    }
    return false;
  },

  /**
   * Wrapper seguro para fetch com medição de tempo e logging automático de falhas.
   */
  fetchWithLog: async (url, options = {}, tag = 'API-HTTP') => {
    const method = (options.method || 'GET').toUpperCase();
    const start = Date.now();
    try {
      const res = await fetch(url, options);
      const durationMs = Date.now() - start;
      if (!res.ok) {
        logger.error(tag, `Requisição HTTP falhou (${method} ${url} -> ${res.status} ${res.statusText}) [${durationMs}ms]`);
      } else {
        logger.debug(tag, `Requisição HTTP concluída (${method} ${url} -> ${res.status}) [${durationMs}ms]`);
      }
      return res;
    } catch (err) {
      const durationMs = Date.now() - start;
      logger.error(tag, `Erro de rede ao executar ${method} ${url} [${durationMs}ms]`, {
        error: err?.message || String(err),
        stack: err?.stack
      });
      return null;
    }
  },

  /**
   * Retorna histórico em memória do ring buffer.
   */
  getHistory: (filterTag = null, minLevel = null) => {
    return ringBuffer.filter(entry => {
      if (filterTag && entry.tag !== filterTag) return false;
      if (minLevel !== null && LOG_LEVELS[entry.level] < minLevel) return false;
      return true;
    });
  },

  /**
   * Limpa o ring buffer.
   */
  clearHistory: () => {
    ringBuffer.length = 0;
    sampleTimestamps.clear();
  },

  /**
   * Exporta todo o histórico como string JSON formatada.
   */
  dump: () => {
    return JSON.stringify(ringBuffer, null, 2);
  }
};

// Registra listeners globais no navegador
if (isBrowser) {
  window.TenniSyncLogger = logger;
  window.setTenniSyncLogLevel = (lvl) => logger.setLevel(lvl);

  window.addEventListener('error', (event) => {
    logger.error('RUNTIME-ERROR', `Erro global não capturado: ${event.message}`, {
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      stack: event.error?.stack || null
    });
  });

  window.addEventListener('unhandledrejection', (event) => {
    logger.error('RUNTIME-ERROR', 'Promise rejeitada não tratada', {
      reason: event.reason?.message || String(event.reason),
      stack: event.reason?.stack || null
    });
  });

  logger.info('SYSTEM', 'Logger TenniSync inicializado no navegador com sucesso.');
}

export default logger;
