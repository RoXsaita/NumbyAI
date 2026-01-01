// Type definitions for window.openai API
declare global {
  interface Window {
    openai?: {
      toolInput: any;
      toolOutput: any;
      toolResponseMetadata: any;
      widgetState: any;
      theme: 'light' | 'dark';
      userAgent: any;
      locale: string;
      maxHeight: number;
      displayMode: 'pip' | 'inline' | 'fullscreen';
      safeArea: any;
      
      callTool: (name: string, args: Record<string, unknown>) => Promise<any>;
      sendFollowupMessage: (args: { prompt: string }) => Promise<void>;
      openExternal: (payload: { href: string }) => void;
      requestDisplayMode: (args: { mode: 'pip' | 'inline' | 'fullscreen' }) => Promise<{ mode: string }>;
      setWidgetState: (state: any) => Promise<void>;
      notifyIntrinsicHeight: (height: number) => void;
    };
  }
}

export {};

