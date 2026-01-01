/**
 * MilestoneCard Component - Individual Milestone Display
 * 
 * Shows milestone details with:
 * - Icon and title
 * - Progress indicator (for in-progress milestones)
 * - Claim button (for completed but unclaimed)
 * - XP reward display
 * - Celebration animation on claim
 */

import React, { useState, useEffect, useMemo } from 'react';
import { MilestoneStatus, getMilestoneCategoryColor, getRandomCelebrationMessage } from '../lib/progression';

// ============================================================================
// CSS KEYFRAMES
// ============================================================================

const KEYFRAMES = `
@keyframes card-pop {
  0% { transform: scale(0.95); opacity: 0; }
  50% { transform: scale(1.02); }
  100% { transform: scale(1); opacity: 1; }
}

@keyframes card-shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-2px); }
  20%, 40%, 60%, 80% { transform: translateX(2px); }
}

@keyframes claim-button-pulse {
  0%, 100% { 
    box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.5);
    transform: scale(1);
  }
  50% { 
    box-shadow: 0 0 0 8px rgba(220, 38, 38, 0);
    transform: scale(1.05);
  }
}

@keyframes progress-fill {
  0% { width: 0; }
  100% { width: var(--progress); }
}

@keyframes xp-pop {
  0% { transform: scale(1); }
  50% { transform: scale(1.3); }
  100% { transform: scale(1); }
}

@keyframes checkmark-draw {
  0% { stroke-dashoffset: 24; }
  100% { stroke-dashoffset: 0; }
}

@keyframes celebrate-glow {
  0% { box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.5); }
  50% { box-shadow: 0 0 20px 10px rgba(22, 163, 74, 0.3); }
  100% { box-shadow: 0 0 0 0 rgba(22, 163, 74, 0); }
}

@keyframes float-up {
  0% { 
    opacity: 1;
    transform: translateY(0) scale(1);
  }
  100% { 
    opacity: 0;
    transform: translateY(-30px) scale(1.2);
  }
}
`;

let keyframesInjected = false;
function injectKeyframes() {
  if (keyframesInjected || typeof document === 'undefined') return;
  
  const existing = document.getElementById('milestonecard-keyframes');
  if (existing) return;
  
  const styleEl = document.createElement('style');
  styleEl.id = 'milestonecard-keyframes';
  styleEl.textContent = KEYFRAMES;
  document.head.appendChild(styleEl);
  keyframesInjected = true;
}

// ============================================================================
// TYPES
// ============================================================================

export interface MilestoneCardProps {
  milestone: MilestoneStatus;
  isCompleted: boolean;
  isCurrent?: boolean;
  onClaim?: () => void;
  theme?: 'light' | 'dark';
  compact?: boolean;
}

// ============================================================================
// COMPONENT
// ============================================================================

