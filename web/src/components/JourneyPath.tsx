/**
 * JourneyPath Component - Unified Premium Journey View
 * 
 * A single cohesive view combining:
 * - Header with mascot, level, and XP progress
 * - Premium vertical scrolling path with milestone nodes
 * - Full milestone details without truncation
 */

import React, { useMemo, useEffect, useRef, useState } from 'react';
import { MilestoneStatus, getMilestoneCategoryColor, ProgressState, getLevelInfo, QUEST_HELP_INSTRUCTIONS, QuestHelp, PHASE_DEFINITIONS, getPhaseForMilestone, AIPhase } from '../lib/progression';
import { QuestHelpModal } from './QuestHelpModal';

// ============================================================================
// CSS KEYFRAMES
// ============================================================================

const KEYFRAMES = `
@keyframes journey-path-draw {
  0% { stroke-dashoffset: 2000; }
  100% { stroke-dashoffset: 0; }
}

@keyframes journey-node-pulse {
  0%, 100% { 
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.6);
  }
  50% { 
    transform: scale(1.08);
    box-shadow: 0 0 0 12px rgba(220, 38, 38, 0);
  }
}

@keyframes journey-node-glow {
  0%, 100% { 
    filter: drop-shadow(0 0 8px rgba(22, 163, 74, 0.4));
  }
  50% { 
    filter: drop-shadow(0 0 16px rgba(22, 163, 74, 0.7));
  }
}

@keyframes journey-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

@keyframes journey-sparkle {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}

@keyframes journey-mascot-bounce {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  25% { transform: translateY(-6px) rotate(-2deg); }
  75% { transform: translateY(-3px) rotate(2deg); }
}

@keyframes journey-xp-shine {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

@keyframes journey-card-enter {
  0% { opacity: 0; transform: translateX(20px); }
  100% { opacity: 1; transform: translateX(0); }
}

@keyframes journey-crown-float {
  0%, 100% { transform: translateY(0) rotate(-5deg); }
  50% { transform: translateY(-8px) rotate(5deg); }
}

@keyframes journey-sparkle-particle {
  0% { 
    opacity: 0;
    transform: translateY(0) scale(0);
  }
  20% {
    opacity: 1;
    transform: translateY(-10px) scale(1);
  }
  100% { 
    opacity: 0;
    transform: translateY(-30px) scale(0.5);
  }
}

@keyframes journey-path-flow {
  0% { stroke-dashoffset: 0; }
  100% { stroke-dashoffset: -40; }
}

@keyframes journey-ribbon-wave {
  0%, 100% { d: path("M60 0 Q80 25 60 50 Q40 75 60 100 Q80 125 60 150"); }
  50% { d: path("M60 0 Q40 25 60 50 Q80 75 60 100 Q40 125 60 150"); }
}

@keyframes journey-claim-pulse {
  0%, 100% { 
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(255, 215, 0, 0.7);
  }
  50% { 
    transform: scale(1.05);
    box-shadow: 0 0 0 8px rgba(255, 215, 0, 0);
  }
}

@keyframes journey-xp-float {
  0% { 
    opacity: 1;
    transform: translateY(0) scale(1);
  }
  100% { 
    opacity: 0;
    transform: translateY(-50px) scale(1.5);
  }
}

@keyframes journey-confetti-burst {
  0% { 
    opacity: 1;
    transform: translate(0, 0) rotate(0deg) scale(1);
  }
  100% { 
    opacity: 0;
    transform: translate(var(--tx), var(--ty)) rotate(720deg) scale(0);
  }
}

@keyframes journey-celebrate-shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-3px); }
  20%, 40%, 60%, 80% { transform: translateX(3px); }
}

@keyframes journey-claim-success {
  0% { 
    transform: scale(0.8);
    opacity: 0;
  }
  50% {
    transform: scale(1.1);
  }
  100% { 
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes companion-modal-fade-in {
  0% { opacity: 0; }
  100% { opacity: 1; }
}

@keyframes companion-modal-slide-up {
  0% { 
    opacity: 0;
    transform: translate(-50%, -45%) scale(0.95);
  }
  100% { 
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}
`;

let keyframesInjected = false;
function injectKeyframes() {
  if (keyframesInjected || typeof document === 'undefined') return;
  
  const existing = document.getElementById('journeypath-v2-keyframes');
  if (existing) return;
  
  const styleEl = document.createElement('style');
  styleEl.id = 'journeypath-v2-keyframes';
  styleEl.textContent = KEYFRAMES;
  document.head.appendChild(styleEl);
  keyframesInjected = true;
}

// ============================================================================
// TYPES
// ============================================================================

export interface JourneyPathProps {
  progress: ProgressState;
  onMilestoneClaim?: (milestoneId: string) => void;
  theme?: 'light' | 'dark';
}

// ============================================================================
// CONSTANTS
// ============================================================================

const NODE_SIZE = 56;
const NODE_SPACING = 140;
const PATH_WIDTH = 6;

// ============================================================================
// COMPONENT
// ============================================================================

