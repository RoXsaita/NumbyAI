/**
 * Progression System for Gamified User Journey
 * 
 * This module calculates user XP, level, and milestone completion
 * based on existing database data (no new models required).
 * 
 * Features infinite leveling with XP-based formula.
 */

import { MASCOT_IMAGE_DATA } from './mascot-data';

// ============================================================================
// TYPES
// ============================================================================

export interface MilestoneDefinition {
  id: string;
  title: string;
  description: string;
  xp: number;
  category: 'onboarding' | 'data' | 'analysis' | 'mastery' | 'tools' | 'longterm';
  icon: string; // SVG path or emoji
  order: number; // Display order in journey path
  unlockLevel?: number; // Optional: level required to unlock this milestone
}

export interface MilestoneStatus extends MilestoneDefinition {
  completed: boolean;
  progress: number; // 0-100 percentage
  current: number;
  target: number;
  claimable: boolean; // True if completed but not yet "claimed" (celebrated)
}

export interface LevelInfo {
  level: number;
  title: string;
  xpRequired: number;
  xpForNext: number;
  mascot: MascotVariant;
  color: string;
}

export type MascotVariant = 
  | 'base' 
  | 'teacher' 
  | 'analyst' 
  | 'laptop' 
  | 'presenter' 
  | 'money' 
  | 'banker' 
  | 'detective' 
  | 'wallet';

export interface ProgressState {
  totalXP: number;
  level: number;
  levelTitle: string;
  currentLevelXP: number; // XP earned in current level
  nextLevelXP: number; // XP needed for next level
  levelProgress: number; // 0-100 percentage to next level
  mascot: MascotVariant;
  mascotImage: string;
  milestones: MilestoneStatus[];
  completedCount: number;
  totalMilestones: number;
  nextMilestone: MilestoneStatus | null;
  bonusXP: number; // XP from repeatable actions (extra months, budgets)
  phase: AIPhase; // Current AI personality phase
}

// ============================================================================
// AI PERSONALITY PHASES
// ============================================================================

export type AIPhase = 'beginner' | 'student' | 'analyst' | 'advisor' | 'master';

export interface PhaseDefinition {
  id: AIPhase;
  displayName: string;
  mascot: MascotVariant;
  description: string;
  triggerMilestone: string | null;
}

export const PHASE_DEFINITIONS: Record<AIPhase, PhaseDefinition> = {
  beginner: {
    id: 'beginner',
    displayName: 'Beginner',
    mascot: 'base',
    description: 'Learning the basics',
    triggerMilestone: null,
  },
  student: {
    id: 'student',
    displayName: 'Student',
    mascot: 'teacher',
    description: 'Building good habits',
    triggerMilestone: 'month_1',
  },
  analyst: {
    id: 'analyst',
    displayName: 'Analyst',
    mascot: 'analyst',
    description: 'Tracking patterns',
    triggerMilestone: 'first_budget',
  },
  advisor: {
    id: 'advisor',
    displayName: 'Advisor',
    mascot: 'presenter',
    description: 'Optimizing finances',
    triggerMilestone: 'month_6',
  },
  master: {
    id: 'master',
    displayName: 'Master',
    mascot: 'wallet',
    description: 'Financial mastery',
    triggerMilestone: 'month_12',
  },
};

/**
 * Determine user's current AI personality phase based on data
 */
export function determinePhase(totalMonths: number, budgetsConfigured: number): AIPhase {
  if (totalMonths >= 12) return 'master';
  if (totalMonths >= 6) return 'advisor';
  if (budgetsConfigured >= 1) return 'analyst';
  if (totalMonths >= 1) return 'student';
  return 'beginner';
}

/**
 * Determine which phase a milestone belongs to based on its order
 * Used for journey path color coding
 */
export function getPhaseForMilestone(milestoneOrder: number): AIPhase {
  // Beginner: orders 1-3 (onboarding milestones)
  if (milestoneOrder <= 3) return 'beginner';
  // Student: orders 4-6 (first steps, early data)
  if (milestoneOrder <= 6) return 'student';
  // Analyst: orders 7-14 (mid-level milestones)
  if (milestoneOrder <= 14) return 'analyst';
  // Advisor: orders 15-18 (year one mastery)
  if (milestoneOrder <= 18) return 'advisor';
  // Master: orders 19+ (advanced milestones)
  return 'master';
}

export interface DataOverview {
  total_months?: number;
  banks?: Array<{ name: string }>;
  budgets_configured?: number;
  date_range?: { from: string; to: string };
}

export interface UserSettings {
  functional_currency?: string;
  bank_accounts_count?: number;
  onboarding_complete?: boolean;
}

export interface ProgressInput {
  settings?: UserSettings | null;
  dataOverview?: DataOverview | null;
  catCount?: number;
  parsingCount?: number;
  mutationCount?: number; // For recategorization tracking
  // Tool usage tracking
  dataFetchCount?: number;
  statementCount?: number;
  preferencesUpdated?: boolean;
  multiMonthAnalysisCount?: number;
  fullYearBudgetSet?: boolean;
  foreignCurrencyStatementCount?: number; // Statements processed in non-functional currency
}

export interface QuestHelp {
  explanation: string;
  promptPreset: string;
  tips: string[];
}

// ============================================================================
// INFINITE LEVELING SYSTEM
// ============================================================================

// Level titles - expanded for multi-year progression
// Levels 1-10: Basic progression
// Levels 11-12: Sage tier (wisdom)
// Levels 13-15: Grandmaster tier (excellence)
// Levels 16-18: Legend tier (legacy)
// Levels 19-20: Titan tier (ultimate)
// Levels 21+: Eternal (infinite scaling)
const LEVEL_TITLES = [
  'Novice',       // 1
  'Learner',      // 2
  'Explorer',     // 3
  'Organizer',    // 4
  'Tracker',      // 5
  'Planner',      // 6
  'Strategist',   // 7
  'Detective',    // 8
  'Expert',       // 9
  'Master',       // 10
  'Sage',         // 11
  'Sage',         // 12
  'Grandmaster',  // 13
  'Grandmaster',  // 14
  'Grandmaster',  // 15
  'Legend',       // 16
  'Legend',       // 17
  'Legend',       // 18
  'Titan',        // 19
  'Titan',        // 20
];

