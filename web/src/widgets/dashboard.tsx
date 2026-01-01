import React, { useMemo, useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';

import {
  dashboardPropsSchema,
  type DashboardProps,
  changeSummarySchema,
  type ChangeSummary,
} from '../shared/schemas';

// Journey system imports
import { calculateProgress, ProgressState, ProgressInput } from '../lib/progression';
import { StatusBar } from '../components/StatusBar';
import { JourneyPath } from '../components/JourneyPath';
import { Confetti } from '../components/Confetti';
import {
  buildPivotRowDisplays,
  buildMonthlyFlowSeries,
  buildBankFilteredPivot,
  buildBudgetVsActualSeries,
  buildBudgetProgressData,
  buildBudgetAllocationData,
  calculateTrendInsights,
  formatCurrency,
  formatDate,
  formatPercentage,
  formatMonthLabel,
  classifyCategory,
  type PivotRowDisplay,
  type TrendInsights,
  type BudgetProgressData,
  type BudgetAllocationData,
} from '../lib/data-transformers';
import { useTheme, useDisplayMode } from '../lib/use-openai-global';
import { useIntrinsicHeight } from '../lib/use-intrinsic-height';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { apiClient } from '../lib/api-client';

declare global {
  interface Window {
    theme?: 'light' | 'dark';
    displayMode?: 'pip' | 'inline' | 'fullscreen';
  }
}

// ============================================================================
// HOOKS
// ============================================================================

function useDashboardData(
  localOverride: DashboardProps | null,
  filters?: { bank_name?: string; month_year?: string; categories?: string[]; profile?: string }
): { data: DashboardProps | null; error: string | null; loading: boolean } {
  const [data, setData] = useState<DashboardProps | null>(localOverride);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(!localOverride);

  useEffect(() => {
    // If we have a local override, use it directly
    if (localOverride) {
      setData(localOverride);
      setError(null);
      setLoading(false);
      return;
    }

    // Fetch from API
    setLoading(true);
    setError(null);
    apiClient.getFinancialData(filters)
      .then((fetchedData) => {
        const parsed = dashboardPropsSchema.safeParse(fetchedData);
        if (parsed.success) {
          setData(parsed.data);
        } else {
          console.error('Dashboard data failed validation', parsed.error);
          setError('Dashboard data is in an unexpected format. Please check the console for details.');
        }
      })
      .catch((err) => {
        console.error('Error fetching dashboard data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [localOverride, filters?.bank_name, filters?.month_year, filters?.categories?.join(','), filters?.profile]);

  return { data, error, loading };
}

// ============================================================================
// DESIGN SYSTEM - RED/BLACK/WHITE/GREY THEME
// ============================================================================

const SPACING = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
};

const TYPOGRAPHY = {
  fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif",
  sizes: {
    xs: 11,
    sm: 12,
    base: 14,
    md: 16,
    lg: 18,
    xl: 24,
    xxl: 32,
    xxxl: 40,
  },
  weights: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
};

// Financial theme: red (primary), black, white, grey
const getThemeColors = (theme: 'light' | 'dark') => ({
  // Primary colors
  primary: '#dc2626', // red-600
  primaryLight: '#ef4444', // red-500
  primaryDark: '#b91c1c', // red-700
  
  // Backgrounds
  bg: {
    primary: theme === 'dark' ? '#1a1a1a' : '#ffffff',
    secondary: theme === 'dark' ? '#2a2a2a' : '#f5f5f5',
    elevated: theme === 'dark' ? '#2a2a2a' : '#ffffff',
    subtle: theme === 'dark' ? 'rgba(42, 42, 42, 0.5)' : 'rgba(245, 245, 245, 0.8)',
    hover: theme === 'dark' ? 'rgba(42, 42, 42, 0.8)' : 'rgba(245, 245, 245, 0.5)',
    total: theme === 'dark' ? 'rgba(42, 42, 42, 0.6)' : 'rgba(245, 245, 245, 0.6)',
  },
  
  // Text
  text: {
    primary: theme === 'dark' ? '#ffffff' : '#000000',
    secondary: theme === 'dark' ? '#a3a3a3' : '#525252',
    tertiary: theme === 'dark' ? '#737373' : '#737373',
    muted: theme === 'dark' ? '#525252' : '#a3a3a3',
    negative: '#dc2626', // red for negative values
    positive: theme === 'dark' ? '#ffffff' : '#000000', // black/white for positive
  },
  
  // Borders
  border: {
    default: theme === 'dark' ? 'rgba(115, 115, 115, 0.2)' : 'rgba(0, 0, 0, 0.1)',
    emphasis: theme === 'dark' ? 'rgba(115, 115, 115, 0.3)' : 'rgba(0, 0, 0, 0.15)',
    hover: theme === 'dark' ? 'rgba(115, 115, 115, 0.4)' : 'rgba(0, 0, 0, 0.2)',
  },
  
  // Chart colors
  chart: {
    inflow: theme === 'dark' ? '#ffffff' : '#000000',
    outflow: '#dc2626',
    internalTransfer: '#737373',
    neutral: '#737373',
  },
  
  // Shadows
  shadow: {
    sm: theme === 'dark'
      ? '0 1px 2px 0 rgba(0, 0, 0, 0.3)'
      : '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    md: theme === 'dark'
      ? '0 4px 6px -1px rgba(0, 0, 0, 0.3)'
      : '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
  },
});

// ============================================================================
// REUSABLE UI COMPONENTS
// ============================================================================

interface MultiSelectProps {
  value: string[];
  onChange: (value: string[]) => void;
  options: Array<{ value: string; label: string }>;
  theme: 'light' | 'dark';
  placeholder?: string;
}

const MultiSelect: React.FC<MultiSelectProps> = ({ value, onChange, options, theme, placeholder }) => {
  const colors = getThemeColors(theme);
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleOption = (optionValue: string) => {
    const newValue = value.includes(optionValue)
      ? value.filter(v => v !== optionValue)
      : [...value, optionValue];
    onChange(newValue);
  };

  const displayText = value.length === 0
    ? placeholder || 'Select...'
    : value.length === 1
    ? options.find(o => o.value === value[0])?.label || value[0]
    : `${value.length} selected`;

  return (
    <div ref={wrapperRef} style={{ position: 'relative', minWidth: 160 }}>
      <div
        onClick={() => setIsOpen(!isOpen)}
        style={{
          padding: `${SPACING.sm}px ${SPACING.md}px`,
          borderRadius: 6,
          fontSize: TYPOGRAPHY.sizes.sm,
          fontWeight: TYPOGRAPHY.weights.medium,
          background: colors.bg.elevated,
          color: colors.text.primary,
          border: `1px solid ${isOpen ? colors.primary : colors.border.default}`,
          cursor: 'pointer',
          fontFamily: TYPOGRAPHY.fontFamily,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          userSelect: 'none',
        }}
      >
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {displayText}
        </span>
        <span style={{ marginLeft: SPACING.sm, fontSize: 10 }}>▼</span>
      </div>

      {isOpen && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            marginTop: 4,
            background: colors.bg.elevated,
            border: `1px solid ${colors.border.default}`,
            borderRadius: 6,
            boxShadow: colors.shadow.md,
            zIndex: 100,
            maxHeight: 300,
            overflowY: 'auto',
          }}
        >
          {options.map((opt) => {
            const isSelected = value.includes(opt.value);
            return (
              <div
                key={opt.value}
                onClick={() => toggleOption(opt.value)}
                style={{
                  padding: `${SPACING.sm}px ${SPACING.md}px`,
                  fontSize: TYPOGRAPHY.sizes.sm,
                  color: colors.text.primary,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  background: isSelected ? colors.bg.hover : 'transparent',
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) e.currentTarget.style.background = colors.bg.hover;
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) e.currentTarget.style.background = 'transparent';
                }}
              >
                <div
                  style={{
                    width: 16,
                    height: 16,
                    borderRadius: 4,
                    border: `1px solid ${isSelected ? colors.primary : colors.border.default}`,
                    background: isSelected ? colors.primary : 'transparent',
                    marginRight: SPACING.sm,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 12,
                    color: '#fff',
                  }}
                >
                  {isSelected && '✓'}
                </div>
                {opt.label}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

interface CardProps {
  children: React.ReactNode;
  theme: 'light' | 'dark';
  padding?: keyof typeof SPACING;
  onClick?: () => void;
  hoverable?: boolean;
}

const Card: React.FC<CardProps> = ({ 
  children, 
  theme, 
  padding = 'lg', 
  onClick,
  hoverable = false,
}) => {
  const colors = getThemeColors(theme);
  const [isHovered, setIsHovered] = useState(false);
  
  return (
    <div
      style={{
        background: colors.bg.elevated,
        border: `1px solid ${isHovered && hoverable ? colors.border.hover : colors.border.default}`,
        borderRadius: 8,
        padding: SPACING[padding],
        boxShadow: isHovered && hoverable ? colors.shadow.md : colors.shadow.sm,
        transition: 'all 0.2s ease',
        cursor: onClick ? 'pointer' : 'default',
      }}
      onClick={onClick}
      onMouseEnter={() => hoverable && setIsHovered(true)}
      onMouseLeave={() => hoverable && setIsHovered(false)}
    >
      {children}
    </div>
  );
};

interface MetricTileProps {
  label: string;
  value: string;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  theme: 'light' | 'dark';
  isNegative?: boolean;
}

const MetricTile: React.FC<MetricTileProps> = ({
  label,
  value,
  subtitle,
  trend,
  theme,
  isNegative = false,
}) => {
  const colors = getThemeColors(theme);
  
  const getTrendIcon = () => {
    if (trend === 'up') return '↑';
    if (trend === 'down') return '↓';
    return '';
  };

  const valueColor = isNegative ? colors.text.negative : colors.text.primary;

  return (
    <div style={{ minWidth: 0 }}>
      <div
        style={{
          fontSize: TYPOGRAPHY.sizes.xs,
          color: colors.text.tertiary,
          textTransform: 'uppercase',
          letterSpacing: 0.5,
          marginBottom: SPACING.xs,
          fontWeight: TYPOGRAPHY.weights.medium,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: TYPOGRAPHY.sizes.xl,
          fontWeight: TYPOGRAPHY.weights.bold,
          color: valueColor,
          marginBottom: subtitle ? SPACING.xs : 0,
        }}
      >
        {value} {trend && <span style={{ fontSize: TYPOGRAPHY.sizes.md }}>{getTrendIcon()}</span>}
      </div>
      {subtitle && (
        <div
          style={{
            fontSize: TYPOGRAPHY.sizes.sm,
            color: colors.text.secondary,
          }}
        >
          {subtitle}
        </div>
      )}
    </div>
  );
};

interface ToggleProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  theme: 'light' | 'dark';
}

const Toggle: React.FC<ToggleProps> = ({ label, checked, onChange, theme }) => {
  const colors = getThemeColors(theme);
  
  return (
    <label
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: SPACING.sm,
        cursor: 'pointer',
        fontSize: TYPOGRAPHY.sizes.sm,
        color: colors.text.secondary,
      }}
    >
      <div
        style={{
          position: 'relative',
          width: 40,
          height: 20,
          background: checked ? colors.primary : colors.bg.secondary,
          borderRadius: 10,
          transition: 'background 0.2s ease',
        }}
        onClick={() => onChange(!checked)}
      >
        <div
          style={{
            position: 'absolute',
            top: 2,
            left: checked ? 22 : 2,
            width: 16,
            height: 16,
            background: '#ffffff',
            borderRadius: '50%',
            transition: 'left 0.2s ease',
            boxShadow: colors.shadow.sm,
          }}
        />
      </div>
      {label}
    </label>
  );
};

interface SelectProps {
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
  theme: 'light' | 'dark';
  placeholder?: string;
}

const Select: React.FC<SelectProps> = ({ value, onChange, options, theme, placeholder }) => {
  const colors = getThemeColors(theme);
  
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{
        padding: `${SPACING.sm}px ${SPACING.md}px`,
        borderRadius: 6,
        fontSize: TYPOGRAPHY.sizes.sm,
        fontWeight: TYPOGRAPHY.weights.medium,
        background: colors.bg.elevated,
        color: colors.text.primary,
        border: `1px solid ${colors.border.default}`,
        cursor: 'pointer',
        fontFamily: TYPOGRAPHY.fontFamily,
        minWidth: 120,
      }}
    >
      {placeholder && <option value="">{placeholder}</option>}
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
};

// ============================================================================
// CHART COMPONENTS
// ============================================================================

interface DonutChartProps {
  data: Array<{ label: string; value: number; color: string }>;
  theme: 'light' | 'dark';
  size?: number;
}

const DonutChart: React.FC<DonutChartProps> = ({ data, theme, size = 200 }) => {
  const colors = getThemeColors(theme);
  
  // Filter out zero or near-zero values
  const nonZeroData = data.filter(d => Math.abs(d.value) > 0.01);
  const isSingleSegment = nonZeroData.length === 1;
  
  if (nonZeroData.length === 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: SPACING.lg }}>
        <div style={{ color: colors.text.secondary }}>No data to display</div>
      </div>
    );
  }
  
  const total = Math.abs(nonZeroData.reduce((sum, d) => sum + d.value, 0));
  
  if (total === 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: SPACING.lg }}>
        <div style={{ color: colors.text.secondary }}>No data to display</div>
      </div>
    );
  }
  
  const radius = size / 2 - 10;
  const innerRadius = radius * 0.6;
  const centerX = size / 2;
  const centerY = size / 2;
  const ringThickness = radius - innerRadius;
  const ringRadius = innerRadius + ringThickness / 2;

  let currentAngle = -Math.PI / 2;

  const segments = isSingleSegment
    ? nonZeroData.map(item => {
        const value = Math.abs(item.value);
        const percentage = total > 0 ? value / total : 0;
        return { color: item.color, label: item.label, value, percentage };
      })
    : nonZeroData.map((item) => {
        const value = Math.abs(item.value);
        const percentage = total > 0 ? value / total : 0;
        const angle = percentage * 2 * Math.PI;
        const startAngle = currentAngle;
        const endAngle = currentAngle + angle;

        const x1 = centerX + radius * Math.cos(startAngle);
        const y1 = centerY + radius * Math.sin(startAngle);
        const x2 = centerX + radius * Math.cos(endAngle);
        const y2 = centerY + radius * Math.sin(endAngle);
        const x3 = centerX + innerRadius * Math.cos(endAngle);
        const y3 = centerY + innerRadius * Math.sin(endAngle);
        const x4 = centerX + innerRadius * Math.cos(startAngle);
        const y4 = centerY + innerRadius * Math.sin(startAngle);

        const largeArc = angle > Math.PI ? 1 : 0;

        const path = [
          `M ${x1} ${y1}`,
          `A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`,
          `L ${x3} ${y3}`,
          `A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${x4} ${y4}`,
          'Z',
        ].join(' ');

        currentAngle += angle;

        return { path, color: item.color, label: item.label, value, percentage };
      });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: SPACING.lg }}>
      <svg width={size} height={size} style={{ display: 'block' }}>
        {isSingleSegment ? (
          <circle
            cx={centerX}
            cy={centerY}
            r={ringRadius}
            fill="none"
            stroke={segments[0].color}
            strokeWidth={ringThickness}
          />
        ) : (
          segments.map((seg, idx) => (
            <path
              key={idx}
              d={seg.path}
              fill={seg.color}
              stroke={colors.bg.elevated}
              strokeWidth={2}
              style={{ transition: 'opacity 0.2s ease' }}
              onMouseEnter={(e) => {
                e.currentTarget.style.opacity = '0.8';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.opacity = '1';
              }}
            />
          ))
        )}
      </svg>
      <div style={{ display: 'flex', flexDirection: 'column', gap: SPACING.xs, width: '100%' }}>
        {segments.map((seg, idx) => (
          <div
            key={idx}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: SPACING.sm,
              fontSize: TYPOGRAPHY.sizes.sm,
            }}
          >
            <div
              style={{
                width: 12,
                height: 12,
                borderRadius: 3,
                background: seg.color,
              }}
            />
            <span style={{ flex: 1, color: colors.text.secondary }}>{seg.label}</span>
            <span style={{ fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.primary }}>
              {formatPercentage(seg.percentage * 100)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

interface HorizontalBarChartProps {
  data: Array<{ label: string; value: number; color: string }>;
  theme: 'light' | 'dark';
  currency: string;
  height?: number;
}

const HorizontalBarChart: React.FC<HorizontalBarChartProps> = ({ 
  data, 
  theme, 
  currency,
  height = 300,
}) => {
  const colors = getThemeColors(theme);
  const maxValue = Math.max(...data.map(d => Math.abs(d.value)), 1);
  const barHeight = Math.max(20, (height - (data.length - 1) * SPACING.md) / data.length);

  return (
    <div style={{ width: '100%', height }}>
      {data.map((item, idx) => {
        const widthPct = (Math.abs(item.value) / maxValue) * 100;
        return (
          <div
            key={idx}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: SPACING.md,
              marginBottom: idx < data.length - 1 ? SPACING.md : 0,
            }}
          >
            <div
              style={{
                minWidth: 120,
                fontSize: TYPOGRAPHY.sizes.sm,
                color: colors.text.secondary,
                fontWeight: TYPOGRAPHY.weights.medium,
              }}
            >
              {item.label}
            </div>
            <div
              style={{
                flex: 1,
                height: barHeight,
                background: colors.bg.secondary,
                borderRadius: 4,
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${widthPct}%`,
                  height: '100%',
                  background: item.color,
                  transition: 'width 0.3s ease',
                }}
              />
            </div>
            <div
              style={{
                minWidth: 100,
                textAlign: 'right',
                fontSize: TYPOGRAPHY.sizes.sm,
                fontWeight: TYPOGRAPHY.weights.semibold,
                color: item.value < 0 ? colors.text.negative : colors.text.primary,
              }}
            >
              {formatCurrency(item.value, currency)}
            </div>
          </div>
        );
      })}
    </div>
  );
};

interface LineChartProps {
  data: Array<{ month: string; value: number }>;
  theme: 'light' | 'dark';
  currency: string;
  color?: string;
  height?: number;
}

const LineChart: React.FC<LineChartProps> = ({ 
  data, 
  theme, 
  currency,
  color,
  height = 250,
}) => {
  const colors = getThemeColors(theme);
  const padding = { top: 20, right: 20, bottom: 40, left: 60 };
  const chartWidth = 600;
  const chartHeight = height - padding.top - padding.bottom;

  const allValues = data.map(d => d.value);
  const maxValue = Math.max(...allValues, 0);
  const minValue = Math.min(...allValues, 0);
  const range = maxValue - minValue || 1;

  const scaleY = (value: number) => {
    return chartHeight - ((value - minValue) / range) * chartHeight;
  };

  const scaleX = (index: number) => {
    return (index / (data.length - 1 || 1)) * chartWidth;
  };

  const path = data
    .map((d, idx) => {
      const x = scaleX(idx);
      const y = scaleY(d.value);
      return `${idx === 0 ? 'M' : 'L'} ${x} ${y}`;
    })
    .join(' ');

  const lineColor = color || colors.chart.outflow;

  return (
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <svg width={chartWidth + padding.left + padding.right} height={height}>
        <g transform={`translate(${padding.left}, ${padding.top})`}>
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
            const y = chartHeight * ratio;
            const value = maxValue - (maxValue - minValue) * ratio;
            return (
              <g key={ratio}>
                <line
                  x1={0}
                  y1={y}
                  x2={chartWidth}
                  y2={y}
                  stroke={colors.border.default}
                  strokeWidth={1}
                  strokeDasharray="4,4"
                />
                <text
                  x={-10}
                  y={y + 4}
                  textAnchor="end"
                  fontSize={TYPOGRAPHY.sizes.xs}
                  fill={colors.text.tertiary}
                >
                  {formatCurrency(value, currency).replace(/[^0-9.,]/g, '')}
                </text>
              </g>
            );
          })}

          {/* Line */}
          <path
            d={path}
            fill="none"
            stroke={lineColor}
            strokeWidth={3}
          />

          {/* Data points */}
          {data.map((d, idx) => {
            const x = scaleX(idx);
            const y = scaleY(d.value);
            return (
              <g key={idx}>
                <circle
                  cx={x}
                  cy={y}
                  r={4}
                  fill={lineColor}
                  style={{ cursor: 'pointer' }}
                />
                <text
                  x={x}
                  y={chartHeight + 20}
                  textAnchor="middle"
                  fontSize={TYPOGRAPHY.sizes.xs}
                  fill={colors.text.secondary}
                >
                  {formatMonthLabel(d.month).split(' ')[0]}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
};


// ============================================================================
// TREND ANALYSIS CHART COMPONENTS
// ============================================================================

interface NetFlowChartProps {
  data: Array<{ month: string; value: number; cumulative: number }>;
  theme: 'light' | 'dark';
  currency: string;
  height?: number;
}

const NetFlowChart: React.FC<NetFlowChartProps> = ({ data, theme, currency, height = 200 }) => {
  const colors = getThemeColors(theme);
  const padding = { top: 40, right: 30, bottom: 45, left: 70 };
  const chartWidth = Math.max(480, data.length * 100);
  const chartHeight = height - padding.top - padding.bottom;

  if (data.length === 0) {
    return (
      <div style={{ color: colors.text.secondary, textAlign: 'center', padding: SPACING.xl }}>
        No data available
      </div>
    );
  }

  const cumulativeValues = data.map(d => d.cumulative);
  const maxValue = Math.max(...cumulativeValues, 0);
  const minValue = Math.min(...cumulativeValues, 0);
  const range = maxValue - minValue || 1;
  const zeroY = chartHeight - ((0 - minValue) / range) * chartHeight;

  const scaleY = (value: number) => chartHeight - ((value - minValue) / range) * chartHeight;
  const scaleX = (index: number) => (index / (data.length - 1 || 1)) * chartWidth;
  
  const finalValue = data[data.length - 1]?.cumulative ?? 0;
  const isPositive = finalValue >= 0;
  const primaryColor = isPositive ? colors.chart.inflow : colors.chart.outflow;

  // Build smooth line path
  const linePath = data
    .map((d, idx) => `${idx === 0 ? 'M' : 'L'} ${scaleX(idx)} ${scaleY(d.cumulative)}`)
    .join(' ');

  const areaPath = `${linePath} L ${scaleX(data.length - 1)} ${zeroY} L ${scaleX(0)} ${zeroY} Z`;

  return (
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <svg width={chartWidth + padding.left + padding.right} height={height}>
        <defs>
          <linearGradient id="netFlowGradientPos" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={colors.chart.inflow} stopOpacity="0.25" />
            <stop offset="100%" stopColor={colors.chart.inflow} stopOpacity="0.02" />
          </linearGradient>
          <linearGradient id="netFlowGradientNeg" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%" stopColor={colors.chart.outflow} stopOpacity="0.25" />
            <stop offset="100%" stopColor={colors.chart.outflow} stopOpacity="0.02" />
          </linearGradient>
        </defs>
        <g transform={`translate(${padding.left}, ${padding.top})`}>
          {/* Subtle grid lines */}
          {[0, 0.5, 1].map((ratio) => {
            const y = chartHeight * ratio;
            const value = maxValue - (maxValue - minValue) * ratio;
            return (
              <g key={ratio}>
                <line
                  x1={0}
                  y1={y}
                  x2={chartWidth}
                  y2={y}
                  stroke={colors.border.default}
                  strokeWidth={1}
                  strokeDasharray="4,4"
                  opacity={0.5}
                />
                <text
                  x={-12}
                  y={y + 4}
                  textAnchor="end"
                  fontSize={TYPOGRAPHY.sizes.xs}
                  fill={colors.text.tertiary}
                >
                  {formatCurrency(value, currency).replace(/[^0-9.,-]/g, '')}
                </text>
              </g>
            );
          })}

          {/* Zero line (if crosses zero) */}
          {minValue < 0 && maxValue > 0 && (
            <line
              x1={0}
              y1={zeroY}
              x2={chartWidth}
              y2={zeroY}
              stroke={colors.text.muted}
              strokeWidth={1}
              opacity={0.6}
            />
          )}

          {/* Gradient area fill */}
          <path
            d={areaPath}
            fill={isPositive ? 'url(#netFlowGradientPos)' : 'url(#netFlowGradientNeg)'}
          />

          {/* Main line */}
          <path
            d={linePath}
            fill="none"
            stroke={primaryColor}
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Data points */}
          {data.map((d, idx) => {
            const x = scaleX(idx);
            const y = scaleY(d.cumulative);
            const pointColor = d.cumulative >= 0 ? colors.chart.inflow : colors.chart.outflow;
            return (
              <g key={idx}>
                {/* Point */}
                <circle
                  cx={x}
                  cy={y}
                  r={6}
                  fill={pointColor}
                  stroke={colors.bg.elevated}
                  strokeWidth={2}
                />
                {/* Value label above point */}
                <text
                  x={x}
                  y={y - 14}
                  textAnchor="middle"
                  fontSize={TYPOGRAPHY.sizes.xs}
                  fontWeight={TYPOGRAPHY.weights.semibold}
                  fill={pointColor}
                >
                  {d.cumulative >= 0 ? '+' : ''}{formatCurrency(d.cumulative, currency).replace(/[^0-9.,-]/g, '')}
                </text>
                {/* Month label */}
                <text
                  x={x}
                  y={chartHeight + 20}
                  textAnchor="middle"
                  fontSize={TYPOGRAPHY.sizes.sm}
                  fill={colors.text.secondary}
                >
                  {formatMonthLabel(d.month).split(' ')[0]}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
};

// ============================================================================
// MONTHLY CASH FLOW BAR CHART - Clean grouped bars for Income vs Spending
// ============================================================================

interface MonthlyCashFlowBarChartProps {
  data: Array<{ month: string; label: string; inflow: number; outflow: number; net: number }>;
  theme: 'light' | 'dark';
  currency: string;
  height?: number;
}

const MonthlyCashFlowBarChart: React.FC<MonthlyCashFlowBarChartProps> = ({
  data,
  theme,
  currency,
  height = 280,
}) => {
  const colors = getThemeColors(theme);
  const padding = { top: 30, right: 20, bottom: 50, left: 70 };
  const chartWidth = Math.max(560, data.length * 120);
  const chartHeight = height - padding.top - padding.bottom;

  if (data.length === 0) {
    return (
      <div style={{ color: colors.text.secondary, textAlign: 'center', padding: SPACING.xl }}>
        No data available
      </div>
    );
  }

  const maxValue = Math.max(...data.flatMap(d => [d.inflow, d.outflow]), 1);
  const groupWidth = chartWidth / data.length;
  const barWidth = Math.min(40, (groupWidth - 24) / 2);

  return (
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <svg width={chartWidth + padding.left + padding.right} height={height}>
        <g transform={`translate(${padding.left}, ${padding.top})`}>
          {/* Horizontal grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
            const y = chartHeight * (1 - ratio);
            const value = maxValue * ratio;
            return (
              <g key={ratio}>
                <line
                  x1={0}
                  y1={y}
                  x2={chartWidth}
                  y2={y}
                  stroke={colors.border.default}
                  strokeWidth={ratio === 0 ? 1.5 : 1}
                  strokeDasharray={ratio === 0 ? 'none' : '3,3'}
                  opacity={ratio === 0 ? 0.6 : 0.4}
                />
                {ratio > 0 && (
                  <text
                    x={-12}
                    y={y + 4}
                    textAnchor="end"
                    fontSize={TYPOGRAPHY.sizes.xs}
                    fill={colors.text.tertiary}
                  >
                    {formatCurrency(value, currency).replace(/[^0-9.,-]/g, '')}
                  </text>
                )}
              </g>
            );
          })}

          {/* Bar groups */}
          {data.map((d, idx) => {
            const groupX = idx * groupWidth + groupWidth / 2;
            const inflowHeight = (d.inflow / maxValue) * chartHeight;
            const outflowHeight = (d.outflow / maxValue) * chartHeight;

            return (
              <g key={d.month}>
                {/* Income bar */}
                <rect
                  x={groupX - barWidth - 4}
                  y={chartHeight - inflowHeight}
                  width={barWidth}
                  height={inflowHeight}
                  fill={colors.chart.inflow}
                  rx={3}
                  opacity={0.85}
                />
                {/* Income value on top */}
                {inflowHeight > 20 && (
                  <text
                    x={groupX - barWidth / 2 - 4}
                    y={chartHeight - inflowHeight - 6}
                    textAnchor="middle"
                    fontSize={TYPOGRAPHY.sizes.xs}
                    fontWeight={TYPOGRAPHY.weights.medium}
                    fill={colors.chart.inflow}
                  >
                    {formatCurrency(d.inflow, currency).replace(/[^0-9.,-]/g, '')}
                  </text>
                )}

                {/* Spending bar */}
                <rect
                  x={groupX + 4}
                  y={chartHeight - outflowHeight}
                  width={barWidth}
                  height={outflowHeight}
                  fill={colors.chart.outflow}
                  rx={3}
                  opacity={0.85}
                />
                {/* Spending value on top */}
                {outflowHeight > 20 && (
                  <text
                    x={groupX + barWidth / 2 + 4}
                    y={chartHeight - outflowHeight - 6}
                    textAnchor="middle"
                    fontSize={TYPOGRAPHY.sizes.xs}
                    fontWeight={TYPOGRAPHY.weights.medium}
                    fill={colors.chart.outflow}
                  >
                    {formatCurrency(d.outflow, currency).replace(/[^0-9.,-]/g, '')}
                  </text>
                )}

                {/* Month label */}
                <text
                  x={groupX}
                  y={chartHeight + 20}
                  textAnchor="middle"
                  fontSize={TYPOGRAPHY.sizes.sm}
                  fontWeight={TYPOGRAPHY.weights.medium}
                  fill={colors.text.secondary}
                >
                  {d.label.split(' ')[0]}
                </text>

                {/* Net value below month */}
                <text
                  x={groupX}
                  y={chartHeight + 36}
                  textAnchor="middle"
                  fontSize={TYPOGRAPHY.sizes.xs}
                  fontWeight={TYPOGRAPHY.weights.semibold}
                  fill={d.net >= 0 ? colors.chart.inflow : colors.chart.outflow}
                >
                  {d.net >= 0 ? '+' : ''}{formatCurrency(d.net, currency).replace(/[^0-9.,-]/g, '')}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Legend */}
      <div
        style={{
          display: 'flex',
          gap: SPACING.xl,
          justifyContent: 'center',
          marginTop: SPACING.md,
          paddingTop: SPACING.md,
          borderTop: `1px solid ${colors.border.default}`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: SPACING.sm }}>
          <div
            style={{
              width: 16,
              height: 16,
              background: colors.chart.inflow,
              borderRadius: 3,
              opacity: 0.85,
            }}
          />
          <span style={{ fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.secondary }}>Income</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: SPACING.sm }}>
          <div
            style={{
              width: 16,
              height: 16,
              background: colors.chart.outflow,
              borderRadius: 3,
              opacity: 0.85,
            }}
          />
          <span style={{ fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.secondary }}>Spending</span>
        </div>
      </div>
    </div>
  );
};

interface BudgetVsActualChartProps {
  data: Array<{ month: string; label: string; actual: number; budget: number; variance: number }>;
  theme: 'light' | 'dark';
  currency: string;
  height?: number;
}

// ============================================================================
// BUDGET COMPONENTS
// ============================================================================

interface BudgetHealthKPIsProps {
  totalBudget: number;
  totalSpent: number;
  remainingBudget: number;
  utilizationPct: number;
  theme: 'light' | 'dark';
  currency: string;
}

const BudgetHealthKPIs: React.FC<BudgetHealthKPIsProps> = ({
  totalBudget,
  totalSpent,
  remainingBudget,
  utilizationPct,
  theme,
  currency,
}) => {
  const colors = getThemeColors(theme);
  const isOverBudget = remainingBudget < 0;

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: SPACING.lg,
      }}
    >
      <Card theme={theme} padding="lg">
        <div style={{ fontSize: TYPOGRAPHY.sizes.xs, color: colors.text.tertiary, marginBottom: SPACING.xs }}>
          Total Budget
        </div>
        <div style={{ fontSize: TYPOGRAPHY.sizes.xl, fontWeight: TYPOGRAPHY.weights.bold, color: colors.text.primary }}>
          {formatCurrency(totalBudget, currency)}
        </div>
      </Card>
      <Card theme={theme} padding="lg">
        <div style={{ fontSize: TYPOGRAPHY.sizes.xs, color: colors.text.tertiary, marginBottom: SPACING.xs }}>
          Total Spent
        </div>
        <div style={{ fontSize: TYPOGRAPHY.sizes.xl, fontWeight: TYPOGRAPHY.weights.bold, color: colors.text.primary }}>
          {formatCurrency(totalSpent, currency)}
        </div>
      </Card>
      <Card theme={theme} padding="lg">
        <div style={{ fontSize: TYPOGRAPHY.sizes.xs, color: colors.text.tertiary, marginBottom: SPACING.xs }}>
          Remaining Budget
        </div>
        <div
          style={{
            fontSize: TYPOGRAPHY.sizes.xl,
            fontWeight: TYPOGRAPHY.weights.bold,
            color: isOverBudget ? colors.text.negative : '#16a34a',
          }}
        >
          {formatCurrency(remainingBudget, currency)}
        </div>
      </Card>
      <Card theme={theme} padding="lg">
        <div style={{ fontSize: TYPOGRAPHY.sizes.xs, color: colors.text.tertiary, marginBottom: SPACING.xs }}>
          Budget Utilization
        </div>
        <div
          style={{
            fontSize: TYPOGRAPHY.sizes.xl,
            fontWeight: TYPOGRAPHY.weights.bold,
            color: utilizationPct > 100 ? colors.text.negative : utilizationPct > 85 ? '#ca8a04' : '#16a34a',
          }}
        >
          {utilizationPct.toFixed(1)}%
        </div>
      </Card>
    </div>
  );
};

interface BudgetProgressChartProps {
  data: BudgetProgressData[];
  theme: 'light' | 'dark';
  currency: string;
}

const BudgetProgressChart: React.FC<BudgetProgressChartProps> = ({ data, theme, currency }) => {
  const colors = getThemeColors(theme);
  const barHeight = 32;
  const gap = SPACING.md;

  if (data.length === 0) {
    return (
      <div style={{ color: colors.text.secondary, textAlign: 'center', padding: SPACING.xl }}>
        No budget data available
      </div>
    );
  }

  const getStatusColor = (status: 'under' | 'on-track' | 'over') => {
    if (status === 'under') return '#16a34a'; // green
    if (status === 'on-track') return '#ca8a04'; // yellow
    return colors.chart.outflow; // red
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap }}>
      {data.map((item, idx) => {
        const utilizationWidth = item.budget > 0 ? (item.actual / item.budget) * 100 : 0;
        const fillWidth = Math.min(utilizationWidth, 100);
        const overWidth = Math.max(0, utilizationWidth - 100);
        const isOver = item.utilizationPct > 100;

        return (
          <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: SPACING.xs }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: SPACING.xs }}>
              <span style={{ fontSize: TYPOGRAPHY.sizes.sm, fontWeight: TYPOGRAPHY.weights.medium, color: colors.text.primary }}>
                {item.category}
              </span>
              <div style={{ display: 'flex', gap: SPACING.md, alignItems: 'center' }}>
                <span style={{ fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.secondary }}>
                  {formatCurrency(item.actual, currency)} / {formatCurrency(item.budget, currency)}
                </span>
                <span
                  style={{
                    fontSize: TYPOGRAPHY.sizes.sm,
                    fontWeight: TYPOGRAPHY.weights.semibold,
                    color: getStatusColor(item.status),
                    minWidth: 50,
                    textAlign: 'right',
                  }}
                >
                  {item.utilizationPct.toFixed(1)}%
                </span>
              </div>
            </div>
            <div
              style={{
                position: 'relative',
                width: '100%',
                height: barHeight,
                background: colors.bg.secondary,
                borderRadius: 4,
                overflow: 'hidden',
              }}
            >
              {/* Budget background bar */}
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  top: 0,
                  width: '100%',
                  height: '100%',
                  background: colors.border.default,
                  opacity: 0.3,
                }}
              />
              {/* Actual spending fill */}
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  top: 0,
                  width: `${fillWidth}%`,
                  height: '100%',
                  background: getStatusColor(item.status),
                  opacity: isOver ? 0.8 : 0.6,
                  transition: 'width 0.3s ease',
                }}
              />
              {/* Over-budget indicator */}
              {isOver && (
                <div
                  style={{
                    position: 'absolute',
                    left: `${Math.min(fillWidth, 100)}%`,
                    top: 0,
                    width: `${overWidth}%`,
                    height: '100%',
                    background: colors.chart.outflow,
                    opacity: 0.9,
                  }}
                />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

interface BudgetAllocationDonutProps {
  data: BudgetAllocationData[];
  theme: 'light' | 'dark';
  currency: string;
}

const BudgetAllocationDonut: React.FC<BudgetAllocationDonutProps> = ({ data, theme, currency }) => {
  const colors = getThemeColors(theme);
  const size = 280;
  const centerX = size / 2;
  const centerY = size / 2;
  const radius = 80;
  const innerRadius = 50;

  if (data.length === 0) {
    return (
      <div style={{ color: colors.text.secondary, textAlign: 'center', padding: SPACING.xl }}>
        No budget allocation data available
      </div>
    );
  }

  const total = data.reduce((sum, d) => sum + d.amount, 0);
  let currentAngle = -Math.PI / 2; // Start at top

  const getCategoryColor = (idx: number) => {
    const palette = [
      colors.primary,
      '#2563eb',
      '#16a34a',
      '#ca8a04',
      '#9333ea',
      '#0891b2',
      '#ea580c',
      '#db2777',
    ];
    return palette[idx % palette.length];
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: SPACING.lg }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {data.map((item, idx) => {
          const percentage = item.percentage / 100;
          const angle = percentage * 2 * Math.PI;
          const startAngle = currentAngle;
          const endAngle = currentAngle + angle;
          currentAngle = endAngle;

          const x1 = centerX + radius * Math.cos(startAngle);
          const y1 = centerY + radius * Math.sin(startAngle);
          const x2 = centerX + radius * Math.cos(endAngle);
          const y2 = centerY + radius * Math.sin(endAngle);

          const largeArcFlag = angle > Math.PI ? 1 : 0;

          const pathData = [
            `M ${centerX} ${centerY}`,
            `L ${x1} ${y1}`,
            `A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2}`,
            'Z',
          ].join(' ');

          const innerX1 = centerX + innerRadius * Math.cos(startAngle);
          const innerY1 = centerY + innerRadius * Math.sin(startAngle);
          const innerX2 = centerX + innerRadius * Math.cos(endAngle);
          const innerY2 = centerY + innerRadius * Math.sin(endAngle);

          const innerPathData = [
            `M ${centerX} ${centerY}`,
            `L ${innerX1} ${innerY1}`,
            `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 1 ${innerX2} ${innerY2}`,
            'Z',
          ].join(' ');

          return (
            <g key={idx}>
              <path
                d={pathData}
                fill={getCategoryColor(idx)}
                opacity={0.7}
                stroke={colors.bg.primary}
                strokeWidth={2}
              />
              <path
                d={innerPathData}
                fill={colors.bg.primary}
              />
            </g>
          );
        })}
        {/* Center text */}
        <text
          x={centerX}
          y={centerY - 5}
          textAnchor="middle"
          fontSize={TYPOGRAPHY.sizes.lg}
          fontWeight={TYPOGRAPHY.weights.bold}
          fill={colors.text.primary}
        >
          {formatCurrency(total, currency)}
        </text>
        <text
          x={centerX}
          y={centerY + 15}
          textAnchor="middle"
          fontSize={TYPOGRAPHY.sizes.xs}
          fill={colors.text.secondary}
        >
          Total Budget
        </text>
      </svg>
      {/* Legend */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: SPACING.xs, width: '100%' }}>
        {data.slice(0, 8).map((item, idx) => (
          <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: SPACING.sm }}>
              <div
                style={{
                  width: 12,
                  height: 12,
                  background: getCategoryColor(idx),
                  borderRadius: 2,
                }}
              />
              <span style={{ fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.primary }}>{item.category}</span>
            </div>
            <div style={{ display: 'flex', gap: SPACING.sm, alignItems: 'center' }}>
              <span style={{ fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.secondary }}>
                {formatCurrency(item.amount, currency)}
              </span>
              <span style={{ fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.tertiary, minWidth: 45, textAlign: 'right' }}>
                {item.percentage.toFixed(1)}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

interface BudgetVarianceTableProps {
  data: BudgetProgressData[];
  theme: 'light' | 'dark';
  currency: string;
}

const BudgetVarianceTable: React.FC<BudgetVarianceTableProps> = ({ data, theme, currency }) => {
  const colors = getThemeColors(theme);
  const [sortField, setSortField] = useState<'category' | 'budget' | 'actual' | 'variance' | 'variancePct'>('variance');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const sortedData = [...data].sort((a, b) => {
    let aVal: number | string = a[sortField];
    let bVal: number | string = b[sortField];
    
    if (sortField === 'category') {
      aVal = a.category.toLowerCase();
      bVal = b.category.toLowerCase();
    }

    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortDirection === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    }

    return sortDirection === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
  });

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const getStatusIndicator = (status: 'under' | 'on-track' | 'over') => {
    if (status === 'under') return { color: '#16a34a', label: 'Under' };
    if (status === 'on-track') return { color: '#ca8a04', label: 'On Track' };
    return { color: colors.chart.outflow, label: 'Over' };
  };

  if (data.length === 0) {
    return (
      <div style={{ color: colors.text.secondary, textAlign: 'center', padding: SPACING.xl }}>
        No budget variance data available
      </div>
    );
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: `2px solid ${colors.border.default}` }}>
            <th
              style={{
                textAlign: 'left',
                padding: SPACING.md,
                fontSize: TYPOGRAPHY.sizes.sm,
                fontWeight: TYPOGRAPHY.weights.semibold,
                color: colors.text.secondary,
                cursor: 'pointer',
                userSelect: 'none',
              }}
              onClick={() => handleSort('category')}
            >
              Category {sortField === 'category' && (sortDirection === 'asc' ? '↑' : '↓')}
            </th>
            <th
              style={{
                textAlign: 'right',
                padding: SPACING.md,
                fontSize: TYPOGRAPHY.sizes.sm,
                fontWeight: TYPOGRAPHY.weights.semibold,
                color: colors.text.secondary,
                cursor: 'pointer',
                userSelect: 'none',
              }}
              onClick={() => handleSort('budget')}
            >
              Budget {sortField === 'budget' && (sortDirection === 'asc' ? '↑' : '↓')}
            </th>
            <th
              style={{
                textAlign: 'right',
                padding: SPACING.md,
                fontSize: TYPOGRAPHY.sizes.sm,
                fontWeight: TYPOGRAPHY.weights.semibold,
                color: colors.text.secondary,
                cursor: 'pointer',
                userSelect: 'none',
              }}
              onClick={() => handleSort('actual')}
            >
              Actual {sortField === 'actual' && (sortDirection === 'asc' ? '↑' : '↓')}
            </th>
            <th
              style={{
                textAlign: 'right',
                padding: SPACING.md,
                fontSize: TYPOGRAPHY.sizes.sm,
                fontWeight: TYPOGRAPHY.weights.semibold,
                color: colors.text.secondary,
                cursor: 'pointer',
                userSelect: 'none',
              }}
              onClick={() => handleSort('variance')}
            >
              Variance {sortField === 'variance' && (sortDirection === 'asc' ? '↑' : '↓')}
            </th>
            <th
              style={{
                textAlign: 'right',
                padding: SPACING.md,
                fontSize: TYPOGRAPHY.sizes.sm,
                fontWeight: TYPOGRAPHY.weights.semibold,
                color: colors.text.secondary,
                cursor: 'pointer',
                userSelect: 'none',
              }}
              onClick={() => handleSort('variancePct')}
            >
              Variance % {sortField === 'variancePct' && (sortDirection === 'asc' ? '↑' : '↓')}
            </th>
            <th
              style={{
                textAlign: 'center',
                padding: SPACING.md,
                fontSize: TYPOGRAPHY.sizes.sm,
                fontWeight: TYPOGRAPHY.weights.semibold,
                color: colors.text.secondary,
              }}
            >
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedData.map((item, idx) => {
            const status = getStatusIndicator(item.status);
            return (
              <tr
                key={idx}
                style={{
                  borderBottom: `1px solid ${colors.border.default}`,
                  transition: 'background 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = colors.bg.secondary;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent';
                }}
              >
                <td style={{ padding: SPACING.md, color: colors.text.primary, fontWeight: TYPOGRAPHY.weights.medium }}>
                  {item.category}
                </td>
                <td style={{ textAlign: 'right', padding: SPACING.md, color: colors.text.primary }}>
                  {formatCurrency(item.budget, currency)}
                </td>
                <td style={{ textAlign: 'right', padding: SPACING.md, color: colors.text.primary }}>
                  {formatCurrency(item.actual, currency)}
                </td>
                <td
                  style={{
                    textAlign: 'right',
                    padding: SPACING.md,
                    fontWeight: TYPOGRAPHY.weights.medium,
                    color: item.variance > 0 ? colors.text.negative : '#16a34a',
                  }}
                >
                  {item.variance > 0 ? '+' : ''}{formatCurrency(item.variance, currency)}
                </td>
                <td
                  style={{
                    textAlign: 'right',
                    padding: SPACING.md,
                    color: item.variancePct > 0 ? colors.text.negative : '#16a34a',
                  }}
                >
                  {item.variancePct > 0 ? '+' : ''}{item.variancePct.toFixed(1)}%
                </td>
                <td style={{ textAlign: 'center', padding: SPACING.md }}>
                  <div
                    style={{
                      display: 'inline-block',
                      padding: `${SPACING.xs}px ${SPACING.sm}px`,
                      background: status.color,
                      color: colors.bg.primary,
                      borderRadius: 4,
                      fontSize: TYPOGRAPHY.sizes.xs,
                      fontWeight: TYPOGRAPHY.weights.semibold,
                    }}
                  >
                    {status.label}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

interface BudgetTrendChartProps {
  data: Array<{ month: string; label: string; actual: number; budget: number; variance: number }>;
  theme: 'light' | 'dark';
  currency: string;
  height?: number;
}

const BudgetTrendChart: React.FC<BudgetTrendChartProps> = ({ data, theme, currency, height = 300 }) => {
  const colors = getThemeColors(theme);
  const padding = { top: 20, right: 20, bottom: 50, left: 70 };
  const chartWidth = 600;
  const chartHeight = height - padding.top - padding.bottom;

  if (data.length === 0) {
    return (
      <div style={{ color: colors.text.secondary, textAlign: 'center', padding: SPACING.xl }}>
        No budget trend data available
      </div>
    );
  }

  const maxValue = Math.max(...data.flatMap(d => [d.actual, d.budget]), 1);
  const pointSpacing = data.length > 1 ? chartWidth / (data.length - 1) : 0;

  // Build path data
  const budgetPoints = data.map((d, idx) => ({
    x: idx * pointSpacing,
    y: chartHeight - (d.budget / maxValue) * chartHeight,
  }));

  const actualPoints = data.map((d, idx) => ({
    x: idx * pointSpacing,
    y: chartHeight - (d.actual / maxValue) * chartHeight,
  }));

  const budgetPath = budgetPoints.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  const actualPath = actualPoints.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

  // Area fill for variance
  const actualPointsReversed = [...actualPoints].reverse();
  const areaPath = [
    `M ${budgetPoints[0].x} ${chartHeight}`,
    ...budgetPoints.map(p => `L ${p.x} ${p.y}`),
    ...actualPointsReversed.map(p => `L ${p.x} ${p.y}`),
    `L ${budgetPoints[0].x} ${chartHeight}`,
    'Z',
  ].join(' ');

  return (
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <svg width={chartWidth + padding.left + padding.right} height={height}>
        <g transform={`translate(${padding.left}, ${padding.top})`}>
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
            const y = chartHeight * ratio;
            const value = maxValue * (1 - ratio);
            return (
              <g key={ratio}>
                <line x1={0} y1={y} x2={chartWidth} y2={y} stroke={colors.border.default} strokeWidth={1} strokeDasharray="4,4" />
                <text x={-10} y={y + 4} textAnchor="end" fontSize={TYPOGRAPHY.sizes.xs} fill={colors.text.tertiary}>
                  {formatCurrency(value, currency).replace(/[^0-9.,]/g, '')}
                </text>
              </g>
            );
          })}

          {/* Variance area fill */}
          <path d={areaPath} fill={colors.chart.outflow} opacity={0.1} />

          {/* Budget line (dashed) */}
          <path
            d={budgetPath}
            fill="none"
            stroke={colors.text.tertiary}
            strokeWidth={2}
            strokeDasharray="6,4"
            opacity={0.6}
          />

          {/* Actual line (solid) */}
          <path
            d={actualPath}
            fill="none"
            stroke={colors.chart.outflow}
            strokeWidth={3}
          />

          {/* Data points */}
          {budgetPoints.map((p, idx) => (
            <circle key={`budget-${idx}`} cx={p.x} cy={p.y} r={4} fill={colors.text.tertiary} opacity={0.6} />
          ))}
          {actualPoints.map((p, idx) => (
            <circle key={`actual-${idx}`} cx={p.x} cy={p.y} r={5} fill={colors.chart.outflow} />
          ))}

          {/* Month labels */}
          {data.map((d, idx) => {
            const x = idx * pointSpacing;
            return (
              <text
                key={idx}
                x={x}
                y={chartHeight + 18}
                textAnchor="middle"
                fontSize={TYPOGRAPHY.sizes.xs}
                fill={colors.text.secondary}
              >
                {d.label.split(' ')[0]}
              </text>
            );
          })}
        </g>
      </svg>
      {/* Legend */}
      <div style={{ display: 'flex', gap: SPACING.lg, justifyContent: 'center', marginTop: SPACING.sm, fontSize: TYPOGRAPHY.sizes.sm }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: SPACING.xs }}>
          <svg width={20} height={3}>
            <line x1={0} y1={1.5} x2={20} y2={1.5} stroke={colors.text.tertiary} strokeWidth={2} strokeDasharray="6,4" opacity={0.6} />
          </svg>
          <span style={{ color: colors.text.secondary }}>Budget</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: SPACING.xs }}>
          <svg width={20} height={3}>
            <line x1={0} y1={1.5} x2={20} y2={1.5} stroke={colors.chart.outflow} strokeWidth={3} />
          </svg>
          <span style={{ color: colors.text.secondary }}>Actual</span>
        </div>
      </div>
    </div>
  );
};

const BudgetVsActualChart: React.FC<BudgetVsActualChartProps> = ({ data, theme, currency, height = 240 }) => {
  const colors = getThemeColors(theme);
  const padding = { top: 20, right: 20, bottom: 50, left: 70 };
  const chartWidth = 560;
  const chartHeight = height - padding.top - padding.bottom;

  if (data.length === 0) {
    return (
      <div style={{ color: colors.text.secondary, textAlign: 'center', padding: SPACING.xl }}>
        No budget data available
      </div>
    );
  }

  const maxValue = Math.max(...data.flatMap(d => [d.actual, d.budget]), 1);
  const barGroupWidth = chartWidth / data.length;
  const barWidth = (barGroupWidth - 20) / 2;

  return (
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <svg width={chartWidth + padding.left + padding.right} height={height}>
        <g transform={`translate(${padding.left}, ${padding.top})`}>
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
            const y = chartHeight * ratio;
            const value = maxValue * (1 - ratio);
            return (
              <g key={ratio}>
                <line x1={0} y1={y} x2={chartWidth} y2={y} stroke={colors.border.default} strokeWidth={1} strokeDasharray="4,4" />
                <text x={-10} y={y + 4} textAnchor="end" fontSize={TYPOGRAPHY.sizes.xs} fill={colors.text.tertiary}>
                  {formatCurrency(value, currency).replace(/[^0-9.,]/g, '')}
                </text>
              </g>
            );
          })}

          {/* Bar groups */}
          {data.map((d, idx) => {
            const groupX = idx * barGroupWidth + 10;
            const actualHeight = (d.actual / maxValue) * chartHeight;
            const budgetHeight = (d.budget / maxValue) * chartHeight;
            const isOverBudget = d.actual > d.budget;

            return (
              <g key={idx}>
                {/* Budget bar */}
                <rect x={groupX} y={chartHeight - budgetHeight} width={barWidth} height={budgetHeight} fill={colors.text.tertiary} opacity={0.4} rx={3} />
                {/* Actual bar */}
                <rect x={groupX + barWidth + 4} y={chartHeight - actualHeight} width={barWidth} height={actualHeight} fill={isOverBudget ? colors.chart.outflow : colors.chart.inflow} rx={3} />
                {/* Variance indicator */}
                {d.variance !== 0 && (
                  <text x={groupX + barWidth + 4 + barWidth / 2} y={chartHeight - actualHeight - 6} textAnchor="middle" fontSize={TYPOGRAPHY.sizes.xs} fontWeight={TYPOGRAPHY.weights.semibold} fill={isOverBudget ? colors.chart.outflow : colors.chart.inflow}>
                    {isOverBudget ? '+' : ''}{Math.round(d.variance)}
                  </text>
                )}
                {/* Month label */}
                <text x={groupX + barGroupWidth / 2 - 5} y={chartHeight + 18} textAnchor="middle" fontSize={TYPOGRAPHY.sizes.xs} fill={colors.text.secondary}>
                  {formatMonthLabel(d.month).split(' ')[0]}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
      {/* Legend */}
      <div style={{ display: 'flex', gap: SPACING.lg, justifyContent: 'center', marginTop: SPACING.sm, fontSize: TYPOGRAPHY.sizes.sm }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: SPACING.xs }}>
          <div style={{ width: 14, height: 14, background: colors.text.tertiary, opacity: 0.4, borderRadius: 2 }} />
          <span style={{ color: colors.text.secondary }}>Budget</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: SPACING.xs }}>
          <div style={{ width: 14, height: 14, background: colors.chart.inflow, borderRadius: 2 }} />
          <span style={{ color: colors.text.secondary }}>Actual (under)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: SPACING.xs }}>
          <div style={{ width: 14, height: 14, background: colors.chart.outflow, borderRadius: 2 }} />
          <span style={{ color: colors.text.secondary }}>Actual (over)</span>
        </div>
      </div>
    </div>
  );
};


interface InsightCardProps {
  title: string;
  value: string;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendLabel?: string;
  theme: 'light' | 'dark';
  accentColor?: string;
  icon?: string;
}

const InsightCard: React.FC<InsightCardProps> = ({ title, value, subtitle, trend, trendLabel, theme, accentColor, icon }) => {
  const colors = getThemeColors(theme);
  
  const getTrendColor = () => {
    if (trend === 'up') return '#16a34a';
    if (trend === 'down') return colors.primary;
    return colors.text.tertiary;
  };

  const getTrendIcon = () => {
    if (trend === 'up') return '↗';
    if (trend === 'down') return '↘';
    return '→';
  };

  return (
    <div
      style={{
        background: colors.bg.elevated,
        border: `1px solid ${colors.border.default}`,
        borderRadius: 12,
        padding: SPACING.lg,
        minWidth: 150,
        flex: 1,
        position: 'relative',
        overflow: 'hidden',
        transition: 'box-shadow 0.2s ease, transform 0.2s ease',
      }}
    >
      {/* Left accent bar */}
      <div
        style={{
          position: 'absolute',
          top: SPACING.md,
          left: 0,
          bottom: SPACING.md,
          width: 3,
          background: accentColor || colors.primary,
          borderRadius: '0 2px 2px 0',
        }}
      />
      
      {/* Header with icon */}
      <div style={{ display: 'flex', alignItems: 'center', gap: SPACING.xs, marginBottom: SPACING.sm, paddingLeft: SPACING.sm }}>
        {icon && (
          <span style={{ fontSize: TYPOGRAPHY.sizes.base }}>{icon}</span>
        )}
        <span
          style={{
            fontSize: TYPOGRAPHY.sizes.xs,
            color: colors.text.tertiary,
            textTransform: 'uppercase',
            letterSpacing: 0.8,
            fontWeight: TYPOGRAPHY.weights.medium,
          }}
        >
          {title}
        </span>
      </div>
      
      {/* Value */}
      <div
        style={{
          fontSize: TYPOGRAPHY.sizes.xxl,
          fontWeight: TYPOGRAPHY.weights.bold,
          color: colors.text.primary,
          marginBottom: SPACING.xs,
          paddingLeft: SPACING.sm,
          lineHeight: 1.1,
        }}
      >
        {value}
      </div>
      
      {/* Trend or subtitle */}
      {(subtitle || trend) && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: SPACING.xs,
            fontSize: TYPOGRAPHY.sizes.sm,
            paddingLeft: SPACING.sm,
          }}
        >
          {trend && (
            <span
              style={{
                color: getTrendColor(),
                fontWeight: TYPOGRAPHY.weights.semibold,
                fontSize: TYPOGRAPHY.sizes.base,
              }}
            >
              {getTrendIcon()}
            </span>
          )}
          <span style={{ color: trendLabel ? getTrendColor() : colors.text.secondary }}>
            {trendLabel || subtitle}
          </span>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// MONTHLY INSIGHTS HELPERS
// ============================================================================

interface ParsedMonthInsight {
  monthKey: string;  // e.g., "2025-07" or raw header
  header: string;    // Full header text e.g., "2025-07 (Santander)"
  content: string;   // The insight content for this month
}

/**
 * Parses statement_insights string into grouped monthly sections.
 * Handles both newline-separated and inline "## YYYY-MM" patterns.
 * Example: "## 2025-07 (Santander) ## At a Glance • Content..."
 */
function parseInsightsByMonth(insights: string): ParsedMonthInsight[] {
  if (!insights) return [];
  
  // First, normalize the string by inserting newlines before "## YYYY-MM" patterns
  // This handles cases where insights are stored as a single line
  const normalizedInsights = insights.replace(/\.\s*##\s+(\d{4}-\d{2})/g, '.\n## $1');
  
  // Split by the month header pattern, capturing the header parts
  // Pattern: ## YYYY-MM followed by optional (Bank) and text until next ## YYYY-MM or end
  const monthPattern = /##\s+(\d{4}-\d{2})(?:\s+\(([^)]+)\))?/g;
  
  const sections: ParsedMonthInsight[] = [];
  let lastIndex = 0;
  let match;
  
  // Find all month headers and their positions
  const matches: { monthKey: string; bank: string; fullHeader: string; index: number; endIndex: number }[] = [];
  
  while ((match = monthPattern.exec(insights)) !== null) {
    matches.push({
      monthKey: match[1],
      bank: match[2] || '',
      fullHeader: match[0],
      index: match.index,
      endIndex: match.index + match[0].length,
    });
  }
  
  // If no month headers found, return empty (will show as single block)
  if (matches.length === 0) {
    return [];
  }
  
  // Extract content for each month section
  for (let i = 0; i < matches.length; i++) {
    const current = matches[i];
    const nextStart = i + 1 < matches.length ? matches[i + 1].index : insights.length;
    
    // Get content between this header end and next header start
    let content = insights.substring(current.endIndex, nextStart).trim();
    
    // Clean up content: remove leading dots/spaces, trailing dots before next section
    content = content.replace(/^\s*[.•]\s*/, '').replace(/\.\s*$/, '');
    
    // Format the header nicely
    const header = current.bank 
      ? `${current.monthKey} (${current.bank})`
      : current.monthKey;
    
    sections.push({
      monthKey: current.monthKey,
      header,
      content,
    });
  }
  
  return sections;
}

interface MonthlyInsightPanelProps {
  insight: ParsedMonthInsight;
  isExpanded: boolean;
  onToggle: () => void;
  theme: 'light' | 'dark';
}

const MonthlyInsightPanel: React.FC<MonthlyInsightPanelProps> = ({
  insight,
  isExpanded,
  onToggle,
  theme,
}) => {
  const colors = getThemeColors(theme);
  
  // Render content with markdown-like formatting
  // Handles both newline-separated and inline formats
  const renderContent = (content: string) => {
    // First, normalize: insert line breaks before ## headers and • bullets
    let normalized = content
      // Add newline before ## sub-headers (At a Glance, Key Highlights, etc.)
      .replace(/\s*##\s+/g, '\n## ')
      // Add newline before bullet points
      .replace(/\s*•\s+/g, '\n• ')
      // Clean up multiple spaces
      .replace(/\s{2,}/g, ' ')
      .trim();
    
    const lines = normalized.split('\n').filter(line => line.trim());
    
    return lines.map((line, idx) => {
      const trimmedLine = line.trim();
      
      // Format sub-headers (## At a Glance, ## Key Highlights, etc.)
      if (trimmedLine.startsWith('## ')) {
        return (
          <h5
            key={idx}
            style={{
              fontSize: TYPOGRAPHY.sizes.sm,
              fontWeight: TYPOGRAPHY.weights.semibold,
              color: colors.text.primary,
              marginTop: idx > 0 ? SPACING.md : 0,
              marginBottom: SPACING.xs,
              borderBottom: `1px solid ${colors.border.default}`,
              paddingBottom: SPACING.xs,
            }}
          >
            {trimmedLine.replace(/^##\s+/, '')}
          </h5>
        );
      }
      
      // Format bullet points
      if (trimmedLine.startsWith('• ') || trimmedLine.startsWith('- ')) {
        const bulletContent = trimmedLine.replace(/^[•-]\s+/, '');
        const hasAmount = /[\d,.]+\s*(PLN|USD|EUR|GBP)/i.test(bulletContent);
        return (
          <div
            key={idx}
            style={{
              paddingLeft: SPACING.md,
              marginBottom: SPACING.sm,
              display: 'flex',
              alignItems: 'flex-start',
              gap: SPACING.sm,
            }}
          >
            <span style={{ 
              color: hasAmount ? colors.primary : colors.text.tertiary,
              flexShrink: 0,
            }}>•</span>
            <span style={{ color: hasAmount ? colors.text.primary : colors.text.secondary }}>
              {bulletContent}
            </span>
          </div>
        );
      }
      
      // Regular text (could be continuation or standalone)
      return (
        <div key={idx} style={{ marginBottom: SPACING.xs, color: colors.text.secondary }}>
          {trimmedLine}
        </div>
      );
    });
  };
  
  return (
    <div
      style={{
        border: `1px solid ${colors.border.default}`,
        borderRadius: 8,
        marginBottom: SPACING.sm,
        overflow: 'hidden',
      }}
    >
      {/* Header button */}
      <button
        onClick={onToggle}
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          width: '100%',
          background: colors.bg.subtle,
          border: 'none',
          padding: `${SPACING.sm}px ${SPACING.md}px`,
          cursor: 'pointer',
          textAlign: 'left',
        }}
        aria-expanded={isExpanded}
      >
        <span
          style={{
            fontSize: TYPOGRAPHY.sizes.sm,
            fontWeight: TYPOGRAPHY.weights.semibold,
            color: colors.text.primary,
          }}
        >
          {insight.header}
        </span>
        <span style={{ fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.tertiary }}>
          {isExpanded ? '▾' : '▸'}
        </span>
      </button>
      
      {/* Collapsible content */}
      {isExpanded && (
        <div
          style={{
            padding: SPACING.md,
            fontSize: TYPOGRAPHY.sizes.sm,
            lineHeight: 1.5,
          }}
        >
          {renderContent(insight.content)}
        </div>
      )}
    </div>
  );
};

interface SavingsGaugeProps {
  rate: number; // -100 to 100+
  theme: 'light' | 'dark';
}

const SavingsGauge: React.FC<SavingsGaugeProps> = ({ rate, theme }) => {
  const colors = getThemeColors(theme);
  const size = 100;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * Math.PI; // Half circle
  const clampedRate = Math.max(-100, Math.min(100, rate));
  const progress = ((clampedRate + 100) / 200) * circumference;

  const getColor = () => {
    if (rate >= 20) return '#16a34a'; // green
    if (rate >= 0) return '#ca8a04'; // yellow
    return colors.chart.outflow; // red
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <svg width={size} height={size / 2 + 10} viewBox={`0 0 ${size} ${size / 2 + 10}`}>
        {/* Background arc */}
        <path
          d={`M ${strokeWidth / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
          fill="none"
          stroke={colors.bg.secondary}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Progress arc */}
        <path
          d={`M ${strokeWidth / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
          fill="none"
          stroke={getColor()}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${progress} ${circumference}`}
          style={{ transition: 'stroke-dasharray 0.5s ease' }}
        />
        {/* Center text */}
        <text x={size / 2} y={size / 2} textAnchor="middle" fontSize={TYPOGRAPHY.sizes.lg} fontWeight={TYPOGRAPHY.weights.bold} fill={colors.text.primary}>
          {rate.toFixed(0)}%
        </text>
      </svg>
      <div style={{ fontSize: TYPOGRAPHY.sizes.xs, color: colors.text.secondary, marginTop: 2 }}>
        {rate >= 20 ? 'Excellent' : rate >= 0 ? 'On track' : 'Spending > Income'}
      </div>
    </div>
  );
};

// ============================================================================
// MAIN DASHBOARD WIDGET
// ============================================================================

type TabType = 'journey' | 'overview' | 'cashflow' | 'trends' | 'budget' | 'details' | 'preferences';

// Type for preferences data
interface CategorizationRule {
  id: string;
  name: string;
  bank_name: string | null;
  rule: { pattern?: string; category?: string; [key: string]: any };
  priority: number;
}

interface UserSettings {
  functional_currency: string;
  bank_accounts_count?: number;
  profiles?: string[];
  onboarding_complete: boolean;
}

interface PreferencesData {
  settings: UserSettings | null;
  categorization_rules: CategorizationRule[];
  parsing_banks: string[];
}

export const DashboardWidget: React.FC = () => {
  const [localDashboardData, setLocalDashboardData] = useState<DashboardProps | null>(null);
  const { data, error, loading } = useDashboardData(localDashboardData);
  const theme = useTheme();
  const [showInsights, setShowInsights] = useState(true);  // Default to showing insights
  
  // Track which monthly insight panels are expanded
  // Initialize based on initial_filters.month_year if present
  const [expandedInsightMonths, setExpandedInsightMonths] = useState<Set<string>>(() => {
    const initialMonth = data?.initial_filters?.month_year;
    return initialMonth ? new Set([initialMonth]) : new Set<string>();
  });
  
  // Update expanded months when initial_filters changes (e.g., when a specific month is requested)
  React.useEffect(() => {
    const filterMonth = data?.initial_filters?.month_year;
    if (filterMonth) {
      setExpandedInsightMonths(new Set([filterMonth]));
    }
  }, [data?.initial_filters?.month_year]);
  
  // Display mode state
  const displayMode = useDisplayMode();
  
  // Handler to toggle fullscreen mode (for standalone app, just update local state)
  const handleToggleFullscreen = async () => {
    const newMode = displayMode === 'fullscreen' ? 'inline' : 'fullscreen';
    window.displayMode = newMode;
    // Trigger re-render by updating a state if needed
    // For now, just update window directly
    } catch (error) {
      console.error('Error requesting display mode:', error);
    }
  };
  
  // Handler to export data as CSV
  const handleExportCSV = () => {
    if (!data || !currentPivot) return;
    
    const pivot = currentPivot;
    const rows: string[][] = [];
    
    // Header row
    const headerRow = ['Category', ...pivot.months.map(m => formatMonthLabel(m)), 'Total'];
    rows.push(headerRow);
    
    // Data rows
    for (let i = 0; i < pivot.categories.length; i++) {
      const category = pivot.categories[i];
      const amounts = pivot.actuals[i] || [];
      const total = amounts.reduce((sum, val) => sum + val, 0);
      const row = [
        category,
        ...amounts.map(a => a.toFixed(2)),
        total.toFixed(2),
      ];
      rows.push(row);
    }
    
    // Total row
    const monthTotals = pivot.months.map(m => pivot.month_totals[m] || 0);
    const grandTotal = monthTotals.reduce((sum, val) => sum + val, 0);
    rows.push([
      'Total',
      ...monthTotals.map(t => t.toFixed(2)),
      grandTotal.toFixed(2),
    ]);
    
    // Add budget section if budgets exist
    const hasBudgets = pivot.budgets.some(b => b.some(v => v > 0));
    if (hasBudgets) {
      rows.push([]); // Empty row separator
      rows.push(['BUDGETS', ...pivot.months.map(m => formatMonthLabel(m)), 'Total']);
      
      for (let i = 0; i < pivot.categories.length; i++) {
        const category = pivot.categories[i];
        const budgetAmounts = pivot.budgets[i] || [];
        const budgetTotal = budgetAmounts.reduce((sum, val) => sum + val, 0);
        rows.push([
          category,
          ...budgetAmounts.map(b => b.toFixed(2)),
          budgetTotal.toFixed(2),
        ]);
      }
    }
    
    // Convert to CSV string
    const csvContent = rows
      .map(row => row.map(cell => {
        // Escape quotes and wrap in quotes if contains comma
        const escaped = String(cell).replace(/"/g, '""');
        return escaped.includes(',') ? `"${escaped}"` : escaped;
      }).join(','))
      .join('\n');
    
    // Generate filename with date
    const dateStr = new Date().toISOString().split('T')[0];
    const bankStr = data.banks.length === 1 ? data.banks[0] : 'all-banks';
    const filename = `finance-dashboard-${bankStr}-${dateStr}.csv`;
    
    // Use data URL approach which works better in iframe/widget contexts
    // The blob URL approach doesn't work reliably in sandboxed iframes
    const dataUrl = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvContent);
    
    const link = document.createElement('a');
    link.href = dataUrl;
    link.download = filename;
    
    // Firefox requires the anchor to be in the DOM for data URL downloads
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
  
  // Filter state - Initialize with prop or empty string
  // Use state initializer function to only run once when data loads
  const [selectedMonths, setSelectedMonths] = useState<string[]>(() => {
    return data?.initial_filters?.month_year ? [data.initial_filters.month_year] : [];
  });

  // Update selected month if data changes and has initial filters (e.g. re-render from backend)
  React.useEffect(() => {
    if (data?.initial_filters?.month_year) {
      setSelectedMonths([data.initial_filters.month_year]);
    }
  }, [data?.initial_filters?.month_year]);

  // Bank Filter State
  const [selectedBanks, setSelectedBanks] = useState<string[]>(() => {
    return data?.initial_filters?.bank_name ? [data.initial_filters.bank_name] : [];
  });

  React.useEffect(() => {
    if (data?.initial_filters?.bank_name) {
      setSelectedBanks([data.initial_filters.bank_name]);
    }
  }, [data?.initial_filters?.bank_name]);

  // Profile Filter State (Household profiles like "Me", "Partner", "Joint")
  const [selectedProfiles, setSelectedProfiles] = useState<string[]>(() => {
    return data?.initial_filters?.profile ? [data.initial_filters.profile] : [];
  });

  React.useEffect(() => {
    if (data?.initial_filters?.profile) {
      setSelectedProfiles([data.initial_filters.profile]);
    }
  }, [data?.initial_filters?.profile]);

  // Tab state - use default_tab from initial_filters, or default to 'journey'
  const [activeTab, setActiveTab] = useState<TabType>(() => {
    const defaultTab = data?.initial_filters?.default_tab;
    // Validate that defaultTab is a valid TabType, otherwise default to 'journey'
    const validTabs: TabType[] = ['journey', 'overview', 'cashflow', 'trends', 'budget', 'details', 'preferences'];
    return (defaultTab && validTabs.includes(defaultTab as TabType)) ? (defaultTab as TabType) : 'journey';
  });
  
  // Update tab when default_tab changes in data
  React.useEffect(() => {
    const defaultTab = data?.initial_filters?.default_tab;
    if (defaultTab) {
      const validTabs: TabType[] = ['journey', 'overview', 'cashflow', 'trends', 'budget', 'details', 'preferences'];
      if (validTabs.includes(defaultTab as TabType)) {
        setActiveTab(defaultTab as TabType);
      }
    }
  }, [data?.initial_filters?.default_tab]);
  
  // Celebration state for journey milestones
  const [showConfetti, setShowConfetti] = useState(false);
  const [celebrationMilestone, setCelebrationMilestone] = useState<string | null>(null);
  
  // Calculate user progress for journey system
  // Derives progress from dashboard data - counts actual data entities
  const progressState = useMemo((): ProgressState | null => {
    if (!data) return null;
    
    // Count unique bank+month combinations (statement count)
    // Each unique bank+month combo from category_summaries represents one statement
    const bankMonthCombos = new Set<string>();
    if (data.category_summaries) {
      data.category_summaries.forEach(cs => {
        if (cs.bank_name && cs.month_year) {
          bankMonthCombos.add(`${cs.bank_name}|${cs.month_year}`);
        }
      });
    }
    const statementCount = bankMonthCombos.size;
    
    // Count budgets that have actual values set
    const budgetCount = data.pivot?.budgets
      ? data.pivot.budgets.filter(row => row.some(v => v > 0)).length
      : 0;
    
    // Use actual user_settings for progression (only includes values actually set by user)
    // Fall back to banks count if user_settings not available
    const userSettings = data?.user_settings;
    const progressSettings: ProgressInput['settings'] = userSettings ? {
      // Only include functional_currency if it's actually set (not null/undefined)
      ...(userSettings.functional_currency ? { functional_currency: userSettings.functional_currency } : {}),
      ...(userSettings.bank_accounts_count !== undefined && userSettings.bank_accounts_count !== null 
        ? { bank_accounts_count: userSettings.bank_accounts_count } : {}),
      ...(userSettings.onboarding_complete !== undefined && userSettings.onboarding_complete !== null 
        ? { onboarding_complete: userSettings.onboarding_complete } : {}),
    } : {
      // If no user_settings, only include bank_accounts_count from data
      bank_accounts_count: data?.banks?.length || 0,
    };
    
    const progressInput: ProgressInput = {
      settings: progressSettings,
      dataOverview: {
        total_months: data?.available_months?.length || data?.pivot?.months?.length || 0,
        banks: data?.banks?.map(b => ({ name: b })) || [],
        budgets_configured: budgetCount,
      },
      catCount: data?.pivot?.categories?.length || 0,
      parsingCount: data?.banks?.length || 0,
      statementCount: statementCount,
      mutationCount: 1, // Assume some mutations have happened
    };
    
    return calculateProgress(progressInput);
  }, [data]);

  // Handler for claiming milestones
  const handleMilestoneClaim = (milestoneId: string) => {
    setCelebrationMilestone(milestoneId);
    setShowConfetti(true);
    
    // Hide confetti after animation
    setTimeout(() => {
      setShowConfetti(false);
      setCelebrationMilestone(null);
    }, 3000);
  };
  
  // Inline editing state for the details table
  const [isEditingTable, setIsEditingTable] = useState(false);
  const [editedCells, setEditedCells] = useState<Record<string, string>>({});
  const [isMutating, setIsMutating] = useState(false);
  const [changeSummary, setChangeSummary] = useState<ChangeSummary | null>(null);
  const [showChangeBanner, setShowChangeBanner] = useState(false);
  
  // Budget editing state
  const [isEditingBudgets, setIsEditingBudgets] = useState(false);
  const [editedBudgets, setEditedBudgets] = useState<Record<string, string>>({});
  const [isSavingBudgets, setIsSavingBudgets] = useState(false);
  
  // Preferences tab state
  const [preferencesData, setPreferencesData] = useState<PreferencesData | null>(null);
  const [isLoadingPreferences, setIsLoadingPreferences] = useState(false);
  const [preferencesError, setPreferencesError] = useState<string | null>(null);
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);
  const [editedRuleName, setEditedRuleName] = useState('');
  const [editedRulePattern, setEditedRulePattern] = useState('');
  const [editedRuleCategory, setEditedRuleCategory] = useState('');
  const [isSavingPreference, setIsSavingPreference] = useState(false);
  
  // Quick transfer modal state
  const [transferModal, setTransferModal] = useState<{
    open: boolean;
    fromCategory: string;
    fromAmount: number;
    month: string;
  } | null>(null);
  const [transferToCategory, setTransferToCategory] = useState('');
  const [transferAmount, setTransferAmount] = useState('');
  
  
  const rootRef = useIntrinsicHeight();
  const colors = getThemeColors(theme);

  // Apply Bank and Profile Filters to Pivot Data
  const currentPivot = useMemo(() => {
    if (!data) return null;
    if (!data.category_summaries || data.category_summaries.length === 0) return data.pivot;
    if (selectedBanks.length === 0 && selectedProfiles.length === 0) return data.pivot;
    
    return buildBankFilteredPivot(data.pivot, data.category_summaries, selectedBanks, selectedProfiles);
  }, [data, selectedBanks, selectedProfiles]);

  const pivotRows = useMemo(() => {
    if (!currentPivot) return [];
    return buildPivotRowDisplays(currentPivot);
  }, [currentPivot]);

  const allMonthlyFlow = useMemo(() => {
    if (!currentPivot) return [];
    return buildMonthlyFlowSeries(currentPivot);
  }, [currentPivot]);

  // Build budget vs actual series
  const budgetVsActualData = useMemo(() => {
    if (!currentPivot) return [];
    return buildBudgetVsActualSeries(currentPivot, [], selectedMonths);
  }, [currentPivot, selectedMonths]);

  // Budget tab data
  const budgetProgressData = useMemo(() => {
    if (!currentPivot) return [];
    return buildBudgetProgressData(currentPivot);
  }, [currentPivot]);

  const budgetAllocationData = useMemo(() => {
    if (!currentPivot) return [];
    return buildBudgetAllocationData(currentPivot);
  }, [currentPivot]);

  const budgetHealthKPIs = useMemo(() => {
    if (!currentPivot || budgetProgressData.length === 0) {
      return {
        totalBudget: 0,
        totalSpent: 0,
        remainingBudget: 0,
        utilizationPct: 0,
      };
    }

    const totalBudget = budgetProgressData.reduce((sum, d) => sum + d.budget, 0);
    const totalSpent = budgetProgressData.reduce((sum, d) => sum + d.actual, 0);
    const remainingBudget = totalBudget - totalSpent;
    const utilizationPct = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0;

    return {
      totalBudget,
      totalSpent,
      remainingBudget,
      utilizationPct,
    };
  }, [budgetProgressData]);

  // Statement-level insights only (category-level insights removed per issue #88)
  const hasStatementInsights = !!data?.statement_insights?.trim();

  // Handler for mutate_categories tool call
  // Using discriminated union to properly type edit vs transfer operations
  const handleMutateCategories = async (
    operations: Array<
      | {
          type: 'edit';
          category: string;
          new_amount: number;
          note?: string;
        }
      | {
          type: 'transfer';
          from_category: string;
          to_category: string;
          transfer_amount: number;
          note?: string;
        }
    >,
    monthYear?: string,
    bankName?: string
  ) => {
    const activeBankFilter = selectedBanks.length === 1 ? selectedBanks[0] : undefined;
    const activeMonthFilter = selectedMonths.length === 1 ? selectedMonths[0] : undefined;

    setIsMutating(true);
    try {
      // Convert operations to transaction updates
      // For edit operations, we need to find transactions and update them
      // For now, we'll refresh the dashboard after updates
      
      // TODO: Implement proper transaction updates based on operations
      // For now, just refresh the dashboard
      const refreshData = await apiClient.getFinancialData({
        bank_name: bankName || activeBankFilter,
        month_year: monthYear || activeMonthFilter,
      });

      const refreshValidated = dashboardPropsSchema.safeParse(refreshData);
      if (refreshValidated.success) {
        setLocalDashboardData({ ...refreshValidated.data, initial_filters: null });
        setSelectedMonths([]);
        setSelectedBanks([]);
      }

      // Show success message
      setChangeSummary([{
        message: 'Categories updated successfully',
        status: 'success',
        category: 'all',
      }]);
      setShowChangeBanner(true);
      setTimeout(() => setShowChangeBanner(false), 5000);

    } catch (error) {
      console.error('Error mutating categories:', error);
      setChangeSummary([{
        message: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        status: 'error',
        category: 'unknown',
      }]);
      setShowChangeBanner(true);
    } finally {
      setIsMutating(false);
    }
  };

  // Handler for saving budgets via API
  const handleSaveBudgets = async () => {
    // Build budgets array from edited values
    const budgets: Array<{
      category: string;
      amount: number;
      month_year?: string | null;
      currency?: string;
    }> = [];

    // Parse edited budget cells - format is "category__month" => "amount"
    for (const [key, value] of Object.entries(editedBudgets)) {
      const amount = parseFloat(value);
      if (isNaN(amount)) continue;

      const [category, month] = key.split('__');
      if (!category) continue;

      budgets.push({
        category,
        amount: Math.abs(amount), // Budgets are positive
        month_year: month || null, // If no month, it's a default budget
        currency: data?.currency || 'USD',
      });
    }

    if (budgets.length === 0) {
      setIsEditingBudgets(false);
      setEditedBudgets({});
      return;
    }

    setIsSavingBudgets(true);
    try {
      await apiClient.saveBudget(budgets);

      // Refresh dashboard to get updated budget data
      const refreshData = await apiClient.getFinancialData();

      const refreshValidated = dashboardPropsSchema.safeParse(refreshData);
      if (refreshValidated.success) {
        setLocalDashboardData({ ...refreshValidated.data, initial_filters: null });
        setSelectedMonths([]);
        setSelectedBanks([]);
      }

      setChangeSummary([{
        message: `Successfully saved ${budgets.length} budget(s)`,
        status: 'success',
        category: budgets.map(b => b.category).join(', '),
      }]);
      setShowChangeBanner(true);
      setTimeout(() => setShowChangeBanner(false), 5000);

    } catch (error) {
      console.error('Error saving budgets:', error);
      setChangeSummary([{
        message: `Error saving budgets: ${error instanceof Error ? error.message : 'Unknown error'}`,
        status: 'error',
        category: 'unknown',
      }]);
      setShowChangeBanner(true);
    } finally {
      setIsSavingBudgets(false);
      setIsEditingBudgets(false);
      setEditedBudgets({});
    }
  };

  // Handler for budget cell edits
  const handleBudgetCellEdit = (category: string, month: string, value: string) => {
    const key = `${category}__${month}`;
    setEditedBudgets(prev => ({ ...prev, [key]: value }));
  };

  // Get budget cell value (edited or from data)
  const getBudgetCellValue = (category: string, month: string): number => {
    const key = `${category}__${month}`;
    if (editedBudgets[key] !== undefined) {
      const parsed = parseFloat(editedBudgets[key]);
      return isNaN(parsed) ? 0 : parsed;
    }
    // Get from pivot data
    const row = pivotRows.find(r => r.category === category);
    const monthData = row?.monthly.find(m => m.month === month);
    return monthData?.budget ?? 0;
  };
  
  // Handler for opening transfer modal
  // Supports both single-month and multi-month selections
  const handleOpenTransferModal = (fromCategory: string, amount: number, month?: string) => {
    // If no month specified, use the latest selected month (or last month in pivot)
    const targetMonth = month || 
      (selectedMonths.length > 0 ? selectedMonths[selectedMonths.length - 1] : null) ||
      (currentPivot?.months?.length ? currentPivot.months[currentPivot.months.length - 1] : null);
    
    if (!targetMonth || !currentPivot) return;
    
    // Get the month-specific amount for this category
    const categoryIndex = currentPivot.categories.indexOf(fromCategory);
    const monthIndex = currentPivot.months.indexOf(targetMonth);
    const monthSpecificAmount = categoryIndex >= 0 && monthIndex >= 0 
      ? (currentPivot.actuals[categoryIndex]?.[monthIndex] ?? 0)
      : amount;
    
    setTransferModal({
      open: true,
      fromCategory,
      fromAmount: monthSpecificAmount,
      month: targetMonth,
    });
    setTransferToCategory('');
    setTransferAmount(Math.abs(monthSpecificAmount).toFixed(2));
  };
  
  // Handler for changing month in transfer modal
  const handleTransferMonthChange = (newMonth: string) => {
    if (!transferModal || !currentPivot) return;
    
    // Get the month-specific amount for this category
    const categoryIndex = currentPivot.categories.indexOf(transferModal.fromCategory);
    const monthIndex = currentPivot.months.indexOf(newMonth);
    const monthSpecificAmount = categoryIndex >= 0 && monthIndex >= 0 
      ? (currentPivot.actuals[categoryIndex]?.[monthIndex] ?? 0)
      : 0;
    
    setTransferModal({
      ...transferModal,
      month: newMonth,
      fromAmount: monthSpecificAmount,
    });
    // Reset transfer amount to the full amount available for the new month
    setTransferAmount(Math.abs(monthSpecificAmount).toFixed(2));
  };
  
  // Handler for executing transfer
  const handleExecuteTransfer = async () => {
    if (!transferModal || !transferToCategory || !transferAmount) return;
    
    const amount = parseFloat(transferAmount);
    if (isNaN(amount) || amount <= 0) return;
    
    await handleMutateCategories([{
      type: 'transfer',
      from_category: transferModal.fromCategory,
      to_category: transferToCategory,
      transfer_amount: amount,
      note: `Quick transfer from ${transferModal.fromCategory} to ${transferToCategory}`,
    }], transferModal.month);
    
    setTransferModal(null);
    setTransferToCategory('');
    setTransferAmount('');
  };

  // Handler for loading preferences when Preferences tab is selected
  const loadPreferences = async () => {
    setIsLoadingPreferences(true);
    setPreferencesError(null);

    try {
      // Fetch preferences using API client
      const [settingsData, catData, listData] = await Promise.all([
        apiClient.getPreferences('settings' as any).catch(() => ({})),
        apiClient.getPreferences('categorization').catch(() => ({})),
        apiClient.getPreferences('list' as any).catch(() => ({})),
      ]);

      setPreferencesData({
        settings: (settingsData as any)?.settings || null,
        categorization_rules: (catData as any)?.preferences || [],
        parsing_banks: (listData as any)?.summary?.parsing?.banks || [],
      });
    } catch (error) {
      console.error('Error loading preferences:', error);
      setPreferencesError(error instanceof Error ? error.message : 'Failed to load preferences');
    } finally {
      setIsLoadingPreferences(false);
    }
  };

  // Load preferences when switching to preferences tab
  React.useEffect(() => {
    if (activeTab === 'preferences' && !preferencesData && !isLoadingPreferences) {
      loadPreferences();
    }
  }, [activeTab]);

  // Handler for saving a categorization rule edit
  const handleSaveRuleEdit = async (ruleId: string) => {
    setIsSavingPreference(true);
    try {
      await apiClient.savePreferences([{
        preference_id: ruleId,
        name: editedRuleName,
        rule: {
          pattern: editedRulePattern,
          category: editedRuleCategory,
        },
      }], 'categorization');
      
      // Refresh preferences
      await loadPreferences();
      setEditingRuleId(null);
    } catch (error) {
      console.error('Error saving rule:', error);
    } finally {
      setIsSavingPreference(false);
    }
  };

  // Handler for deleting a categorization rule (disable it)
  const handleDeleteRule = async (ruleId: string) => {
    if (!confirm('Are you sure you want to delete this rule?')) return;
    
    setIsSavingPreference(true);
    try {
      // TODO: Implement delete rule API endpoint
      // For now, just refresh after the operation
      await loadPreferences();
    } catch (error) {
      console.error('Error deleting rule:', error);
    } finally {
      setIsSavingPreference(false);
    }
  };

  // Start editing a rule
  const startEditingRule = (rule: CategorizationRule) => {
    setEditingRuleId(rule.id);
    setEditedRuleName(rule.name);
    setEditedRulePattern(rule.rule?.pattern || '');
    setEditedRuleCategory(rule.rule?.category || '');
  };

  // Cancel editing
  const cancelEditingRule = () => {
    setEditingRuleId(null);
    setEditedRuleName('');
    setEditedRulePattern('');
    setEditedRuleCategory('');
  };

  // Filter data based on selected month
  const filteredPivotRows = useMemo(() => {
    if (!currentPivot) return pivotRows;
    if (selectedMonths.length === 0) return pivotRows;

    return pivotRows
      .map(row => {
        const filteredMonthly = row.monthly.filter(m => selectedMonths.includes(m.month));
        if (filteredMonthly.length === 0) return null;

        // Recalculate totals for filtered months
        const totalActual = filteredMonthly.reduce((sum, m) => sum + m.actual, 0);
        const totalBudget = filteredMonthly.reduce((sum, m) => sum + m.budget, 0);
        const classification = classifyCategory(row.category, totalActual);
        const actualForVariance = classification === 'outflows' ? Math.abs(totalActual) : totalActual;
        const budgetForVariance = classification === 'outflows' ? Math.abs(totalBudget) : totalBudget;
        const variance = actualForVariance - budgetForVariance;
        const variancePct = budgetForVariance ? (variance / Math.abs(budgetForVariance)) * 100 : 0;

        return {
          ...row,
          monthly: filteredMonthly,
          totalActual,
          totalBudget,
          variance,
          variancePct,
        };
      })
      .filter((row): row is PivotRowDisplay => row !== null);
  }, [currentPivot, pivotRows, selectedMonths]);

  // Recalculate metrics based on filtered data
  const filteredMetrics = useMemo(() => {
    if (!data) return null;
    // ALWAYS calculate from filteredPivotRows to respect bank/month filters
    // If no filters are applied, filteredPivotRows is same as all rows, so calculation is valid

    // Calculate metrics from filtered pivot rows
    const inflows = filteredPivotRows
      .filter(r => classifyCategory(r.category, r.totalActual) === 'inflows')
      .reduce((sum, r) => sum + r.totalActual, 0);

    const outflows = Math.abs(filteredPivotRows
      .filter(r => classifyCategory(r.category, r.totalActual) === 'outflows')
      .reduce((sum, r) => sum + r.totalActual, 0));

    const internalTransfers = filteredPivotRows
      .filter(r => classifyCategory(r.category, r.totalActual) === 'internal_transfers')
      .reduce((sum, r) => sum + r.totalActual, 0);

    const netCash = inflows - outflows + internalTransfers;

    // Calculate budget coverage
    const totalBudget = filteredPivotRows.reduce((sum, r) => sum + Math.abs(r.totalBudget), 0);
    const budgetCoveragePct = totalBudget > 0 ? (Math.abs(outflows) / totalBudget) * 100 : 0;

    return {
      ...data.metrics,
      inflows,
      outflows: -outflows, // Keep negative for display
      internal_transfers: internalTransfers,
      net_cash: netCash,
      budget_coverage_pct: budgetCoveragePct,
      month_over_month_delta: null, // Not easily applicable for multi-select/bank filtered
      month_over_month_pct: null,
    };
  }, [data, filteredPivotRows]);

  // Filter monthly flow for trends
  const monthlyFlow = useMemo(() => {
    if (!currentPivot) return allMonthlyFlow;
    if (selectedMonths.length === 0) return allMonthlyFlow;

    // Filter flow points to match selected months
    return allMonthlyFlow.filter(pt => selectedMonths.includes(pt.month));
  }, [allMonthlyFlow, selectedMonths, currentPivot]);

  // Calculate trend insights using filtered flow
  const trendInsights = useMemo(() => {
    if (!currentPivot || monthlyFlow.length === 0) return null;
    return calculateTrendInsights(monthlyFlow, currentPivot, selectedMonths);
  }, [currentPivot, monthlyFlow, selectedMonths]);

  // Filter months for comparison chart
  const comparisonMonths = useMemo(() => {
    const months = currentPivot?.months ?? [];

    if (selectedMonths.length === 0) {
      // Show last 3 months if no filter
      return months.slice(-3);
    }

    // Show selected months, sorted chronologically
    return months.filter(m => selectedMonths.includes(m));
  }, [selectedMonths, currentPivot]);

  const originalCellValues = useMemo(() => {
    if (!currentPivot) return {};
    const valueMap: Record<string, number> = {};
    filteredPivotRows.forEach(row => {
      currentPivot.months.forEach(month => {
        const monthData = row.monthly.find(m => m.month === month);
        valueMap[`${row.category}__${month}`] = monthData?.actual ?? 0;
      });
    });
    return valueMap;
  }, [filteredPivotRows, currentPivot]);

  const getCellValue = React.useCallback(
    (category: string, month: string) => {
      const key = `${category}__${month}`;
      const edited = editedCells[key];
      if (edited !== undefined) {
        const parsed = parseFloat(edited);
        if (!Number.isNaN(parsed)) {
          return parsed;
        }
      }
      return originalCellValues[key] ?? 0;
    },
    [editedCells, originalCellValues]
  );

  const handleCellEdit = (category: string, month: string, value: string) => {
    setEditedCells(prev => ({ ...prev, [`${category}__${month}`]: value }));
  };

  const handleCancelInlineEdits = () => {
    setIsEditingTable(false);
    setEditedCells({});
  };

  const handleSaveInlineEdits = async () => {
    if (isMutating) return;

    const opsByMonth: Record<string, Array<{ type: 'edit'; category: string; new_amount: number }>> = {};

    Object.entries(editedCells).forEach(([key, value]) => {
      const [category, month] = key.split('__');
      if (!category || !month) return;
      if (value.trim() === '') return;

      const parsed = parseFloat(value);
      if (Number.isNaN(parsed)) return;

      const original = originalCellValues[key] ?? 0;
      if (Math.abs(parsed - original) < 0.0001) return;

      if (!opsByMonth[month]) opsByMonth[month] = [];
      opsByMonth[month].push({
        type: 'edit',
        category,
        new_amount: parsed,
      });
    });

    const monthEntries = Object.entries(opsByMonth);

    if (monthEntries.length === 0) {
      handleCancelInlineEdits();
      return;
    }

    const bankForOps = selectedBanks.length === 1 ? selectedBanks[0] : undefined;

    for (const [monthYear, operations] of monthEntries) {
      await handleMutateCategories(operations, monthYear, bankForOps);
    }

    handleCancelInlineEdits();
  };

  // Calculate P&L structure - inflows, outflows, and internal transfers as separate sections
  const plStructure = useMemo(() => {
    if (!currentPivot) return null;
    
    const inflowCategories = filteredPivotRows
      .filter(r => classifyCategory(r.category, r.totalActual) === 'inflows')
      .map(cat => ({ label: cat.category, value: cat.totalActual }));
    const outflowCategories = filteredPivotRows
      .filter(r => classifyCategory(r.category, r.totalActual) === 'outflows')
      .map(cat => ({ label: cat.category, value: Math.abs(cat.totalActual) }));
    const internalTransferCategories = filteredPivotRows
      .filter(r => classifyCategory(r.category, r.totalActual) === 'internal_transfers')
      .map(cat => ({ label: cat.category, value: cat.totalActual }));

    const totalInflowsValue = inflowCategories.reduce((sum, cat) => sum + cat.value, 0);
    const totalOutflowsValue = outflowCategories.reduce((sum, cat) => sum + cat.value, 0);
    const netInternalTransfers = internalTransferCategories.reduce((sum, cat) => sum + cat.value, 0);

    // Net cash = inflows - outflows + net internal transfers
    const netCash = totalInflowsValue - totalOutflowsValue + netInternalTransfers;

    return {
      inflows: {
        total: totalInflowsValue,
        categories: inflowCategories.sort((a, b) => Math.abs(b.value) - Math.abs(a.value)),
      },
      outflows: {
        total: totalOutflowsValue,
        categories: outflowCategories.sort((a, b) => Math.abs(b.value) - Math.abs(a.value)),
      },
      internalTransfers: {
        total: netInternalTransfers,
        categories: internalTransferCategories.sort((a, b) => Math.abs(b.value) - Math.abs(a.value)),
      },
      netCash,
    };
  }, [data, filteredPivotRows, selectedMonths]);

  // Top spending categories for bar chart
  const topSpendingCategories = useMemo(() => {
    if (!data) return [];

    const outflowsList = filteredPivotRows
      .filter(r => classifyCategory(r.category, r.totalActual) === 'outflows')
      .map(r => ({
        label: r.category,
        value: Math.abs(r.totalActual),
        color: colors.chart.neutral,
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
    
    if (outflowsList.length > 0) {
      outflowsList[0].color = colors.primary; // Largest in red
    }
    
    return outflowsList;
  }, [filteredPivotRows, colors, data]);

  // Donut chart data
  const donutData = useMemo(() => {
    if (!data) return [];

    const inflowValue = filteredPivotRows
      .filter(r => classifyCategory(r.category, r.totalActual) === 'inflows')
      .reduce((sum, r) => sum + r.totalActual, 0);
    
    const outflowValue = filteredPivotRows
      .filter(r => classifyCategory(r.category, r.totalActual) === 'outflows')
      .reduce((sum, r) => sum + Math.abs(r.totalActual), 0);
    
    return [
      { label: 'Inflows', value: inflowValue, color: colors.chart.inflow },
      { label: 'Outflows', value: outflowValue, color: colors.chart.outflow },
    ].filter(d => d.value > 0);
  }, [filteredPivotRows, colors, data]);

  // Coverage text
  const coverageText = useMemo(() => {
    const coverage = data?.coverage;
    return coverage?.start && coverage?.end
      ? `${formatDate(coverage.start)} → ${formatDate(coverage.end)}`
      : 'Not available';
  }, [data?.coverage?.start, data?.coverage?.end]);

  const tabs: Array<{ id: TabType; label: string; icon?: string }> = [
    { id: 'journey', label: 'Journey', icon: '🏔️' },
    { id: 'overview', label: 'Overview' },
    { id: 'cashflow', label: 'Cashflow P&L' },
    { id: 'trends', label: 'Trends' },
    { id: 'budget', label: 'Budget' },
    { id: 'details', label: 'Details' },
    { id: 'preferences', label: 'Preferences' },
  ];

  // Error State
  if (error) {
    return (
      <div
        ref={rootRef}
        style={{
          fontFamily: TYPOGRAPHY.fontFamily,
          padding: SPACING.lg,
          color: colors.text.negative,
          textAlign: 'center',
        }}
      >
        <div style={{ fontSize: TYPOGRAPHY.sizes.md, fontWeight: TYPOGRAPHY.weights.medium }}>
          {error}
        </div>
      </div>
    );
  }

  // Loading State
  if (!data || !filteredMetrics || !plStructure || !currentPivot) {
    return (
      <div
        ref={rootRef}
        style={{
          fontFamily: TYPOGRAPHY.fontFamily,
          padding: SPACING.xxxl,
          color: colors.text.tertiary,
          textAlign: 'center',
        }}
      >
        <div style={{ fontSize: TYPOGRAPHY.sizes.md }}>
          Waiting for dashboard data&hellip;
        </div>
      </div>
    );
  }

  const { banks, currency } = data;
  const pivot = currentPivot;

  return (
    <div
      ref={rootRef}
      style={{
        fontFamily: TYPOGRAPHY.fontFamily,
        background: colors.bg.primary,
        color: colors.text.primary,
        minHeight: '100%',
      }}
    >
      {/* Header */}
      <header
        style={{
          padding: SPACING.sm,
          borderBottom: `1px solid ${colors.border.default}`,
          background: colors.bg.elevated,
        }}
      >
        <div style={{ marginBottom: SPACING.xs, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1
              style={{
                fontSize: TYPOGRAPHY.sizes.lg,
                fontWeight: TYPOGRAPHY.weights.bold,
                margin: 0,
                marginBottom: 2,
                color: colors.text.primary,
              }}
            >
              Financial Dashboard
            </h1>
            <div
              style={{
                fontSize: TYPOGRAPHY.sizes.xs,
                color: colors.text.secondary,
              }}
            >
              {currency} • {banks.length > 0 ? banks.join(', ') : 'All Banks'} • {coverageText}
            </div>
          </div>
          <div style={{ display: 'flex', gap: SPACING.sm }}>
            <button
              onClick={handleExportCSV}
              style={{
                padding: `${SPACING.sm}px ${SPACING.md}px`,
                fontSize: TYPOGRAPHY.sizes.sm,
                fontWeight: TYPOGRAPHY.weights.medium,
                color: colors.text.primary,
                background: colors.bg.secondary,
                border: `1px solid ${colors.border.default}`,
                borderRadius: 6,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: SPACING.xs,
              }}
              title="Export to CSV"
            >
              <span style={{ fontSize: 14 }}>↓</span>
              <span>Export</span>
            </button>
            {window.openai?.requestDisplayMode && (
              <button
                onClick={handleToggleFullscreen}
                style={{
                  padding: `${SPACING.sm}px ${SPACING.md}px`,
                  fontSize: TYPOGRAPHY.sizes.sm,
                  fontWeight: TYPOGRAPHY.weights.medium,
                  color: colors.text.primary,
                  background: colors.bg.secondary,
                  border: `1px solid ${colors.border.default}`,
                  borderRadius: 6,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: SPACING.xs,
                }}
                title={displayMode === 'fullscreen' ? 'Exit fullscreen' : 'Expand to fullscreen'}
              >
                {displayMode === 'fullscreen' ? (
                  <>
                    <span style={{ fontSize: 14 }}>↙</span>
                    <span>Exit</span>
                  </>
                ) : (
                  <>
                    <span style={{ fontSize: 14 }}>⤢</span>
                    <span>Expand</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        {/* Filter Controls */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: SPACING.sm,
            alignItems: 'center',
            paddingTop: SPACING.xs,
            borderTop: `1px solid ${colors.border.default}`,
          }}
        >
          {/* Month Selector - Use available_months for ALL options, fallback to pivot.months */}
          <MultiSelect
            value={selectedMonths}
            onChange={setSelectedMonths}
            options={(data.available_months?.length ? data.available_months : pivot.months).map(m => ({ value: m, label: formatMonthLabel(m) }))}
            theme={theme}
            placeholder="All Months"
          />

          {/* Bank Selector - Use available_banks for ALL options, fallback to banks */}
          {(data.available_banks?.length || banks.length) > 1 && (
            <MultiSelect
              value={selectedBanks}
              onChange={setSelectedBanks}
              options={(data.available_banks?.length ? data.available_banks : banks).map(b => ({ value: b, label: b }))}
              theme={theme}
              placeholder="All Banks"
            />
          )}

          {/* Profile Selector - Show only if profiles exist */}
          {(data.available_profiles?.length ?? 0) > 0 && (
            <MultiSelect
              value={selectedProfiles}
              onChange={setSelectedProfiles}
              options={(data.available_profiles ?? []).map(p => ({ value: p, label: p }))}
              theme={theme}
              placeholder="All Profiles"
            />
          )}

          <div
            style={{
              fontSize: TYPOGRAPHY.sizes.xs,
              color: colors.text.tertiary,
              marginLeft: SPACING.sm,
            }}
            title="Select filters to update dashboard data."
          >
            {selectedMonths.length > 0
              ? `Months: ${selectedMonths.length} selected`
              : 'Months: All'}
            {selectedBanks.length > 0
              ? ` • Banks: ${selectedBanks.length} selected`
              : ' • Banks: All'}
            {selectedProfiles.length > 0
              ? ` • Profiles: ${selectedProfiles.length} selected`
              : ''}
          </div>
        </div>

        {/* Journey Status Bar - Compact progress display */}
        {progressState && activeTab !== 'journey' && (
          <div style={{ marginTop: SPACING.md }}>
            <StatusBar 
              progress={progressState}
              onJourneyClick={() => setActiveTab('journey')}
              theme={theme}
              compact={false}
            />
          </div>
        )}
      </header>

      {/* Tabs */}
      <div
        style={{
          display: 'flex',
          borderBottom: `2px solid ${colors.border.default}`,
          background: colors.bg.elevated,
        }}
      >
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: `${SPACING.md}px ${SPACING.xl}px`,
              background: activeTab === tab.id ? colors.bg.primary : 'transparent',
              border: 'none',
              borderBottom: activeTab === tab.id ? `3px solid ${colors.primary}` : '3px solid transparent',
              color: activeTab === tab.id ? colors.text.primary : colors.text.secondary,
              fontSize: TYPOGRAPHY.sizes.base,
              fontWeight: activeTab === tab.id ? TYPOGRAPHY.weights.semibold : TYPOGRAPHY.weights.normal,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              display: 'flex',
              alignItems: 'center',
              gap: SPACING.xs,
            }}
          >
            {tab.icon && <span>{tab.icon}</span>}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Confetti Celebration Effect */}
      {showConfetti && <Confetti theme={theme} />}

      {/* Tab Content */}
      <div style={{ padding: activeTab === 'journey' ? 0 : SPACING.xl }}>
        {/* JOURNEY TAB */}
        {activeTab === 'journey' && progressState && (
          <div style={{ height: 'calc(100vh - 240px)', minHeight: 600 }}>
            <JourneyPath 
              progress={progressState}
              onMilestoneClaim={handleMilestoneClaim}
              theme={theme}
            />
          </div>
        )}

        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div>
            {/* KPI Strip */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: SPACING.lg,
                marginBottom: SPACING.xxxl,
              }}
            >
              <Card theme={theme} padding="lg">
                <MetricTile
                  label="Total Inflows"
                  value={formatCurrency(filteredMetrics.inflows, currency)}
                  theme={theme}
                />
              </Card>
              <Card theme={theme} padding="lg">
                <MetricTile
                  label="Total Outflows"
                  value={formatCurrency(filteredMetrics.outflows, currency)}
                  theme={theme}
                  isNegative
                />
              </Card>
              <Card theme={theme} padding="lg">
                <MetricTile
                  label="Internal Transfers"
                  value={formatCurrency(filteredMetrics.internal_transfers, currency)}
                  theme={theme}
                />
              </Card>
              <Card theme={theme} padding="lg">
                <MetricTile
                  label="Net Cash Result"
                  value={formatCurrency(filteredMetrics.net_cash, currency)}
                  subtitle={filteredMetrics.month_over_month_delta !== null && filteredMetrics.month_over_month_delta !== undefined
                    ? `${filteredMetrics.month_over_month_delta >= 0 ? '+' : ''}${formatCurrency(filteredMetrics.month_over_month_delta, currency)} vs last month`
                    : undefined}
                  theme={theme}
                  isNegative={filteredMetrics.net_cash < 0}
                  trend={filteredMetrics.month_over_month_delta !== null && filteredMetrics.month_over_month_delta !== undefined
                    ? (filteredMetrics.month_over_month_delta >= 0 ? 'up' : 'down')
                    : undefined}
                />
              </Card>
              {filteredMetrics.month_over_month_delta !== null && (
                <Card theme={theme} padding="lg">
                  <MetricTile
                    label="MoM Change"
                    value={formatCurrency(filteredMetrics.month_over_month_delta, currency)}
                    theme={theme}
                    isNegative={filteredMetrics.month_over_month_delta < 0}
                    trend={filteredMetrics.month_over_month_delta >= 0 ? 'up' : 'down'}
                  />
                </Card>
              )}
              <Card theme={theme} padding="lg">
                <MetricTile
                  label="Budget Coverage"
                  value={`${Math.min(Math.max(filteredMetrics.budget_coverage_pct, 0), 100).toFixed(1)}%`}
                  theme={theme}
                />
              </Card>
            </div>

            {/* Charts Row */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                gap: SPACING.xl,
                marginBottom: SPACING.xxxl,
              }}
            >
              {/* Donut Chart */}
              {donutData.length > 0 && (
                <Card theme={theme} padding="xl">
                  <h3
                    style={{
                      fontSize: TYPOGRAPHY.sizes.lg,
                      fontWeight: TYPOGRAPHY.weights.semibold,
                      margin: 0,
                      marginBottom: SPACING.md,
                      color: colors.text.primary,
                    }}
                  >
                    Inflows vs Outflows
                  </h3>
                  <DonutChart data={donutData} theme={theme} size={220} />
                </Card>
              )}

              {/* Top Spending Categories */}
              {topSpendingCategories.length > 0 && (
                <Card theme={theme} padding="xl">
                  <h3
                    style={{
                      fontSize: TYPOGRAPHY.sizes.lg,
                      fontWeight: TYPOGRAPHY.weights.semibold,
                      margin: 0,
                      marginBottom: SPACING.md,
                      color: colors.text.primary,
                    }}
                  >
                    Top Spending Categories
                  </h3>
                  <HorizontalBarChart
                    data={topSpendingCategories}
                    theme={theme}
                    currency={currency}
                    height={300}
                  />
                </Card>
              )}
            </div>

            {/* Insights (statement + category-level) */}
            {data && (
              <Card theme={theme} padding="lg" style={{ marginTop: SPACING.xl }}>
                {/* Master collapse/expand toggle */}
                <button
                  onClick={() => setShowInsights(prev => !prev)}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    width: '100%',
                    background: 'transparent',
                    border: 'none',
                    color: colors.text.primary,
                    fontSize: TYPOGRAPHY.sizes.lg,
                    fontWeight: TYPOGRAPHY.weights.semibold,
                    padding: 0,
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                  aria-expanded={showInsights}
                  aria-controls="insights-panel"
                >
                  <span>Insights (click to {showInsights ? 'hide' : 'show'})</span>
                  <span style={{ fontSize: TYPOGRAPHY.sizes.md }}>
                    {showInsights ? '▾' : '▸'}
                  </span>
                </button>

                {showInsights && (
                  <div
                    id="insights-panel"
                    style={{
                      marginTop: SPACING.md,
                      fontSize: TYPOGRAPHY.sizes.base,
                      color: colors.text.primary,
                      lineHeight: 1.6,
                    }}
                  >
                    {hasStatementInsights ? (
                      (() => {
                        const monthlyInsights = parseInsightsByMonth(data.statement_insights!);
                        
                        // If no monthly structure found, render as single block
                        if (monthlyInsights.length === 0) {
                          return (
                            <div style={{ color: colors.text.secondary }}>
                              {data.statement_insights}
                            </div>
                          );
                        }
                        
                        // Toggle helpers
                        const toggleMonth = (monthKey: string) => {
                          setExpandedInsightMonths(prev => {
                            const next = new Set(prev);
                            if (next.has(monthKey)) {
                              next.delete(monthKey);
                            } else {
                              next.add(monthKey);
                            }
                            return next;
                          });
                        };
                        
                        const expandAll = () => {
                          setExpandedInsightMonths(new Set(monthlyInsights.map(m => m.monthKey)));
                        };
                        
                        const collapseAll = () => {
                          setExpandedInsightMonths(new Set());
                        };
                        
                        const allExpanded = monthlyInsights.every(m => expandedInsightMonths.has(m.monthKey));
                        const noneExpanded = expandedInsightMonths.size === 0;
                        
                        return (
                          <div>
                            {/* Expand/Collapse All controls */}
                            <div
                              style={{
                                display: 'flex',
                                gap: SPACING.sm,
                                marginBottom: SPACING.md,
                                justifyContent: 'flex-end',
                              }}
                            >
                              <button
                                onClick={expandAll}
                                disabled={allExpanded}
                                style={{
                                  fontSize: TYPOGRAPHY.sizes.xs,
                                  color: allExpanded ? colors.text.tertiary : colors.primary,
                                  background: 'transparent',
                                  border: 'none',
                                  cursor: allExpanded ? 'default' : 'pointer',
                                  padding: `${SPACING.xs}px ${SPACING.sm}px`,
                                  textDecoration: allExpanded ? 'none' : 'underline',
                                }}
                              >
                                Expand All
                              </button>
                              <span style={{ color: colors.text.tertiary }}>|</span>
                              <button
                                onClick={collapseAll}
                                disabled={noneExpanded}
                                style={{
                                  fontSize: TYPOGRAPHY.sizes.xs,
                                  color: noneExpanded ? colors.text.tertiary : colors.primary,
                                  background: 'transparent',
                                  border: 'none',
                                  cursor: noneExpanded ? 'default' : 'pointer',
                                  padding: `${SPACING.xs}px ${SPACING.sm}px`,
                                  textDecoration: noneExpanded ? 'none' : 'underline',
                                }}
                              >
                                Collapse All
                              </button>
                            </div>
                            
                            {/* Monthly insight panels */}
                            {monthlyInsights.map((insight) => (
                              <MonthlyInsightPanel
                                key={insight.monthKey}
                                insight={insight}
                                isExpanded={expandedInsightMonths.has(insight.monthKey)}
                                onToggle={() => toggleMonth(insight.monthKey)}
                                theme={theme}
                              />
                            ))}
                          </div>
                        );
                      })()
                    ) : (
                      <div style={{ color: colors.text.secondary }}>
                        No insights saved yet. Insights will appear here after processing a statement.
                      </div>
                    )}
                  </div>
                )}
              </Card>
            )}
          </div>
        )}

        {/* CASHFLOW P&L TAB */}
        {activeTab === 'cashflow' && (
          <div>
            <Card theme={theme} padding="lg">
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  fontSize: TYPOGRAPHY.sizes.sm,
                }}
              >
                <thead>
                  <tr style={{ borderBottom: `2px solid ${colors.border.emphasis}` }}>
                    <th style={{ textAlign: 'left', padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.secondary }}>
                      Category
                    </th>
                    <th style={{ textAlign: 'right', padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.secondary }}>
                      Selected Total
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {/* Inflows Section */}
                  <tr>
                    <td colSpan={2} style={{ padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.primary, background: colors.bg.subtle }}>
                      Inflows
                    </td>
                  </tr>
                  {plStructure.inflows.categories.map(cat => (
                    <tr key={`inflow-${cat.label}`} style={{ borderTop: `1px solid ${colors.border.default}` }}>
                      <td style={{ padding: SPACING.md, color: colors.text.primary }}>
                        {cat.label}
                      </td>
                      <td style={{ textAlign: 'right', padding: SPACING.md, color: colors.text.primary }}>
                        {formatCurrency(cat.value, currency)}
                      </td>
                    </tr>
                  ))}
                  <tr style={{ borderTop: `1px solid ${colors.border.default}`, borderBottom: `2px solid ${colors.border.emphasis}` }}>
                    <td style={{ padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.bold, color: colors.text.primary, background: colors.bg.total }}>
                      Total Inflows
                    </td>
                    <td style={{ textAlign: 'right', padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.bold, color: colors.text.primary, background: colors.bg.total }}>
                      {formatCurrency(plStructure.inflows.total, currency)}
                    </td>
                  </tr>

                  {/* Outflows Section */}
                  <tr>
                    <td colSpan={2} style={{ padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.primary, background: colors.bg.subtle, paddingTop: SPACING.lg }}>
                      Outflows
                    </td>
                  </tr>
                  {plStructure.outflows.categories.map(cat => (
                    <tr key={`outflow-${cat.label}`} style={{ borderTop: `1px solid ${colors.border.default}` }}>
                      <td style={{ padding: SPACING.md, color: colors.text.primary }}>
                        {cat.label}
                      </td>
                      <td style={{ textAlign: 'right', padding: SPACING.md, color: colors.text.negative }}>
                        {formatCurrency(-cat.value, currency)}
                      </td>
                    </tr>
                  ))}
                  <tr style={{ borderTop: `1px solid ${colors.border.default}`, borderBottom: `2px solid ${colors.border.emphasis}` }}>
                    <td style={{ padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.bold, color: colors.text.primary, background: colors.bg.total }}>
                      Total Outflows
                    </td>
                    <td style={{ textAlign: 'right', padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.bold, color: colors.text.negative, background: colors.bg.total }}>
                      {formatCurrency(-plStructure.outflows.total, currency)}
                    </td>
                  </tr>

                  {/* Net Internal Transfers Section */}
                  <tr>
                    <td colSpan={2} style={{ padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.primary, background: colors.bg.subtle, paddingTop: SPACING.lg }}>
                      Net Internal Transfers
                    </td>
                  </tr>
                  {plStructure.internalTransfers.categories.length > 0 ? (
                    plStructure.internalTransfers.categories.map(cat => (
                      <tr key={`transfer-${cat.label}`} style={{ borderTop: `1px solid ${colors.border.default}` }}>
                        <td style={{ padding: SPACING.md, color: colors.text.primary }}>
                          {cat.label}
                        </td>
                        <td style={{ textAlign: 'right', padding: SPACING.md, color: cat.value < 0 ? colors.text.negative : colors.text.primary }}>
                          {formatCurrency(cat.value, currency)}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr style={{ borderTop: `1px solid ${colors.border.default}` }}>
                      <td colSpan={2} style={{ padding: SPACING.md, color: colors.text.secondary, fontStyle: 'italic' }}>
                        No internal transfers
                      </td>
                    </tr>
                  )}
                  <tr style={{ borderTop: `1px solid ${colors.border.default}`, borderBottom: `2px solid ${colors.border.emphasis}` }}>
                    <td style={{ padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.bold, color: colors.text.primary, background: colors.bg.total }}>
                      Net Internal Transfers
                    </td>
                    <td style={{ textAlign: 'right', padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.bold, color: plStructure.internalTransfers.total < 0 ? colors.text.negative : colors.text.primary, background: colors.bg.total }}>
                      {formatCurrency(plStructure.internalTransfers.total, currency)}
                    </td>
                  </tr>

                  {/* Net Cash Result */}
                  <tr style={{ borderTop: `3px solid ${colors.border.emphasis}` }}>
                    <td style={{ padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.bold, fontSize: TYPOGRAPHY.sizes.md, color: colors.text.primary, background: colors.bg.total }}>
                      Net Cash Result
                    </td>
                    <td style={{ textAlign: 'right', padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.bold, fontSize: TYPOGRAPHY.sizes.md, color: plStructure.netCash < 0 ? colors.text.negative : colors.text.primary, background: colors.bg.total }}>
                      {formatCurrency(plStructure.netCash, currency)}
                    </td>
                  </tr>
                </tbody>
              </table>
            </Card>
          </div>
        )}

        {/* TRENDS TAB */}
        {activeTab === 'trends' && (
          <div>
            {/* Key Insights Row */}
            {trendInsights && (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: SPACING.lg,
                  marginBottom: SPACING.xxl,
                }}
              >
                <InsightCard
                  title="Savings Rate"
                  value={`${trendInsights.savingsRate.toFixed(0)}%`}
                  trend={trendInsights.savingsRate >= 15 ? 'up' : trendInsights.savingsRate >= 0 ? 'neutral' : 'down'}
                  trendLabel={trendInsights.savingsRate >= 20 ? 'Great!' : trendInsights.savingsRate >= 10 ? 'Good' : trendInsights.savingsRate >= 0 ? 'Building' : 'Overspent'}
                  theme={theme}
                  accentColor={trendInsights.savingsRate >= 15 ? '#16a34a' : trendInsights.savingsRate >= 0 ? '#ca8a04' : colors.primary}
                  icon="💰"
                />
                <InsightCard
                  title="Avg Monthly Income"
                  value={formatCurrency(trendInsights.avgMonthlyIncome, currency)}
                  subtitle="per month"
                  theme={theme}
                  accentColor={colors.chart.inflow}
                  icon="📈"
                />
                <InsightCard
                  title="Avg Monthly Spend"
                  value={formatCurrency(trendInsights.avgMonthlySpend, currency)}
                  trend={trendInsights.spendingTrend === 'decreasing' ? 'up' : trendInsights.spendingTrend === 'increasing' ? 'down' : 'neutral'}
                  trendLabel={trendInsights.spendingTrend === 'increasing' ? 'Rising' : trendInsights.spendingTrend === 'decreasing' ? 'Falling' : 'Stable'}
                  theme={theme}
                  accentColor={colors.primary}
                  icon="💳"
                />
              </div>
            )}

            {/* Monthly Cash Flow - Primary Chart */}
            {monthlyFlow.length > 0 && (
              <Card theme={theme} padding="xl">
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: SPACING.lg,
                  }}
                >
                  <div>
                    <h3
                      style={{
                        fontSize: TYPOGRAPHY.sizes.lg,
                        fontWeight: TYPOGRAPHY.weights.bold,
                        margin: 0,
                        marginBottom: SPACING.xs,
                        color: colors.text.primary,
                      }}
                    >
                      Monthly Cash Flow
                    </h3>
                    <p
                      style={{
                        fontSize: TYPOGRAPHY.sizes.sm,
                        color: colors.text.secondary,
                        margin: 0,
                      }}
                    >
                      Compare your income vs spending each month
                    </p>
                  </div>
                </div>
                <MonthlyCashFlowBarChart
                  data={monthlyFlow}
                  theme={theme}
                  currency={currency}
                  height={300}
                />
              </Card>
            )}

            {/* Two-column layout for secondary charts */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
                gap: SPACING.xl,
                marginTop: SPACING.xl,
              }}
            >
              {/* Net Cash Position */}
              {trendInsights && trendInsights.netCashTrend.length > 0 && (
                <Card theme={theme} padding="xl">
                  <div style={{ marginBottom: SPACING.md }}>
                    <h3
                      style={{
                        fontSize: TYPOGRAPHY.sizes.lg,
                        fontWeight: TYPOGRAPHY.weights.bold,
                        margin: 0,
                        marginBottom: SPACING.xs,
                        color: colors.text.primary,
                      }}
                    >
                      Cumulative Net Position
                    </h3>
                    <p
                      style={{
                        fontSize: TYPOGRAPHY.sizes.sm,
                        color: colors.text.secondary,
                        margin: 0,
                      }}
                    >
                      Running total of income minus spending
                    </p>
                  </div>
                  <NetFlowChart
                    data={trendInsights.netCashTrend}
                    theme={theme}
                    currency={currency}
                    height={220}
                  />
                </Card>
              )}

              {/* Top Spending Categories */}
              {topSpendingCategories.length > 0 && (
                <Card theme={theme} padding="xl">
                  <div style={{ marginBottom: SPACING.md }}>
                    <h3
                      style={{
                        fontSize: TYPOGRAPHY.sizes.lg,
                        fontWeight: TYPOGRAPHY.weights.bold,
                        margin: 0,
                        marginBottom: SPACING.xs,
                        color: colors.text.primary,
                      }}
                    >
                      Where Your Money Goes
                    </h3>
                    <p
                      style={{
                        fontSize: TYPOGRAPHY.sizes.sm,
                        color: colors.text.secondary,
                        margin: 0,
                      }}
                    >
                      Top spending categories for selected period
                    </p>
                  </div>
                  <HorizontalBarChart
                    data={topSpendingCategories.slice(0, 6)}
                    theme={theme}
                    currency={currency}
                    height={220}
                  />
                </Card>
              )}
            </div>

            {/* Month-over-Month Comparison */}
            {currentPivot && currentPivot.months.length >= 2 && (
              <Card theme={theme} padding="xl" style={{ marginTop: SPACING.xl }}>
                <div style={{ marginBottom: SPACING.lg }}>
                  <h3
                    style={{
                      fontSize: TYPOGRAPHY.sizes.lg,
                      fontWeight: TYPOGRAPHY.weights.bold,
                      margin: 0,
                      marginBottom: SPACING.xs,
                      color: colors.text.primary,
                    }}
                  >
                    Month-over-Month Comparison
                  </h3>
                  <p
                    style={{
                      fontSize: TYPOGRAPHY.sizes.sm,
                      color: colors.text.secondary,
                      margin: 0,
                    }}
                  >
                    Category changes between the last two months
                  </p>
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table
                    style={{
                      width: '100%',
                      borderCollapse: 'collapse',
                      fontSize: TYPOGRAPHY.sizes.sm,
                    }}
                  >
                    <thead>
                      <tr style={{ borderBottom: `2px solid ${colors.border.emphasis}` }}>
                        <th style={{ textAlign: 'left', padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.secondary }}>
                          Category
                        </th>
                        <th style={{ textAlign: 'right', padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.secondary }}>
                          {formatMonthLabel(currentPivot.months[currentPivot.months.length - 2])}
                        </th>
                        <th style={{ textAlign: 'right', padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.secondary }}>
                          {formatMonthLabel(currentPivot.months[currentPivot.months.length - 1])}
                        </th>
                        <th style={{ textAlign: 'right', padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.secondary }}>
                          Change
                        </th>
                        <th style={{ textAlign: 'right', padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.secondary }}>
                          % Change
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {(() => {
                        const prevMonth = currentPivot.months[currentPivot.months.length - 2];
                        const currMonth = currentPivot.months[currentPivot.months.length - 1];
                        const prevIdx = currentPivot.months.indexOf(prevMonth);
                        const currIdx = currentPivot.months.indexOf(currMonth);
                        
                        return currentPivot.categories
                          .map((category, catIdx) => {
                            const prevVal = currentPivot.actuals[catIdx]?.[prevIdx] ?? 0;
                            const currVal = currentPivot.actuals[catIdx]?.[currIdx] ?? 0;
                            const change = currVal - prevVal;
                            const pctChange = prevVal !== 0 ? (change / Math.abs(prevVal)) * 100 : (currVal !== 0 ? 100 : 0);
                            
                            return { category, prevVal, currVal, change, pctChange };
                          })
                          .filter(row => row.prevVal !== 0 || row.currVal !== 0)
                          .sort((a, b) => Math.abs(b.change) - Math.abs(a.change))
                          .slice(0, 10)
                          .map((row, idx) => (
                            <tr
                              key={row.category}
                              style={{
                                borderBottom: `1px solid ${colors.border.default}`,
                              }}
                            >
                              <td style={{ padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.medium, color: colors.text.primary }}>
                                {row.category}
                              </td>
                              <td style={{ textAlign: 'right', padding: SPACING.md, color: row.prevVal < 0 ? colors.text.negative : colors.text.primary }}>
                                {formatCurrency(row.prevVal, currency)}
                              </td>
                              <td style={{ textAlign: 'right', padding: SPACING.md, color: row.currVal < 0 ? colors.text.negative : colors.text.primary }}>
                                {formatCurrency(row.currVal, currency)}
                              </td>
                              <td style={{ textAlign: 'right', padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.medium, color: row.change > 0 ? '#16a34a' : row.change < 0 ? colors.primary : colors.text.tertiary }}>
                                {row.change > 0 ? '+' : ''}{formatCurrency(row.change, currency)}
                              </td>
                              <td style={{ textAlign: 'right', padding: SPACING.md, color: row.pctChange > 0 ? '#16a34a' : row.pctChange < 0 ? colors.primary : colors.text.tertiary }}>
                                {row.pctChange > 0 ? '+' : ''}{row.pctChange.toFixed(1)}%
                              </td>
                            </tr>
                          ));
                      })()}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}
          </div>
        )}

        {/* BUDGET TAB */}
        {activeTab === 'budget' && (
          <div>
            {/* Budget Health KPI Strip */}
            <Card theme={theme} padding="xl" style={{ marginBottom: SPACING.xl }}>
              <div style={{ marginBottom: SPACING.lg }}>
                <h3
                  style={{
                    fontSize: TYPOGRAPHY.sizes.lg,
                    fontWeight: TYPOGRAPHY.weights.bold,
                    margin: 0,
                    marginBottom: SPACING.xs,
                    color: colors.text.primary,
                  }}
                >
                  Budget Overview
                </h3>
                <p
                  style={{
                    fontSize: TYPOGRAPHY.sizes.sm,
                    color: colors.text.secondary,
                    margin: 0,
                  }}
                >
                  Key metrics at a glance
                </p>
              </div>
              <BudgetHealthKPIs
                totalBudget={budgetHealthKPIs.totalBudget}
                totalSpent={budgetHealthKPIs.totalSpent}
                remainingBudget={budgetHealthKPIs.remainingBudget}
                utilizationPct={budgetHealthKPIs.utilizationPct}
                theme={theme}
                currency={currency}
              />
            </Card>

            {/* Budget Progress by Category */}
            {budgetProgressData.length > 0 && (
              <Card theme={theme} padding="xl" style={{ marginBottom: SPACING.xl }}>
                <div style={{ marginBottom: SPACING.lg }}>
                  <h3
                    style={{
                      fontSize: TYPOGRAPHY.sizes.lg,
                      fontWeight: TYPOGRAPHY.weights.bold,
                      margin: 0,
                      marginBottom: SPACING.xs,
                      color: colors.text.primary,
                    }}
                  >
                    Budget Progress by Category
                  </h3>
                  <p
                    style={{
                      fontSize: TYPOGRAPHY.sizes.sm,
                      color: colors.text.secondary,
                      margin: 0,
                    }}
                  >
                    Track spending against budget for each category
                  </p>
                </div>
                <BudgetProgressChart data={budgetProgressData} theme={theme} currency={currency} />
              </Card>
            )}

            {/* Budget Allocation and Variance Side by Side */}
            {budgetAllocationData.length > 0 && budgetProgressData.length > 0 && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: SPACING.xl, marginBottom: SPACING.xl }}>
                {/* Budget Allocation Donut */}
                <Card theme={theme} padding="xl">
                  <div style={{ marginBottom: SPACING.lg }}>
                    <h3
                      style={{
                        fontSize: TYPOGRAPHY.sizes.lg,
                        fontWeight: TYPOGRAPHY.weights.bold,
                        margin: 0,
                        marginBottom: SPACING.xs,
                        color: colors.text.primary,
                      }}
                    >
                      Budget Allocation
                    </h3>
                    <p
                      style={{
                        fontSize: TYPOGRAPHY.sizes.sm,
                        color: colors.text.secondary,
                        margin: 0,
                      }}
                    >
                      How your budget is distributed
                    </p>
                  </div>
                  <BudgetAllocationDonut data={budgetAllocationData} theme={theme} currency={currency} />
                </Card>

                {/* Budget Variance Table */}
                <Card theme={theme} padding="xl">
                  <div style={{ marginBottom: SPACING.lg }}>
                    <h3
                      style={{
                        fontSize: TYPOGRAPHY.sizes.lg,
                        fontWeight: TYPOGRAPHY.weights.bold,
                        margin: 0,
                        marginBottom: SPACING.xs,
                        color: colors.text.primary,
                      }}
                    >
                      Budget Variance
                    </h3>
                    <p
                      style={{
                        fontSize: TYPOGRAPHY.sizes.sm,
                        color: colors.text.secondary,
                        margin: 0,
                      }}
                    >
                      Detailed comparison by category
                    </p>
                  </div>
                  <BudgetVarianceTable data={budgetProgressData} theme={theme} currency={currency} />
                </Card>
              </div>
            )}

            {/* Monthly Budget Trend */}
            {budgetVsActualData.length > 0 && (
              <Card theme={theme} padding="xl">
                <div style={{ marginBottom: SPACING.lg }}>
                  <h3
                    style={{
                      fontSize: TYPOGRAPHY.sizes.lg,
                      fontWeight: TYPOGRAPHY.weights.bold,
                      margin: 0,
                      marginBottom: SPACING.xs,
                      color: colors.text.primary,
                    }}
                  >
                    Monthly Budget Trend
                  </h3>
                  <p
                    style={{
                      fontSize: TYPOGRAPHY.sizes.sm,
                      color: colors.text.secondary,
                      margin: 0,
                    }}
                  >
                    Budget vs actual spending over time
                  </p>
                </div>
                <BudgetTrendChart data={budgetVsActualData} theme={theme} currency={currency} height={300} />
              </Card>
            )}
          </div>
        )}

        {/* DETAILS TAB */}
        {activeTab === 'details' && (
          <div>
            <Card theme={theme} padding="md">
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: SPACING.md,
                  flexWrap: 'wrap',
                  marginBottom: SPACING.md,
                }}
              >
                <h3
                  style={{
                    margin: 0,
                    fontSize: TYPOGRAPHY.sizes.lg,
                    fontWeight: TYPOGRAPHY.weights.semibold,
                    color: colors.text.primary,
                  }}
                >
                  Category Details
                </h3>
                <div style={{ display: 'flex', gap: SPACING.sm, flexWrap: 'wrap' }}>
                  {!isEditingTable && !isEditingBudgets ? (
                    <>
                      <button
                        onClick={() => {
                          setIsEditingTable(true);
                          setEditedCells({});
                        }}
                        style={{
                          padding: `${SPACING.sm}px ${SPACING.md}px`,
                          fontSize: TYPOGRAPHY.sizes.sm,
                          fontWeight: TYPOGRAPHY.weights.medium,
                          color: colors.bg.primary,
                          background: colors.primary,
                          border: 'none',
                          borderRadius: 4,
                          cursor: 'pointer',
                        }}
                      >
                        Edit Amounts
                      </button>
                      <button
                        onClick={() => {
                          setIsEditingBudgets(true);
                          setEditedBudgets({});
                        }}
                        style={{
                          padding: `${SPACING.sm}px ${SPACING.md}px`,
                          fontSize: TYPOGRAPHY.sizes.sm,
                          fontWeight: TYPOGRAPHY.weights.medium,
                          color: colors.text.primary,
                          background: colors.bg.secondary,
                          border: `1px solid ${colors.border.default}`,
                          borderRadius: 4,
                          cursor: 'pointer',
                        }}
                      >
                        Set Budgets
                      </button>
                    </>
                  ) : isEditingTable ? (
                    <>
                      <button
                        onClick={handleSaveInlineEdits}
                        disabled={isMutating}
                        style={{
                          padding: `${SPACING.sm}px ${SPACING.md}px`,
                          fontSize: TYPOGRAPHY.sizes.sm,
                          fontWeight: TYPOGRAPHY.weights.medium,
                          color: colors.bg.primary,
                          background: colors.primary,
                          border: 'none',
                          borderRadius: 4,
                          cursor: isMutating ? 'not-allowed' : 'pointer',
                          opacity: isMutating ? 0.6 : 1,
                        }}
                      >
                        Save
                      </button>
                      <button
                        onClick={handleCancelInlineEdits}
                        disabled={isMutating}
                        style={{
                          padding: `${SPACING.sm}px ${SPACING.md}px`,
                          fontSize: TYPOGRAPHY.sizes.sm,
                          fontWeight: TYPOGRAPHY.weights.medium,
                          color: colors.text.primary,
                          background: colors.bg.secondary,
                          border: `1px solid ${colors.border.default}`,
                          borderRadius: 4,
                          cursor: isMutating ? 'not-allowed' : 'pointer',
                          opacity: isMutating ? 0.6 : 1,
                        }}
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={handleSaveBudgets}
                        disabled={isSavingBudgets}
                        style={{
                          padding: `${SPACING.sm}px ${SPACING.md}px`,
                          fontSize: TYPOGRAPHY.sizes.sm,
                          fontWeight: TYPOGRAPHY.weights.medium,
                          color: colors.bg.primary,
                          background: colors.primary,
                          border: 'none',
                          borderRadius: 4,
                          cursor: isSavingBudgets ? 'not-allowed' : 'pointer',
                          opacity: isSavingBudgets ? 0.6 : 1,
                        }}
                      >
                        {isSavingBudgets ? 'Saving...' : 'Save Budgets'}
                      </button>
                      <button
                        onClick={() => {
                          setIsEditingBudgets(false);
                          setEditedBudgets({});
                        }}
                        disabled={isSavingBudgets}
                        style={{
                          padding: `${SPACING.sm}px ${SPACING.md}px`,
                          fontSize: TYPOGRAPHY.sizes.sm,
                          fontWeight: TYPOGRAPHY.weights.medium,
                          color: colors.text.primary,
                          background: colors.bg.secondary,
                          border: `1px solid ${colors.border.default}`,
                          borderRadius: 4,
                          cursor: isSavingBudgets ? 'not-allowed' : 'pointer',
                          opacity: isSavingBudgets ? 0.6 : 1,
                        }}
                      >
                        Cancel
                      </button>
                    </>
                  )}
                </div>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table
                  style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    fontSize: TYPOGRAPHY.sizes.sm,
                  }}
                >
                  <thead>
                    <tr style={{ borderBottom: `2px solid ${colors.border.emphasis}` }}>
                      <th style={{ textAlign: 'left', padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.secondary }}>
                        Category
                      </th>
                      {pivot.months.map(month => (
                        <th
                          key={month}
                          colSpan={isEditingBudgets ? 2 : 1}
                          style={{ textAlign: 'right', padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.secondary }}
                        >
                          {formatMonthLabel(month).split(' ')[0]}
                        </th>
                      ))}
                      <th style={{ textAlign: 'right', padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.secondary, background: colors.bg.total }}>
                        Total
                      </th>
                      {!isEditingTable && !isEditingBudgets && (
                        <th style={{ textAlign: 'center', padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.tertiary, width: 60 }}>
                          
                        </th>
                      )}
                    </tr>
                    {isEditingBudgets && (
                      <tr style={{ borderBottom: `1px solid ${colors.border.default}` }}>
                        <th style={{ textAlign: 'left', padding: SPACING.sm, fontWeight: TYPOGRAPHY.weights.normal, color: colors.text.tertiary, fontSize: TYPOGRAPHY.sizes.xs }}>
                          
                        </th>
                        {pivot.months.map(month => (
                          <React.Fragment key={`header-${month}`}>
                            <th style={{ textAlign: 'right', padding: SPACING.sm, fontWeight: TYPOGRAPHY.weights.normal, color: colors.text.tertiary, fontSize: TYPOGRAPHY.sizes.xs }}>
                              Actual
                            </th>
                            <th style={{ textAlign: 'right', padding: SPACING.sm, fontWeight: TYPOGRAPHY.weights.normal, color: colors.primary, fontSize: TYPOGRAPHY.sizes.xs }}>
                              Budget
                            </th>
                          </React.Fragment>
                        ))}
                        <th style={{ textAlign: 'right', padding: SPACING.sm, fontWeight: TYPOGRAPHY.weights.normal, color: colors.text.tertiary, fontSize: TYPOGRAPHY.sizes.xs, background: colors.bg.total }}>
                          
                        </th>
                      </tr>
                    )}
                  </thead>
                  <tbody>
                    {filteredPivotRows.map((row, idx) => {
                        const rowTotal = pivot.months.reduce(
                          (sum, month) => sum + getCellValue(row.category, month),
                          0
                        );
                        const isNegative = rowTotal < 0;
                        return (
                          <tr
                            key={row.category}
                            style={{
                              borderBottom: idx < filteredPivotRows.length - 1 ? `1px solid ${colors.border.default}` : 'none',
                            }}
                          >
                            <td
                              style={{
                                padding: SPACING.md,
                                fontWeight: TYPOGRAPHY.weights.medium,
                                color: colors.text.primary,
                              }}
                            >
                              {row.category}
                            </td>
                            {pivot.months.map((month) => {
                              const key = `${row.category}__${month}`;
                              const monthData = row.monthly.find(m => m.month === month);
                              const value = getCellValue(row.category, month);
                              const inputValue = editedCells[key] ?? (monthData?.actual?.toString() ?? '0');
                              const budgetInputValue = editedBudgets[key] ?? (monthData?.budget?.toString() ?? '0');
                              
                              if (isEditingBudgets) {
                                return (
                                  <React.Fragment key={month}>
                                    <td
                                      style={{
                                        textAlign: 'right',
                                        padding: SPACING.md,
                                        color: value < 0 ? colors.text.negative : colors.text.primary,
                                      }}
                                    >
                                      {formatCurrency(value, currency)}
                                    </td>
                                    <td
                                      style={{
                                        textAlign: 'right',
                                        padding: SPACING.sm,
                                      }}
                                    >
                                      <input
                                        type="number"
                                        step="0.01"
                                        min="0"
                                        value={budgetInputValue}
                                        onChange={(e) => handleBudgetCellEdit(row.category, month, e.target.value)}
                                        style={{
                                          width: 80,
                                          textAlign: 'right',
                                          padding: `${SPACING.xs}px ${SPACING.sm}px`,
                                          border: `1px solid ${colors.primary}`,
                                          borderRadius: 4,
                                          background: colors.bg.primary,
                                          color: colors.primary,
                                          fontWeight: TYPOGRAPHY.weights.medium,
                                        }}
                                      />
                                    </td>
                                  </React.Fragment>
                                );
                              }
                              
                              return (
                                <td
                                  key={month}
                                  style={{
                                    textAlign: 'right',
                                    padding: SPACING.md,
                                    color: value < 0 ? colors.text.negative : colors.text.primary,
                                  }}
                                >
                                  {isEditingTable ? (
                                    <input
                                      type="number"
                                      step="0.01"
                                      value={inputValue}
                                      onChange={(e) => handleCellEdit(row.category, month, e.target.value)}
                                      style={{
                                        width: '100%',
                                        textAlign: 'right',
                                        padding: `${SPACING.xs}px ${SPACING.sm}px`,
                                        border: `1px solid ${colors.border.default}`,
                                        borderRadius: 4,
                                        background: colors.bg.primary,
                                        color: colors.text.primary,
                                      }}
                                    />
                                  ) : (
                                    formatCurrency(value, currency)
                                  )}
                                </td>
                              );
                            })}
                            <td
                              style={{
                                textAlign: 'right',
                                padding: SPACING.md,
                                fontWeight: TYPOGRAPHY.weights.bold,
                                color: isNegative ? colors.text.negative : colors.text.primary,
                                background: colors.bg.total,
                              }}
                            >
                              {formatCurrency(rowTotal, currency)}
                            </td>
                            {!isEditingTable && !isEditingBudgets && (
                              <td
                                style={{
                                  textAlign: 'center',
                                  padding: SPACING.sm,
                                }}
                              >
                                <button
                                  onClick={() => handleOpenTransferModal(row.category, rowTotal)}
                                  title={`Transfer amount from ${row.category}`}
                                  style={{
                                    padding: `${SPACING.xs}px ${SPACING.sm}px`,
                                    fontSize: TYPOGRAPHY.sizes.xs,
                                    fontWeight: TYPOGRAPHY.weights.medium,
                                    color: colors.text.secondary,
                                    background: 'transparent',
                                    border: `1px solid ${colors.border.default}`,
                                    borderRadius: 4,
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 4,
                                    transition: 'all 0.15s ease',
                                  }}
                                  onMouseEnter={(e) => {
                                    e.currentTarget.style.background = colors.bg.hover;
                                    e.currentTarget.style.borderColor = colors.primary;
                                    e.currentTarget.style.color = colors.primary;
                                  }}
                                  onMouseLeave={(e) => {
                                    e.currentTarget.style.background = 'transparent';
                                    e.currentTarget.style.borderColor = colors.border.default;
                                    e.currentTarget.style.color = colors.text.secondary;
                                  }}
                                >
                                  <span style={{ fontSize: 12 }}>↔</span>
                                  <span>Move</span>
                                </button>
                              </td>
                            )}
                          </tr>
                        );
                      })}
                    {/* Column Totals */}
                    <tr style={{ borderTop: `2px solid ${colors.border.emphasis}` }}>
                      <td style={{ padding: SPACING.md, fontWeight: TYPOGRAPHY.weights.bold, color: colors.text.primary, background: colors.bg.total }}>
                        Total
                      </td>
                      {pivot.months.map(month => {
                        const monthTotal = filteredPivotRows.reduce((sum, row) => {
                          return sum + getCellValue(row.category, month);
                        }, 0);
                        const monthBudgetTotal = filteredPivotRows.reduce((sum, row) => {
                          return sum + getBudgetCellValue(row.category, month);
                        }, 0);
                        
                        if (isEditingBudgets) {
                          return (
                            <React.Fragment key={month}>
                              <td
                                style={{
                                  textAlign: 'right',
                                  padding: SPACING.md,
                                  fontWeight: TYPOGRAPHY.weights.bold,
                                  color: monthTotal < 0 ? colors.text.negative : colors.text.primary,
                                  background: colors.bg.total,
                                }}
                              >
                                {formatCurrency(monthTotal, currency)}
                              </td>
                              <td
                                style={{
                                  textAlign: 'right',
                                  padding: SPACING.md,
                                  fontWeight: TYPOGRAPHY.weights.bold,
                                  color: colors.primary,
                                  background: colors.bg.total,
                                }}
                              >
                                {formatCurrency(monthBudgetTotal, currency)}
                              </td>
                            </React.Fragment>
                          );
                        }
                        
                        return (
                          <td
                            key={month}
                            style={{
                              textAlign: 'right',
                              padding: SPACING.md,
                              fontWeight: TYPOGRAPHY.weights.bold,
                              color: monthTotal < 0 ? colors.text.negative : colors.text.primary,
                              background: colors.bg.total,
                            }}
                          >
                            {formatCurrency(monthTotal, currency)}
                          </td>
                        );
                      })}
                      <td
                        style={{
                          textAlign: 'right',
                          padding: SPACING.md,
                          fontWeight: TYPOGRAPHY.weights.bold,
                          color: colors.text.primary,
                          background: colors.bg.total,
                        }}
                      >
                        {formatCurrency(
                          filteredPivotRows.reduce((sum, row) => {
                            const rowTotal = pivot.months.reduce(
                              (rowSum, month) => rowSum + getCellValue(row.category, month),
                              0
                            );
                            return sum + rowTotal;
                          }, 0),
                          currency
                        )}
                      </td>
                      {!isEditingTable && !isEditingBudgets && (
                        <td style={{ background: colors.bg.total }}></td>
                      )}
                    </tr>
                  </tbody>
                </table>
              </div>
            </Card>


            {/* Change Summary Banner */}
            {showChangeBanner && changeSummary && (
              <Card theme={theme} padding="md" style={{ marginTop: SPACING.lg }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    {changeSummary.map((change, idx) => (
                      <div
                        key={idx}
                        style={{
                          fontSize: TYPOGRAPHY.sizes.sm,
                          color: change.status === 'success' ? colors.text.primary : colors.text.negative,
                          marginBottom: idx < changeSummary.length - 1 ? SPACING.xs : 0,
                        }}
                      >
                        {change.message}
                      </div>
                    ))}
                  </div>
                  <button
                    onClick={() => setShowChangeBanner(false)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: colors.text.secondary,
                      cursor: 'pointer',
                      fontSize: TYPOGRAPHY.sizes.lg,
                      padding: 0,
                      marginLeft: SPACING.md,
                    }}
                  >
                    ×
                  </button>
                </div>
              </Card>
            )}

            {/* Insights Panel */}
            {filteredMetrics.top_variances && filteredMetrics.top_variances.length > 0 && (
              <Card theme={theme} padding="lg" style={{ marginTop: SPACING.xl }}>
                <h3
                  style={{
                    fontSize: TYPOGRAPHY.sizes.lg,
                    fontWeight: TYPOGRAPHY.weights.semibold,
                    margin: 0,
                    marginBottom: SPACING.md,
                    color: colors.text.primary,
                  }}
                >
                  Insights
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: SPACING.md }}>
                  <div>
                    <div style={{ fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.secondary, marginBottom: SPACING.xs }}>
                      Top 3 Spending Categories
                    </div>
                    <div style={{ fontSize: TYPOGRAPHY.sizes.base, color: colors.text.primary }}>
                      {filteredMetrics.top_variances
                        .filter(v => v.direction === 'over' && v.actual < 0)
                        .slice(0, 3)
                        .map(v => v.category)
                        .join(', ')}
                    </div>
                  </div>
                  {filteredMetrics.month_over_month_delta !== null && filteredMetrics.month_over_month_delta !== undefined && (
                    <div>
                      <div style={{ fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.secondary, marginBottom: SPACING.xs }}>
                        Month-over-Month Change
                      </div>
                      <div style={{ fontSize: TYPOGRAPHY.sizes.base, color: filteredMetrics.month_over_month_delta >= 0 ? colors.text.primary : colors.text.negative }}>
                        {filteredMetrics.month_over_month_delta >= 0 ? '+' : ''}{formatCurrency(filteredMetrics.month_over_month_delta, currency)} 
                        {typeof filteredMetrics.month_over_month_pct === 'number' && (
                          ` (${(filteredMetrics.month_over_month_pct as number) >= 0 ? '+' : ''}${(filteredMetrics.month_over_month_pct as number).toFixed(1)}%)`
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </Card>
            )}
          </div>
        )}

        {/* PREFERENCES TAB */}
        {activeTab === 'preferences' && (
          <div>
            <Card theme={theme} padding="lg">
              <h3
                style={{
                  fontSize: TYPOGRAPHY.sizes.lg,
                  fontWeight: TYPOGRAPHY.weights.semibold,
                  margin: 0,
                  marginBottom: SPACING.lg,
                  color: colors.text.primary,
                }}
              >
                User Preferences
              </h3>

              {isLoadingPreferences && (
                <div style={{ textAlign: 'center', padding: SPACING.xl, color: colors.text.secondary }}>
                  Loading preferences...
                </div>
              )}

              {preferencesError && (
                <div style={{ textAlign: 'center', padding: SPACING.xl, color: colors.text.negative }}>
                  {preferencesError}
                  <button
                    onClick={loadPreferences}
                    style={{
                      display: 'block',
                      margin: `${SPACING.md}px auto 0`,
                      padding: `${SPACING.sm}px ${SPACING.md}px`,
                      background: colors.primary,
                      color: colors.bg.primary,
                      border: 'none',
                      borderRadius: 4,
                      cursor: 'pointer',
                    }}
                  >
                    Retry
                  </button>
                </div>
              )}

              {preferencesData && !isLoadingPreferences && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: SPACING.xl }}>
                  {/* Settings Section */}
                  <div>
                    <h4
                      style={{
                        fontSize: TYPOGRAPHY.sizes.md,
                        fontWeight: TYPOGRAPHY.weights.semibold,
                        margin: 0,
                        marginBottom: SPACING.md,
                        color: colors.text.primary,
                      }}
                    >
                      Settings
                    </h4>
                    {preferencesData.settings ? (
                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                          gap: SPACING.md,
                        }}
                      >
                        <div style={{ padding: SPACING.md, background: colors.bg.secondary, borderRadius: 8 }}>
                          <div style={{ fontSize: TYPOGRAPHY.sizes.xs, color: colors.text.secondary, marginBottom: SPACING.xs }}>
                            Functional Currency
                          </div>
                          <div style={{ fontSize: TYPOGRAPHY.sizes.md, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.primary }}>
                            {preferencesData.settings.functional_currency}
                          </div>
                        </div>
                        <div style={{ padding: SPACING.md, background: colors.bg.secondary, borderRadius: 8 }}>
                          <div style={{ fontSize: TYPOGRAPHY.sizes.xs, color: colors.text.secondary, marginBottom: SPACING.xs }}>
                            Onboarding Status
                          </div>
                          <div style={{ fontSize: TYPOGRAPHY.sizes.md, fontWeight: TYPOGRAPHY.weights.semibold, color: preferencesData.settings.onboarding_complete ? colors.text.primary : colors.text.negative }}>
                            {preferencesData.settings.onboarding_complete ? 'Complete' : 'Incomplete'}
                          </div>
                        </div>
                        {preferencesData.settings.profiles && preferencesData.settings.profiles.length > 0 && (
                          <div style={{ padding: SPACING.md, background: colors.bg.secondary, borderRadius: 8 }}>
                            <div style={{ fontSize: TYPOGRAPHY.sizes.xs, color: colors.text.secondary, marginBottom: SPACING.xs }}>
                              Household Profiles
                            </div>
                            <div style={{ fontSize: TYPOGRAPHY.sizes.md, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.primary }}>
                              {preferencesData.settings.profiles.join(', ')}
                            </div>
                          </div>
                        )}
                        {preferencesData.parsing_banks.length > 0 && (
                          <div style={{ padding: SPACING.md, background: colors.bg.secondary, borderRadius: 8 }}>
                            <div style={{ fontSize: TYPOGRAPHY.sizes.xs, color: colors.text.secondary, marginBottom: SPACING.xs }}>
                              Banks with Parsing Rules
                            </div>
                            <div style={{ fontSize: TYPOGRAPHY.sizes.md, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.primary }}>
                              {preferencesData.parsing_banks.join(', ')}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div style={{ color: colors.text.secondary, fontStyle: 'italic' }}>
                        No settings configured. Ask the AI to help you complete onboarding.
                      </div>
                    )}
                  </div>

                  {/* Categorization Rules Section */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: SPACING.md }}>
                      <h4
                        style={{
                          fontSize: TYPOGRAPHY.sizes.md,
                          fontWeight: TYPOGRAPHY.weights.semibold,
                          margin: 0,
                          color: colors.text.primary,
                        }}
                      >
                        Categorization Rules ({preferencesData.categorization_rules.length})
                      </h4>
                      <button
                        onClick={loadPreferences}
                        style={{
                          padding: `${SPACING.xs}px ${SPACING.sm}px`,
                          fontSize: TYPOGRAPHY.sizes.sm,
                          background: colors.bg.secondary,
                          color: colors.text.primary,
                          border: `1px solid ${colors.border.default}`,
                          borderRadius: 4,
                          cursor: 'pointer',
                        }}
                      >
                        Refresh
                      </button>
                    </div>

                    {preferencesData.categorization_rules.length === 0 ? (
                      <div style={{ color: colors.text.secondary, fontStyle: 'italic', padding: SPACING.md }}>
                        No categorization rules saved yet. Upload a statement and the AI will learn your preferences.
                      </div>
                    ) : (
                      <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                          <thead>
                            <tr style={{ background: colors.bg.secondary }}>
                              <th style={{ textAlign: 'left', padding: SPACING.md, fontSize: TYPOGRAPHY.sizes.sm, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.secondary }}>
                                Rule Name
                              </th>
                              <th style={{ textAlign: 'left', padding: SPACING.md, fontSize: TYPOGRAPHY.sizes.sm, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.secondary }}>
                                Pattern
                              </th>
                              <th style={{ textAlign: 'left', padding: SPACING.md, fontSize: TYPOGRAPHY.sizes.sm, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.secondary }}>
                                Category
                              </th>
                              <th style={{ textAlign: 'left', padding: SPACING.md, fontSize: TYPOGRAPHY.sizes.sm, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.secondary }}>
                                Bank
                              </th>
                              <th style={{ textAlign: 'center', padding: SPACING.md, fontSize: TYPOGRAPHY.sizes.sm, fontWeight: TYPOGRAPHY.weights.semibold, color: colors.text.secondary, width: 100 }}>
                                Actions
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            {preferencesData.categorization_rules.map((rule, idx) => (
                              <tr
                                key={rule.id}
                                style={{
                                  background: idx % 2 === 0 ? colors.bg.primary : colors.bg.subtle,
                                  borderBottom: `1px solid ${colors.border.default}`,
                                }}
                              >
                                {editingRuleId === rule.id ? (
                                  <>
                                    <td style={{ padding: SPACING.sm }}>
                                      <input
                                        type="text"
                                        value={editedRuleName}
                                        onChange={(e) => setEditedRuleName(e.target.value)}
                                        style={{
                                          width: '100%',
                                          padding: SPACING.xs,
                                          fontSize: TYPOGRAPHY.sizes.sm,
                                          border: `1px solid ${colors.border.default}`,
                                          borderRadius: 4,
                                          background: colors.bg.primary,
                                          color: colors.text.primary,
                                        }}
                                      />
                                    </td>
                                    <td style={{ padding: SPACING.sm }}>
                                      <input
                                        type="text"
                                        value={editedRulePattern}
                                        onChange={(e) => setEditedRulePattern(e.target.value)}
                                        placeholder="e.g., CARREFOUR, BIEDRONKA"
                                        style={{
                                          width: '100%',
                                          padding: SPACING.xs,
                                          fontSize: TYPOGRAPHY.sizes.sm,
                                          border: `1px solid ${colors.border.default}`,
                                          borderRadius: 4,
                                          background: colors.bg.primary,
                                          color: colors.text.primary,
                                        }}
                                      />
                                    </td>
                                    <td style={{ padding: SPACING.sm }}>
                                      <input
                                        type="text"
                                        value={editedRuleCategory}
                                        onChange={(e) => setEditedRuleCategory(e.target.value)}
                                        placeholder="e.g., Food & Groceries"
                                        style={{
                                          width: '100%',
                                          padding: SPACING.xs,
                                          fontSize: TYPOGRAPHY.sizes.sm,
                                          border: `1px solid ${colors.border.default}`,
                                          borderRadius: 4,
                                          background: colors.bg.primary,
                                          color: colors.text.primary,
                                        }}
                                      />
                                    </td>
                                    <td style={{ padding: SPACING.md, fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.secondary }}>
                                      {rule.bank_name || 'Global'}
                                    </td>
                                    <td style={{ padding: SPACING.sm, textAlign: 'center' }}>
                                      <button
                                        onClick={() => handleSaveRuleEdit(rule.id)}
                                        disabled={isSavingPreference}
                                        style={{
                                          padding: `${SPACING.xs}px ${SPACING.sm}px`,
                                          marginRight: SPACING.xs,
                                          fontSize: TYPOGRAPHY.sizes.xs,
                                          background: colors.primary,
                                          color: colors.bg.primary,
                                          border: 'none',
                                          borderRadius: 4,
                                          cursor: isSavingPreference ? 'not-allowed' : 'pointer',
                                          opacity: isSavingPreference ? 0.6 : 1,
                                        }}
                                      >
                                        Save
                                      </button>
                                      <button
                                        onClick={cancelEditingRule}
                                        style={{
                                          padding: `${SPACING.xs}px ${SPACING.sm}px`,
                                          fontSize: TYPOGRAPHY.sizes.xs,
                                          background: colors.bg.secondary,
                                          color: colors.text.primary,
                                          border: `1px solid ${colors.border.default}`,
                                          borderRadius: 4,
                                          cursor: 'pointer',
                                        }}
                                      >
                                        Cancel
                                      </button>
                                    </td>
                                  </>
                                ) : (
                                  <>
                                    <td style={{ padding: SPACING.md, fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.primary }}>
                                      {rule.name}
                                    </td>
                                    <td style={{ padding: SPACING.md, fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.primary, fontFamily: 'monospace' }}>
                                      {rule.rule?.pattern || '-'}
                                    </td>
                                    <td style={{ padding: SPACING.md, fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.primary }}>
                                      {rule.rule?.category || '-'}
                                    </td>
                                    <td style={{ padding: SPACING.md, fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.secondary }}>
                                      {rule.bank_name || 'Global'}
                                    </td>
                                    <td style={{ padding: SPACING.sm, textAlign: 'center' }}>
                                      <button
                                        onClick={() => startEditingRule(rule)}
                                        style={{
                                          padding: `${SPACING.xs}px ${SPACING.sm}px`,
                                          fontSize: TYPOGRAPHY.sizes.xs,
                                          background: colors.bg.secondary,
                                          color: colors.text.primary,
                                          border: `1px solid ${colors.border.default}`,
                                          borderRadius: 4,
                                          cursor: 'pointer',
                                        }}
                                      >
                                        Edit
                                      </button>
                                    </td>
                                  </>
                                )}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>

                  {/* Help Text */}
                  <div
                    style={{
                      padding: SPACING.md,
                      background: colors.bg.subtle,
                      borderRadius: 8,
                      fontSize: TYPOGRAPHY.sizes.sm,
                      color: colors.text.secondary,
                    }}
                  >
                    <strong>How categorization rules work:</strong> When you upload statements, the AI uses these rules to automatically categorize transactions. Rules are learned over time as you confirm categorizations. Global rules apply to all banks; bank-specific rules only apply to that bank's statements.
                  </div>
                </div>
              )}
            </Card>
          </div>
        )}
      </div>
      
      {/* Transfer Modal */}
      {transferModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={() => setTransferModal(null)}
        >
          <div
            style={{
              background: colors.bg.elevated,
              borderRadius: 12,
              padding: SPACING.xl,
              maxWidth: 400,
              width: '90%',
              boxShadow: colors.shadow.md,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3
              style={{
                fontSize: TYPOGRAPHY.sizes.lg,
                fontWeight: TYPOGRAPHY.weights.semibold,
                color: colors.text.primary,
                margin: 0,
                marginBottom: SPACING.xs,
              }}
            >
              Transfer Amount
            </h3>
            
            <div style={{ marginBottom: SPACING.md }}>
              <div style={{ fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.secondary, marginBottom: SPACING.xs }}>
                Month
              </div>
              <select
                value={transferModal.month}
                onChange={(e) => handleTransferMonthChange(e.target.value)}
                style={{
                  width: '100%',
                  padding: `${SPACING.sm}px ${SPACING.md}px`,
                  fontSize: TYPOGRAPHY.sizes.base,
                  border: `1px solid ${colors.border.default}`,
                  borderRadius: 6,
                  background: colors.bg.primary,
                  color: colors.text.primary,
                }}
              >
                {currentPivot?.months.map(month => (
                  <option key={month} value={month}>{formatMonthLabel(month)}</option>
                ))}
              </select>
            </div>
            
            <div style={{ marginBottom: SPACING.md }}>
              <div style={{ fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.secondary, marginBottom: SPACING.xs }}>
                From
              </div>
              <div style={{ fontSize: TYPOGRAPHY.sizes.base, fontWeight: TYPOGRAPHY.weights.medium, color: colors.text.primary }}>
                {transferModal.fromCategory}
                <span style={{ color: colors.text.secondary, marginLeft: SPACING.sm }}>
                  ({formatCurrency(transferModal.fromAmount, currency)})
                </span>
              </div>
            </div>
            
            <div style={{ marginBottom: SPACING.md }}>
              <div style={{ fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.secondary, marginBottom: SPACING.xs }}>
                To Category
              </div>
              <select
                value={transferToCategory}
                onChange={(e) => setTransferToCategory(e.target.value)}
                style={{
                  width: '100%',
                  padding: `${SPACING.sm}px ${SPACING.md}px`,
                  fontSize: TYPOGRAPHY.sizes.base,
                  border: `1px solid ${colors.border.default}`,
                  borderRadius: 6,
                  background: colors.bg.primary,
                  color: colors.text.primary,
                }}
              >
                <option value="">Select category...</option>
                {currentPivot?.categories
                  .filter(c => c !== transferModal.fromCategory)
                  .map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
              </select>
            </div>
            
            <div style={{ marginBottom: SPACING.lg }}>
              <div style={{ fontSize: TYPOGRAPHY.sizes.sm, color: colors.text.secondary, marginBottom: SPACING.xs }}>
                Amount to Transfer
              </div>
              <input
                type="number"
                step="0.01"
                min="0"
                max={Math.abs(transferModal.fromAmount)}
                value={transferAmount}
                onChange={(e) => setTransferAmount(e.target.value)}
                style={{
                  width: '100%',
                  padding: `${SPACING.sm}px ${SPACING.md}px`,
                  fontSize: TYPOGRAPHY.sizes.base,
                  border: `1px solid ${colors.border.default}`,
                  borderRadius: 6,
                  background: colors.bg.primary,
                  color: colors.text.primary,
                }}
              />
            </div>
            
            <div style={{ display: 'flex', gap: SPACING.sm, justifyContent: 'flex-end' }}>
              <button
                onClick={() => setTransferModal(null)}
                style={{
                  padding: `${SPACING.sm}px ${SPACING.lg}px`,
                  fontSize: TYPOGRAPHY.sizes.sm,
                  fontWeight: TYPOGRAPHY.weights.medium,
                  color: colors.text.primary,
                  background: colors.bg.secondary,
                  border: `1px solid ${colors.border.default}`,
                  borderRadius: 6,
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteTransfer}
                disabled={!transferToCategory || !transferAmount || isMutating}
                style={{
                  padding: `${SPACING.sm}px ${SPACING.lg}px`,
                  fontSize: TYPOGRAPHY.sizes.sm,
                  fontWeight: TYPOGRAPHY.weights.medium,
                  color: colors.bg.primary,
                  background: colors.primary,
                  border: 'none',
                  borderRadius: 6,
                  cursor: !transferToCategory || !transferAmount || isMutating ? 'not-allowed' : 'pointer',
                  opacity: !transferToCategory || !transferAmount || isMutating ? 0.6 : 1,
                }}
              >
                {isMutating ? 'Transferring...' : 'Transfer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// MOUNT
// ============================================================================

const container = document.getElementById('dashboard-root');
if (container) {
  const root = createRoot(container);
  root.render(
    <ErrorBoundary>
      <DashboardWidget />
    </ErrorBoundary>
  );
}
