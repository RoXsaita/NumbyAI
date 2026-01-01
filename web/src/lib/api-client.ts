/**
 * API Client - REST API client for NumbyAI backend
 * 
 * Replaces window.openai.callTool() with standard REST API calls
 */
import type { DashboardProps } from '../shared/schemas';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

export interface Transaction {
  id: string;
  date: string;
  description: string;
  merchant: string | null;
  amount: number;
  currency: string;
  category: string;
  bank_name: string;
  profile: string | null;
}

export interface TransactionFilters {
  bank_name?: string;
  category?: string;
  date_from?: string;
  date_to?: string;
}

export interface Budget {
  category: string;
  month_year: string | null;
  amount: number;
  currency: string;
}

export interface Preferences {
  categorization?: any[];
  parsing?: any[];
}

class ApiClient {
  private baseUrl: string;
  private authToken: string | null = null;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
  }

  setAuthToken(token: string | null) {
    this.authToken = token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(error.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  // Chat endpoints
  async sendChatMessage(
    message: string,
    file?: File,
    netFlow?: number
  ): Promise<{ message_id: string; response: string }> {
    const formData = new FormData();
    formData.append('message', message);
    if (file) {
      formData.append('file', file);
    }
    if (netFlow !== undefined) {
      formData.append('net_flow', netFlow.toString());
    }

    const response = await fetch(`${this.baseUrl}/api/chat/messages`, {
      method: 'POST',
      body: formData,
      headers: this.authToken
        ? { Authorization: `Bearer ${this.authToken}` }
        : {},
    });

    if (!response.ok) {
      throw new Error(`Failed to send chat message: ${response.statusText}`);
    }

    return response.json();
  }

  async streamChatResponse(
    messageId: string,
    onChunk: (chunk: string) => void
  ): Promise<void> {
    const response = await fetch(
      `${this.baseUrl}/api/chat/stream?message_id=${messageId}`,
      {
        headers: this.authToken
          ? { Authorization: `Bearer ${this.authToken}` }
          : {},
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to stream chat response: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('Response body is not readable');
    }

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.content) {
              onChunk(data.content);
            }
          } catch (e) {
            // Ignore parse errors
          }
        }
      }
    }
  }

  // Financial data
  async getFinancialData(filters?: {
    bank_name?: string;
    month_year?: string;
    categories?: string[];
    profile?: string;
  }): Promise<DashboardProps> {
    const params = new URLSearchParams();
    if (filters?.bank_name) params.append('bank_name', filters.bank_name);
    if (filters?.month_year) params.append('month_year', filters.month_year);
    if (filters?.categories) {
      filters.categories.forEach(cat => params.append('categories', cat));
    }
    if (filters?.profile) params.append('profile', filters.profile);

    const query = params.toString();
    return this.request<DashboardProps>(
      `/api/financial-data${query ? `?${query}` : ''}`
    );
  }

  // Transactions
  async getTransactions(filters?: TransactionFilters): Promise<{
    transactions: Transaction[];
    count: number;
  }> {
    const params = new URLSearchParams();
    if (filters?.bank_name) params.append('bank_name', filters.bank_name);
    if (filters?.category) params.append('category', filters.category);
    if (filters?.date_from) params.append('date_from', filters.date_from);
    if (filters?.date_to) params.append('date_to', filters.date_to);

    const query = params.toString();
    return this.request<{ transactions: Transaction[]; count: number }>(
      `/api/transactions${query ? `?${query}` : ''}`
    );
  }

  async updateTransaction(
    id: string,
    updates: Partial<Transaction>
  ): Promise<Transaction> {
    return this.request<Transaction>('/api/transactions', {
      method: 'PATCH',
      body: JSON.stringify({ id, updates }),
    });
  }

  // Budgets
  async getBudgets(): Promise<{ budgets: Budget[] }> {
    return this.request<{ budgets: Budget[] }>('/api/budgets');
  }

  async saveBudget(budgets: Budget[]): Promise<void> {
    await this.request('/api/budgets', {
      method: 'POST',
      body: JSON.stringify({ budgets }),
    });
  }

  // Preferences
  async getPreferences(preferenceType?: 'categorization' | 'parsing'): Promise<Preferences> {
    const params = new URLSearchParams();
    if (preferenceType) {
      params.append('preference_type', preferenceType);
    }
    const query = params.toString();
    return this.request<Preferences>(
      `/api/preferences${query ? `?${query}` : ''}`
    );
  }

  async savePreferences(
    preferences: any[],
    preferenceType: 'categorization' | 'parsing' = 'categorization'
  ): Promise<void> {
    await this.request('/api/preferences', {
      method: 'POST',
      body: JSON.stringify({ preferences, preference_type: preferenceType }),
    });
  }

  // Statement upload
  async uploadStatement(
    file: File,
    netFlow?: number,
    bankName?: string
  ): Promise<{
    job_id: string;
    status: string;
    analysis?: any;
    transactions_count?: number;
    transactions?: any[];
  }> {
    const formData = new FormData();
    formData.append('file', file);
    if (netFlow !== undefined) {
      formData.append('net_flow', netFlow.toString());
    }
    if (bankName) {
      formData.append('bank_name', bankName);
    }

    const response = await fetch(`${this.baseUrl}/api/statements/upload`, {
      method: 'POST',
      body: formData,
      headers: this.authToken
        ? { Authorization: `Bearer ${this.authToken}` }
        : {},
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(error.error || `Failed to upload statement: ${response.statusText}`);
    }

    return response.json();
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