// Extended tier info for levels beyond 20
const ETERNAL_TITLE = 'Eternal';

// Mascot variants that cycle - wallet is the final evolved form
const MASCOT_CYCLE: MascotVariant[] = [
  'base',       // 1 - Starting out
  'teacher',    // 2 - Learning basics
  'analyst',    // 3 - Analyzing data
  'laptop',     // 4 - Getting organized
  'presenter',  // 5 - Presenting insights
  'money',      // 6 - Money management
  'banker',     // 7 - Professional level
  'detective',  // 8 - Deep analysis
  'money',      // 9 - Master of money
  'wallet',     // 10+ - Ultimate financial mastery
];

// Level colors - expanded with premium tiers
const LEVEL_COLORS = [
  '#6B7280', // 1 - Gray (Novice)
  '#8B5CF6', // 2 - Purple (Learner)
  '#3B82F6', // 3 - Blue (Explorer)
  '#10B981', // 4 - Green (Organizer)
  '#F59E0B', // 5 - Amber (Tracker)
  '#EF4444', // 6 - Red (Planner)
  '#EC4899', // 7 - Pink (Strategist)
  '#8B5CF6', // 8 - Purple (Detective)
  '#F59E0B', // 9 - Amber (Expert)
  '#FFD700', // 10 - Gold (Master)
  '#00CED1', // 11 - Dark Cyan (Sage I)
  '#20B2AA', // 12 - Light Sea Green (Sage II)
  '#FF6347', // 13 - Tomato (Grandmaster I)
  '#FF4500', // 14 - Orange Red (Grandmaster II)
  '#DC143C', // 15 - Crimson (Grandmaster III)
  '#9400D3', // 16 - Dark Violet (Legend I)
  '#8A2BE2', // 17 - Blue Violet (Legend II)
  '#9932CC', // 18 - Dark Orchid (Legend III)
  '#FFD700', // 19 - Gold (Titan I)
  '#FFA500', // 20 - Orange (Titan II)
];

/**
 * Calculate XP required for a given level using quadratic scaling
 * Formula: XP = 50 * level^2
 * Level 1: 0, Level 2: 100, Level 3: 250, Level 4: 450, etc.
 */
function getXPForLevel(level: number): number {
  if (level <= 1) return 0;
  // Cumulative XP needed: sum of 50, 100, 150, 200...
  // = 50 * (1 + 2 + 3 + ... + (level-1))
  // = 50 * (level-1) * level / 2
  // = 25 * level * (level - 1)
  return 25 * level * (level - 1);
}

/**
 * Calculate level from total XP (inverse of getXPForLevel)
 * Solving: totalXP = 25 * level * (level - 1)
 * level = (1 + sqrt(1 + 4*totalXP/25)) / 2
 */
function getLevelFromXP(totalXP: number): number {
  if (totalXP <= 0) return 1;
  const level = Math.floor((1 + Math.sqrt(1 + (4 * totalXP) / 25)) / 2);
  return Math.max(1, level);
}

/**
 * Get level info for a given level number
 * Supports extended progression with themed tiers
 */
export function getLevelInfo(level: number): LevelInfo {
  const mascotIndex = Math.min(level - 1, MASCOT_CYCLE.length - 1);
  const colorIndex = Math.min(level - 1, LEVEL_COLORS.length - 1);
  
  let title: string;
  
  if (level <= LEVEL_TITLES.length) {
    // Use predefined titles for levels 1-20
    title = LEVEL_TITLES[level - 1];
    
    // Add tier suffixes for grouped titles
    if (level >= 11 && level <= 12) {
      // Sage I, Sage II
      title = `${title} ${toRomanNumeral(level - 10)}`;
    } else if (level >= 13 && level <= 15) {
      // Grandmaster I, II, III
      title = `${title} ${toRomanNumeral(level - 12)}`;
    } else if (level >= 16 && level <= 18) {
      // Legend I, II, III
      title = `${title} ${toRomanNumeral(level - 15)}`;
    } else if (level >= 19 && level <= 20) {
      // Titan I, II
      title = `${title} ${toRomanNumeral(level - 18)}`;
    }
  } else {
    // Eternal tier for levels 21+
    const eternalTier = level - 20;
    title = `${ETERNAL_TITLE} ${toRomanNumeral(eternalTier)}`;
  }
  
  return {
    level,
    title,
    xpRequired: getXPForLevel(level),
    xpForNext: getXPForLevel(level + 1),
    mascot: MASCOT_CYCLE[mascotIndex],
    color: LEVEL_COLORS[colorIndex],
  };
}

function toRomanNumeral(num: number): string {
  if (num <= 1) return '';
  const numerals: [number, string][] = [
    [10, 'X'], [9, 'IX'], [5, 'V'], [4, 'IV'], [1, 'I']
  ];
  let result = '';
  for (const [value, symbol] of numerals) {
    while (num >= value) {
      result += symbol;
      num -= value;
    }
  }
  return result;
}

// ============================================================================
// MILESTONE DEFINITIONS
// ============================================================================

