/**
 * Simple Upload Page - Multi-step Statement Processing Wizard
 * 
 * Step-by-step flow:
 * 1. File upload
 * 2. Currency selection (if needed)
 * 3. Bank selection
 * 4. Header mapping (if parsing preferences don't exist)
 * 5. Net flow input
 * 6. Processing
 * 7. Dashboard
 */
import React, { useState, useEffect, useRef } from 'react';
import { apiClient } from '../lib/api-client';
import { DashboardWidget } from '../widgets/dashboard';

type UploadStep =
  | 'file_upload'
  | 'currency_selection'
  | 'bank_selection'
  | 'header_mapping'
  | 'net_flow_input'
  | 'processing'
  | 'success';

const COMMON_CURRENCIES = [
  'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD', 'CNY', 'HKD',
  'SGD', 'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'RON', 'BGN', 'HRK',
  'RUB', 'TRY', 'ZAR', 'BRL', 'MXN', 'ARS', 'CLP', 'COP', 'PEN', 'INR',
  'IDR', 'MYR', 'PHP', 'THB', 'VND', 'KRW', 'TWD', 'ILS', 'AED', 'SAR',
  'QAR', 'KWD', 'BHD', 'OMR', 'JOD', 'EGP', 'NGN', 'KES', 'GHS', 'MAD',
];

// Helper function to convert column index to Excel-style letter (A, B, C... AA, AB, etc.)
const getColumnLetter = (index: number): string => {
  let result = '';
  index++; // Convert 0-indexed to 1-indexed
  while (index > 0) {
    index--;
    result = String.fromCharCode(65 + (index % 26)) + result;
    index = Math.floor(index / 26);
  }
  return result;
};

