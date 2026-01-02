/**
 * API Client - REST API client for NumbyAI backend
 * 
 * Replaces window.openai.callTool() with standard REST API calls
 */
import type { DashboardProps } from '../shared/schemas';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  'http://localhost:8000';

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
  preferences?: any[];
  settings?: any;
  summary?: any;
  categorization?: any[];
  parsing?: any[];
}

export type CategoryMutationOperation =
  | {
      type: 'edit';
      category: string;
      new_amount: number;
      note?: string;
    }
  | {
      type: 'transfer';
      from_category: string;
      to_category: string;
      transfer_amount: number;
      note?: string;
    };

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
    message: string,
    onChunk: (chunk: string) => void,
    onComplete?: () => void,
    onError?: (error: string) => void
  ): Promise<void> {
    const params = new URLSearchParams();
    params.append('message', message);
    if (this.authToken) {
      // Note: SSE doesn't support custom headers in some browsers, 
      // so we might need to pass token as query param or use cookies
      params.append('user_id', ''); // Can be enhanced with actual user ID
    }

    const response = await fetch(
      `${this.baseUrl}/api/chat/stream?${params.toString()}`,
      {
        headers: this.authToken
          ? { Authorization: `Bearer ${this.authToken}` }
          : {},
      }
    );

    if (!response.ok) {
      const error = `Failed to stream chat response: ${response.statusText}`;
      if (onError) onError(error);
      throw new Error(error);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      const error = 'Response body is not readable';
      if (onError) onError(error);
      throw new Error(error);
    }

    try {
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Keep the last incomplete line in buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === 'content' && data.content) {
                onChunk(data.content);
              } else if (data.type === 'done') {
                if (onComplete) onComplete();
                return;
              } else if (data.type === 'error') {
                const error = data.content || 'Unknown error';
                if (onError) onError(error);
                throw new Error(error);
              }
            } catch (e) {
              // Ignore parse errors for malformed JSON
              if (e instanceof Error && e.message !== 'Unexpected end of JSON input') {
                console.warn('Failed to parse SSE data:', e);
              }
            }
          }
        }
      }

      // Process any remaining buffer
      if (buffer.trim()) {
        const line = buffer.trim();
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'content' && data.content) {
              onChunk(data.content);
            }
          } catch (e) {
            // Ignore parse errors
          }
        }
      }

      if (onComplete) onComplete();
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      if (onError) onError(errorMsg);
      throw error;
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
  async getPreferences(
    preferenceType?: 'categorization' | 'parsing' | 'settings' | 'list',
    bankName?: string
  ): Promise<Preferences> {
    const params = new URLSearchParams();
    if (preferenceType) {
      params.append('preference_type', preferenceType);
    }
    if (bankName) {
      params.append('bank_name', bankName);
    }
    const query = params.toString();
    return this.request<Preferences>(
      `/api/preferences${query ? `?${query}` : ''}`
    );
  }

  async savePreferences(
    preferences: any[],
    preferenceType: 'categorization' | 'parsing' | 'settings' = 'categorization'
  ): Promise<void> {
    await this.request('/api/preferences', {
      method: 'POST',
      body: JSON.stringify({ preferences, preference_type: preferenceType }),
    });
  }

  async deletePreference(preferenceId: string): Promise<void> {
    await this.request(`/api/preferences/${preferenceId}`, {
      method: 'DELETE',
    });
  }

  async mutateCategories(input: {
    operations: CategoryMutationOperation[];
    bank_name?: string;
    month_year?: string;
  }): Promise<{ updated_categories: Record<string, number>; change_summary: any[]; status: string }> {
    return this.request('/api/mutate-categories', {
      method: 'POST',
      body: JSON.stringify(input),
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
    currency_detected?: string | null;
    currency_required?: boolean;
    parsing_preferences_exist?: boolean;
    detected_headers?: string[];
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

  // Banks management
  async getBanks(): Promise<{ banks: string[] }> {
    const response = await this.request<any>('/api/preferences?preference_type=settings');
    // Response structure: { settings: { registered_banks: [...] } }
    const settings = response?.settings || {};
    return { banks: settings.registered_banks || [] };
  }

  async addBank(bankName: string): Promise<void> {
    const currentBanks = await this.getBanks();
    const updatedBanks = [...currentBanks.banks, bankName];
    await this.savePreferences(
      [{
        registered_banks: updatedBanks
      }],
      'settings'
    );
  }

  // Currency management
  async saveCurrency(currency: string): Promise<void> {
    await this.savePreferences(
      [{
        functional_currency: currency
      }],
      'settings'
    );
  }

  async getCurrency(): Promise<string | null> {
    const response = await this.request<any>('/api/preferences?preference_type=settings');
    // Response structure: { settings: { functional_currency: "USD" } }
    const settings = response?.settings || {};
    return settings.functional_currency || null;
  }

  // Header mapping
  async saveHeaderMapping(
    bankName: string,
    mapping: {
      column_mappings: any;  // New structure: field type -> column reference
      has_headers?: boolean;
      first_transaction_row?: number;
      date_format?: string;
      currency?: string;
    }
  ): Promise<void> {
    console.log('[API] saveHeaderMapping called with:', {
      bankName,
      column_mappings: mapping.column_mappings,
      first_transaction_row: mapping.first_transaction_row
    });

    const schema = {
      column_mappings: mapping.column_mappings || {},
      date_format: mapping.date_format || 'DD/MM/YYYY',
      currency: mapping.currency || 'USD',
      has_headers: mapping.has_headers ?? true,
      skip_rows: 0,  // Will be calculated from first_transaction_row in parser
      first_transaction_row: mapping.first_transaction_row || 1,
      amount_positive_is: 'debit',
    };

    console.log('[API] Sending schema to backend:', schema);

    await this.savePreferences(
      [{
        name: `parsing_${bankName}_csv`,
        bank_name: bankName,
        rule: schema  // Use 'rule' field for parsing preferences
      }],
      'parsing'
    );

    console.log('[API] saveHeaderMapping completed successfully');
  }

  // Process statement with all collected data
  async processStatement(
    file: File,
    bankName: string,
    netFlow?: number,
    headerMapping?: {
      column_mappings: any;
      has_headers?: boolean;
      first_transaction_row?: number;
      date_format?: string;
      currency?: string;
    }
  ): Promise<{
    status: string;
    transactions_processed?: number;
    categories?: number;
    dashboard?: any;
    message?: string;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('bank_name', bankName);
    if (netFlow !== undefined) {
      formData.append('net_flow', netFlow.toString());
    }
    if (headerMapping) {
      formData.append('header_mapping', JSON.stringify(headerMapping));
    }

    const response = await fetch(`${this.baseUrl}/api/statements/process`, {
      method: 'POST',
      body: formData,
      headers: this.authToken
        ? { Authorization: `Bearer ${this.authToken}` }
        : {},
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(error.error || `Failed to process statement: ${response.statusText}`);
    }

    return response.json();
  }

  async processStatementStream(
    file: File,
    bankName: string,
    netFlow: number | undefined,
    headerMapping: {
      column_mappings: any;
      has_headers?: boolean;
      first_transaction_row?: number;
      date_format?: string;
      currency?: string;
    } | undefined,
    onEvent?: (event: any) => void
  ): Promise<{
    status: string;
    transactions_processed?: number;
    categories?: number;
    dashboard?: any;
    message?: string;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('bank_name', bankName);
    if (netFlow !== undefined) {
      formData.append('net_flow', netFlow.toString());
    }
    if (headerMapping) {
      formData.append('header_mapping', JSON.stringify(headerMapping));
    }

    const response = await fetch(`${this.baseUrl}/api/statements/process-stream`, {
      method: 'POST',
      body: formData,
      headers: {
        Accept: 'text/event-stream',
        ...(this.authToken ? { Authorization: `Bearer ${this.authToken}` } : {}),
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(error.error || `Failed to process statement: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('Response body is not readable');
    }

    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data:')) continue;

        const payload = trimmed.slice(5).trim();
        if (!payload) continue;

        try {
          const event = JSON.parse(payload);
          if (event.type === 'complete') {
            return event.result;
          }
          if (event.type === 'error') {
            throw new Error(event.error || 'Processing failed');
          }
          if (onEvent) onEvent(event);
        } catch (e) {
          // Ignore malformed JSON fragments
        }
      }
    }

    throw new Error('Processing stream ended without completion');
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
