import { useEffect, useRef } from 'react';

/**
 * Hook to report the component's intrinsic height to the host.
 * This helps avoid infinite resizing loops by letting the host know
 * exactly how tall the content is.
 */
export function useIntrinsicHeight() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // If the API is not available, do nothing
    if (!window.openai?.notifyIntrinsicHeight) return;

    const element = ref.current;
    if (!element) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        // Use borderBoxSize if available, fallback to contentRect
        let height = 0;
        if (entry.borderBoxSize && entry.borderBoxSize.length > 0) {
          height = entry.borderBoxSize[0].blockSize;
        } else {
          height = entry.contentRect.height;
        }

        // Report the height to the host
        // Add a small buffer or ceil to avoid subpixel issues
        window.openai?.notifyIntrinsicHeight?.(Math.ceil(height));
      }
    });

    observer.observe(element);

    return () => observer.disconnect();
  }, []);

  return ref;
}

