/**
 * Confetti Component - Celebration Animation
 * 
 * Shows a burst of confetti particles when a milestone is claimed.
 * Uses CSS animations with randomized colors and positions.
 */

import React, { useEffect, useState, useMemo } from 'react';

// ============================================================================
// CSS KEYFRAMES
// ============================================================================

const KEYFRAMES = `
@keyframes confetti-fall {
  0% {
    transform: translateY(-100vh) rotate(0deg);
    opacity: 1;
  }
  100% {
    transform: translateY(100vh) rotate(720deg);
    opacity: 0;
  }
}

@keyframes confetti-sway {
  0%, 100% { margin-left: 0; }
  25% { margin-left: 30px; }
  50% { margin-left: -10px; }
  75% { margin-left: 20px; }
}

@keyframes level-up-overlay {
  0% { opacity: 0; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.1); }
  100% { opacity: 0; transform: scale(1); }
}

@keyframes star-burst {
  0% { transform: scale(0) rotate(0deg); opacity: 1; }
  50% { transform: scale(1.5) rotate(180deg); opacity: 0.8; }
  100% { transform: scale(0) rotate(360deg); opacity: 0; }
}

@keyframes celebrate-text {
  0% { transform: scale(0.5); opacity: 0; }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); opacity: 1; }
}
`;

let keyframesInjected = false;
function injectKeyframes() {
  if (keyframesInjected || typeof document === 'undefined') return;
  
  const existing = document.getElementById('confetti-keyframes');
  if (existing) return;
  
  const styleEl = document.createElement('style');
  styleEl.id = 'confetti-keyframes';
  styleEl.textContent = KEYFRAMES;
  document.head.appendChild(styleEl);
  keyframesInjected = true;
}

// ============================================================================
// TYPES
// ============================================================================

export interface ConfettiProps {
  theme?: 'light' | 'dark';
  particleCount?: number;
  duration?: number;
  colors?: string[];
}

interface Particle {
  id: number;
  x: number;
  color: string;
  size: number;
  delay: number;
  swayDuration: number;
  fallDuration: number;
  shape: 'circle' | 'square' | 'triangle' | 'star';
}

// ============================================================================
// CONSTANTS
// ============================================================================

const DEFAULT_COLORS = [
  '#dc2626', // Red (primary)
  '#FFD700', // Gold
  '#4A7ABF', // Finley Blue
  '#16a34a', // Success Green
  '#8B5CF6', // Purple
  '#EC4899', // Pink
  '#F59E0B', // Amber
];

const SHAPES = ['circle', 'square', 'triangle', 'star'] as const;

// ============================================================================
// COMPONENT
// ============================================================================

export const Confetti: React.FC<ConfettiProps> = ({
  theme = 'light',
  particleCount = 50,
  duration = 3000,
  colors = DEFAULT_COLORS,
}) => {
  useEffect(() => {
    injectKeyframes();
  }, []);

  const [isVisible, setIsVisible] = useState(true);

  // Generate random particles
  const particles = useMemo((): Particle[] => {
    return Array.from({ length: particleCount }, (_, i) => ({
      id: i,
      x: Math.random() * 100, // Position across screen (0-100%)
      color: colors[Math.floor(Math.random() * colors.length)],
      size: Math.random() * 8 + 4, // 4-12px
      delay: Math.random() * 500, // 0-500ms delay
      swayDuration: Math.random() * 2 + 1, // 1-3s sway
      fallDuration: Math.random() * 2 + 2, // 2-4s fall
      shape: SHAPES[Math.floor(Math.random() * SHAPES.length)],
    }));
  }, [particleCount, colors]);

  // Hide after duration
  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(false), duration);
    return () => clearTimeout(timer);
  }, [duration]);

  if (!isVisible) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 9999,
        overflow: 'hidden',
      }}
    >
      {particles.map(particle => (
        <ConfettiParticle key={particle.id} particle={particle} />
      ))}
    </div>
  );
};

// ============================================================================
// PARTICLE COMPONENT
// ============================================================================

interface ConfettiParticleProps {
  particle: Particle;
}