export const MilestoneCard: React.FC<MilestoneCardProps> = ({
  milestone,
  isCompleted,
  isCurrent = false,
  onClaim,
  theme = 'light',
  compact = false,
}) => {
  useEffect(() => {
    injectKeyframes();
  }, []);

  const [isHovered, setIsHovered] = useState(false);
  const [isClaiming, setIsClaiming] = useState(false);
  const [showCelebration, setShowCelebration] = useState(false);
  const [celebrationMessage, setCelebrationMessage] = useState('');

  // Theme colors
  const colors = useMemo(() => ({
    bg: theme === 'dark' ? '#1a1a1a' : '#ffffff',
    bgSecondary: theme === 'dark' ? '#2a2a2a' : '#f5f5f5',
    bgTertiary: theme === 'dark' ? '#333333' : '#f0f0f0',
    text: theme === 'dark' ? '#ffffff' : '#000000',
    textSecondary: theme === 'dark' ? '#a3a3a3' : '#525252',
    textMuted: theme === 'dark' ? '#525252' : '#a3a3a3',
    border: theme === 'dark' ? '#404040' : '#e5e5e5',
    primary: '#dc2626',
    success: '#16a34a',
    gold: '#FFD700',
  }), [theme]);

  const categoryColor = getMilestoneCategoryColor(milestone.category);

  // Handle claim action
  const handleClaim = () => {
    if (!onClaim || !isCompleted || isClaiming) return;
    
    setIsClaiming(true);
    setCelebrationMessage(getRandomCelebrationMessage(milestone.id));
    
    // Show celebration animation
    setTimeout(() => {
      setShowCelebration(true);
      onClaim();
    }, 300);
    
    // Reset after animation
    setTimeout(() => {
      setShowCelebration(false);
      setIsClaiming(false);
    }, 2000);
  };

  // Card container styles
  const cardStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: compact ? 'row' : 'column',
    gap: compact ? 10 : 12,
    padding: compact ? 10 : 16,
    backgroundColor: isCompleted ? (showCelebration ? `${colors.success}10` : colors.bgSecondary) : colors.bg,
    borderRadius: 12,
    border: `1px solid ${isCompleted ? colors.success : isCurrent ? colors.primary : colors.border}`,
    transition: 'all 0.3s ease',
    animation: showCelebration 
      ? 'celebrate-glow 1s ease-out' 
      : isClaiming 
        ? 'card-shake 0.5s ease-in-out' 
        : 'card-pop 0.4s ease-out',
    cursor: isCompleted && onClaim && !isClaiming ? 'pointer' : 'default',
    boxShadow: isHovered && !isCompleted 
      ? '0 4px 12px rgba(0,0,0,0.1)' 
      : '0 2px 4px rgba(0,0,0,0.05)',
    position: 'relative',
    overflow: 'hidden',
    opacity: !isCompleted && !isCurrent ? 0.6 : 1,
  };

  // Icon styles
  const iconStyle: React.CSSProperties = {
    width: compact ? 32 : 40,
    height: compact ? 32 : 40,
    borderRadius: 8,
    backgroundColor: isCompleted ? colors.success : categoryColor,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: compact ? 16 : 20,
    flexShrink: 0,
  };

  // Content styles
  const contentStyle: React.CSSProperties = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: compact ? 2 : 6,
    minWidth: 0,
  };

  // Title styles
  const titleStyle: React.CSSProperties = {
    fontSize: compact ? 12 : 14,
    fontWeight: 600,
    color: colors.text,
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  };

  // Description styles
  const descriptionStyle: React.CSSProperties = {
    fontSize: compact ? 10 : 12,
    color: colors.textSecondary,
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  };

  // XP badge styles
  const xpBadgeStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    padding: '2px 8px',
    backgroundColor: isCompleted ? colors.gold : colors.bgTertiary,
    color: isCompleted ? '#000' : colors.textSecondary,
    borderRadius: 12,
    fontSize: compact ? 10 : 11,
    fontWeight: 600,
    animation: showCelebration ? 'xp-pop 0.5s ease-out' : 'none',
  };

  // Progress bar styles (for in-progress milestones)
  const progressBarContainerStyle: React.CSSProperties = {
    height: 4,
    backgroundColor: colors.border,
    borderRadius: 2,
    overflow: 'hidden',
    marginTop: 4,
  };

  const progressBarFillStyle: React.CSSProperties = {
    height: '100%',
    width: `${milestone.progress}%`,
    backgroundColor: isCurrent ? colors.primary : categoryColor,
    borderRadius: 2,
    transition: 'width 0.5s ease-out',
  };

  // Progress text styles
  const progressTextStyle: React.CSSProperties = {
    fontSize: 10,
    color: colors.textMuted,
    marginTop: 2,
  };

  // Claim button styles
  const claimButtonStyle: React.CSSProperties = {
    padding: compact ? '4px 10px' : '6px 14px',
    backgroundColor: colors.primary,
    color: '#ffffff',
    border: 'none',
    borderRadius: 8,
    fontSize: compact ? 10 : 12,
    fontWeight: 600,
    cursor: 'pointer',
    animation: 'claim-button-pulse 2s ease-in-out infinite',
    transition: 'background-color 0.2s ease',
  };

  // Completed checkmark
  const CheckmarkIcon: React.FC = () => (
    <svg 
      width={compact ? 16 : 20} 
      height={compact ? 16 : 20} 
      viewBox="0 0 24 24" 
      fill="none"
    >
      <path
        d="M5 13l4 4L19 7"
        stroke={colors.success}
        strokeWidth={3}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray="24"
        strokeDashoffset="0"
        style={{ animation: isCompleted ? 'checkmark-draw 0.5s ease-out forwards' : 'none' }}
      />
    </svg>
  );

  return (
    <div 
      style={cardStyle}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={handleClaim}
    >
      {/* Category indicator stripe */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        height: 3,
        backgroundColor: isCompleted ? colors.success : categoryColor,
        opacity: 0.8,
      }} />

      {/* Icon */}
      <div style={iconStyle}>
        {isCompleted ? <CheckmarkIcon /> : milestone.icon}
      </div>

      {/* Content */}
      <div style={contentStyle}>
        <div style={titleStyle} title={milestone.title}>
          {milestone.title}
        </div>
        
        <div style={descriptionStyle} title={milestone.description}>
          {milestone.description}
        </div>

        {/* Progress bar for incomplete milestones */}
        {!isCompleted && isCurrent && milestone.progress > 0 && milestone.progress < 100 && (
          <>
            <div style={progressBarContainerStyle}>
              <div style={progressBarFillStyle} />
            </div>
            <div style={progressTextStyle}>
              {milestone.current} / {milestone.target}
            </div>
          </>
        )}

        {/* Bottom row with XP and action */}
        {!compact && (
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            marginTop: 4,
          }}>
            <div style={xpBadgeStyle}>
              <span>+{milestone.xp}</span>
              <span style={{ color: colors.gold }}>XP</span>
            </div>

            {/* Claim button for completed milestones */}
            {isCompleted && onClaim && !showCelebration && (
              <button 
                style={claimButtonStyle}
                onClick={(e) => {
                  e.stopPropagation();
                  handleClaim();
                }}
              >
                Claim!
              </button>
            )}
          </div>
        )}
      </div>

      {/* Compact XP badge */}
      {compact && (
        <div style={{ ...xpBadgeStyle, flexShrink: 0 }}>
          +{milestone.xp}
        </div>
      )}

      {/* Celebration overlay */}
      {showCelebration && (
        <div style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: `${colors.success}20`,
          borderRadius: 12,
        }}>
          <div style={{
            fontSize: compact ? 12 : 14,
            fontWeight: 600,
            color: colors.success,
            textAlign: 'center',
            padding: 8,
            animation: 'float-up 1.5s ease-out forwards',
          }}>
            {celebrationMessage}
          </div>
        </div>
      )}

      {/* Floating XP on celebration */}
      {showCelebration && (
        <div style={{
          position: 'absolute',
          top: '50%',
          right: 16,
          fontSize: compact ? 14 : 18,
          fontWeight: 700,
          color: colors.gold,
          animation: 'float-up 1s ease-out forwards',
        }}>
          +{milestone.xp} XP
        </div>
      )}
    </div>
  );
};

