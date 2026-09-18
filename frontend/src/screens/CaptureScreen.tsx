import { useMutation, useQuery } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';

import type { Operation } from '@/app/types';
import { CaptureCorrectionEditor } from '@/components/CaptureCorrectionEditor';
import { EmptyCard, ScreenHeader } from '@/components/ScreenHeader';
import { captureLabel } from '@/i18n/capture';
import { ApiError, api } from '@/lib/api';
import { haptic } from '@/lib/telegram';

interface Accepted {
  inbox_item_id: string;
  status: string;
}

const PROCESSING_STATUSES = ['received', 'queued', 'processing'];

export function CaptureScreen(): JSX.Element {
  const t = (key: string): string => captureLabel(null, key);
  const [text, setText] = useState('');
  const [operationId, setOperationId] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [savedOperation, setSavedOperation] = useState<Operation | null>(null);
  const voiceInput = useRef<HTMLInputElement>(null);
  const imageInput = useRef<HTMLInputElement>(null);

  const createText = useMutation({
    mutationFn: () =>
      api.post<Accepted>('/capture/text', {
        text,
        idempotency_key: `web:${crypto.randomUUID()}`,
      }),
    onSuccess: (data) => {
      setOperationId(data.inbox_item_id);
      haptic('success');
    },
    onError: () => haptic('error'),
  });
  const upload = useMutation({
    mutationFn: ({ path, file }: { path: string; file: File }) => {
      const form = new FormData();
      form.append('file', file);
      form.append('idempotency_key', `web:${crypto.randomUUID()}`);
      return api.upload<Accepted>(path, form);
    },
    onSuccess: (data) => setOperationId(data.inbox_item_id),
    onError: () => haptic('error'),
  });
  const operation = useQuery({
    queryKey: ['capture-operation', operationId],
    queryFn: () => api.get<Operation>(`/operations/${operationId}`),
    enabled: operationId !== null,
    refetchInterval: (query) =>
      PROCESSING_STATUSES.includes(query.state.data?.status ?? '') ? 1200 : false,
  });
  const currentOperation = savedOperation ?? operation.data;

  useEffect(() => {
    if (operation.data?.status === 'completed') haptic('success');
  }, [operation.data?.status]);

  const busy =
    createText.isPending ||
    upload.isPending ||
    (currentOperation && PROCESSING_STATUSES.includes(currentOperation.status));
  const chooseFile = (path: string, input: React.RefObject<HTMLInputElement | null>): void => {
    const file = input.current?.files?.[0];
    if (file) upload.mutate({ path, file });
  };
  const reset = (): void => {
    setOperationId(null);
    setSavedOperation(null);
    setEditing(false);
    setText('');
  };

  return (
    <section className="p-4">
      <ScreenHeader title={t('title')} />
      {operationId ? (
        <div className="od-card">
          <p className="font-medium">
            {currentOperation?.status === 'completed'
              ? t('created')
              : currentOperation?.status === 'needs_confirmation'
                ? t('clarify')
                : t('processing')}
          </p>
          {currentOperation?.clarification_question && (
            <p className="mt-3 rounded-card bg-warning/15 p-3 text-sm text-warning">
              {currentOperation.clarification_question}
            </p>
          )}
          {currentOperation?.created.map((item) => (
            <div className="mt-3 rounded-card border border-line p-3" key={item.entity_id}>
              {item.entity_type}
            </div>
          ))}
          {currentOperation?.status === 'failed' && (
            <p className="mt-3 text-danger">{currentOperation.error ?? t('failed')}</p>
          )}
          {currentOperation?.ai_result &&
            ['completed', 'needs_confirmation'].includes(currentOperation.status) &&
            (editing ? (
              <CaptureCorrectionEditor
                operation={currentOperation}
                onCancel={() => setEditing(false)}
                onSaved={(updated) => {
                  setSavedOperation(updated);
                  setEditing(false);
                  haptic('success');
                }}
              />
            ) : (
              <button className="od-button-ghost mt-4" onClick={() => setEditing(true)}>
                {t('fix')}
              </button>
            ))}
          <button className="od-button-ghost mt-4" onClick={reset}>
            {t('newCapture')}
          </button>
        </div>
      ) : (
        <>
          <textarea
            className="min-h-36 w-full rounded-card border border-line bg-surface-raised p-4 text-base"
            aria-label="Capture text"
            placeholder={t('placeholder')}
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
          <button
            className="od-button-primary mt-3 w-full disabled:opacity-50"
            disabled={!text.trim() || Boolean(busy)}
            onClick={() => createText.mutate()}
          >
            {t('send')}
          </button>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <button
              className="od-button-ghost"
              disabled={Boolean(busy)}
              onClick={() => voiceInput.current?.click()}
            >
              {t('voice')}
            </button>
            <button
              className="od-button-ghost"
              disabled={Boolean(busy)}
              onClick={() => imageInput.current?.click()}
            >
              {t('photo')}
            </button>
          </div>
          <input
            ref={voiceInput}
            className="hidden"
            type="file"
            accept="audio/ogg,audio/mpeg,audio/mp4,audio/wav"
            onChange={() => chooseFile('/capture/voice', voiceInput)}
          />
          <input
            ref={imageInput}
            className="hidden"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={() => chooseFile('/capture/image', imageInput)}
          />
          {upload.error instanceof ApiError && <EmptyCard>{upload.error.message}</EmptyCard>}
        </>
      )}
    </section>
  );
}