const ConfettiParticle: React.FC<ConfettiParticleProps> = ({ particle }) => {
  const shapeStyle = useMemo((): React.CSSProperties => {
    const base: React.CSSProperties = {
      position: 'absolute',
      left: `${particle.x}%`,
      top: 0,
      width: particle.size,
      height: particle.size,
      backgroundColor: particle.shape !== 'triangle' ? particle.color : 'transparent',
      animation: `confetti-fall ${particle.fallDuration}s ease-in forwards, confetti-sway ${particle.swayDuration}s ease-in-out infinite`,
      animationDelay: `${particle.delay}ms`,
      opacity: 0,
    };

    switch (particle.shape) {
      case 'circle':
        return { ...base, borderRadius: '50%' };
      case 'square':
        return { ...base, borderRadius: 2 };
      case 'triangle':
        return {
          ...base,
          width: 0,
          height: 0,
          borderLeft: `${particle.size / 2}px solid transparent`,
          borderRight: `${particle.size / 2}px solid transparent`,
          borderBottom: `${particle.size}px solid ${particle.color}`,
        };
      case 'star':
        return {
          ...base,
          clipPath: 'polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)',
        };
      default:
        return base;
    }
  }, [particle]);

  return <div style={shapeStyle} />;
};

// ============================================================================
// LEVEL UP OVERLAY
// ============================================================================

export interface LevelUpOverlayProps {
  newLevel: number;
  levelTitle: string;
  onComplete?: () => void;
  theme?: 'light' | 'dark';
}

export const LevelUpOverlay: React.FC<LevelUpOverlayProps> = ({
  newLevel,
  levelTitle,
  onComplete,
  theme = 'light',
}) => {
  useEffect(() => {
    injectKeyframes();
    
    // Call onComplete after animation
    if (onComplete) {
      const timer = setTimeout(onComplete, 3000);
      return () => clearTimeout(timer);
    }
  }, [onComplete]);

  const colors = useMemo(() => ({
    bg: theme === 'dark' ? 'rgba(26, 26, 26, 0.95)' : 'rgba(255, 255, 255, 0.95)',
    text: theme === 'dark' ? '#ffffff' : '#000000',
    gold: '#FFD700',
    primary: '#dc2626',
  }), [theme]);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: colors.bg,
        zIndex: 10000,
        animation: 'level-up-overlay 3s ease-in-out forwards',
      }}
    >
      {/* Star burst background */}
      <div style={{
        position: 'absolute',
        width: 200,
        height: 200,
        animation: 'star-burst 2s ease-out forwards',
      }}>
        {[...Array(8)].map((_, i) => (
          <div
            key={i}
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              width: 4,
              height: 80,
              backgroundColor: colors.gold,
              transform: `rotate(${i * 45}deg) translateY(-50%)`,
              transformOrigin: 'center bottom',
              borderRadius: 2,
            }}
          />
        ))}
      </div>

      {/* Level badge */}
      <div
        style={{
          fontSize: 64,
          fontWeight: 700,
          color: colors.gold,
          textShadow: '0 4px 20px rgba(255, 215, 0, 0.5)',
          animation: 'celebrate-text 0.8s ease-out forwards',
          animationDelay: '0.3s',
          opacity: 0,
        }}
      >
        Level {newLevel}
      </div>

      {/* Title */}
      <div
        style={{
          fontSize: 24,
          fontWeight: 600,
          color: colors.text,
          marginTop: 16,
          animation: 'celebrate-text 0.8s ease-out forwards',
          animationDelay: '0.6s',
          opacity: 0,
        }}
      >
        {levelTitle}
      </div>

      {/* Subtitle */}
      <div
        style={{
          fontSize: 16,
          color: theme === 'dark' ? '#a3a3a3' : '#525252',
          marginTop: 8,
          animation: 'celebrate-text 0.8s ease-out forwards',
          animationDelay: '0.9s',
          opacity: 0,
        }}
      >
        Congratulations! Keep up the great work!
      </div>

      {/* Confetti */}
      <Confetti theme={theme} particleCount={80} duration={3000} />
    </div>
  );
};

// ============================================================================
// XP GAINED POPUP
// ============================================================================

export interface XPGainedPopupProps {
  xp: number;
  x: number;
  y: number;
  onComplete?: () => void;
}

export const XPGainedPopup: React.FC<XPGainedPopupProps> = ({
  xp,
  x,
  y,
  onComplete,
}) => {
  useEffect(() => {
    if (onComplete) {
      const timer = setTimeout(onComplete, 1500);
      return () => clearTimeout(timer);
    }
  }, [onComplete]);

  return (
    <div
      style={{
        position: 'fixed',
        left: x,
        top: y,
        transform: 'translate(-50%, -50%)',
        fontSize: 24,
        fontWeight: 700,
        color: '#FFD700',
        textShadow: '0 2px 4px rgba(0,0,0,0.3)',
        animation: 'celebrate-text 0.5s ease-out, confetti-fall 1s ease-in 0.5s forwards',
        pointerEvents: 'none',
        zIndex: 10001,
      }}
    >
      +{xp} XP
    </div>
  );
};

export default Confetti;

