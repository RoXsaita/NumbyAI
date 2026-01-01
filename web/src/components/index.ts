/**
 * Components Index
 * 
 * Exports all journey system components for easy importing.
 */

// Mascot components
export { Mascot, MiniMascot, CelebratingMascot } from './Mascot';
export type { MascotProps, MiniMascotProps, CelebratingMascotProps, MascotState } from './Mascot';

// Status bar components
export { StatusBar, ExpandedStatus } from './StatusBar';
export type { StatusBarProps, ExpandedStatusProps } from './StatusBar';

// Journey path component
export { JourneyPath } from './JourneyPath';
export type { JourneyPathProps } from './JourneyPath';

// Milestone card components
export { MilestoneCard, MilestoneList } from './MilestoneCard';
export type { MilestoneCardProps, MilestoneListProps } from './MilestoneCard';

// Celebration effects
export { Confetti, LevelUpOverlay, XPGainedPopup } from './Confetti';
export type { ConfettiProps, LevelUpOverlayProps, XPGainedPopupProps } from './Confetti';

// Quest help modal
export { QuestHelpModal } from './QuestHelpModal';
export type { QuestHelpModalProps } from './QuestHelpModal';

// Error boundary (existing)
export { ErrorBoundary } from './ErrorBoundary';