// ============================================================================
// MILESTONE LIST COMPONENT
// ============================================================================

export interface MilestoneListProps {
  milestones: MilestoneStatus[];
  onClaim?: (milestoneId: string) => void;
  theme?: 'light' | 'dark';
  showAll?: boolean;
}

export const MilestoneList: React.FC<MilestoneListProps> = ({
  milestones,
  onClaim,
  theme = 'light',
  showAll = false,
}) => {
  // Filter to show relevant milestones
  const displayedMilestones = useMemo(() => {
    if (showAll) return milestones;
    
    // Show completed, current, and next 2 milestones
    const completed = milestones.filter(m => m.completed);
    const incomplete = milestones.filter(m => !m.completed);
    
    return [...completed, ...incomplete.slice(0, 3)];
  }, [milestones, showAll]);

  const colors = useMemo(() => ({
    text: theme === 'dark' ? '#ffffff' : '#000000',
    textSecondary: theme === 'dark' ? '#a3a3a3' : '#525252',
    border: theme === 'dark' ? '#333333' : '#e5e5e5',
  }), [theme]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Section headers */}
      {displayedMilestones.some(m => m.completed) && (
        <div style={{
          fontSize: 12,
          fontWeight: 600,
          color: colors.textSecondary,
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
          marginBottom: 4,
        }}>
          Completed
        </div>
      )}
      
      {displayedMilestones
        .filter(m => m.completed)
        .map(milestone => (
          <MilestoneCard
            key={milestone.id}
            milestone={milestone}
            isCompleted={true}
            onClaim={onClaim ? () => onClaim(milestone.id) : undefined}
            theme={theme}
          />
        ))}

      {displayedMilestones.some(m => !m.completed) && (
        <div style={{
          fontSize: 12,
          fontWeight: 600,
          color: colors.textSecondary,
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
          marginTop: 8,
          marginBottom: 4,
        }}>
          Up Next
        </div>
      )}
      
      {displayedMilestones
        .filter(m => !m.completed)
        .map((milestone, index) => (
          <MilestoneCard
            key={milestone.id}
            milestone={milestone}
            isCompleted={false}
            isCurrent={index === 0}
            theme={theme}
          />
        ))}
    </div>
  );
};

export default MilestoneCard;