export const MILESTONE_DEFINITIONS: MilestoneDefinition[] = [
  // ========== ONBOARDING MILESTONES (Order 1-3) ==========
  {
    id: 'currency_set',
    title: 'Currency Pioneer',
    description: 'Set your functional currency',
    xp: 50,
    category: 'onboarding',
    icon: '💱',
    order: 1,
  },
  {
    id: 'banks_configured',
    title: 'Bank Setup',
    description: 'save banking preferences',
    xp: 50,
    category: 'onboarding',
    icon: '🏦',
    order: 2,
  },
  {
    id: 'first_parsing',
    title: 'Statement Decoder',
    description: 'Set up your first parsing preference',
    xp: 100,
    category: 'onboarding',
    icon: '📄',
    order: 3,
  },
  
  // ========== EARLY DATA MILESTONES (Order 4-7) ==========
  {
    id: 'month_1',
    title: 'First Steps',
    description: 'Save your first month of data',
    xp: 200,
    category: 'data',
    icon: '📅',
    order: 4,
  },
  {
    id: 'statements_2',
    title: 'Double Entry',
    description: 'Save 2 bank statements (bank + month combos)',
    xp: 150,
    category: 'data',
    icon: '📑',
    order: 4.3,
  },
  {
    id: 'statements_3',
    title: 'Triple Tracker',
    description: 'Save 3 bank statements',
    xp: 200,
    category: 'data',
    icon: '📚',
    order: 4.6,
  },
  {
    id: 'categories_5',
    title: 'Category Starter',
    description: 'Create 5+ categorization rules',
    xp: 100,
    category: 'data',
    icon: '🏷️',
    order: 5,
  },
  {
    id: 'first_budget',
    title: 'Budget Beginner',
    description: 'Set your first budget',
    xp: 150,
    category: 'analysis',
    icon: '💰',
    order: 6,
  },
  {
    id: 'categories_10',
    title: 'Category Builder',
    description: 'Create 10+ categorization rules',
    xp: 150,
    category: 'data',
    icon: '🗂️',
    order: 7,
  },
  
  // ========== EARLY TOOL QUESTS (Order 8-10) ==========
  {
    id: 'first_data_fetch',
    title: 'Data Explorer',
    description: 'Fetch your financial data for the first time',
    xp: 75,
    category: 'tools',
    icon: '🔍',
    order: 8,
  },
  {
    id: 'month_3',
    title: 'Quarter Champion',
    description: 'Track 3 months of data',
    xp: 300,
    category: 'data',
    icon: '📊',
    order: 9,
  },
  {
    id: 'recategorization',
    title: 'Fine Tuner',
    description: 'Recategorize transactions',
    xp: 100,
    category: 'analysis',
    icon: '🔄',
    order: 10,
  },
  
  // ========== MID-LEVEL MILESTONES (Order 11-15) ==========
  {
    id: 'categories_20',
    title: 'Category Expert',
    description: 'Create 20+ categorization rules',
    xp: 200,
    category: 'data',
    icon: '🎯',
    order: 11,
  },
  {
    id: 'budgets_5',
    title: 'Budget Builder',
    description: 'Set 5+ budgets',
    xp: 250,
    category: 'analysis',
    icon: '📈',
    order: 12,
  },
  {
    id: 'preferences_updated',
    title: 'Customizer',
    description: 'Update your app preferences',
    xp: 50,
    category: 'tools',
    icon: '⚙️',
    order: 13,
    unlockLevel: 5,
  },
  {
    id: 'month_6',
    title: 'Half Year Hero',
    description: 'Track 6 months of data',
    xp: 400,
    category: 'data',
    icon: '🏆',
    order: 14,
  },
  {
    id: 'multi_month_analysis',
    title: 'Trend Spotter',
    description: 'Analyze 3+ months of data at once',
    xp: 150,
    category: 'tools',
    icon: '📉',
    order: 15,
    unlockLevel: 6,
  },
  
  // ========== YEAR ONE MASTERY (Order 16-18) ==========
  {
    id: 'budgets_10',
    title: 'Budget Architect',
    description: 'Set 10+ budgets across categories',
    xp: 350,
    category: 'analysis',
    icon: '🏗️',
    order: 16,
    unlockLevel: 7,
  },
  {
    id: 'categories_50',
    title: 'Category Grandmaster',
    description: 'Create 50+ categorization rules',
    xp: 400,
    category: 'data',
    icon: '🏅',
    order: 17,
    unlockLevel: 8,
  },
  {
    id: 'month_12',
    title: 'Full Year Champion',
    description: 'Track 12 months of financial data',
    xp: 500,
    category: 'mastery',
    icon: '👑',
    order: 18,
  },
  
  // ========== ADVANCED TOOL QUESTS (Order 19-21) ==========
  {
    id: 'statements_10',
    title: 'Statement Pro',
    description: 'Process 10+ bank statements',
    xp: 300,
    category: 'tools',
    icon: '📑',
    order: 19,
    unlockLevel: 10,
  },
  {
    id: 'mutations_50',
    title: 'Recategorization Master',
    description: 'Perform 50+ transaction recategorizations',
    xp: 400,
    category: 'tools',
    icon: '🔀',
    order: 20,
    unlockLevel: 10,
  },
  {
    id: 'full_year_budget',
    title: 'Annual Planner',
    description: 'Create budgets covering a full year',
    xp: 450,
    category: 'tools',
    icon: '📆',
    order: 21,
    unlockLevel: 11,
  },
  {
    id: 'foreign_currency_statement',
    title: 'Currency Converter',
    description: 'Process a statement in a foreign currency',
    xp: 400,
    category: 'tools',
    icon: '🌍',
    order: 21.5,
    unlockLevel: 11,
  },
  
  // ========== YEAR TWO MILESTONES (Order 22-24) ==========
  {
    id: 'month_18',
    title: 'Year and a Half',
    description: 'Track 18 months of financial history',
    xp: 600,
    category: 'longterm',
    icon: '⏳',
    order: 22,
    unlockLevel: 12,
  },
  {
    id: 'categories_100',
    title: 'Category Overlord',
    description: 'Create 100+ categorization rules',
    xp: 500,
    category: 'data',
    icon: '🌟',
    order: 23,
    unlockLevel: 13,
  },
  {
    id: 'month_24',
    title: 'Two Year Titan',
    description: 'Track 2 full years of financial data',
    xp: 800,
    category: 'longterm',
    icon: '🎖️',
    order: 24,
    unlockLevel: 14,
  },
  
  // ========== YEAR THREE+ MILESTONES (Order 25-27) ==========
  {
    id: 'budgets_20',
    title: 'Budget Emperor',
    description: 'Set 20+ budgets for complete coverage',
    xp: 600,
    category: 'analysis',
    icon: '👨‍💼',
    order: 25,
    unlockLevel: 15,
  },
  {
    id: 'month_36',
    title: 'Three Year Legend',
    description: 'Track 3 full years of financial history',
    xp: 1000,
    category: 'longterm',
    icon: '🏰',
    order: 26,
    unlockLevel: 16,
  },
  {
    id: 'financial_mastery',
    title: 'Financial Enlightenment',
    description: 'Achieve complete financial tracking mastery',
    xp: 1500,
    category: 'mastery',
    icon: '🌅',
    order: 27,
    unlockLevel: 18,
  },
];