export const JourneyPath: React.FC<JourneyPathProps> = ({
  progress,
  onMilestoneClaim,
  theme = 'light',
}) => {
  useEffect(() => {
    injectKeyframes();
  }, []);

  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollY, setScrollY] = useState(0);
  const [helpModalQuest, setHelpModalQuest] = useState<MilestoneStatus | null>(null);
  const [showCompanionHelp, setShowCompanionHelp] = useState(false);
  
  // Theme colors
  const colors = useMemo(() => ({
    bg: theme === 'dark' ? '#0f0f0f' : '#fafafa',
    bgCard: theme === 'dark' ? '#1a1a1a' : '#ffffff',
    bgElevated: theme === 'dark' ? '#252525' : '#f5f5f5',
    text: theme === 'dark' ? '#ffffff' : '#000000',
    textSecondary: theme === 'dark' ? '#a3a3a3' : '#525252',
    textMuted: theme === 'dark' ? '#666666' : '#9ca3af',
    border: theme === 'dark' ? '#333333' : '#e5e5e5',
    primary: '#dc2626',
    primaryGlow: 'rgba(220, 38, 38, 0.3)',
    success: '#16a34a',
    successGlow: 'rgba(22, 163, 74, 0.3)',
    gold: '#FFD700',
    goldGlow: 'rgba(255, 215, 0, 0.4)',
    pathInactive: theme === 'dark' ? '#333333' : '#e5e5e5',
    pathActive: theme === 'dark' 
      ? 'linear-gradient(180deg, #dc2626 0%, #f59e0b 50%, #16a34a 100%)'
      : 'linear-gradient(180deg, #dc2626 0%, #f59e0b 50%, #16a34a 100%)',
  }), [theme]);

  // Sort milestones by order (top-to-bottom display - lowest order first)
  const sortedMilestones = useMemo(() => {
    return [...progress.milestones].sort((a, b) => a.order - b.order);
  }, [progress.milestones]);

  // Phase color mapping
  const phaseColors: Record<AIPhase, string> = {
    beginner: '#3B82F6', // Blue - welcoming, starting
    student: '#10B981',   // Green - growth, learning
    analyst: '#F59E0B',   // Amber - analysis, tracking
    advisor: '#EF4444',   // Red - optimization, action
    master: '#FFD700',    // Gold - mastery, achievement
  };

  // Calculate phase boundaries and gradient stops
  const phaseGradientStops = useMemo(() => {
    if (sortedMilestones.length === 0) return [];
    
    // Group milestones by phase
    const phaseGroups: Record<AIPhase, number[]> = {
      beginner: [],
      student: [],
      analyst: [],
      advisor: [],
      master: [],
    };
    
    sortedMilestones.forEach((milestone, index) => {
      const phase = getPhaseForMilestone(milestone.order);
      phaseGroups[phase].push(index);
    });
    
    // Calculate percentage boundaries for each phase
    const total = sortedMilestones.length;
    const stops: Array<{ offset: number; color: string; phase: AIPhase }> = [];
    
    let currentOffset = 0;
    const phases: AIPhase[] = ['beginner', 'student', 'analyst', 'advisor', 'master'];
    
    phases.forEach((phase, phaseIndex) => {
      const phaseMilestones = phaseGroups[phase];
      if (phaseMilestones.length === 0) return;
      
      const phaseStart = currentOffset / total;
      const phaseEnd = (currentOffset + phaseMilestones.length) / total;
      
      // Add start stop (transition from previous phase)
      if (phaseIndex === 0) {
        stops.push({ offset: phaseStart, color: phaseColors[phase], phase });
      } else {
        // Transition point: blend with previous phase
        const prevPhase = phases[phaseIndex - 1];
        const transitionOffset = phaseStart;
        stops.push({ offset: transitionOffset, color: phaseColors[prevPhase], phase: prevPhase });
        stops.push({ offset: Math.min(transitionOffset + 0.02, phaseEnd), color: phaseColors[phase], phase });
      }
      
      // Add end stop
      stops.push({ offset: phaseEnd, color: phaseColors[phase], phase });
      
      currentOffset += phaseMilestones.length;
    });
    
    return stops;
  }, [sortedMilestones]);

  // Find current milestone index
  const currentMilestoneIndex = useMemo(() => {
    const idx = sortedMilestones.findIndex(m => !m.completed);
    return idx === -1 ? sortedMilestones.length : idx;
  }, [sortedMilestones]);

  // Get next level info
  const nextLevelInfo = useMemo(() => getLevelInfo(progress.level + 1), [progress.level]);

  // Scroll to current milestone (from top)
  useEffect(() => {
    if (scrollRef.current && currentMilestoneIndex < sortedMilestones.length) {
      const targetY = currentMilestoneIndex * NODE_SPACING;
      setTimeout(() => {
        scrollRef.current?.scrollTo({ top: Math.max(0, targetY - 250), behavior: 'smooth' });
      }, 300);
    }
  }, []);

  // Track scroll
  const handleScroll = () => {
    if (scrollRef.current) {
      setScrollY(scrollRef.current.scrollTop);
    }
  };

  // Total height: START node (top) + milestones + Master/Crown (bottom) + padding
  const totalHeight = 100 + (sortedMilestones.length + 2) * NODE_SPACING + 60;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: colors.bg,
      overflow: 'hidden',
    }}>
      {/* Unified Header with AI Companion and Progress */}
      <div style={{
        padding: '8px 16px',
        background: theme === 'dark' 
          ? 'linear-gradient(180deg, #1a1a1a 0%, #0f0f0f 100%)'
          : 'linear-gradient(180deg, #ffffff 0%, #fafafa 100%)',
        borderBottom: `1px solid ${colors.border}`,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        minHeight: 64,
      }}>
        {/* AI Companion Mascot */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}>
          <div style={{ position: 'relative' }}>
            <div style={{
              width: 72,
              height: 72,
              borderRadius: 14,
              overflow: 'hidden',
              backgroundColor: colors.bgElevated,
              border: `2px solid ${colors.gold}`,
              boxShadow: `0 0 12px ${colors.goldGlow}`,
              animation: 'journey-mascot-bounce 3s ease-in-out infinite',
              flexShrink: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <img 
                src={progress.mascotImage}
                alt={`${PHASE_DEFINITIONS[progress.phase].displayName} Mode`}
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'contain',
                }}
              />
            </div>
            <button
              onClick={() => setShowCompanionHelp(true)}
              title={`About ${PHASE_DEFINITIONS[progress.phase].displayName}`}
              style={{
                position: 'absolute',
                right: -6,
                top: -6,
                width: 22,
                height: 22,
                borderRadius: '50%',
                border: `1px solid ${colors.border}`,
                background: colors.bgElevated,
                color: colors.textSecondary,
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s ease',
                padding: 0,
                boxShadow: '0 2px 6px rgba(0,0,0,0.12)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = colors.primary;
                e.currentTarget.style.color = '#ffffff';
                e.currentTarget.style.borderColor = colors.primary;
                e.currentTarget.style.transform = 'scale(1.05)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = colors.bgElevated;
                e.currentTarget.style.color = colors.textSecondary;
                e.currentTarget.style.borderColor = colors.border;
                e.currentTarget.style.transform = 'scale(1)';
              }}
            >
              ?
            </button>
          </div>
        </div>

        {/* Level and Progress Info */}
        <div style={{ flex: 1 }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginBottom: 4,
          }}>
            <span style={{
              fontSize: 18,
              fontWeight: 800,
              color: colors.text,
              letterSpacing: '-0.5px',
            }}>
              Level {progress.level}
            </span>
            <span style={{
              padding: '2px 8px',
              backgroundColor: colors.primary,
              color: '#ffffff',
              borderRadius: 12,
              fontSize: 10,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}>
              {PHASE_DEFINITIONS[progress.phase].displayName}
            </span>
            <span style={{
              fontSize: 9,
              color: colors.textSecondary,
              fontStyle: 'italic',
            }}>
              {PHASE_DEFINITIONS[progress.phase].description}
            </span>
          </div>

          {/* XP Progress Bar */}
          <div style={{ marginBottom: 3 }}>
            <div style={{
              height: 6,
              backgroundColor: colors.bgElevated,
              borderRadius: 3,
              overflow: 'hidden',
              position: 'relative',
            }}>
              <div style={{
                position: 'absolute',
                inset: 0,
                background: `linear-gradient(90deg, ${colors.primary} 0%, ${colors.gold} 100%)`,
                width: `${progress.levelProgress}%`,
                borderRadius: 3,
                transition: 'width 0.5s ease-out',
              }} />
              <div style={{
                position: 'absolute',
                inset: 0,
                background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)',
                backgroundSize: '200% 100%',
                animation: 'journey-xp-shine 2s ease-in-out infinite',
              }} />
            </div>
          </div>

          {/* XP Text */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: 10,
            color: colors.textSecondary,
          }}>
            <span style={{ fontWeight: 600, color: colors.gold }}>
              {progress.totalXP.toLocaleString()} XP
            </span>
            <span>
              {(nextLevelInfo.xpRequired - progress.totalXP).toLocaleString()} XP to Level {progress.level + 1}
            </span>
          </div>
        </div>

        {/* Stats */}
        <div style={{
          display: 'flex',
          gap: 10,
          paddingLeft: 12,
          borderLeft: `1px solid ${colors.border}`,
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: colors.success }}>
              {progress.completedCount}
            </div>
            <div style={{ fontSize: 8, color: colors.textMuted, textTransform: 'uppercase' }}>
              Done
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: colors.textSecondary }}>
              {progress.totalMilestones - progress.completedCount}
            </div>
            <div style={{ fontSize: 8, color: colors.textMuted, textTransform: 'uppercase' }}>
              Left
            </div>
          </div>
        </div>
      </div>

      {/* Journey Path Scroll Area */}
      <div 
        ref={scrollRef}
        onScroll={handleScroll}
        style={{
          flex: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          position: 'relative',
        }}
      >
        <div style={{
          position: 'relative',
          minHeight: totalHeight,
          padding: '40px 24px',
        }}>
          {/* Premium SVG Path with Ribbon Effect */}
          <svg 
            style={{
              position: 'absolute',
              left: '50%',
              transform: 'translateX(-70px)',
              top: 0,
              pointerEvents: 'none',
            }}
            width={140}
            height={totalHeight}
          >
            <defs>
              {/* Phase-based multi-color gradient matching agent personas */}
              <linearGradient id="pathGradientPremium" x1="0%" y1="0%" x2="0%" y2="100%">
                {phaseGradientStops.map((stop, index) => (
                  <stop 
                    key={`${stop.phase}-${index}`}
                    offset={`${(stop.offset * 100).toFixed(1)}%`}
                    stopColor={stop.color}
                  />
                ))}
              </linearGradient>
              
              {/* Animated flow gradient */}
              <linearGradient id="pathFlow" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="rgba(255,255,255,0)" />
                <stop offset="40%" stopColor="rgba(255,255,255,0.4)" />
                <stop offset="60%" stopColor="rgba(255,255,255,0.4)" />
                <stop offset="100%" stopColor="rgba(255,255,255,0)" />
              </linearGradient>
              
              {/* Glow filter */}
              <filter id="pathGlowPremium" x="-100%" y="-10%" width="300%" height="120%">
                <feGaussianBlur stdDeviation="6" result="blur" />
                <feFlood floodColor={colors.gold} floodOpacity="0.3" result="color"/>
                <feComposite in="color" in2="blur" operator="in" result="glow"/>
                <feMerge>
                  <feMergeNode in="glow" />
                  <feMergeNode in="glow" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              
              {/* Inner shadow for depth */}
              <filter id="innerShadow" x="-50%" y="-50%" width="200%" height="200%">
                <feComponentTransfer in="SourceAlpha">
                  <feFuncA type="table" tableValues="1 0" />
                </feComponentTransfer>
                <feGaussianBlur stdDeviation="2"/>
                <feOffset dx="0" dy="2" result="shadow"/>
                <feFlood floodColor="#000" floodOpacity="0.3"/>
                <feComposite in2="shadow" operator="in"/>
                <feMerge>
                  <feMergeNode />
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>

            {/* Background path - subtle dashed pattern */}
            <path
              d={generatePathD(sortedMilestones.length, totalHeight, NODE_SPACING)}
              fill="none"
              stroke={colors.pathInactive}
              strokeWidth={PATH_WIDTH + 4}
              strokeLinecap="round"
              opacity={0.3}
            />
            
            {/* Background path - solid */}
            <path
              d={generatePathD(sortedMilestones.length, totalHeight, NODE_SPACING)}
              fill="none"
              stroke={colors.pathInactive}
              strokeWidth={PATH_WIDTH}
              strokeLinecap="round"
              strokeDasharray="8 4"
              opacity={0.5}
            />

            {/* Active path with premium gradient */}
            <path
              d={generatePathD(sortedMilestones.length, totalHeight, NODE_SPACING)}
              fill="none"
              stroke="url(#pathGradientPremium)"
              strokeWidth={PATH_WIDTH + 2}
              strokeLinecap="round"
              strokeDasharray="2000"
              strokeDashoffset={2000 - (progress.completedCount / progress.totalMilestones) * 2000}
              filter="url(#pathGlowPremium)"
              style={{ transition: 'stroke-dashoffset 1s ease-out' }}
            />
            
            {/* Animated energy flow on active path */}
            <path
              d={generatePathD(sortedMilestones.length, totalHeight, NODE_SPACING)}
              fill="none"
              stroke="url(#pathFlow)"
              strokeWidth={PATH_WIDTH - 2}
              strokeLinecap="round"
              strokeDasharray="20 20"
              strokeDashoffset={2000 - (progress.completedCount / progress.totalMilestones) * 2000}
              style={{ 
                animation: 'journey-path-flow 1s linear infinite',
                transition: 'stroke-dashoffset 1s ease-out'
              }}
            />
          </svg>
          
          {/* Sparkle particles on completed path */}
          {progress.completedCount > 0 && (
            <SparkleParticles 
              count={Math.min(progress.completedCount * 3, 15)}
              height={totalHeight}
              completedRatio={progress.completedCount / progress.totalMilestones}
              colors={colors}
            />
          )}

          {/* Start Node at Top */}
          <div style={{
            position: 'absolute',
            left: '50%',
            transform: 'translateX(-50%)',
            top: 20,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            zIndex: 2,
          }}>
            <div style={{
              width: 48,
              height: 48,
              borderRadius: '50%',
              backgroundColor: colors.success,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 24,
              boxShadow: `0 0 20px ${colors.successGlow}`,
            }}>
              🚀
            </div>
            <span style={{
              fontSize: 11,
              fontWeight: 700,
              color: colors.success,
              textTransform: 'uppercase',
              letterSpacing: '2px',
              marginTop: 8,
            }}>
              Start
            </span>
          </div>

          {/* Milestone Nodes */}
          {sortedMilestones.map((milestone, index) => {
            const isCompleted = milestone.completed;
            const isCurrent = index === currentMilestoneIndex;
            const y = 100 + (index + 1) * NODE_SPACING;
            const isLeft = index % 2 === 0;
            
            return (
              <MilestoneNode
                key={milestone.id}
                milestone={milestone}
                isCompleted={isCompleted}
                isCurrent={isCurrent}
                y={y}
                isLeft={isLeft}
                colors={colors}
                onClaim={onMilestoneClaim}
                onHelpClick={setHelpModalQuest}
                animationDelay={index * 0.1}
                currentLevel={progress.level}
              />
            );
          })}

          {/* Master Crown at Bottom */}
          <div style={{
            position: 'absolute',
            left: '50%',
            transform: 'translateX(-50%)',
            top: 100 + (sortedMilestones.length + 1) * NODE_SPACING,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            zIndex: 2,
          }}>
            <div style={{
              fontSize: 40,
              animation: 'journey-crown-float 3s ease-in-out infinite',
              filter: progress.level >= 10 ? 'none' : 'grayscale(0.8) opacity(0.4)',
            }}>
              👑
            </div>
            <span style={{
              fontSize: 11,
              fontWeight: 700,
              color: progress.level >= 10 ? colors.gold : colors.textMuted,
              textTransform: 'uppercase',
              letterSpacing: '2px',
              marginTop: 4,
            }}>
              Master
            </span>
          </div>
        </div>
      </div>
      
      {/* Help Modal */}
      {helpModalQuest && (
        <QuestHelpModal
          milestone={helpModalQuest}
          helpData={QUEST_HELP_INSTRUCTIONS[helpModalQuest.id]}
          onClose={() => setHelpModalQuest(null)}
          theme={theme}
        />
      )}
      {showCompanionHelp && (
        <CompanionHelpModal
          mascotImage={progress.mascotImage}
          phaseName={PHASE_DEFINITIONS[progress.phase].displayName}
          phaseDescription={PHASE_DEFINITIONS[progress.phase].description}
          onClose={() => setShowCompanionHelp(false)}
          theme={theme}
        />
      )}
    </div>
  );
};

