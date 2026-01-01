import { useSyncExternalStore } from 'react';

type OpenAiGlobals = Window['openai'];

/**
 * Small helper hook that mirrors the Apps SDK example.
 * Lets components subscribe to host-provided globals such as theme or displayMode.
 */
export function useOpenAiGlobal<K extends keyof OpenAiGlobals>(
  key: K,
  fallback: OpenAiGlobals[K] | null = null
): OpenAiGlobals[K] | null {
  return useSyncExternalStore(
    (onChange) => {
      if (typeof window === 'undefined' || !window.addEventListener) {
        return () => {};
      }

      const handler = (event: Event) => {
        const customEvent = event as CustomEvent<{ globals: Partial<OpenAiGlobals> }>;
        if (customEvent.detail?.globals[key] !== undefined) {
          onChange();
        }
      };

      window.addEventListener('openai:set_globals', handler as EventListener, {
        passive: true,
      });

      return () => window.removeEventListener('openai:set_globals', handler as EventListener);
    },
    () => window.openai?.[key] ?? fallback,
    () => window.openai?.[key] ?? fallback
  );
}