// ============================================================================
// MASCOT IMAGES (Base64 encoded for reliable bundling)
// ============================================================================

export const MASCOT_IMAGES: Record<MascotVariant, string> = MASCOT_IMAGE_DATA as Record<MascotVariant, string>;

// ============================================================================
// CELEBRATION MESSAGES
// ============================================================================

export const CELEBRATION_MESSAGES: Record<string, string[]> = {
  // Onboarding
  currency_set: [
    "Excellent! You've set the foundation!",
    "Great start! Your financial journey begins!",
    "Perfect! Now we can speak your language!",
  ],
  banks_configured: [
    "Awesome! Your banks are ready!",
    "Nice! Time to connect the dots!",
    "Great! Let's track those accounts!",
  ],
  first_parsing: [
    "Amazing! First statement decoded!",
    "Brilliant! You're a natural!",
    "Fantastic! Data flows in!",
  ],
  foreign_currency_statement: [
    "Multi-currency master!",
    "Global finances unlocked!",
    "Currency barriers broken!",
  ],
  
  // Month milestones
  month_1: [
    "Incredible! Your first month saved!",
    "Wonderful! The journey continues!",
    "Superb! Data tells stories!",
  ],
  statements_2: [
    "Double the data, double the insights!",
    "Two down, many more to come!",
    "You're building a solid foundation!",
  ],
  statements_3: [
    "Triple threat activated!",
    "Pattern recognition unlocked!",
    "Three's a trend - you're tracking!",
  ],
  month_3: [
    "A whole quarter! Amazing!",
    "Patterns are emerging!",
    "Consistency is key - you've got it!",
  ],
  month_6: [
    "Half a year of data! Legendary!",
    "Trends are crystal clear now!",
    "Dedication pays off!",
  ],
  month_12: [
    "A FULL YEAR! MASTER LEVEL!",
    "You've reached the pinnacle!",
    "Financial wisdom achieved!",
  ],
  month_18: [
    "Year and a half! Incredible commitment!",
    "Long-term tracking unlocked!",
    "Your data story grows stronger!",
  ],
  month_24: [
    "TWO FULL YEARS! TITAN STATUS!",
    "Unparalleled dedication!",
    "Financial historian level achieved!",
  ],
  month_36: [
    "THREE YEARS! LEGENDARY!",
    "You're writing financial history!",
    "True mastery of time and money!",
  ],
  
  // Category milestones
  categories_5: [
    "Nice organization skills!",
    "You're getting the hang of it!",
    "Categories make everything clearer!",
  ],
  categories_10: [
    "Double digits! Impressive!",
    "Your system is taking shape!",
    "Organization level: Expert!",
  ],
  categories_20: [
    "Category master!",
    "Your system is comprehensive!",
    "Thorough and organized!",
  ],
  categories_50: [
    "FIFTY categories! Grandmaster level!",
    "Ultimate organization achieved!",
    "Every transaction has a home!",
  ],
  categories_100: [
    "ONE HUNDRED! CATEGORY OVERLORD!",
    "The ultimate categorizer!",
    "Nothing escapes your system!",
  ],
  
  // Budget milestones
  first_budget: [
    "Budget master in the making!",
    "Smart move! Tracking = growth!",
    "Financial wisdom unlocked!",
  ],
  budgets_5: [
    "Budget boss mode!",
    "Multiple targets, focused vision!",
    "Financial planning pro!",
  ],
  budgets_10: [
    "TEN budgets! Architect level!",
    "Comprehensive financial control!",
    "Every category planned!",
  ],
  budgets_20: [
    "TWENTY budgets! Emperor status!",
    "Complete financial domination!",
    "Nothing left to chance!",
  ],
  
  // Analysis milestones
  recategorization: [
    "Fine-tuning like a pro!",
    "Precision is your strength!",
    "Every detail matters!",
  ],
  
  // Tool usage quests
  first_data_fetch: [
    "Data Explorer activated!",
    "Your financial insights await!",
    "Curious minds unlock wealth!",
  ],
  preferences_updated: [
    "Customization complete!",
    "Your app, your way!",
    "Personal touch applied!",
  ],
  multi_month_analysis: [
    "Trend spotter extraordinaire!",
    "Big picture thinking!",
    "Patterns reveal secrets!",
  ],
  statements_10: [
    "Statement processing pro!",
    "Data pipeline master!",
    "Ten down, infinity to go!",
  ],
  mutations_50: [
    "FIFTY recategorizations! Master tuner!",
    "Precision at scale!",
    "Every transaction perfected!",
  ],
  full_year_budget: [
    "Full year planned! Annual planner!",
    "12 months of financial vision!",
    "Future secured!",
  ],
  
  // Mastery
  financial_mastery: [
    "FINANCIAL ENLIGHTENMENT ACHIEVED!",
    "You've transcended finance tracking!",
    "True mastery of wealth wisdom!",
  ],
};

// ============================================================================
// QUEST HELP INSTRUCTIONS
// ============================================================================

