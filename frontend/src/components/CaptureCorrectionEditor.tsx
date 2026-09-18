import type { CaptureResult, Operation } from '@/app/types';
import { captureLabel } from '@/i18n/capture';
import { ApiError, api } from '@/lib/api';
import { useMutation } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

interface Props {
  operation: Operation;
  onCancel: () => void;
  onSaved: (operation: Operation) => void;
}

function parseResult(value: string): CaptureResult {
  const parsed: unknown = JSON.parse(value);
  if (!parsed || typeof parsed !== 'object') throw new Error('invalid');
  const candidate = parsed as Partial<CaptureResult>;
  if (!Array.isArray(candidate.intents) || candidate.intents.length === 0) {
    throw new Error('invalid');
  }
  return {
    ...(candidate as CaptureResult),
    needs_confirmation: false,
    clarification_question: null,
  };
}

export function CaptureCorrectionEditor({ operation, onCancel, onSaved }: Props): JSX.Element {
  const t = (key: string): string => captureLabel(null, key);
  const [value, setValue] = useState('');
  const [validationError, setValidationError] = useState(false);

  useEffect(() => {
    setValue(JSON.stringify(operation.ai_result, null, 2));
    setValidationError(false);
  }, [operation.ai_result]);

  const correction = useMutation({
    mutationFn: (result: CaptureResult) =>
      api.post<Operation>(`/operations/${operation.inbox_item_id}/correction`, { result }),
    onSuccess: onSaved,
  });

  const save = (): void => {
    try {
      const result = parseResult(value);
      setValidationError(false);
      correction.mutate(result);
    } catch {
      setValidationError(true);
    }
  };

  return (
    <div className="mt-4 rounded-card border border-line p-3">
      <label className="text-sm font-medium" htmlFor="capture-correction">
        {t('structuredData')}
      </label>
      <p className="mt-1 text-xs text-ink-muted">{t('structuredHint')}</p>
      <textarea
        id="capture-correction"
        className="mt-3 min-h-64 w-full rounded-card border border-line bg-surface p-3 font-mono text-xs"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        aria-invalid={validationError}
      />
      {validationError && (
        <p className="mt-2 text-sm text-danger" role="alert">
          {t('invalidCorrection')}
        </p>
      )}
      {correction.error && (
        <p className="mt-2 text-sm text-danger" role="alert">
          {correction.error instanceof ApiError ? correction.error.message : t('saveFailed')}
        </p>
      )}
      <div className="mt-3 flex gap-2">
        <button
          className="od-button-primary flex-1 disabled:opacity-50"
          disabled={correction.isPending}
          onClick={save}
        >
          {correction.isPending ? t('saving') : t('saveCorrection')}
        </button>
        <button
          className="od-button-ghost flex-1"
          disabled={correction.isPending}
          onClick={onCancel}
        >
          {t('cancel')}
        </button>
      </div>
    </div>
  );
}