export const SimpleUpload: React.FC = () => {
  const [step, setStep] = useState<UploadStep>('file_upload');
  const [file, setFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string>('');
  const [currency, setCurrency] = useState<string>('');
  const [userCurrency, setUserCurrency] = useState<string | null>(null);
  const [banks, setBanks] = useState<string[]>([]);
  const [bankName, setBankName] = useState<string>('');
  const [newBankName, setNewBankName] = useState<string>('');
  const [showNewBankInput, setShowNewBankInput] = useState(false);
  // Column mappings: maps column index to field type
  const [columnMappings, setColumnMappings] = useState<{
    [columnIndex: number]: string;  // Maps column index to field type
  }>({});
  // Removed hasHeaders - we always use first_transaction_row instead
  const [firstTransactionRow, setFirstTransactionRow] = useState<number>(1);
  const [netFlow, setNetFlow] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [processingProgress, setProcessingProgress] = useState<string>('');
  const [processingSteps, setProcessingSteps] = useState<Array<{
    label: string;
    status: 'pending' | 'active' | 'done';
  }>>([]);
  const processingTimers = useRef<number[]>([]);
  const processingInterval = useRef<number | null>(null);

  // Load user settings on mount
  useEffect(() => {
    loadUserSettings();
  }, []);

  useEffect(() => {
    return () => {
      processingTimers.current.forEach((timerId) => window.clearTimeout(timerId));
      processingTimers.current = [];
      if (processingInterval.current !== null) {
        window.clearInterval(processingInterval.current);
        processingInterval.current = null;
      }
    };
  }, []);

  const clearProcessingTimers = () => {
    processingTimers.current.forEach((timerId) => window.clearTimeout(timerId));
    processingTimers.current = [];
    if (processingInterval.current !== null) {
      window.clearInterval(processingInterval.current);
      processingInterval.current = null;
    }
  };

  const updateProcessingStep = (
    index: number,
    status: 'pending' | 'active' | 'done',
    label?: string
  ) => {
    setProcessingSteps((prev) => {
      if (!prev.length) return prev;
      return prev.map((step, idx) => {
        if (idx !== index) return step;
        return {
          ...step,
          status,
          label: label ?? step.label,
        };
      });
    });
  };

  const estimateBatchCount = () => {
    const estimatedTransactions = uploadResult?.transactions_count
      ?? (uploadResult?.total_rows
        ? Math.max(0, uploadResult.total_rows - (firstTransactionRow || 1) + 1)
        : 0);
    return Math.max(1, Math.ceil((estimatedTransactions || 1) / 20));
  };

  const startProcessingProgress = (totalBatches: number) => {
    clearProcessingTimers();
    const batches = Math.max(1, totalBatches);
    const minTotalMs = 12000;
    const maxTotalMs = 45000;
    const targetTotalMs = Math.min(maxTotalMs, Math.max(minTotalMs, batches * 1200));
    const perBatchMs = Math.max(800, Math.round(targetTotalMs / batches));
    const steps = [
      { label: 'Validating file', status: 'active' as const },
      { label: 'Parsing transactions', status: 'pending' as const },
      { label: 'Normalizing data', status: 'pending' as const },
      { label: `Categorizing batch 1/${batches}`, status: 'pending' as const },
      { label: 'Saving transactions', status: 'pending' as const },
      { label: 'Building dashboard', status: 'pending' as const },
    ];
    setProcessingSteps(steps);
    setProcessingProgress('Validating file...');

    const schedule = (delayMs: number, callback: () => void) => {
      const timerId = window.setTimeout(callback, delayMs);
      processingTimers.current.push(timerId);
    };

    schedule(800, () => {
      updateProcessingStep(0, 'done');
      updateProcessingStep(1, 'active');
      setProcessingProgress('Parsing transactions...');
    });

    schedule(2000, () => {
      updateProcessingStep(1, 'done');
      updateProcessingStep(2, 'active');
      setProcessingProgress('Normalizing data...');
    });

    schedule(3200, () => {
      updateProcessingStep(2, 'done');
      updateProcessingStep(3, 'active');
      let currentBatch = 1;
      updateProcessingStep(3, 'active', `Categorizing batch ${currentBatch}/${batches}`);
      setProcessingProgress(`Categorizing batch ${currentBatch}/${batches}...`);

      processingInterval.current = window.setInterval(() => {
        currentBatch += 1;
        if (currentBatch <= batches) {
          updateProcessingStep(3, 'active', `Categorizing batch ${currentBatch}/${batches}`);
          setProcessingProgress(`Categorizing batch ${currentBatch}/${batches}...`);
          return;
        }

        if (processingInterval.current !== null) {
          window.clearInterval(processingInterval.current);
          processingInterval.current = null;
        }

        updateProcessingStep(3, 'done');
        updateProcessingStep(4, 'active');
        setProcessingProgress('Saving transactions...');

        schedule(1400, () => {
          updateProcessingStep(4, 'done');
          updateProcessingStep(5, 'active');
          setProcessingProgress('Building dashboard...');
        });
      }, perBatchMs);
    });
  };

  const loadUserSettings = async () => {
    try {
      const currency = await apiClient.getCurrency();
      setUserCurrency(currency);

      const banksData = await apiClient.getBanks();
      setBanks(banksData.banks || []);
    } catch (err) {
      console.error('Failed to load user settings:', err);
    }
  };

  const handleFileSelect = async (selectedFile: File) => {
    if (!selectedFile) return;

    setFile(selectedFile);
    setError(null);
    setIsUploading(true);
    setUploadProgress('Uploading file...');

    try {
      // Simulate progress steps
      setTimeout(() => setUploadProgress('Analyzing file structure...'), 500);

      // Upload file and get analysis
      const result = await apiClient.uploadStatement(selectedFile);

      setTimeout(() => setUploadProgress('Detecting columns and format...'), 1000);
      setTimeout(() => {
        setUploadResult(result);
        setIsUploading(false);
        setUploadProgress('');
      }, 1500);

      // Check if currency is required
      if (result.currency_required && !userCurrency) {
        setCurrency(result.currency_detected || '');
        setStep('currency_selection');
        return;
      }

      // Stay on main screen (file_upload step) - user can now select bank and enter net flow
    } catch (err) {
      console.error('Upload error:', err);
      setIsUploading(false);
      setUploadProgress('');
      setError(err instanceof Error ? err.message : 'Failed to upload file');
      setStep('file_upload'); // Stay on file upload step on error
    }
  };

  const handleMainScreenContinue = async () => {
    if (!file || !uploadResult) {
      setError('Please upload a file first');
      return;
    }

    let finalBankName = bankName;

    // If adding new bank
    if (showNewBankInput) {
      if (!newBankName.trim()) {
        setError('Please enter a bank name');
        return;
      }
      finalBankName = newBankName.trim();

      try {
        await apiClient.addBank(finalBankName);
        setBanks([...banks, finalBankName]);
        setBankName(finalBankName);
        setShowNewBankInput(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to add bank');
        return;
      }
    } else {
      if (!bankName) {
        setError('Please select a bank');
        return;
      }
    }

    // Move to next step based on whether parsing preferences exist
    // If bank has saved mappings, always show mapping step (user can review/edit)
    // Only auto-process if preferences exist but no saved_mappings (legacy behavior)
    if (uploadResult?.parsing_preferences_exist && !uploadResult?.saved_mappings) {
      // Existing bank with preferences - go directly to processing
      await handleProcess();
    } else {
      // Need header mapping (new bank or bank with saved mappings to review/edit)
      // Initialize first_transaction_row from analysis if available
      if (uploadResult?.analysis?.skip_rows !== undefined) {
        setFirstTransactionRow((uploadResult.analysis.skip_rows || 0) + 1);
      }
      // Auto-load preferences if they exist
      if (uploadResult?.saved_mappings) {
        const saved = uploadResult.saved_mappings;
        const mappings: { [key: number]: string } = {};
        let hasInvalidMappings = false;

        // Helper to check if a value looks like data instead of a column reference
        const looksLikeData = (value: string): boolean => {
          if (!value || typeof value !== 'string') return false;
          
          // Numeric index check - must be ONLY digits and small
          const num = parseInt(value);
          if (!isNaN(num) && num >= 0 && num < 100 && value === num.toString()) {
            return false; // Valid index
          }
          
          // Everything else is suspicious (dates, amounts, long strings, etc.)
          return true;
        };

        // Convert saved mappings to column index -> field type
        Object.keys(saved.column_mappings || {}).forEach((fieldType) => {
          const columnRef = saved.column_mappings[fieldType];
          if (columnRef) {
            if (fieldType === 'description' && Array.isArray(columnRef)) {
              // Handle description array
              columnRef.forEach((col: string) => {
                // Check if it looks like data
                if (looksLikeData(col)) {
                  hasInvalidMappings = true;
                  return;
                }
                // Try to parse as numeric index first (new format)
                const idx = parseInt(col);
                if (!isNaN(idx) && idx >= 0) {
                  mappings[idx] = 'description';
                } else {
                  // Fallback: try to find by header name (old format)
                  const headerIdx = uploadResult.detected_headers?.indexOf(col);
                  if (headerIdx !== undefined && headerIdx >= 0) {
                    mappings[headerIdx] = 'description';
                  } else {
                    hasInvalidMappings = true;
                  }
                }
              });
            } else if (typeof columnRef === 'string') {
              // Check if it looks like data
              if (looksLikeData(columnRef)) {
                hasInvalidMappings = true;
                return;
              }
              // Try to parse as numeric index first (new format)
              const idx = parseInt(columnRef);
              if (!isNaN(idx) && idx >= 0) {
                mappings[idx] = fieldType;
              } else {
                // Fallback: try to find by header name (old format)
                const headerIdx = uploadResult.detected_headers?.indexOf(columnRef);
                if (headerIdx !== undefined && headerIdx >= 0) {
                  mappings[headerIdx] = fieldType;
                } else {
                  hasInvalidMappings = true;
                }
              }
            }
          }
        });

        if (hasInvalidMappings) {
          setError('Saved column mappings appear to be corrupted (contain data values instead of column indices). Please re-map your columns.');
          // Don't load the corrupted mappings
          setColumnMappings({});
        } else {
          setColumnMappings(mappings);
        }
        setFirstTransactionRow(saved.first_transaction_row ?? 1);
      }
      setStep('header_mapping');
    }
  };

  const handleCurrencySave = async () => {
    if (!currency) {
      setError('Please select a currency');
      return;
    }

    try {
      await apiClient.saveCurrency(currency);
      setUserCurrency(currency);

      // Return to main screen after saving currency
      setStep('file_upload');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save currency');
    }
  };

  const handleBankSelect = async () => {
    let finalBankName = bankName;

    // If adding new bank
    if (showNewBankInput) {
      if (!newBankName.trim()) {
        setError('Please enter a bank name');
        return;
      }
      finalBankName = newBankName.trim();

      try {
        await apiClient.addBank(finalBankName);
        setBanks([...banks, finalBankName]);
        setBankName(finalBankName);
        setShowNewBankInput(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to add bank');
        return;
      }
    } else {
      if (!bankName) {
        setError('Please select a bank');
        return;
      }
    }

    // Move to next step based on whether parsing preferences exist
    if (uploadResult?.parsing_preferences_exist) {
      // Skip header mapping, go to net flow
      setStep('net_flow_input');
    } else {
      // Need header mapping
      setStep('header_mapping');
    }
  };

  // Validation helper: Check if a value looks like data instead of a column index
  const validateColumnReference = (columnRef: string | string[]): boolean => {
    // Handle array (for description columns)
    if (Array.isArray(columnRef)) {
      return columnRef.every(ref => validateColumnReference(ref));
    }

    if (!columnRef || typeof columnRef !== 'string') return false;

    // Must be numeric string like "0", "1", "2"
    const idx = parseInt(columnRef);
    if (isNaN(idx) || idx < 0 || idx > 100) return false;

    // Must be EXACTLY the string representation of the number (no extra chars)
    if (columnRef !== idx.toString()) return false;

    // Reject if it looks like data
    if (/^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$/.test(columnRef)) return false; // Date pattern
    if (/^\d+[.,]\d+$/.test(columnRef)) return false; // Number with decimal
    if (columnRef.length > 3) return false; // Column index should be short

    return true;
  };

  // Helper function to convert columnMappings to API format
  const convertMappingsToAPI = () => {
    const result: any = {
      column_mappings: {},
      has_headers: false, // Always false - we use first_transaction_row instead
      first_transaction_row: firstTransactionRow,
      date_format: uploadResult?.analysis?.date_format || 'DD/MM/YYYY',
      currency: currency || userCurrency || 'USD',
    };

    // Convert column index -> field type to field type -> column reference
    // Use column index (as string) instead of header name for reliability
    // The backend will resolve this to the actual column name
    const descriptionCols: string[] = [];
    Object.keys(columnMappings).forEach((colIdxStr) => {
      const colIdx = parseInt(colIdxStr);
      const fieldType = columnMappings[colIdx];

      if (!fieldType || fieldType === 'do_not_use') return;

      // Use column index as the reference (more reliable than header names)
      // Format: "0", "1", "2" etc. which works whether has_headers is true or false
      const columnRef = colIdxStr; // Use index as string

      if (fieldType === 'description') {
        descriptionCols.push(columnRef);
      } else {
        result.column_mappings[fieldType] = columnRef;
      }
    });

    if (descriptionCols.length > 0) {
      result.column_mappings.description = descriptionCols;
    }

    // Validate all column references before returning
    const invalidRefs: string[] = [];
    Object.entries(result.column_mappings).forEach(([fieldType, columnRef]) => {
      if (!validateColumnReference(columnRef)) {
        invalidRefs.push(`${fieldType}: ${JSON.stringify(columnRef)}`);
      }
    });

    if (invalidRefs.length > 0) {
      console.error('[VALIDATION ERROR] Invalid column references detected:', invalidRefs);
      throw new Error(
        `Invalid column mappings detected. The following fields contain data values instead of column indices: ${invalidRefs.join(', ')}. ` +
        'Column references must be numeric indices like "0", "1", "2".'
      );
    }

    console.log('[DEBUG] Column mappings validated successfully:', result.column_mappings);
    return result;
  };

  const handleHeaderMappingSave = async () => {
    // Validate required fields
    const dateMapped = Object.values(columnMappings).includes('date');
    const amountMapped = Object.values(columnMappings).includes('amount');
    const descriptionMapped = Object.values(columnMappings).filter(v => v === 'description').length > 0;

    console.log('[DEBUG] handleHeaderMappingSave - columnMappings state:', columnMappings);
    console.log('[DEBUG] Required fields check:', { dateMapped, amountMapped, descriptionMapped });

    if (!dateMapped || !amountMapped || !descriptionMapped) {
      setError('Please map all required columns: Date, Amount, and at least one Description column');
      return;
    }

    if (!firstTransactionRow || firstTransactionRow < 1) {
      setError('Please specify the row number of the first transaction');
      return;
    }

    if (!bankName) {
      setError('Bank name is required');
      return;
    }

    try {
      const mappingData = convertMappingsToAPI();
      console.log('[DEBUG] Converted mapping data to send to API:', mappingData);
      await apiClient.saveHeaderMapping(bankName, mappingData);
      // Go directly to processing after saving mapping
      await handleProcess();
    } catch (err) {
      console.error('[ERROR] Failed to save header mapping:', err);
      setError(err instanceof Error ? err.message : 'Failed to save header mapping');
    }
  };

  const handleProcess = async () => {
    if (!file || !bankName) {
      setError('File and bank name are required');
      return;
    }

    setStep('processing');
    setError(null);
    startProcessingProgress(estimateBatchCount());

    try {
      const netFlowValue = netFlow ? parseFloat(netFlow) : undefined;
      // Include mappings if it's a new bank
      const mapping = uploadResult?.parsing_preferences_exist ? undefined : convertMappingsToAPI();

      setProcessingProgress('Parsing transactions...');
      const result = await apiClient.processStatement(
        file,
        bankName,
        netFlowValue,
        mapping
      );

      if (result.status === 'success') {
        clearProcessingTimers();
        setProcessingSteps((prev) => prev.map((step) => ({ ...step, status: 'done' })));
        setProcessingProgress('Complete!');
        setStep('success');
      } else {
        throw new Error((result as any).error || 'Processing failed');
      }
    } catch (err) {
      clearProcessingTimers();
      setError(err instanceof Error ? err.message : 'Failed to process statement');
      setProcessingProgress('Processing failed.');
      setProcessingSteps([]);
      // Go back to appropriate step based on whether mapping was needed
      if (uploadResult?.parsing_preferences_exist && !uploadResult?.saved_mappings) {
        setStep('file_upload');
      } else {
        setStep('header_mapping');
      }
    }
  };

  const reset = () => {
    clearProcessingTimers();
    setStep('file_upload');
    setFile(null);
    setUploadResult(null);
    setCurrency('');
    setBankName('');
    setNewBankName('');
    setShowNewBankInput(false);
    setColumnMappings({});
    setFirstTransactionRow(1);
    setNetFlow('');
    setError(null);
    setProcessingProgress('');
    setProcessingSteps([]);
  };

  // Success view
  if (step === 'success') {
    return (
      <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
        <div style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button
            onClick={reset}
            style={{
              padding: '8px 16px',
              backgroundColor: '#dc2626',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: 600,
            }}
          >
            ← Upload Another Statement
          </button>
          <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 700, color: '#1a202c' }}>
            Your Financial Dashboard
          </h2>
        </div>
        <DashboardWidget />
      </div>
    );
  }

  // Processing view
  if (step === 'processing') {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        padding: '24px',
      }}>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
          }
          @keyframes slideIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
          }
        `}</style>
        <div style={{
          backgroundColor: 'white',
          borderRadius: '16px',
          padding: '48px',
          boxShadow: '0 20px 60px rgba(0,0,0,0.1)',
          maxWidth: '500px',
          width: '100%',
          textAlign: 'center',
        }}>
          <div style={{ marginBottom: '24px' }}>
            <div style={{
              width: '60px',
              height: '60px',
              border: '4px solid #f3f4f6',
              borderTop: '4px solid #dc2626',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              margin: '0 auto',
            }} />
          </div>
          <h2 style={{ fontSize: '24px', fontWeight: 700, color: '#1a202c', marginBottom: '8px' }}>
            Processing Statement
          </h2>
          <p style={{ fontSize: '16px', color: '#6b7280' }}>
            {processingProgress || 'Please wait...'}
          </p>
          {processingSteps.length > 0 && (
            <div style={{
              marginTop: '24px',
              textAlign: 'left',
              borderTop: '1px solid #e5e7eb',
              paddingTop: '16px',
            }}>
              {processingSteps.map((stepItem, idx) => {
                const isActive = stepItem.status === 'active';
                const isDone = stepItem.status === 'done';
                const statusColor = isDone ? '#16a34a' : isActive ? '#dc2626' : '#d1d5db';
                return (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      padding: '6px 0',
                      color: isDone ? '#14532d' : '#374151',
                      animation: 'slideIn 0.2s ease-out',
                    }}
                  >
                    <span style={{
                      width: '10px',
                      height: '10px',
                      borderRadius: '999px',
                      backgroundColor: statusColor,
                      flexShrink: 0,
                      animation: isActive ? 'pulse 1.2s ease-in-out infinite' : undefined,
                    }} />
                    <span style={{
                      fontSize: '13px',
                      fontWeight: isDone ? 600 : 500,
                    }}>
                      {stepItem.label}
                    </span>
                    {isDone && (
                      <span style={{
                        fontSize: '11px',
                        color: '#16a34a',
                        marginLeft: 'auto',
                      }}>
                        Done
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Main wizard form
  return (
    <>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .progress-step {
          animation: slideIn 0.3s ease-out;
        }
      `}</style>
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        padding: '24px',
      }}>
        <div style={{
          backgroundColor: 'white',
          borderRadius: '16px',
          padding: '48px',
          boxShadow: '0 20px 60px rgba(0,0,0,0.1)',
          maxWidth: '1400px',
          width: '100%',
        }}>
          {/* Progress indicator */}
          <div style={{ marginBottom: '32px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              {['file_upload', 'currency_selection', 'header_mapping'].map((s, idx) => {
                const stepIndex = ['file_upload', 'currency_selection', 'header_mapping'].indexOf(step);
                const isActive = idx <= stepIndex;
                return (
                  <div
                    key={s}
                    style={{
                      width: '30px',
                      height: '30px',
                      borderRadius: '50%',
                      backgroundColor: isActive ? '#dc2626' : '#e5e7eb',
                      color: isActive ? 'white' : '#9ca3af',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '12px',
                      fontWeight: 600,
                    }}
                  >
                    {idx + 1}
                  </div>
                );
              })}
            </div>
          </div>

          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <h1 style={{
              fontSize: '32px',
              fontWeight: 700,
              color: '#dc2626',
              margin: '0 0 8px 0',
              letterSpacing: '-0.5px',
            }}>
              NumbyAI
            </h1>
            <p style={{
              fontSize: '16px',
              color: '#6b7280',
              margin: 0,
            }}>
              {step === 'file_upload' && (isUploading ? 'Analyzing your statement...' : 'Upload your bank statement')}
              {step === 'currency_selection' && 'Select your currency'}
              {step === 'header_mapping' && 'Map statement columns'}
            </p>
          </div>

          {error && (
            <div style={{
              padding: '12px',
              backgroundColor: '#fee2e2',
              border: '1px solid #fecaca',
              borderRadius: '8px',
              marginBottom: '24px',
              color: '#991b1b',
              fontSize: '14px',
            }}>
              {error}
            </div>
          )}

          {/* Step 1: Main Screen - File Upload, Bank Selection, Net Flow */}
          {step === 'file_upload' && (
            <div>
              {/* File Upload Section */}
              <div style={{ marginBottom: '24px' }}>
                <label style={{
                  display: 'block',
                  fontSize: '14px',
                  fontWeight: 600,
                  color: '#374151',
                  marginBottom: '8px',
                }}>
                  Bank Statement (CSV/Excel)
                </label>
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={(e) => {
                    const selectedFile = e.target.files?.[0];
                    if (selectedFile) handleFileSelect(selectedFile);
                  }}
                  disabled={isUploading}
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '2px dashed #d1d5db',
                    borderRadius: '8px',
                    fontSize: '14px',
                    cursor: isUploading ? 'not-allowed' : 'pointer',
                    opacity: isUploading ? 0.6 : 1,
                  }}
                />
                {file && (
                  <div style={{ marginTop: '12px' }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      marginBottom: isUploading ? '12px' : '0',
                    }}>
                      <span style={{ fontSize: '14px', color: '#6b7280' }}>
                        Selected: <strong>{file.name}</strong>
                      </span>
                      {isUploading && (
                        <div style={{
                          width: '16px',
                          height: '16px',
                          border: '2px solid #f3f4f6',
                          borderTop: '2px solid #dc2626',
                          borderRadius: '50%',
                          animation: 'spin 0.8s linear infinite',
                        }} />
                      )}
                    </div>

                    {isUploading && uploadProgress && (
                      <div style={{
                        marginTop: '12px',
                        padding: '12px',
                        backgroundColor: '#f9fafb',
                        borderRadius: '8px',
                        border: '1px solid #e5e7eb',
                      }}>
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px',
                          marginBottom: '8px',
                        }}>
                          <div style={{
                            width: '20px',
                            height: '20px',
                            border: '3px solid #f3f4f6',
                            borderTop: '3px solid #dc2626',
                            borderRadius: '50%',
                            animation: 'spin 0.8s linear infinite',
                          }} />
                          <span style={{
                            fontSize: '14px',
                            fontWeight: 600,
                            color: '#374151',
                          }}>
                            {uploadProgress}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Bank Selection Section */}
              <div style={{ marginBottom: '24px' }}>
                <label style={{
                  display: 'block',
                  fontSize: '14px',
                  fontWeight: 600,
                  color: '#374151',
                  marginBottom: '8px',
                }}>
                  Bank Name *
                </label>
                {!showNewBankInput ? (
                  <select
                    value={bankName}
                    onChange={(e) => {
                      if (e.target.value === '__new__') {
                        setShowNewBankInput(true);
                      } else {
                        setBankName(e.target.value);
                      }
                    }}
                    disabled={isUploading}
                    style={{
                      width: '100%',
                      padding: '12px',
                      border: '1px solid #d1d5db',
                      borderRadius: '8px',
                      fontSize: '14px',
                      opacity: isUploading ? 0.6 : 1,
                      cursor: isUploading ? 'not-allowed' : 'pointer',
                    }}
                  >
                    <option value="">Select bank...</option>
                    {banks.map(bank => (
                      <option key={bank} value={bank}>{bank}</option>
                    ))}
                    <option value="__new__">+ Add New Bank</option>
                  </select>
                ) : (
                  <div>
                    <input
                      type="text"
                      value={newBankName}
                      onChange={(e) => setNewBankName(e.target.value)}
                      placeholder="Enter bank name..."
                      disabled={isUploading}
                      style={{
                        width: '100%',
                        padding: '12px',
                        border: '1px solid #d1d5db',
                        borderRadius: '8px',
                        fontSize: '14px',
                        marginBottom: '8px',
                        opacity: isUploading ? 0.6 : 1,
                      }}
                    />
                    <button
                      onClick={() => {
                        setShowNewBankInput(false);
                        setNewBankName('');
                      }}
                      disabled={isUploading}
                      style={{
                        padding: '8px 16px',
                        backgroundColor: '#e5e7eb',
                        color: '#374151',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '14px',
                        cursor: isUploading ? 'not-allowed' : 'pointer',
                        opacity: isUploading ? 0.6 : 1,
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>

              {/* Net Flow Input Section */}
              <div style={{ marginBottom: '24px' }}>
                <label style={{
                  display: 'block',
                  fontSize: '14px',
                  fontWeight: 600,
                  color: '#374151',
                  marginBottom: '8px',
                }}>
                  Net Flow (optional)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={netFlow}
                  onChange={(e) => setNetFlow(e.target.value)}
                  placeholder="Ending balance - Starting balance"
                  disabled={isUploading}
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '1px solid #d1d5db',
                    borderRadius: '8px',
                    fontSize: '14px',
                    opacity: isUploading ? 0.6 : 1,
                  }}
                />
                <p style={{ marginTop: '4px', fontSize: '12px', color: '#9ca3af' }}>
                  Leave empty to auto-calculate from transactions
                </p>
              </div>

              {/* Continue Button */}
              <button
                onClick={handleMainScreenContinue}
                disabled={isUploading || (!file && !uploadResult) || (!bankName && !showNewBankInput)}
                style={{
                  width: '100%',
                  padding: '14px',
                  backgroundColor: (!isUploading && (file || uploadResult) && (bankName || showNewBankInput)) ? '#dc2626' : '#9ca3af',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: (!isUploading && (file || uploadResult) && (bankName || showNewBankInput)) ? 'pointer' : 'not-allowed',
                }}
              >
                {isUploading ? 'Uploading...' :
                  !file && !uploadResult ? 'Upload a file first' :
                    uploadResult?.parsing_preferences_exist ? 'Process Statement' :
                      'Continue to Mapping'}
              </button>
            </div>
          )}

          {/* Step 2: Currency Selection */}
          {step === 'currency_selection' && (
            <div>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: 600,
                color: '#374151',
                marginBottom: '8px',
              }}>
                Currency {uploadResult?.currency_detected && `(Detected: ${uploadResult.currency_detected})`}
              </label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                style={{
                  width: '100%',
                  padding: '12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '8px',
                  fontSize: '14px',
                  marginBottom: '16px',
                }}
              >
                <option value="">Select currency...</option>
                {COMMON_CURRENCIES.map(curr => (
                  <option key={curr} value={curr}>{curr}</option>
                ))}
              </select>
              <button
                onClick={handleCurrencySave}
                disabled={!currency}
                style={{
                  width: '100%',
                  padding: '14px',
                  backgroundColor: currency ? '#dc2626' : '#9ca3af',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: currency ? 'pointer' : 'not-allowed',
                }}
              >
                Continue
              </button>
            </div>
          )}


          {/* Step 4: Header Mapping - Lunch Money Style */}
          {step === 'header_mapping' && uploadResult?.detected_headers && (
            <div>
              {/* Instruction Box */}
              <div style={{
                backgroundColor: '#1e40af',
                color: 'white',
                padding: '16px',
                borderRadius: '8px',
                marginBottom: '24px',
              }}>
                <p style={{ margin: '0 0 8px 0', fontSize: '14px', fontWeight: 500 }}>
                  Match columns. We need to match the column data. Use the dropdowns to correspond columns from your file to the appropriate fields.
                </p>
                <p style={{ margin: '0', fontSize: '13px', fontWeight: 400, opacity: 0.9 }}>
                  💡 You can select <strong>multiple columns as Description</strong> - they will be concatenated. The description is what the AI uses to categorize transactions.
                </p>
              </div>

              {/* Combined Scrollable Container for Dropdowns and Table */}
              {uploadResult.preview_data && uploadResult.preview_data.length > 0 && (
                <div style={{ marginBottom: '24px' }}>
                  <div style={{
                    border: '1px solid #d1d5db',
                    borderRadius: '8px',
                    overflow: 'auto',
                    maxHeight: '600px',
                    width: '100%',
                  }}>
                    {/* Horizontal Dropdowns Row - Fixed at top */}
                    <div style={{
                      display: 'flex',
                      gap: '0',
                      padding: '0',
                      backgroundColor: '#f9fafb',
                      borderBottom: '2px solid #d1d5db',
                      position: 'sticky',
                      top: 0,
                      zIndex: 20,
                    }}>
                      {/* Row number column header - matches table row number column */}
                      <div style={{
                        minWidth: '50px',
                        maxWidth: '50px',
                        width: '50px',
                        flexShrink: 0,
                        padding: '8px',
                        boxSizing: 'border-box',
                      }}></div>
                      {Array.from({ length: Math.min(10, uploadResult.total_columns || uploadResult.preview_data[0]?.length || 0) }, (_, i) => {
                        const fieldOptions = [
                          { value: 'do_not_use', label: 'Do not use' },
                          { value: 'date', label: 'Date *' },
                          { value: 'vendor_payee', label: 'Vendor/Payee' },
                          { value: 'description', label: 'Description *' },
                          { value: 'category', label: 'Category' },
                          { value: 'balance', label: 'Balance' },
                          { value: 'amount', label: 'Amount *' },
                          { value: 'inflow', label: 'Inflow' },
                          { value: 'outflow', label: 'Outflow' },
                          { value: 'currency', label: 'Currency' },
                        ];

                        return (
                          <div key={i} style={{
                            minWidth: '180px',
                            maxWidth: '180px',
                            width: '180px',
                            flexShrink: 0,
                            padding: '8px',
                            boxSizing: 'border-box',
                          }}>
                            <label style={{
                              display: 'block',
                              fontSize: '12px',
                              fontWeight: 600,
                              color: '#374151',
                              marginBottom: '4px',
                            }}>
                              {getColumnLetter(i)}
                            </label>
                            <select
                              value={columnMappings[i] || 'do_not_use'}
                              onChange={(e) => {
                                const newMappings = { ...columnMappings };
                                if (e.target.value === 'do_not_use') {
                                  delete newMappings[i];
                                } else {
                                  newMappings[i] = e.target.value;
                                }
                                setColumnMappings(newMappings);
                              }}
                              style={{
                                width: '100%',
                                padding: '8px',
                                border: '1px solid #d1d5db',
                                borderRadius: '6px',
                                fontSize: '13px',
                                backgroundColor: 'white',
                                boxSizing: 'border-box',
                              }}
                            >
                              {fieldOptions.map(opt => (
                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                              ))}
                            </select>
                          </div>
                        );
                      })}
                    </div>

                    {/* Preview Table - Scrolls with dropdowns */}
                    <table style={{
                      width: '100%',
                      borderCollapse: 'collapse',
                      fontSize: '12px',
                      fontFamily: 'monospace',
                    }}>
                      <thead>
                        <tr>
                          <th style={{
                            padding: '8px',
                            backgroundColor: '#f3f4f6',
                            border: '1px solid #d1d5db',
                            textAlign: 'center',
                            fontWeight: 600,
                            position: 'sticky',
                            left: 0,
                            zIndex: 10,
                            minWidth: '50px',
                            maxWidth: '50px',
                            width: '50px',
                            boxSizing: 'border-box',
                          }}></th>
                          {Array.from({ length: Math.min(10, uploadResult.total_columns || uploadResult.preview_data[0]?.length || 0) }, (_, i) => {
                            const mappedField = columnMappings[i];
                            return (
                              <th key={i} style={{
                                padding: '8px',
                                backgroundColor: mappedField && mappedField !== 'do_not_use' ? '#dbeafe' : '#f3f4f6',
                                border: '1px solid #d1d5db',
                                textAlign: 'center',
                                fontWeight: 600,
                                minWidth: '180px',
                                maxWidth: '180px',
                                width: '180px',
                                boxSizing: 'border-box',
                              }}>
                                {getColumnLetter(i)}
                                {mappedField && mappedField !== 'do_not_use' && (
                                  <div style={{ fontSize: '10px', color: '#3b82f6', marginTop: '2px' }}>
                                    → {mappedField.replace('_', '/')}
                                  </div>
                                )}
                              </th>
                            );
                          })}
                        </tr>
                      </thead>
                      <tbody>
                        {uploadResult.preview_data.slice(0, 20).map((row: any[], rowIndex: number) => {
                          // Since preview_data now shows raw file (header=None), rowIndex maps directly to file rows
                          // rowIndex 0 = file row 1, rowIndex 1 = file row 2, etc.
                          const fileRowNumber = rowIndex + 1;
                          const isFirstTransactionRow = fileRowNumber === firstTransactionRow;
                          return (
                            <tr key={rowIndex} style={{
                              backgroundColor: isFirstTransactionRow
                                ? '#fef3c7' // Highlight with yellow background
                                : (rowIndex % 2 === 0 ? '#ffffff' : '#f9fafb'),
                              border: isFirstTransactionRow ? '2px solid #f59e0b' : undefined,
                              boxShadow: isFirstTransactionRow ? '0 0 0 1px #f59e0b' : undefined,
                            }}>
                              <td style={{
                                padding: '8px',
                                backgroundColor: isFirstTransactionRow ? '#fef3c7' : '#f3f4f6',
                                border: isFirstTransactionRow ? '2px solid #f59e0b' : '1px solid #d1d5db',
                                textAlign: 'center',
                                fontWeight: 600,
                                position: 'sticky',
                                left: 0,
                                zIndex: 5,
                                minWidth: '50px',
                                maxWidth: '50px',
                                width: '50px',
                                boxSizing: 'border-box',
                              }}>
                                {fileRowNumber}
                              </td>
                              {Array.from({ length: Math.min(10, row.length) }, (_, colIndex) => (
                                <td key={colIndex} style={{
                                  padding: '8px',
                                  border: '1px solid #d1d5db',
                                  whiteSpace: 'nowrap',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  minWidth: '180px',
                                  maxWidth: '180px',
                                  width: '180px',
                                  boxSizing: 'border-box',
                                }}>
                                  {row[colIndex] || ''}
                                </td>
                              ))}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* First Transaction Row Input */}
              <div style={{ marginBottom: '24px' }}>
                <label style={{
                  display: 'block',
                  fontSize: '14px',
                  fontWeight: 600,
                  color: '#374151',
                  marginBottom: '8px',
                }}>
                  Row number of first transaction *
                </label>
                <input
                  type="number"
                  min="1"
                  max={uploadResult.total_rows || 100}
                  value={firstTransactionRow}
                  onChange={(e) => setFirstTransactionRow(parseInt(e.target.value) || 1)}
                  placeholder="e.g., 5 if transactions start at row 5"
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '1px solid #d1d5db',
                    borderRadius: '8px',
                    fontSize: '14px',
                  }}
                />
                <p style={{ marginTop: '4px', fontSize: '12px', color: '#9ca3af' }}>
                  Specify which row contains the first transaction (some statements have headers or summary rows at the top)
                </p>
              </div>

              <button
                onClick={handleHeaderMappingSave}
                disabled={
                  !Object.values(columnMappings).includes('date') ||
                  !Object.values(columnMappings).includes('amount') ||
                  !Object.values(columnMappings).includes('description') ||
                  !firstTransactionRow
                }
                style={{
                  width: '100%',
                  padding: '14px',
                  backgroundColor: (
                    Object.values(columnMappings).includes('date') &&
                    Object.values(columnMappings).includes('amount') &&
                    Object.values(columnMappings).includes('description') &&
                    firstTransactionRow
                  ) ? '#dc2626' : '#9ca3af',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: (
                    Object.values(columnMappings).includes('date') &&
                    Object.values(columnMappings).includes('amount') &&
                    Object.values(columnMappings).includes('description') &&
                    firstTransactionRow
                  ) ? 'pointer' : 'not-allowed',
                }}
              >
                Save & Process Statement
              </button>
            </div>
          )}

        </div>
      </div>
    </>
  );
};
