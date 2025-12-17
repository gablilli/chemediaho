/**
 * ClasseViva API Client
 * Handles all direct communication with ClasseViva API from the browser
 * 
 * Architecture Notes:
 * - All API calls are made directly from the user's browser to ClasseViva servers
 * - This avoids IP blocking issues since requests come from residential IPs
 * - Credentials are temporarily stored in sessionStorage (cleared on logout/close)
 * - The backend never communicates with ClasseViva, only handles session management
 * 
 * CORS: ClasseViva API allows cross-origin requests (designed for mobile apps)
 */

const ClasseVivaAPI = {
  BASE_URL: 'https://web.spaggiari.eu/rest/v1',
  API_KEY: 'Tg1NWEwNGIgIC0K',
  USER_AGENT: 'CVVS/std/4.1.7 Android/10',

  /**
   * Login to ClasseViva
   * @param {string} userId - User ID (e.g., G123456789P)
   * @param {string} password - User password
   * @returns {Promise<Object>} Login response with token
   */
  async login(userId, password) {
    const url = `${this.BASE_URL}/auth/login`;
    const headers = {
      'Content-Type': 'application/json',
      'Z-Dev-ApiKey': this.API_KEY,
      'User-Agent': this.USER_AGENT
    };
    const body = {
      ident: null,
      pass: password,
      uid: userId
    };

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        if (response.status === 422) {
          throw new Error('INVALID_CREDENTIALS');
        }
        throw new Error(`HTTP_ERROR_${response.status}`);
      }

      return await response.json();
    } catch (error) {
      if (error.message.startsWith('HTTP_ERROR_') || error.message === 'INVALID_CREDENTIALS') {
        throw error;
      }
      throw new Error('NETWORK_ERROR');
    }
  },

  /**
   * Get student grades
   * @param {string} studentId - Student ID (numeric)
   * @param {string} token - Authentication token
   * @returns {Promise<Object>} Grades data
   */
  async getGrades(studentId, token) {
    const url = `${this.BASE_URL}/students/${studentId}/grades`;
    const headers = {
      'Content-Type': 'application/json',
      'Z-Dev-ApiKey': this.API_KEY,
      'User-Agent': this.USER_AGENT,
      'Z-Auth-Token': token
    };

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: headers
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('TOKEN_EXPIRED');
        }
        throw new Error(`HTTP_ERROR_${response.status}`);
      }

      return await response.json();
    } catch (error) {
      if (error.message.startsWith('HTTP_ERROR_') || error.message === 'TOKEN_EXPIRED') {
        throw error;
      }
      throw new Error('NETWORK_ERROR');
    }
  },

  /**
   * Get student periods
   * @param {string} studentId - Student ID (numeric)
   * @param {string} token - Authentication token
   * @returns {Promise<Object>} Periods data
   */
  async getPeriods(studentId, token) {
    const url = `${this.BASE_URL}/students/${studentId}/periods`;
    const headers = {
      'Content-Type': 'application/json',
      'Z-Dev-ApiKey': this.API_KEY,
      'User-Agent': this.USER_AGENT,
      'Z-Auth-Token': token
    };

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: headers
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('TOKEN_EXPIRED');
        }
        throw new Error(`HTTP_ERROR_${response.status}`);
      }

      return await response.json();
    } catch (error) {
      if (error.message.startsWith('HTTP_ERROR_') || error.message === 'TOKEN_EXPIRED') {
        throw error;
      }
      throw new Error('NETWORK_ERROR');
    }
  },

  /**
   * Extract student ID from user ID
   * @param {string} userId - User ID (e.g., G123456789P)
   * @returns {string} Student ID (numeric only)
   */
  extractStudentId(userId) {
    return userId.replace(/\D/g, '');
  },

  /**
   * Store credentials in sessionStorage
   * @param {string} token - Authentication token
   * @param {string} userId - User ID
   */
  storeCredentials(token, userId) {
    sessionStorage.setItem('cv_token', token);
    sessionStorage.setItem('cv_user_id', userId);
  },

  /**
   * Get stored credentials from sessionStorage
   * @returns {Object|null} Credentials or null if not found
   */
  getStoredCredentials() {
    const token = sessionStorage.getItem('cv_token');
    const userId = sessionStorage.getItem('cv_user_id');
    
    if (token && userId) {
      return { token, userId };
    }
    return null;
  },

  /**
   * Clear stored credentials
   */
  clearCredentials() {
    sessionStorage.removeItem('cv_token');
    sessionStorage.removeItem('cv_user_id');
  }
};

// Make it available globally
window.ClasseVivaAPI = ClasseVivaAPI;
