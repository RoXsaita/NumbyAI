/**
 * StatusBar Component - Compact Progress Display
 * 
 * A slim, always-visible progress bar showing:
 * - Mascot thumbnail with bounce animation
 * - Level badge with title
 * - XP progress bar with gradient fill
 * - Next milestone hint (clickable to expand Journey tab)
 */

import React, { useMemo, useEffect, useState } from 'react';
import { MiniMascot } from './Mascot';
import { ProgressState, getMascotPersonality, getLevelInfo } from '../lib/progression';

// ============================================================================
// CSS KEYFRAMES
// ============================================================================

const KEYFRAMES = `
@keyframes xp-bar-fill {
  0% { width: 0; }
  100% { width: var(--target-width); }
}

@keyframes xp-bar-shine {
  0% { left: -100%; }
  100% { left: 200%; }
}

@keyframes level-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

@keyframes status-slide-in {
  0% { transform: translateY(-100%); opacity: 0; }
  100% { transform: translateY(0); opacity: 1; }
}

@keyframes hint-fade {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}
`;

let keyframesInjected = false;
function injectKeyframes() {
  if (keyframesInjected || typeof document === 'undefined') return;
  
  const existing = document.getElementById('statusbar-keyframes');
  if (existing) return;
  
  const styleEl = document.createElement('style');
  styleEl.id = 'statusbar-keyframes';
  styleEl.textContent = KEYFRAMES;
  document.head.appendChild(styleEl);
  keyframesInjected = true;
}

// ============================================================================
// TYPES
// ============================================================================

export interface StatusBarProps {
  progress: ProgressState;
  onJourneyClick?: () => void;
  theme?: 'light' | 'dark';
  compact?: boolean;
}

// ============================================================================
// COMPONENT
// ============================================================================

export const StatusBar: React.FC<StatusBarProps> = ({
  progress,
  onJourneyClick,
  theme = 'light',
  compact = false,
}) => {
  useEffect(() => {
    injectKeyframes();
  }, []);

  const [isHovered, setIsHovered] = useState(false);
  
  // Theme colors
  const colors = useMemo(() => ({
    bg: theme === 'dark' ? '#1a1a1a' : '#ffffff',
    bgSecondary: theme === 'dark' ? '#2a2a2a' : '#f5f5f5',
    text: theme === 'dark' ? '#ffffff' : '#000000',
    textSecondary: theme === 'dark' ? '#a3a3a3' : '#525252',
    textMuted: theme === 'dark' ? '#525252' : '#a3a3a3',
    border: theme === 'dark' ? '#333333' : '#e5e5e5',
    primary: '#dc2626',
    finleyBlue: '#4A7ABF',
    gold: '#FFD700',
    success: '#16a34a',
  }), [theme]);

  // Get level info using infinite leveling system
  const currentLevelInfo = useMemo(() => getLevelInfo(progress.level), [progress.level]);
  const nextLevelInfo = useMemo(() => getLevelInfo(progress.level + 1), [progress.level]);
  
  // Get personality for encouragement
  const personality = getMascotPersonality(progress.level);

  // Container styles
  const containerStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: compact ? 8 : 12,
    padding: compact ? '6px 10px' : '8px 16px',
    backgroundColor: colors.bgSecondary,
    borderRadius: 12,
    border: `1px solid ${colors.border}`,
    animation: 'status-slide-in 0.4s ease-out forwards',
    cursor: onJourneyClick ? 'pointer' : 'default',
    transition: 'all 0.2s ease',
    boxShadow: isHovered ? '0 4px 12px rgba(0,0,0,0.1)' : '0 2px 4px rgba(0,0,0,0.05)',
  };

  // Level badge styles
  const levelBadgeStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '4px 10px',
    backgroundColor: currentLevelInfo.color,
    color: '#ffffff',
    borderRadius: 16,
    fontSize: compact ? 11 : 12,
    fontWeight: 600,
    whiteSpace: 'nowrap',
    animation: progress.levelProgress === 100 ? 'level-pulse 1s ease-in-out infinite' : 'none',
  };

  // XP bar container styles
  const xpBarContainerStyle: React.CSSProperties = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    minWidth: compact ? 80 : 120,
    maxWidth: compact ? 150 : 200,
  };

  // XP bar track styles
  const xpBarTrackStyle: React.CSSProperties = {
    height: compact ? 6 : 8,
    backgroundColor: colors.border,
    borderRadius: 4,
    overflow: 'hidden',
    position: 'relative',
  };

  // XP bar fill styles
  const xpBarFillStyle: React.CSSProperties = {
    height: '100%',
    width: `${progress.levelProgress}%`,
    background: `linear-gradient(90deg, ${colors.primary} 0%, ${colors.gold} 100%)`,
    borderRadius: 4,
    transition: 'width 0.5s ease-out',
    position: 'relative',
    overflow: 'hidden',
  };

  // XP bar shine effect
  const xpBarShineStyle: React.CSSProperties = {
    position: 'absolute',
    top: 0,
    left: '-100%',
    width: '50%',
    height: '100%',
    background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)',
    animation: 'xp-bar-shine 2s ease-in-out infinite',
  };

  // XP text styles
  const xpTextStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: compact ? 9 : 10,
    color: colors.textSecondary,
  };

  // Next milestone hint styles
  const hintStyle: React.CSSProperties = {
    fontSize: compact ? 10 : 11,
    color: colors.textMuted,
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    maxWidth: compact ? 100 : 160,
    animation: 'hint-fade 3s ease-in-out infinite',
  };

  // Arrow indicator for clickable
  const arrowStyle: React.CSSProperties = {
    fontSize: compact ? 12 : 14,
    color: colors.textMuted,
    transition: 'transform 0.2s ease',
    transform: isHovered ? 'translateX(4px)' : 'translateX(0)',
  };

  return (
    <div 
      style={containerStyle}
      onClick={onJourneyClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      role={onJourneyClick ? 'button' : undefined}
      tabIndex={onJourneyClick ? 0 : undefined}
      aria-label={`Level ${progress.level} ${progress.levelTitle}, ${progress.totalXP} XP`}
    >
      {/* Mini Mascot */}
      <MiniMascot 
        variant={progress.mascot}
        level={progress.level}
        isAnimating={true}
        theme={theme}
      />

      {/* Level Badge */}
      <div style={levelBadgeStyle}>
        <span style={{ fontSize: compact ? 10 : 12 }}>Lv.{progress.level}</span>
        {!compact && <span>{progress.levelTitle}</span>}
      </div>

      {/* XP Progress Bar */}
      <div style={xpBarContainerStyle}>
        <div style={xpBarTrackStyle}>
          <div style={xpBarFillStyle}>
            <div style={xpBarShineStyle} />
          </div>
        </div>
        <div style={xpTextStyle}>
          <span>{progress.totalXP} XP</span>
          <span>{nextLevelInfo.xpRequired - progress.totalXP} to Lv.{progress.level + 1}</span>
        </div>
      </div>

      {/* Next Milestone Hint */}
      {!compact && progress.nextMilestone && (
        <div style={hintStyle} title={progress.nextMilestone.description}>
          Next: {progress.nextMilestone.title}
        </div>
      )}

      {/* Arrow Indicator */}
      {onJourneyClick && (
        <span style={arrowStyle}>→</span>
      )}
    </div>
  );
};