export const QUEST_HELP_INSTRUCTIONS: Record<string, QuestHelp> = {
  // ========== ONBOARDING ==========
  currency_set: {
    explanation: "Set your functional currency - this is the currency that all your financial data will be converted to and displayed in. The AI will automatically translate statements from other currencies to your functional currency when consolidating your dashboard. Use the currency which you conduct most of your transactions in.",
    promptPreset: "Save my functional currency as PLN",
    tips: [
      "Double-check that the AI confirms the tool call succeeded",
      "Common currencies: USD, EUR, GBP, PLN, CAD, AUD",
    ],
  },
  banks_configured: {
    explanation: "Tell the AI about your bank accounts. This helps organize your statements and track finances across multiple institutions. You can add as many banks as you need, including different accounts at the same bank.",
    promptPreset: "I use 2 bank accounts, \"Bank A\" (main account) and \"Bank B\" (savings). Please save those as my banking preferences",
    tips: [
      "Include the bank name and account type (checking, savings, credit)",
      "You can add more accounts anytime",
      "The AI will remember your banks for future statements",
    ],
  },
  first_parsing: {
    explanation: "Upload your first bank statement (CSV or Excel) and teach the AI how to understand it. Specify specific columns such as date and transaction amount. The AI will ask you about column mappings and date formats. First-time setup takes a bit longer, but future statements from the same bank will be instant!",
    promptPreset: "I'm uploading my first bank statement from PKO BP. Column X contains the transaction amounts, Column B is date.\nThe net flow for this statement is $1,250.50.\n([Add other considerations. For example: The first row appears to be metadata, so please ignore.]).\n\nPlease verify that the calculated net flow per csv matches $1,250.50, then save these parsing preferences for future statements from this bank.",
    tips: [
      "Export a statement from your bank's online portal (CSV preferred)",
      "Explain any unusual columns or date formats",
      "The AI saves your parsing preferences for future imports",
    ],
  },
  
  // ========== EARLY DATA MILESTONES ==========
  month_1: {
    explanation: "Save your first complete month of financial data. After the AI parses your statement, ask it to save the data. The AI will consolidate transactions, apply categories, and store everything in your dashboard.",
    promptPreset: "Save my November 2024 statement data",
    tips: [
      "Make sure to review the parsed transactions first",
      "The AI will ask for confirmation before saving",
      "You can recategorize transactions later if needed",
    ],
  },
  statements_2: {
    explanation: "Save 2 bank statements to build your financial history. Each unique bank + month combination counts as one statement. This could be 2 months from one bank or 1 month from 2 different banks.",
    promptPreset: "I want to add another bank statement. Here's my December statement from PKO BP.",
    tips: [
      "Each bank + month combo counts as one statement",
      "You can add multiple banks or multiple months",
      "Building history improves spending insights",
    ],
  },
  statements_3: {
    explanation: "Save 3 bank statements to unlock pattern recognition. With 3+ data points, the AI can start identifying trends and seasonal patterns in your spending.",
    promptPreset: "Let me add my January statement as well to complete Q4 data.",
    tips: [
      "3 months is the minimum for trend analysis",
      "Consider adding statements from all your active banks",
      "Quarterly data reveals spending patterns",
    ],
  },
  categories_5: {
    explanation: "Create categorization rules to automatically classify your transactions. Rules can match transaction descriptions, merchants, or amounts. Once created, they apply to all future and past transactions.",
    promptPreset: "Create a category rule: match 'NETFLIX' as Entertainment",
    tips: [
      "Start with your most frequent transactions",
      "Rules are case-insensitive by default",
      "You can use partial matches (e.g., 'UBER' matches 'UBER EATS' too)",
    ],
  },
  first_budget: {
    explanation: "Set up your first budget to track spending against targets. Choose a category and set a monthly limit. The dashboard will show your progress and alert you when you're close to the limit.",
    promptPreset: "Set a budget of 500 PLN for Dining Out this month",
    tips: [
      "Start with categories where you want to reduce spending",
      "Budgets are per-month by default",
      "You'll see budget progress in your dashboard",
    ],
  },
  categories_10: {
    explanation: "Keep building your categorization system! More rules mean better automatic classification and more accurate spending insights.",
    promptPreset: "Create rules: 'ALLEGRO' as Shopping, 'SPOTIFY' as Entertainment, 'ORLEN' as Transportation",
    tips: [
      "Batch multiple rules in one prompt for efficiency",
      "Review uncategorized transactions for rule ideas",
      "Consider creating a 'Subscriptions' category",
    ],
  },
  
  // ========== TOOL QUESTS ==========
  first_data_fetch: {
    explanation: "Ask the AI to fetch and display your financial data. This shows your spending breakdown, category totals, and trends. Use this to review your finances anytime.",
    promptPreset: "Show me my financial data for last month",
    tips: [
      "You can ask for specific date ranges",
      "Request comparisons between months",
      "Ask for category breakdowns or top expenses",
    ],
  },
  month_3: {
    explanation: "Track 3 months of data to start seeing meaningful trends. Consistency is key - try to import statements regularly to keep your data current.",
    promptPreset: "Save my October, November, and December statements",
    tips: [
      "Import statements in chronological order for best results",
      "The AI can handle multiple months at once",
      "Three months reveals seasonal patterns",
    ],
  },
  recategorization: {
    explanation: "Fine-tune your transaction categories. If the AI miscategorized something, you can correct it. The AI learns from your corrections to improve future categorization.",
    promptPreset: "Change the category of my 'ZABKA' transaction from Groceries to Snacks",
    tips: [
      "Be specific about which transaction to change",
      "You can recategorize multiple transactions at once",
      "Consider creating new rules after recategorizing",
    ],
  },
  
  // ========== MID-LEVEL MILESTONES ==========
  categories_20: {
    explanation: "Your categorization system is growing! Keep adding rules to cover more of your spending patterns.",
    promptPreset: "Show me my uncategorized transactions and help me create rules for them",
    tips: [
      "Ask the AI to suggest categories for unknown transactions",
      "Group similar merchants under the same rule",
      "Consider subcategories for detailed tracking",
    ],
  },
  budgets_5: {
    explanation: "Expand your budget coverage. Multiple budgets help you control spending across different areas of your life.",
    promptPreset: "Set up budgets: Entertainment 300, Dining 500, Shopping 400, Transportation 200",
    tips: [
      "Cover your major spending categories",
      "Leave some buffer for unexpected expenses",
      "Review and adjust budgets monthly",
    ],
  },
  preferences_updated: {
    explanation: "Customize your app settings. You can change your functional currency, update bank configurations, or adjust display preferences.",
    promptPreset: "Update my preferences to show amounts in thousands (e.g., 1.5k instead of 1500)",
    tips: [
      "Review your settings periodically",
      "Ask the AI what settings are available",
      "Changes take effect immediately",
    ],
  },
  month_6: {
    explanation: "Half a year of data! You now have enough history to see meaningful long-term trends and seasonal patterns.",
    promptPreset: "Analyze my spending trends over the last 6 months",
    tips: [
      "Look for seasonal spending patterns",
      "Compare similar months year-over-year",
      "Identify categories with the most growth",
    ],
  },
  multi_month_analysis: {
    explanation: "Analyze multiple months at once to spot trends. The AI can compare spending across periods, identify changes, and highlight patterns.",
    promptPreset: "Compare my spending between Q3 and Q4 2024",
    tips: [
      "Ask for month-over-month comparisons",
      "Request trend analysis for specific categories",
      "Look for anomalies or unusual spending",
    ],
  },
  
  // ========== YEAR ONE MASTERY ==========
  budgets_10: {
    explanation: "Comprehensive budget coverage! With 10+ budgets, you have detailed control over your spending.",
    promptPreset: "Help me create a complete budget plan covering all my main expense categories",
    tips: [
      "Include both fixed and variable expenses",
      "Set up an 'Emergency' or 'Buffer' budget",
      "Review total budgets vs total income",
    ],
  },
  categories_50: {
    explanation: "Expert-level categorization! Your system now handles most transactions automatically.",
    promptPreset: "Show me category coverage statistics - what percentage of transactions are auto-categorized?",
    tips: [
      "Aim for 90%+ auto-categorization",
      "Create catch-all rules for edge cases",
      "Consider hierarchical categories",
    ],
  },
  month_12: {
    explanation: "A full year of financial data! This is a major milestone enabling year-over-year comparisons and comprehensive analysis.",
    promptPreset: "Give me my complete 2024 financial year in review",
    tips: [
      "Request annual summaries and trends",
      "Compare to previous year if available",
      "Identify your biggest spending categories",
    ],
  },
  
  // ========== ADVANCED TOOL QUESTS ==========
  statements_10: {
    explanation: "You've processed 10+ statements! Your parsing preferences are well-established for all your banks.",
    promptPreset: "Show me a summary of all statements I've imported",
    tips: [
      "Check for any missing months",
      "Verify transaction counts match bank records",
      "Look for duplicate imports",
    ],
  },
  mutations_50: {
    explanation: "Master-level transaction tuning! Your corrections have significantly improved categorization accuracy.",
    promptPreset: "Show me my recategorization history and patterns",
    tips: [
      "Identify frequently corrected categories",
      "Create rules based on correction patterns",
      "Review rule effectiveness",
    ],
  },
  full_year_budget: {
    explanation: "Create an annual budget plan. This helps you track progress toward yearly financial goals.",
    promptPreset: "Create an annual budget plan for 2025 based on my 2024 spending patterns",
    tips: [
      "Include seasonal variations",
      "Set quarterly review points",
      "Account for annual expenses (insurance, subscriptions)",
    ],
  },
  
  // ========== LONG-TERM MILESTONES ==========
  month_18: {
    explanation: "A year and a half of financial history! You can now analyze long-term trends and annual patterns.",
    promptPreset: "Compare my spending patterns across 2023 and 2024",
    tips: [
      "Look for year-over-year improvements",
      "Identify lifestyle changes in spending",
      "Track progress toward financial goals",
    ],
  },
  categories_100: {
    explanation: "Category overlord status! Your system handles virtually every transaction type automatically.",
    promptPreset: "Audit my category rules - find overlapping or redundant rules",
    tips: [
      "Consolidate similar rules",
      "Remove outdated merchant rules",
      "Optimize rule order for performance",
    ],
  },
  month_24: {
    explanation: "Two full years of data! You have comprehensive historical data for deep analysis.",
    promptPreset: "Analyze my 2-year financial journey - key trends and milestones",
    tips: [
      "Export annual reports for records",
      "Set multi-year financial goals",
      "Celebrate your consistency!",
    ],
  },
  budgets_20: {
    explanation: "Budget emperor! You have granular control over every aspect of your finances.",
    promptPreset: "Show me my budget performance across all 20 categories for this year",
    tips: [
      "Identify underutilized budgets",
      "Reallocate from surplus to deficit categories",
      "Consider budget categories for savings goals",
    ],
  },
  month_36: {
    explanation: "Three years of financial history! This is legendary-level data for trend analysis.",
    promptPreset: "Generate my 3-year financial evolution report",
    tips: [
      "Document major financial decisions",
      "Track net worth progression",
      "Plan the next 3 years based on patterns",
    ],
  },
  financial_mastery: {
    explanation: "You've achieved complete financial mastery! 36+ months of data, 100+ categories, and 20+ budgets. You are a true finance tracking legend.",
    promptPreset: "Generate my complete financial mastery achievement report",
    tips: [
      "Share your success story",
      "Consider advanced analytics",
      "Help others start their journey",
    ],
  },
  
  // ========== FOREIGN CURRENCY QUEST ==========
  foreign_currency_statement: {
    explanation: "Process a bank statement in a foreign currency. The AI will automatically convert all transactions to your functional currency using historical exchange rates. Great for travel expenses or multi-currency accounts like Revolut!",
    promptPreset: "I have a Revolut statement in Mexican Pesos (MXN). Convert it to my functional currency (PLN).",
    tips: [
      "Tell the AI the statement currency before uploading",
      "The AI uses historical exchange rates for accuracy",
      "Works with any currency: MXN, USD, EUR, GBP, etc.",
      "Great for tracking travel expenses",
    ],
  },
};

