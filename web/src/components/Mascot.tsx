/**
 * Mascot Component - "Finley" the Financial Buddy
 * 
 * A blue blob mascot that evolves with the user's progression level.
 * Features multiple animation states and contextual expressions.
 */

import React, { useEffect, useState, useMemo } from 'react';
import { MascotVariant, MASCOT_IMAGES, getMascotPersonality } from '../lib/progression';

// ============================================================================
// TYPES
// ============================================================================

export type MascotState = 'idle' | 'happy' | 'encouraging' | 'celebrating' | 'thinking' | 'sleeping';

export interface MascotProps {
  variant: MascotVariant;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  state?: MascotState;
  level?: number;
  showSpeechBubble?: boolean;
  speechText?: string;
  onClick?: () => void;
  className?: string;
  style?: React.CSSProperties;
  theme?: 'light' | 'dark';
}

// ============================================================================
// SIZE CONFIGURATIONS
// ============================================================================

const SIZES = {
  xs: { width: 24, height: 32 },
  sm: { width: 32, height: 42 },
  md: { width: 64, height: 85 },
  lg: { width: 96, height: 128 },
  xl: { width: 128, height: 170 },
};

// ============================================================================
// CSS KEYFRAMES (Injected once)
// ============================================================================

const KEYFRAMES = `
@keyframes mascot-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

@keyframes mascot-wobble {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(-3deg); }
  75% { transform: rotate(3deg); }
}

@keyframes mascot-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.05); opacity: 0.9; }
}

@keyframes mascot-celebrate {
  0% { transform: scale(1) rotate(0deg); }
  25% { transform: scale(1.1) rotate(-5deg); }
  50% { transform: scale(1.15) rotate(5deg); }
  75% { transform: scale(1.1) rotate(-3deg); }
  100% { transform: scale(1) rotate(0deg); }
}

@keyframes mascot-float {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  25% { transform: translateY(-4px) rotate(1deg); }
  50% { transform: translateY(-2px) rotate(0deg); }
  75% { transform: translateY(-4px) rotate(-1deg); }
}

@keyframes mascot-glow {
  0%, 100% { filter: drop-shadow(0 0 4px rgba(74, 122, 191, 0.3)); }
  50% { filter: drop-shadow(0 0 12px rgba(74, 122, 191, 0.6)); }
}

@keyframes mascot-thinking {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-2px); }
  75% { transform: translateX(2px); }
}

@keyframes mascot-sleep {
  0%, 100% { transform: translateY(0) rotate(0deg); opacity: 0.8; }
  50% { transform: translateY(2px) rotate(-2deg); opacity: 0.6; }
}

@keyframes speech-bubble-pop {
  0% { transform: scale(0) translateY(10px); opacity: 0; }
  50% { transform: scale(1.1) translateY(-2px); opacity: 1; }
  100% { transform: scale(1) translateY(0); opacity: 1; }
}

@keyframes speech-bubble-fade {
  0% { opacity: 1; }
  100% { opacity: 0; transform: translateY(-10px); }
}

@keyframes level-badge-shine {
  0% { background-position: -100% 0; }
  100% { background-position: 200% 0; }
}
`;

// Inject keyframes once
let keyframesInjected = false;
function injectKeyframes() {
  if (keyframesInjected || typeof document === 'undefined') return;
  
  const styleEl = document.createElement('style');
  styleEl.id = 'mascot-keyframes';
  styleEl.textContent = KEYFRAMES;
  document.head.appendChild(styleEl);
  keyframesInjected = true;
}

// ============================================================================
// ANIMATION CONFIGURATIONS
// ============================================================================

const STATE_ANIMATIONS: Record<MascotState, React.CSSProperties> = {
  idle: {
    animation: 'mascot-float 3s ease-in-out infinite',
  },
  happy: {
    animation: 'mascot-bounce 0.6s ease-in-out infinite',
  },
  encouraging: {
    animation: 'mascot-wobble 1s ease-in-out infinite, mascot-glow 2s ease-in-out infinite',
  },
  celebrating: {
    animation: 'mascot-celebrate 0.8s ease-in-out',
  },
  thinking: {
    animation: 'mascot-thinking 2s ease-in-out infinite',
  },
  sleeping: {
    animation: 'mascot-sleep 4s ease-in-out infinite',
  },
};

// ============================================================================
// MASCOT COMPONENT
// ============================================================================