// ============================================================================
// EXPANDED STATUS CARD (For journey tab header)
// ============================================================================

export interface ExpandedStatusProps {
  progress: ProgressState;
  theme?: 'light' | 'dark';
}

export const ExpandedStatus: React.FC<ExpandedStatusProps> = ({
  progress,
  theme = 'light',
}) => {
  useEffect(() => {
    injectKeyframes();
  }, []);

  const colors = useMemo(() => ({
    bg: theme === 'dark' ? '#1a1a1a' : '#ffffff',
    bgSecondary: theme === 'dark' ? '#2a2a2a' : '#f5f5f5',
    text: theme === 'dark' ? '#ffffff' : '#000000',
    textSecondary: theme === 'dark' ? '#a3a3a3' : '#525252',
    border: theme === 'dark' ? '#333333' : '#e5e5e5',
    primary: '#dc2626',
    finleyBlue: '#4A7ABF',
    gold: '#FFD700',
  }), [theme]);

  const currentLevelInfo = useMemo(() => getLevelInfo(progress.level), [progress.level]);
  const nextLevelInfo = useMemo(() => getLevelInfo(progress.level + 1), [progress.level]);
  const personality = getMascotPersonality(progress.level);

  const containerStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
    padding: 20,
    backgroundColor: colors.bgSecondary,
    borderRadius: 16,
    border: `1px solid ${colors.border}`,
  };

  const headerStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
  };

  const statsGridStyle: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 12,
    marginTop: 8,
  };

  const statCardStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: 12,
    backgroundColor: colors.bg,
    borderRadius: 12,
    border: `1px solid ${colors.border}`,
  };

  const statValueStyle: React.CSSProperties = {
    fontSize: 24,
    fontWeight: 700,
    color: colors.text,
  };

  const statLabelStyle: React.CSSProperties = {
    fontSize: 11,
    color: colors.textSecondary,
    marginTop: 4,
  };

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        {/* Mascot will be rendered by parent */}
        <div style={{ flex: 1 }}>
          <div style={{ 
            fontSize: 20, 
            fontWeight: 700, 
            color: colors.text,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}>
            Level {progress.level}
            <span style={{
              padding: '2px 8px',
              backgroundColor: currentLevelInfo.color,
              color: '#ffffff',
              borderRadius: 12,
              fontSize: 12,
              fontWeight: 600,
            }}>
              {progress.levelTitle}
            </span>
          </div>
          <div style={{ 
            fontSize: 14, 
            color: colors.textSecondary,
            marginTop: 4,
          }}>
            {personality.encouragement}
          </div>
          
          {/* XP Progress */}
          <div style={{ marginTop: 12 }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 12,
              color: colors.textSecondary,
              marginBottom: 4,
            }}>
              <span>{progress.totalXP} XP Total</span>
              <span>{nextLevelInfo.xpRequired} XP for Level {progress.level + 1}</span>
            </div>
            <div style={{
              height: 12,
              backgroundColor: colors.border,
              borderRadius: 6,
              overflow: 'hidden',
            }}>
              <div style={{
                height: '100%',
                width: `${progress.levelProgress}%`,
                background: `linear-gradient(90deg, ${colors.primary} 0%, ${colors.gold} 100%)`,
                borderRadius: 6,
                transition: 'width 0.5s ease-out',
              }} />
            </div>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div style={statsGridStyle}>
        <div style={statCardStyle}>
          <div style={statValueStyle}>{progress.completedCount}</div>
          <div style={statLabelStyle}>Completed</div>
        </div>
        <div style={statCardStyle}>
          <div style={statValueStyle}>{progress.totalMilestones - progress.completedCount}</div>
          <div style={statLabelStyle}>Remaining</div>
        </div>
        <div style={statCardStyle}>
          <div style={{ ...statValueStyle, color: colors.gold }}>{progress.totalXP}</div>
          <div style={statLabelStyle}>Total XP</div>
        </div>
      </div>
    </div>
  );
};

export default StatusBar;