// ============================================================================
// CALCULATION FUNCTIONS
// ============================================================================

/**
 * Calculate milestone completion status based on user data
 */
function calculateMilestoneStatus(
  definition: MilestoneDefinition,
  input: ProgressInput
): MilestoneStatus {
  const { 
    settings, 
    dataOverview, 
    catCount = 0, 
    parsingCount = 0, 
    mutationCount = 0,
    dataFetchCount = 0,
    statementCount = 0,
    preferencesUpdated = false,
    multiMonthAnalysisCount = 0,
    fullYearBudgetSet = false,
    foreignCurrencyStatementCount = 0,
  } = input;
  
  let completed = false;
  let progress = 0;
  let current = 0;
  let target = 1;
  
  const totalMonths = dataOverview?.total_months ?? 0;
  const budgetsConfigured = dataOverview?.budgets_configured ?? 0;
  
  switch (definition.id) {
    // ========== ONBOARDING ==========
    case 'currency_set':
      completed = !!settings?.functional_currency;
      progress = completed ? 100 : 0;
      current = completed ? 1 : 0;
      break;
      
    case 'banks_configured':
      completed = (settings?.bank_accounts_count ?? 0) > 0;
      progress = completed ? 100 : 0;
      current = settings?.bank_accounts_count ?? 0;
      break;
      
    case 'first_parsing':
      completed = parsingCount >= 1;
      progress = Math.min(100, parsingCount * 100);
      current = parsingCount;
      break;
      
    case 'foreign_currency_statement':
      completed = foreignCurrencyStatementCount >= 1;
      progress = Math.min(100, foreignCurrencyStatementCount * 100);
      current = foreignCurrencyStatementCount;
      break;
      
    // ========== MONTH MILESTONES ==========
    case 'month_1':
      completed = totalMonths >= 1;
      progress = Math.min(100, totalMonths * 100);
      current = totalMonths;
      break;
      
    case 'month_3':
      target = 3;
      completed = totalMonths >= 3;
      progress = Math.min(100, (totalMonths / 3) * 100);
      current = totalMonths;
      break;
      
    case 'month_6':
      target = 6;
      completed = totalMonths >= 6;
      progress = Math.min(100, (totalMonths / 6) * 100);
      current = totalMonths;
      break;
      
    case 'month_12':
      target = 12;
      completed = totalMonths >= 12;
      progress = Math.min(100, (totalMonths / 12) * 100);
      current = totalMonths;
      break;
      
    case 'month_18':
      target = 18;
      completed = totalMonths >= 18;
      progress = Math.min(100, (totalMonths / 18) * 100);
      current = totalMonths;
      break;
      
    case 'month_24':
      target = 24;
      completed = totalMonths >= 24;
      progress = Math.min(100, (totalMonths / 24) * 100);
      current = totalMonths;
      break;
      
    case 'month_36':
      target = 36;
      completed = totalMonths >= 36;
      progress = Math.min(100, (totalMonths / 36) * 100);
      current = totalMonths;
      break;
      
    // ========== CATEGORY MILESTONES ==========
    case 'categories_5':
      target = 5;
      completed = catCount >= 5;
      progress = Math.min(100, (catCount / 5) * 100);
      current = catCount;
      break;
      
    case 'categories_10':
      target = 10;
      completed = catCount >= 10;
      progress = Math.min(100, (catCount / 10) * 100);
      current = catCount;
      break;
      
    case 'categories_20':
      target = 20;
      completed = catCount >= 20;
      progress = Math.min(100, (catCount / 20) * 100);
      current = catCount;
      break;
      
    case 'categories_50':
      target = 50;
      completed = catCount >= 50;
      progress = Math.min(100, (catCount / 50) * 100);
      current = catCount;
      break;
      
    case 'categories_100':
      target = 100;
      completed = catCount >= 100;
      progress = Math.min(100, (catCount / 100) * 100);
      current = catCount;
      break;
      
    // ========== BUDGET MILESTONES ==========
    case 'first_budget':
      completed = budgetsConfigured >= 1;
      progress = Math.min(100, budgetsConfigured * 100);
      current = budgetsConfigured;
      break;
      
    case 'budgets_5':
      target = 5;
      completed = budgetsConfigured >= 5;
      progress = Math.min(100, (budgetsConfigured / 5) * 100);
      current = budgetsConfigured;
      break;
      
    case 'budgets_10':
      target = 10;
      completed = budgetsConfigured >= 10;
      progress = Math.min(100, (budgetsConfigured / 10) * 100);
      current = budgetsConfigured;
      break;
      
    case 'budgets_20':
      target = 20;
      completed = budgetsConfigured >= 20;
      progress = Math.min(100, (budgetsConfigured / 20) * 100);
      current = budgetsConfigured;
      break;
      
    // ========== ANALYSIS MILESTONES ==========
    case 'recategorization':
      completed = mutationCount >= 1;
      progress = Math.min(100, mutationCount * 100);
      current = mutationCount;
      break;
      
    // ========== TOOL USAGE QUESTS ==========
    case 'first_data_fetch':
      completed = dataFetchCount >= 1;
      progress = Math.min(100, dataFetchCount * 100);
      current = dataFetchCount;
      break;
      
    case 'preferences_updated':
      completed = preferencesUpdated;
      progress = completed ? 100 : 0;
      current = completed ? 1 : 0;
      break;
      
    case 'multi_month_analysis':
      target = 3;
      completed = multiMonthAnalysisCount >= 3;
      progress = Math.min(100, (multiMonthAnalysisCount / 3) * 100);
      current = multiMonthAnalysisCount;
      break;
      
    case 'statements_2':
      target = 2;
      completed = statementCount >= 2;
      progress = Math.min(100, (statementCount / 2) * 100);
      current = statementCount;
      break;
      
    case 'statements_3':
      target = 3;
      completed = statementCount >= 3;
      progress = Math.min(100, (statementCount / 3) * 100);
      current = statementCount;
      break;
      
    case 'statements_10':
      target = 10;
      completed = statementCount >= 10;
      progress = Math.min(100, (statementCount / 10) * 100);
      current = statementCount;
      break;
      
    case 'mutations_50':
      target = 50;
      completed = mutationCount >= 50;
      progress = Math.min(100, (mutationCount / 50) * 100);
      current = mutationCount;
      break;
      
    case 'full_year_budget':
      completed = fullYearBudgetSet;
      progress = completed ? 100 : 0;
      current = completed ? 1 : 0;
      break;
      
    // ========== MASTERY MILESTONES ==========
    case 'financial_mastery':
      // Requires: 36+ months, 100+ categories, 20+ budgets
      const masteryReqs = (totalMonths >= 36 ? 1 : 0) + (catCount >= 100 ? 1 : 0) + (budgetsConfigured >= 20 ? 1 : 0);
      target = 3;
      completed = masteryReqs >= 3;
      progress = Math.min(100, (masteryReqs / 3) * 100);
      current = masteryReqs;
      break;
  }
  
  return {
    ...definition,
    completed,
    progress,
    current,
    target,
    claimable: completed,
  };
}