export const Mascot: React.FC<MascotProps> = ({
  variant,
  size = 'md',
  state = 'idle',
  level = 1,
  showSpeechBubble = false,
  speechText,
  onClick,
  className,
  style,
  theme = 'light',
}) => {
  // Inject keyframes on mount
  useEffect(() => {
    injectKeyframes();
  }, []);
  
  // Get size dimensions
  const dimensions = SIZES[size];
  
  // Get mascot image path
  const imagePath = MASCOT_IMAGES[variant];
  
  // Get personality for speech bubbles
  const personality = useMemo(() => getMascotPersonality(level), [level]);
  
  // Auto-generate speech text if not provided
  const displayText = speechText ?? (showSpeechBubble ? personality.greeting : '');
  
  // Random animation delay for multi-instance scenarios
  const [animationDelay] = useState(() => Math.random() * 500);
  
  // Container styles
  const containerStyle: React.CSSProperties = {
    position: 'relative',
    display: 'inline-flex',
    flexDirection: 'column',
    alignItems: 'center',
    cursor: onClick ? 'pointer' : 'default',
    ...style,
  };
  
  // Image wrapper styles with animation
  const imageWrapperStyle: React.CSSProperties = {
    position: 'relative',
    width: dimensions.width,
    height: dimensions.height,
    ...STATE_ANIMATIONS[state],
    animationDelay: `${animationDelay}ms`,
  };
  
  // Image styles
  const imageStyle: React.CSSProperties = {
    width: '100%',
    height: '100%',
    objectFit: 'contain',
    imageRendering: 'auto',
    userSelect: 'none',
    pointerEvents: 'none',
  };
  
  // Level badge styles (shown on md and larger)
  const showBadge = size !== 'xs' && size !== 'sm' && level > 1;
  const badgeStyle: React.CSSProperties = {
    position: 'absolute',
    bottom: -4,
    right: -4,
    backgroundColor: theme === 'dark' ? '#2a2a2a' : '#ffffff',
    border: `2px solid #FFD700`,
    borderRadius: '50%',
    width: size === 'xl' ? 32 : size === 'lg' ? 24 : 20,
    height: size === 'xl' ? 32 : size === 'lg' ? 24 : 20,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: size === 'xl' ? 14 : size === 'lg' ? 12 : 10,
    fontWeight: 700,
    color: '#FFD700',
    boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
    background: theme === 'dark' 
      ? 'linear-gradient(135deg, #2a2a2a 0%, #3a3a3a 100%)'
      : 'linear-gradient(135deg, #ffffff 0%, #f5f5f5 100%)',
  };
  
  // Speech bubble styles
  const speechBubbleStyle: React.CSSProperties = {
    position: 'absolute',
    top: -8,
    left: '50%',
    transform: 'translateX(-50%) translateY(-100%)',
    backgroundColor: theme === 'dark' ? '#2a2a2a' : '#ffffff',
    color: theme === 'dark' ? '#ffffff' : '#000000',
    padding: '8px 12px',
    borderRadius: 12,
    fontSize: size === 'xs' || size === 'sm' ? 10 : 12,
    fontWeight: 500,
    maxWidth: size === 'xl' ? 200 : size === 'lg' ? 160 : 120,
    textAlign: 'center',
    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
    animation: 'speech-bubble-pop 0.4s ease-out forwards',
    whiteSpace: 'nowrap',
    zIndex: 10,
  };
  
  // Speech bubble tail
  const speechBubbleTailStyle: React.CSSProperties = {
    position: 'absolute',
    bottom: -6,
    left: '50%',
    transform: 'translateX(-50%)',
    width: 0,
    height: 0,
    borderLeft: '6px solid transparent',
    borderRight: '6px solid transparent',
    borderTop: `8px solid ${theme === 'dark' ? '#2a2a2a' : '#ffffff'}`,
  };
  
  return (
    <div 
      style={containerStyle} 
      className={className}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {/* Speech Bubble */}
      {showSpeechBubble && displayText && (
        <div style={speechBubbleStyle}>
          {displayText}
          <div style={speechBubbleTailStyle} />
        </div>
      )}
      
      {/* Mascot Image */}
      <div style={imageWrapperStyle}>
        <img 
          src={imagePath} 
          alt={`Finley - Level ${level} ${variant}`}
          style={imageStyle}
          draggable={false}
        />
        
        {/* Level Badge */}
        {showBadge && (
          <div style={badgeStyle}>
            {level}
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// MINI MASCOT (For status bar and compact displays)
// ============================================================================

export interface MiniMascotProps {
  variant: MascotVariant;
  level: number;
  isAnimating?: boolean;
  onClick?: () => void;
  theme?: 'light' | 'dark';
}

export const MiniMascot: React.FC<MiniMascotProps> = ({
  variant,
  level,
  isAnimating = true,
  onClick,
  theme = 'light',
}) => {
  useEffect(() => {
    injectKeyframes();
  }, []);
  
  const imagePath = MASCOT_IMAGES[variant];
  
  const containerStyle: React.CSSProperties = {
    position: 'relative',
    width: 32,
    height: 32,
    borderRadius: '50%',
    overflow: 'hidden',
    backgroundColor: theme === 'dark' ? '#2a2a2a' : '#f5f5f5',
    border: `2px solid ${theme === 'dark' ? '#4A7ABF' : '#4A7ABF'}`,
    cursor: onClick ? 'pointer' : 'default',
    animation: isAnimating ? 'mascot-bounce 2s ease-in-out infinite' : 'none',
    boxShadow: '0 2px 8px rgba(74, 122, 191, 0.3)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  };
  
  const imageStyle: React.CSSProperties = {
    width: '100%',
    height: '100%',
    objectFit: 'contain',
  };
  
  return (
    <div style={containerStyle} onClick={onClick}>
      <img 
        src={imagePath} 
        alt={`Finley Level ${level}`}
        style={imageStyle}
        draggable={false}
      />
    </div>
  );
};

// ============================================================================
// CELEBRATING MASCOT (For milestone completion)
// ============================================================================

export interface CelebratingMascotProps {
  variant: MascotVariant;
  level: number;
  message: string;
  onComplete?: () => void;
  theme?: 'light' | 'dark';
}

export const CelebratingMascot: React.FC<CelebratingMascotProps> = ({
  variant,
  level,
  message,
  onComplete,
  theme = 'light',
}) => {
  useEffect(() => {
    injectKeyframes();
    
    // Trigger onComplete after celebration animation
    if (onComplete) {
      const timer = setTimeout(onComplete, 2000);
      return () => clearTimeout(timer);
    }
  }, [onComplete]);
  
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 16,
    }}>
      <Mascot 
        variant={variant}
        size="lg"
        state="celebrating"
        level={level}
        theme={theme}
      />
      <div style={{
        fontSize: 16,
        fontWeight: 600,
        color: theme === 'dark' ? '#ffffff' : '#000000',
        textAlign: 'center',
        animation: 'speech-bubble-pop 0.6s ease-out forwards',
        animationDelay: '0.3s',
        opacity: 0,
      }}>
        {message}
      </div>
    </div>
  );
};

export default Mascot;

