/**
 * Application Configuration
 *
 * Centralized configuration for the Finance App widgets.
 * Allows switching between mock data (dev mode) and real tool data (production).
 *
 * Usage:
 * - In development: Use mock data for fast iteration without backend
 * - In production: Use real tool responses from the MCP server
 *
 * Set the DATA_SOURCE environment variable to control behavior:
 * - DATA_SOURCE=mock → Use mock data from mocks/dashboard-mock-data.ts
 * - DATA_SOURCE=tool → Use real data from window.openai.toolOutput (default)
 */

// ============================================================================
// TYPES
// ============================================================================

export type DataSource = 'mock' | 'tool';

export interface AppConfig {
  /**
   * Where to get widget data from
   */
  dataSource: DataSource;

  /**
   * Enable debug logging
   */
  debug: boolean;

  /**
   * Widget version
   */
  version: string;
}

// ============================================================================
// ENVIRONMENT DETECTION
// ============================================================================

/**
 * Detect if we're running in development mode
 */
function isDevelopment(): boolean {
  // Check if we're in a dev environment
  // In production (ChatGPT), window.openai will always exist
  // In local dev, it might not
  return !window.openai || import.meta.env?.MODE === 'development';
}

/**
 * Get data source from environment or auto-detect
 */
function getDataSource(): DataSource {
  // Explicit environment variable takes precedence
  const envSource = import.meta.env?.DATA_SOURCE;
  if (envSource === 'mock' || envSource === 'tool') {
    return envSource;
  }

  // Auto-detect based on environment
  // If window.openai doesn't exist, we're definitely in mock mode
  if (!window.openai) {
    return 'mock';
  }

  // Default to tool mode in production
  return 'tool';
}

/**
 * Enable debug mode based on environment
 */
function isDebugEnabled(): boolean {
  return import.meta.env?.DEBUG === 'true' || isDevelopment();
}

// ============================================================================
// CONFIGURATION
// ============================================================================

/**
 * Application configuration object
 */
export const config: AppConfig = {
  dataSource: getDataSource(),
  debug: isDebugEnabled(),
  version: '1.0.0',
};

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Check if we're using mock data
 */
export function isUsingMockData(): boolean {
  return config.dataSource === 'mock';
}

/**
 * Check if we're using tool data
 */
export function isUsingToolData(): boolean {
  return config.dataSource === 'tool';
}

/**
 * Log configuration on startup (if debug enabled)
 */
if (config.debug) {
  console.log('[Config] Application configuration:', {
    dataSource: config.dataSource,
    debug: config.debug,
    version: config.version,
    hasOpenAI: !!window.openai,
    environment: isDevelopment() ? 'development' : 'production',
  });
}