// ============================================================================
// AI COMPANION HELP MODAL
// ============================================================================

interface CompanionHelpModalProps {
  mascotImage: string;
  phaseName: string;
  phaseDescription: string;
  onClose: () => void;
  theme?: 'light' | 'dark';
}

const CompanionHelpModal: React.FC<CompanionHelpModalProps> = ({
  mascotImage,
  phaseName,
  phaseDescription,
  onClose,
  theme = 'light',
}) => {
  const colors = useMemo(() => ({
    bg: theme === 'dark' ? '#1a1a1a' : '#ffffff',
    bgOverlay: theme === 'dark' ? 'rgba(0, 0, 0, 0.85)' : 'rgba(0, 0, 0, 0.6)',
    bgElevated: theme === 'dark' ? '#252525' : '#f5f5f5',
    text: theme === 'dark' ? '#ffffff' : '#000000',
    textSecondary: theme === 'dark' ? '#a3a3a3' : '#525252',
    textMuted: theme === 'dark' ? '#666666' : '#9ca3af',
    border: theme === 'dark' ? '#333333' : '#e5e5e5',
    primary: '#dc2626',
    gold: '#FFD700',
    goldGlow: 'rgba(255, 215, 0, 0.35)',
  }), [theme]);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: colors.bgOverlay,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        animation: 'companion-modal-fade-in 0.2s ease-out',
      }}
      onClick={onClose}
    >
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '92%',
          maxWidth: 520,
          maxHeight: '85vh',
          backgroundColor: colors.bg,
          borderRadius: 20,
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.4)',
          overflow: 'hidden',
          animation: 'companion-modal-slide-up 0.3s ease-out',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{
          padding: '20px 24px',
          background: `linear-gradient(135deg, ${colors.gold}22 0%, ${colors.primary}12 100%)`,
          borderBottom: `1px solid ${colors.border}`,
          position: 'relative',
        }}>
          <button
            onClick={onClose}
            style={{
              position: 'absolute',
              top: 16,
              right: 16,
              width: 32,
              height: 32,
              borderRadius: '50%',
              border: 'none',
              background: colors.bgElevated,
              color: colors.textSecondary,
              fontSize: 18,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = colors.primary;
              e.currentTarget.style.color = '#ffffff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = colors.bgElevated;
              e.currentTarget.style.color = colors.textSecondary;
            }}
          >
            ×
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{
              width: 56,
              height: 56,
              borderRadius: 14,
              background: colors.bgElevated,
              border: `2px solid ${colors.gold}`,
              boxShadow: `0 8px 18px ${colors.goldGlow}`,
              overflow: 'hidden',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <img
                src={mascotImage}
                alt="AI Companion"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            </div>
            <div>
              <div style={{
                fontSize: 10,
                fontWeight: 600,
                color: colors.primary,
                textTransform: 'uppercase',
                letterSpacing: '0.6px',
                marginBottom: 4,
              }}>
                Progress-Aware Guide
              </div>
              <div style={{
                fontSize: 20,
                fontWeight: 700,
                color: colors.text,
              }}>
                AI Companion
              </div>
              <div style={{
                fontSize: 13,
                color: colors.textSecondary,
                marginTop: 2,
              }}>
                Current mode: {phaseName} — {phaseDescription}
              </div>
            </div>
          </div>
        </div>

        <div style={{
          padding: '20px 24px',
          maxHeight: 'calc(85vh - 200px)',
          overflowY: 'auto',
        }}>
          <div style={{ marginBottom: 20 }}>
            <div style={{
              fontSize: 12,
              fontWeight: 600,
              color: colors.textMuted,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: 8,
            }}>
              What it is
            </div>
            <div style={{
              fontSize: 14,
              color: colors.text,
              lineHeight: 1.6,
            }}>
              Your AI Companion is ChatGPT, tuned to guide you through your financial journey.
              You can talk to it the same way you normally talk to ChatGPT.
            </div>
          </div>

          <div style={{ marginBottom: 20 }}>
            <div style={{
              fontSize: 12,
              fontWeight: 600,
              color: colors.textMuted,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: 8,
            }}>
              How it works
            </div>
            <ul style={{
              margin: 0,
              paddingLeft: 18,
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
              color: colors.textSecondary,
              fontSize: 13,
              lineHeight: 1.5,
            }}>
              <li>Your latest status and progress are shared so it has the full picture.</li>
              <li>Guidance adapts to your phase, focusing on the most relevant next steps.</li>
              <li>Responses stay aligned with your in-app progress and goals.</li>
            </ul>
          </div>

          <div>
            <div style={{
              fontSize: 12,
              fontWeight: 600,
              color: colors.textMuted,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: 8,
            }}>
              Unlocks over time
            </div>
            <div style={{
              fontSize: 13,
              color: colors.textSecondary,
              lineHeight: 1.6,
            }}>
              As you progress, you unlock new companion instructions and deeper guidance modes.
              Each phase refines the AI's focus so advice feels more personalized and actionable.
            </div>
          </div>
        </div>

        <div style={{
          padding: '16px 24px',
          borderTop: `1px solid ${colors.border}`,
          display: 'flex',
          justifyContent: 'flex-end',
        }}>
          <button
            onClick={onClose}
            style={{
              padding: '10px 20px',
              background: colors.bgElevated,
              color: colors.text,
              border: `1px solid ${colors.border}`,
              borderRadius: 10,
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = colors.primary;
              e.currentTarget.style.color = '#ffffff';
              e.currentTarget.style.borderColor = colors.primary;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = colors.bgElevated;
              e.currentTarget.style.color = colors.text;
              e.currentTarget.style.borderColor = colors.border;
            }}
          >
            Got it!
          </button>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// SPARKLE PARTICLES
// ============================================================================

interface SparkleParticlesProps {
  count: number;
  height: number;
  completedRatio: number;
  colors: Record<string, string>;
}

const SparkleParticles: React.FC<SparkleParticlesProps> = ({ count, height, completedRatio, colors }) => {
  const particles = useMemo(() => {
    return Array.from({ length: count }, (_, i) => ({
      id: i,
      x: 50 + (Math.random() - 0.5) * 30, // Near center
      y: Math.random() * height * completedRatio, // In completed section (from top)
      delay: Math.random() * 3000,
      duration: 2000 + Math.random() * 1000,
      size: 3 + Math.random() * 4,
    }));
  }, [count, height, completedRatio]);

  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'hidden' }}>
      {particles.map(p => (
        <div
          key={p.id}
          style={{
            position: 'absolute',
            left: `${p.x}%`,
            top: p.y,
            width: p.size,
            height: p.size,
            borderRadius: '50%',
            backgroundColor: colors.gold,
            boxShadow: `0 0 ${p.size * 2}px ${colors.gold}`,
            animation: `journey-sparkle-particle ${p.duration}ms ease-out infinite`,
            animationDelay: `${p.delay}ms`,
          }}
        />
      ))}
    </div>
  );
};