/**
 * Calculate bonus XP from repeatable actions beyond milestones
 * - Each month beyond 12: +50 XP
 * - Each budget beyond 5: +25 XP
 * - Each category rule beyond 20: +10 XP
 */
function calculateBonusXP(input: ProgressInput): number {
  const { dataOverview, catCount = 0 } = input;
  const totalMonths = dataOverview?.total_months ?? 0;
  const budgetsConfigured = dataOverview?.budgets_configured ?? 0;
  
  let bonus = 0;
  
  // Bonus for months beyond 12
  if (totalMonths > 12) {
    bonus += (totalMonths - 12) * 50;
  }
  
  // Bonus for budgets beyond 5
  if (budgetsConfigured > 5) {
    bonus += (budgetsConfigured - 5) * 25;
  }
  
  // Bonus for categories beyond 20
  if (catCount > 20) {
    bonus += (catCount - 20) * 10;
  }
  
  return bonus;
}

/**
 * Get random celebration message for a milestone
 */
export function getRandomCelebrationMessage(milestoneId: string): string {
  const messages = CELEBRATION_MESSAGES[milestoneId] || ['Great job!'];
  const randomIndex = Math.floor(Math.random() * messages.length);
  return messages[randomIndex];
}

/**
 * Main function to calculate complete progress state
 */
