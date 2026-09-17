import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';

import type { Operation } from '@/app/types';
import { EmptyCard, ScreenHeader } from '@/components/ScreenHeader';
import { ApiError, api } from '@/lib/api';
import { haptic } from '@/lib/telegram';

interface Accepted { inbox_item_id: string; status: string }

export function CaptureScreen(): JSX.Element {
  const [text, setText] = useState(''); const [operationId, setOperationId] = useState<string | null>(null); const voiceInput = useRef<HTMLInputElement>(null); const imageInput = useRef<HTMLInputElement>(null);
  const createText = useMutation({ mutationFn: () => api.post<Accepted>('/capture/text', { text, idempotency_key: `web:${crypto.randomUUID()}` }), onSuccess: (data) => { setOperationId(data.inbox_item_id); haptic('success'); }, onError: () => haptic('error') });
  const upload = useMutation({ mutationFn: ({ path, file }: { path: string; file: File }) => { const form = new FormData(); form.append('file', file); form.append('idempotency_key', `web:${crypto.randomUUID()}`); return api.upload<Accepted>(path, form); }, onSuccess: (data) => setOperationId(data.inbox_item_id), onError: () => haptic('error') });
  const operation = useQuery({ queryKey: ['capture-operation', operationId], queryFn: () => api.get<Operation>(`/operations/${operationId}`), enabled: operationId !== null, refetchInterval: (query) => ['received','queued','processing'].includes(query.state.data?.status ?? '') ? 1200 : false });
  useEffect(() => { if (operation.data?.status === 'completed') haptic('success'); }, [operation.data?.status]);
  const busy = createText.isPending || upload.isPending || (operation.data && ['received','queued','processing'].includes(operation.data.status));
  const chooseFile = (path: string, input: React.RefObject<HTMLInputElement>) => { const file = input.current?.files?.[0]; if (file) upload.mutate({ path, file }); };
  return <section className="p-4"><ScreenHeader title="Capture" />{operationId ? <div className="od-card"><p className="font-medium">{operation.data?.status === 'completed' ? 'Created' : operation.data?.status === 'needs_confirmation' ? 'One question before saving' : 'Parsing your message'}</p>{operation.data?.clarification_question && <p className="mt-3 rounded-card bg-warning/15 p-3 text-sm text-warning">{operation.data.clarification_question}</p>}{operation.data?.created.map(item => <div className="mt-3 rounded-card border border-line p-3" key={item.entity_id}>{item.entity_type}</div>)}{operation.data?.status === 'failed' && <p className="mt-3 text-danger">{operation.data.error ?? 'Nothing was saved'}</p>}<button className="od-button-ghost mt-4" onClick={() => { setOperationId(null); setText(''); }}>New capture</button></div> : <><textarea className="min-h-36 w-full rounded-card border border-line bg-surface-raised p-4 text-base" aria-label="Capture text" placeholder="Tomorrow at 15:00 meeting with Andrew, 45 PLN taxi" value={text} onChange={(event) => setText(event.target.value)} /><button className="od-button-primary mt-3 w-full disabled:opacity-50" disabled={!text.trim() || busy} onClick={() => createText.mutate()}>Send</button><div className="mt-3 grid grid-cols-2 gap-3"><button className="od-button-ghost" disabled={busy} onClick={() => voiceInput.current?.click()}>Voice</button><button className="od-button-ghost" disabled={busy} onClick={() => imageInput.current?.click()}>Photo</button></div><input ref={voiceInput} className="hidden" type="file" accept="audio/ogg,audio/mpeg,audio/mp4,audio/wav" onChange={() => chooseFile('/capture/voice', voiceInput)} /><input ref={imageInput} className="hidden" type="file" accept="image/jpeg,image/png,image/webp" onChange={() => chooseFile('/capture/image', imageInput)} />{upload.error instanceof ApiError && <EmptyCard>{upload.error.message}</EmptyCard>}</>}</section>;
}