// ============================================================================
// PATH GENERATOR
// ============================================================================

function generatePathD(count: number, totalHeight: number, spacing: number): string {
  const centerX = 70; // Center in the 140px SVG
  const segments: string[] = [];
  
  // Start from START node position at top
  // START is at y = 20 (top) + 40 (container padding) = 60
  let y = 60;
  segments.push(`M ${centerX} ${y}`);
  
  // Create exactly count segments (one per milestone, plus one for the crown)
  // Flow from top to bottom
  for (let i = 0; i < count + 1; i++) {
    const nextY = y + spacing;
    const curveOffset = 25;
    const direction = i % 2 === 0 ? 1 : -1;
    
    // Bezier curve for organic feel (flowing downward)
    segments.push(
      `C ${centerX + direction * curveOffset} ${y + spacing * 0.3} ` +
      `${centerX - direction * curveOffset} ${nextY - spacing * 0.3} ` +
      `${centerX} ${nextY}`
    );
    
    y = nextY;
  }
  
  return segments.join(' ');
}

// ============================================================================
// MILESTONE NODE COMPONENT
// ============================================================================

interface MilestoneNodeProps {
  milestone: MilestoneStatus;
  isCompleted: boolean;
  isCurrent: boolean;
  y: number;
  isLeft: boolean;
  colors: Record<string, string>;
  onClaim?: (id: string) => void;
  onHelpClick?: (milestone: MilestoneStatus) => void;
  animationDelay: number;
  currentLevel: number;
}

