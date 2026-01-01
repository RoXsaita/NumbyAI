/**
 * QuestHelpModal Component - Help instructions for quests
 * 
 * A modal overlay that displays:
 * - Quest title and icon
 * - Detailed explanation
 * - Example prompt preset
 * - Pro tips
 */

import React, { useEffect, useMemo } from 'react';
import { MilestoneStatus, QuestHelp, getMilestoneCategoryColor } from '../lib/progression';

// ============================================================================
// CSS KEYFRAMES
// ============================================================================

const KEYFRAMES = `
@keyframes quest-modal-fade-in {
  0% { opacity: 0; }
  100% { opacity: 1; }
}

@keyframes quest-modal-slide-up {
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
  
  const existing = document.getElementById('quest-help-modal-keyframes');
  if (existing) return;
  
  const styleEl = document.createElement('style');
  styleEl.id = 'quest-help-modal-keyframes';
  styleEl.textContent = KEYFRAMES;
  document.head.appendChild(styleEl);
  keyframesInjected = true;
}

// ============================================================================
// TYPES
// ============================================================================

export interface QuestHelpModalProps {
  milestone: MilestoneStatus;
  helpData: QuestHelp | undefined;
  onClose: () => void;
  theme?: 'light' | 'dark';
}

// ============================================================================
// COMPONENT
// ============================================================================

export const QuestHelpModal: React.FC<QuestHelpModalProps> = ({
  milestone,
  helpData,
  onClose,
  theme = 'light',
}) => {
  useEffect(() => {
    injectKeyframes();
  }, []);

  // Theme colors
  const colors = useMemo(() => ({
    bg: theme === 'dark' ? '#1a1a1a' : '#ffffff',
    bgOverlay: theme === 'dark' ? 'rgba(0, 0, 0, 0.85)' : 'rgba(0, 0, 0, 0.6)',
    bgElevated: theme === 'dark' ? '#252525' : '#f5f5f5',
    bgCode: theme === 'dark' ? '#0d1117' : '#f6f8fa',
    text: theme === 'dark' ? '#ffffff' : '#000000',
    textSecondary: theme === 'dark' ? '#a3a3a3' : '#525252',
    textMuted: theme === 'dark' ? '#666666' : '#9ca3af',
    border: theme === 'dark' ? '#333333' : '#e5e5e5',
    primary: '#dc2626',
    success: '#16a34a',
    gold: '#FFD700',
  }), [theme]);

  const categoryColor = getMilestoneCategoryColor(milestone.category);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);

  if (!helpData) {
    return null;
  }

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
        animation: 'quest-modal-fade-in 0.2s ease-out',
      }}
      onClick={onClose}
    >
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '90%',
          maxWidth: 480,
          maxHeight: '85vh',
          backgroundColor: colors.bg,
          borderRadius: 20,
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.4)',
          overflow: 'hidden',
          animation: 'quest-modal-slide-up 0.3s ease-out',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          background: `linear-gradient(135deg, ${categoryColor}15 0%, ${categoryColor}05 100%)`,
          borderBottom: `1px solid ${colors.border}`,
          position: 'relative',
        }}>
          {/* Close button */}
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

          {/* Icon and title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{
              width: 56,
              height: 56,
              borderRadius: 14,
              background: `linear-gradient(135deg, ${categoryColor} 0%, ${categoryColor}cc 100%)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 28,
              boxShadow: `0 4px 12px ${categoryColor}40`,
            }}>
              {milestone.icon}
            </div>
            <div>
              <div style={{
                fontSize: 10,
                fontWeight: 600,
                color: categoryColor,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                marginBottom: 4,
              }}>
                {milestone.category}
              </div>
              <div style={{
                fontSize: 20,
                fontWeight: 700,
                color: colors.text,
              }}>
                {milestone.title}
              </div>
              <div style={{
                fontSize: 13,
                color: colors.textSecondary,
                marginTop: 2,
              }}>
                {milestone.description}
              </div>
            </div>
          </div>
        </div>

        {/* Content - Scrollable */}
        <div style={{
          padding: '20px 24px',
          maxHeight: 'calc(85vh - 200px)',
          overflowY: 'auto',
        }}>
          {/* Explanation */}
          <div style={{ marginBottom: 24 }}>
            <div style={{
              fontSize: 12,
              fontWeight: 600,
              color: colors.textMuted,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: 8,
            }}>
              How to Complete
            </div>
            <div style={{
              fontSize: 14,
              color: colors.text,
              lineHeight: 1.6,
            }}>
              {helpData.explanation}
            </div>
          </div>

          {/* Prompt Preset */}
          <div style={{ marginBottom: 24 }}>
            <div style={{
              fontSize: 12,
              fontWeight: 600,
              color: colors.textMuted,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: 8,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}>
              <span>💬</span>
              Try This Prompt (TWEAK TO MATCH YOUR STATEMENT DETAILS)
            </div>
            <div style={{
              backgroundColor: colors.bgCode,
              borderRadius: 12,
              border: `1px solid ${colors.border}`,
              padding: '14px 16px',
              fontSize: 13,
              fontFamily: '"SF Mono", "Fira Code", "Consolas", monospace',
              color: colors.text,
              lineHeight: 1.5,
              wordBreak: 'break-word',
            }}>
              {helpData.promptPreset}
            </div>
          </div>

          {/* Tips */}
          {helpData.tips && helpData.tips.length > 0 && (
            <div>
              <div style={{
                fontSize: 12,
                fontWeight: 600,
                color: colors.textMuted,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                marginBottom: 10,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}>
                <span>💡</span>
                Pro Tips
              </div>
              <ul style={{
                margin: 0,
                paddingLeft: 20,
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
              }}>
                {helpData.tips.map((tip, index) => (
                  <li key={index} style={{
                    fontSize: 13,
                    color: colors.textSecondary,
                    lineHeight: 1.5,
                  }}>
                    {tip}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '16px 24px',
          borderTop: `1px solid ${colors.border}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 12px',
            background: `linear-gradient(135deg, ${colors.gold}20 0%, ${colors.gold}10 100%)`,
            borderRadius: 8,
          }}>
            <span style={{ fontSize: 14 }}>🎁</span>
            <span style={{
              fontSize: 13,
              fontWeight: 700,
              color: colors.gold,
            }}>
              +{milestone.xp} XP
            </span>
          </div>
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

export default QuestHelpModal;

