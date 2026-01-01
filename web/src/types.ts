// Type definitions for standalone app (no OpenAI SDK)
declare global {
  interface Window {
    // Theme and display mode (if needed for standalone app)
    theme?: 'light' | 'dark';
    displayMode?: 'pip' | 'inline' | 'fullscreen';
  }
}

export {};