export function calculateProgress(input: ProgressInput): ProgressState {
  // Calculate status for all milestones
  const milestones = MILESTONE_DEFINITIONS
    .map(def => calculateMilestoneStatus(def, input))
    .sort((a, b) => a.order - b.order);
  
  // Sum up XP from completed milestones
  const milestoneXP = milestones
    .filter(m => m.completed)
    .reduce((sum, m) => sum + m.xp, 0);
  
  // Add bonus XP from repeatable actions
  const bonusXP = calculateBonusXP(input);
  const totalXP = milestoneXP + bonusXP;
  
  // Calculate level using infinite leveling formula
  const level = getLevelFromXP(totalXP);
  const levelInfo = getLevelInfo(level);
  const nextLevelInfo = getLevelInfo(level + 1);
  
  // Calculate progress within current level
  const currentLevelXP = totalXP - levelInfo.xpRequired;
  const nextLevelXP = nextLevelInfo.xpRequired - levelInfo.xpRequired;
  const levelProgress = nextLevelXP > 0 
    ? Math.min(100, (currentLevelXP / nextLevelXP) * 100) 
    : 100;
  
  // Find next incomplete milestone
  const nextMilestone = milestones.find(m => !m.completed) || null;
  
  // Count completions
  const completedCount = milestones.filter(m => m.completed).length;
  
  // Determine AI personality phase
  const totalMonths = input.dataOverview?.total_months ?? 0;
  const budgetsConfigured = input.dataOverview?.budgets_configured ?? 0;
  const phase = determinePhase(totalMonths, budgetsConfigured);
  const phaseDefinition = PHASE_DEFINITIONS[phase];
  
  return {
    totalXP,
    level,
    levelTitle: levelInfo.title,
    currentLevelXP,
    nextLevelXP,
    levelProgress,
    mascot: phaseDefinition.mascot, // Use phase mascot instead of level mascot
    mascotImage: MASCOT_IMAGES[phaseDefinition.mascot],
    milestones,
    completedCount,
    totalMilestones: milestones.length,
    nextMilestone,
    bonusXP,
    phase,
  };
}

/**
 * Get mascot personality text based on level
 * Used for UI messages, not AI prompts
 */
export function getMascotPersonality(level: number): {
  greeting: string;
  encouragement: string;
  personality: string;
} {
  if (level <= 2) {
    return {
      greeting: "Hi there! I'm Finley, your financial buddy!",
      encouragement: "Let's learn together! Every step counts.",
      personality: "eager learner",
    };
  } else if (level <= 4) {
    return {
      greeting: "Hey! Great to see you back!",
      encouragement: "You're making awesome progress!",
      personality: "supportive coach",
    };
  } else if (level <= 6) {
    return {
      greeting: "Welcome back, finance tracker!",
      encouragement: "Your data skills are impressive!",
      personality: "proud mentor",
    };
  } else if (level <= 8) {
    return {
      greeting: "Greetings, financial strategist!",
      encouragement: "Your insights are sharpening daily!",
      personality: "wise advisor",
    };
  } else {
    return {
      greeting: "Ah, the master returns!",
      encouragement: "You've achieved financial enlightenment!",
      personality: "reverent guide",
    };
  }
}

/**
 * Calculate XP needed for specific actions (preview)
 */
export function getXPPreview(action: string): number {
  const milestone = MILESTONE_DEFINITIONS.find(m => m.id === action);
  return milestone?.xp ?? 0;
}

/**
 * Get category color for visual grouping
 */
export function getMilestoneCategoryColor(category: MilestoneDefinition['category']): string {
  switch (category) {
    case 'onboarding': return '#8B5CF6'; // Purple
    case 'data': return '#3B82F6'; // Blue
    case 'analysis': return '#10B981'; // Green
    case 'mastery': return '#FFD700'; // Gold
    case 'tools': return '#F97316'; // Orange
    case 'longterm': return '#06B6D4'; // Cyan/Teal
    default: return '#6B7280'; // Gray
  }
}