const MilestoneNode: React.FC<MilestoneNodeProps> = ({
  milestone,
  isCompleted,
  isCurrent,
  y,
  isLeft,
  colors,
  onClaim,
  onHelpClick,
  animationDelay,
  currentLevel,
}) => {
  const categoryColor = getMilestoneCategoryColor(milestone.category);
  const [isHovered, setIsHovered] = React.useState(false);
  const [isClaiming, setIsClaiming] = React.useState(false);
  const [showCelebration, setShowCelebration] = React.useState(false);
  const [isClaimed, setIsClaimed] = React.useState(false);
  
  // Check if milestone is level-locked
  const isLevelLocked = milestone.unlockLevel !== undefined && milestone.unlockLevel > currentLevel;
  const levelsNeeded = isLevelLocked ? (milestone.unlockLevel! - currentLevel) : 0;
  
  // Handle claim action with celebration
  const handleClaim = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isClaiming || isClaimed) return;
    
    setIsClaiming(true);
    
    // Trigger celebration after brief delay
    setTimeout(() => {
      setShowCelebration(true);
      onClaim?.(milestone.id);
    }, 200);
    
    // Mark as claimed and hide celebration
    setTimeout(() => {
      setIsClaimed(true);
      setIsClaiming(false);
    }, 1500);
    
    setTimeout(() => {
      setShowCelebration(false);
    }, 2000);
  };
  
  return (
    <div style={{
      position: 'absolute',
      top: y,
      left: 0,
      right: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      animation: `journey-card-enter 0.5s ease-out ${animationDelay}s both`,
    }}>
      {/* Card positioned to the left side */}
      <div 
        style={{
          position: 'relative',
          width: 220,
          padding: 16,
          marginRight: isLeft ? 16 : 0,
          marginLeft: isLeft ? 0 : 16,
          order: isLeft ? 0 : 2,
          overflow: 'hidden',
          background: isLevelLocked
            ? `linear-gradient(135deg, ${colors.bgElevated} 0%, ${colors.bgCard} 100%)`
            : isCompleted 
              ? `linear-gradient(135deg, ${colors.bgCard} 0%, rgba(22, 163, 74, 0.08) 100%)`
              : isCurrent
                ? `linear-gradient(135deg, ${colors.bgCard} 0%, rgba(220, 38, 38, 0.05) 100%)`
                : colors.bgCard,
          borderRadius: 16,
          border: `1px solid ${isLevelLocked ? colors.border : isCompleted ? 'rgba(22, 163, 74, 0.3)' : isCurrent ? 'rgba(220, 38, 38, 0.3)' : colors.border}`,
          boxShadow: isLevelLocked
            ? 'none'
            : isCompleted 
              ? `0 8px 32px ${colors.successGlow}, 0 2px 8px rgba(0,0,0,0.1)`
              : isCurrent 
                ? `0 8px 32px ${colors.primaryGlow}, 0 2px 8px rgba(0,0,0,0.1)`
                : '0 4px 16px rgba(0,0,0,0.08)',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          opacity: isLevelLocked ? 0.5 : (!isCompleted && !isCurrent ? 0.7 : 1),
          transform: isHovered && !isLevelLocked ? 'translateY(-2px)' : 'translateY(0)',
          backdropFilter: 'blur(8px)',
          flexShrink: 0,
          filter: isLevelLocked ? 'grayscale(0.5)' : 'none',
        }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {/* Header with category and status */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 10,
        }}>
          {/* Category badge */}
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            padding: '3px 10px',
            background: isCompleted 
              ? `linear-gradient(135deg, ${colors.success} 0%, #15803d 100%)`
              : `linear-gradient(135deg, ${categoryColor} 0%, ${categoryColor}dd 100%)`,
            color: '#ffffff',
            borderRadius: 12,
            fontSize: 10,
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          }}>
            {isCompleted && <span>✓</span>}
            {milestone.category}
          </div>
          
          {/* Right side: Help icon + XP Badge */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {/* Help icon button */}
            {QUEST_HELP_INSTRUCTIONS[milestone.id] && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onHelpClick?.(milestone);
                }}
                style={{
                  width: 20,
                  height: 20,
                  borderRadius: '50%',
                  border: `1px solid ${colors.border}`,
                  background: colors.bgElevated,
                  color: colors.textSecondary,
                  fontSize: 11,
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.2s ease',
                  padding: 0,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = colors.primary;
                  e.currentTarget.style.color = '#ffffff';
                  e.currentTarget.style.borderColor = colors.primary;
                  e.currentTarget.style.transform = 'scale(1.1)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = colors.bgElevated;
                  e.currentTarget.style.color = colors.textSecondary;
                  e.currentTarget.style.borderColor = colors.border;
                  e.currentTarget.style.transform = 'scale(1)';
                }}
                title="How to complete this quest"
              >
                ?
              </button>
            )}
            
            {/* XP Badge - Premium style */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 3,
              padding: '3px 10px',
              background: isCompleted 
                ? `linear-gradient(135deg, ${colors.gold} 0%, #d97706 100%)`
                : `linear-gradient(135deg, ${colors.bgElevated} 0%, ${colors.border} 100%)`,
              color: isCompleted ? '#000' : colors.textSecondary,
              borderRadius: 12,
              fontSize: 11,
              fontWeight: 700,
              boxShadow: isCompleted ? `0 2px 8px ${colors.goldGlow}` : 'none',
            }}>
              <span>+{milestone.xp}</span>
              <span style={{ 
                fontSize: 9, 
                opacity: 0.8,
                fontWeight: 600,
              }}>XP</span>
            </div>
          </div>
        </div>

        {/* Title - Full display */}
        <div style={{
          fontSize: 16,
          fontWeight: 700,
          color: colors.text,
          marginBottom: 6,
          lineHeight: 1.3,
          letterSpacing: '-0.3px',
        }}>
          {milestone.title}
        </div>

        {/* Description - Full display */}
        <div style={{
          fontSize: 13,
          color: colors.textSecondary,
          marginBottom: 14,
          lineHeight: 1.5,
        }}>
          {milestone.description}
        </div>

        {/* Progress bar for current milestone */}
        {isCurrent && !isCompleted && milestone.progress > 0 && milestone.progress < 100 && (
          <div style={{ marginBottom: 14 }}>
            <div style={{
              height: 8,
              backgroundColor: colors.bgElevated,
              borderRadius: 4,
              overflow: 'hidden',
              boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.1)',
            }}>
              <div style={{
                height: '100%',
                width: `${milestone.progress}%`,
                background: `linear-gradient(90deg, ${colors.primary} 0%, #ef4444 100%)`,
                borderRadius: 4,
                transition: 'width 0.5s ease-out',
                boxShadow: `0 0 8px ${colors.primaryGlow}`,
              }} />
            </div>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 11,
              color: colors.textMuted,
              marginTop: 6,
            }}>
              <span>{milestone.current} / {milestone.target}</span>
              <span>{Math.round(milestone.progress)}%</span>
            </div>
          </div>
        )}

        {/* Bottom action row */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
        }}>
          {isCompleted && !isClaimed && !showCelebration ? (
            // Claimable state - show claim button
            <button
              onClick={handleClaim}
              disabled={isClaiming}
              style={{
                padding: '8px 18px',
                background: `linear-gradient(135deg, ${colors.gold} 0%, #d97706 100%)`,
                color: '#000',
                border: 'none',
                borderRadius: 12,
                fontSize: 12,
                fontWeight: 700,
                cursor: isClaiming ? 'default' : 'pointer',
                transition: 'all 0.2s ease',
                boxShadow: `0 4px 12px ${colors.goldGlow}`,
                animation: isClaiming ? 'none' : 'journey-claim-pulse 2s ease-in-out infinite',
                opacity: isClaiming ? 0.7 : 1,
              }}
              onMouseEnter={(e) => {
                if (!isClaiming) {
                  e.currentTarget.style.transform = 'scale(1.08)';
                  e.currentTarget.style.boxShadow = `0 6px 24px ${colors.goldGlow}`;
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'scale(1)';
                e.currentTarget.style.boxShadow = `0 4px 12px ${colors.goldGlow}`;
              }}
            >
              {isClaiming ? '✨ Claiming...' : `🎁 Claim +${milestone.xp} XP`}
            </button>
          ) : isCompleted && (isClaimed || showCelebration) ? (
            // Claimed state
            <span style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 12,
              fontWeight: 600,
              color: colors.success,
              animation: showCelebration ? 'journey-claim-success 0.5s ease-out' : 'none',
            }}>
              <span style={{ fontSize: 14 }}>🎉</span>
              Completed!
            </span>
          ) : isLevelLocked ? (
            <span style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 11,
              fontWeight: 600,
              color: '#9333EA', // Purple for level-locked
              background: 'rgba(147, 51, 234, 0.1)',
              padding: '4px 10px',
              borderRadius: 8,
            }}>
              <span style={{ fontSize: 12 }}>⭐</span>
              Unlocks at Lv.{milestone.unlockLevel}
            </span>
          ) : isCurrent && onClaim ? (
            <button
              onClick={() => onClaim(milestone.id)}
              style={{
                padding: '8px 18px',
                background: `linear-gradient(135deg, ${colors.primary} 0%, #991b1b 100%)`,
                color: '#ffffff',
                border: 'none',
                borderRadius: 12,
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                boxShadow: `0 4px 12px ${colors.primaryGlow}`,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'scale(1.05)';
                e.currentTarget.style.boxShadow = `0 6px 20px ${colors.primaryGlow}`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'scale(1)';
                e.currentTarget.style.boxShadow = `0 4px 12px ${colors.primaryGlow}`;
              }}
            >
              🎯 In Progress
            </button>
          ) : (
            <span style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 11,
              color: colors.textMuted,
            }}>
              <span style={{ fontSize: 12 }}>🔒</span>
              Locked
            </span>
          )}
        </div>
        
        {/* Celebration overlay with confetti */}
        {showCelebration && (
          <>
            {/* Floating XP */}
            <div style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              fontSize: 24,
              fontWeight: 800,
              color: colors.gold,
              textShadow: `0 2px 10px ${colors.goldGlow}`,
              animation: 'journey-xp-float 1.5s ease-out forwards',
              zIndex: 10,
              pointerEvents: 'none',
            }}>
              +{milestone.xp} XP!
            </div>
            
            {/* Confetti particles */}
            {Array.from({ length: 12 }).map((_, i) => {
              const angle = (i / 12) * 360;
              const tx = Math.cos(angle * Math.PI / 180) * (60 + Math.random() * 40);
              const ty = Math.sin(angle * Math.PI / 180) * (40 + Math.random() * 30) - 20;
              const confettiColors = ['#FFD700', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7'];
              return (
                <div
                  key={i}
                  style={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    width: 8,
                    height: 8,
                    backgroundColor: confettiColors[i % confettiColors.length],
                    borderRadius: i % 2 === 0 ? '50%' : '2px',
                    animation: 'journey-confetti-burst 1s ease-out forwards',
                    animationDelay: `${i * 30}ms`,
                    zIndex: 9,
                    pointerEvents: 'none',
                    // @ts-ignore - CSS custom properties for animation
                    '--tx': `${tx}px`,
                    '--ty': `${ty}px`,
                  } as React.CSSProperties}
                />
              );
            })}
          </>
        )}
      </div>

      {/* Premium Node Circle - Always centered */}
      <div style={{
        width: NODE_SIZE,
        height: NODE_SIZE,
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 24,
        fontWeight: 600,
        flexShrink: 0,
        position: 'relative',
        zIndex: 2,
        order: 1,
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        transform: isHovered ? 'scale(1.1)' : 'scale(1)',
        ...(isCompleted ? {
          background: `linear-gradient(145deg, ${colors.success} 0%, #15803d 100%)`,
          color: '#ffffff',
          boxShadow: `
            0 4px 20px ${colors.successGlow},
            inset 0 2px 4px rgba(255,255,255,0.3),
            inset 0 -2px 4px rgba(0,0,0,0.1)
          `,
          animation: 'journey-node-glow 2s ease-in-out infinite',
        } : isLevelLocked ? {
          background: `linear-gradient(145deg, ${colors.bgElevated} 0%, ${colors.bgCard} 100%)`,
          border: `2px dashed ${colors.border}`,
          color: colors.textMuted,
          boxShadow: 'none',
          filter: 'grayscale(0.7)',
          opacity: 0.5,
        } : isCurrent ? {
          background: `linear-gradient(145deg, ${colors.primary} 0%, #991b1b 100%)`,
          color: '#ffffff',
          boxShadow: `
            0 0 0 4px ${colors.primaryGlow},
            0 4px 20px ${colors.primaryGlow},
            inset 0 2px 4px rgba(255,255,255,0.2)
          `,
          animation: 'journey-node-pulse 2s ease-in-out infinite',
        } : {
          background: `linear-gradient(145deg, ${colors.bgCard} 0%, ${colors.bgElevated} 100%)`,
          border: `2px dashed ${colors.border}`,
          color: colors.textMuted,
          boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.05)',
        }),
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      >
        {isCompleted ? '✓' : milestone.icon}
        
        {/* Animated ring for current */}
        {isCurrent && (
          <div style={{
            position: 'absolute',
            inset: -8,
            borderRadius: '50%',
            border: `2px solid ${colors.primary}`,
            animation: 'journey-node-pulse 2s ease-in-out infinite',
            opacity: 0.5,
          }} />
        )}
        
        {/* Success checkmark glow */}
        {isCompleted && (
          <div style={{
            position: 'absolute',
            inset: -4,
            borderRadius: '50%',
            background: `radial-gradient(circle, ${colors.successGlow} 0%, transparent 70%)`,
            animation: 'journey-node-glow 2s ease-in-out infinite',
            zIndex: -1,
          }} />
        )}
      </div>

      {/* Spacer for the opposite side */}
      <div style={{
        width: 220,
        flexShrink: 0,
        order: isLeft ? 2 : 0,
      }} />
    </div>
  );
};

export default JourneyPath;
