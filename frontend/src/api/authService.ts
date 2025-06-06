import config from '../config';

export interface User {
  id: string;
  username: string;
  email?: string;
  full_name?: string;
  role: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  full_name?: string;
  role?: string;
}

export interface AuthResponse {
  message: string;
  user: User;
  active_tree_id?: string;
}

export interface SessionResponse {
  isAuthenticated: boolean;
  user: User | null;
  active_tree_id?: string;
}

export interface PasswordResetRequest {
  email_or_username: string;
}

export interface PasswordResetData {
  new_password: string;
}

class AuthService {
  private baseUrl = config.apiUrl;

  /**
   * Login user with credentials
   */
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await fetch(`${this.baseUrl}/api/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include', // Include cookies for session management
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Login failed');
    }

    return response.json();
  }

  /**
   * Register new user
   */
  async register(userData: RegisterData): Promise<{ message: string; user: { id: string; username: string } }> {
    const response = await fetch(`${this.baseUrl}/api/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(userData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Registration failed');
    }

    return response.json();
  }

  /**
   * Logout current user
   */
  async logout(): Promise<{ message: string }> {
    const response = await fetch(`${this.baseUrl}/api/logout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Logout failed');
    }

    return response.json();
  }

  /**
   * Check current session status
   */
  async getSession(): Promise<SessionResponse> {
    const response = await fetch(`${this.baseUrl}/api/session`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('Failed to check session status');
    }

    return response.json();
  }

  /**
   * Request password reset
   */
  async requestPasswordReset(data: PasswordResetRequest): Promise<{ message: string }> {
    const response = await fetch(`${this.baseUrl}/api/request-password-reset`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Password reset request failed');
    }

    return response.json();
  }

  /**
   * Reset password with token
   */
  async resetPassword(token: string, data: PasswordResetData): Promise<{ message: string }> {
    const response = await fetch(`${this.baseUrl}/api/reset-password/${token}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Password reset failed');
    }

    return response.json();
  }
}

export const authService = new AuthService();
export default authService;
