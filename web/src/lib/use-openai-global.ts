/**
 * DEPRECATED: This file is no longer needed after removing OpenAI Apps SDK.
 * 
 * For theme/display mode, use direct window access or a proper state management solution.
 * 
 * This file is kept for backward compatibility but should not be used in new code.
 */

// Simple theme hook replacement
export function useTheme(): 'light' | 'dark' {
  // Default to light theme for standalone app
  return window.theme || 'light';
}

// Simple display mode hook replacement
export function useDisplayMode(): 'pip' | 'inline' | 'fullscreen' {
  // Default to fullscreen for standalone app
  return window.displayMode || 'fullscreen';
}

