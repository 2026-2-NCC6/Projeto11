/**
 * Utilitário de Autenticação JWT e Gerenciamento de Rede do TenniSync.
 * Garante que todas as requisições HTTP e WebSockets transportem as credenciais
 * e resolve URLs dinâmicas para funcionamento em tunnels e redes externas.
 */

const TOKEN_KEY = 'tennisync_access_token';
const USER_KEY = 'tennisync_user_name';

export const authClient = {
  getToken: () => {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },

  setToken: (token) => {
    try {
      if (token) {
        localStorage.setItem(TOKEN_KEY, token);
      } else {
        localStorage.removeItem(TOKEN_KEY);
      }
    } catch (e) {
      console.warn('Erro ao salvar token no localStorage:', e);
    }
  },

  getUser: () => {
    try {
      return localStorage.getItem(USER_KEY) || 'admin';
    } catch {
      return 'admin';
    }
  },

  setUser: (username) => {
    try {
      if (username) {
        localStorage.setItem(USER_KEY, username);
      } else {
        localStorage.removeItem(USER_KEY);
      }
    } catch (e) {
      console.warn('Erro ao salvar usuário no localStorage:', e);
    }
  },

  isAuthenticated: () => {
    return Boolean(authClient.getToken());
  },

  login: async (username, password) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Falha na autenticação. Usuário ou senha incorretos.');
    }

    const data = await res.json();
    authClient.setToken(data.access_token);
    authClient.setUser(data.username || username);
    return data;
  },

  logout: async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' }).catch(() => {});
    } finally {
      authClient.setToken(null);
      authClient.setUser(null);
      window.location.reload();
    }
  },

  /**
   * Wrapper seguro para fetch com inclusão automática do token JWT
   */
  fetchWithAuth: async (url, options = {}) => {
    const token = authClient.getToken();
    const headers = {
      ...(options.headers || {})
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
      // Token expirou ou é inválido
      authClient.setToken(null);
      window.dispatchEvent(new CustomEvent('tennisync:unauthorized'));
    }
    return res;
  },

  /**
   * Constrói URL do WebSocket dinâmica e relativa ao host atual (sem hardcode de porta 8000)
   */
  getWsUrl: (path) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Se o Vite está em modo dev e usando proxy, conectar em window.location.host
    // O proxy do Vite ou o servidor FastAPI repassa /ws/* diretamente.
    const host = window.location.host;
    const token = authClient.getToken();
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    const tokenParam = token ? `?token=${encodeURIComponent(token)}` : '';
    return `${protocol}//${host}${cleanPath}${tokenParam}`;
  }
};

export default authClient;
