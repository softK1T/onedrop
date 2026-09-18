import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { CaptureResult, Operation } from '@/app/types';
import { api } from '@/lib/api';
import { CaptureScreen } from '@/screens/CaptureScreen';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

vi.mock('@/lib/telegram', () => ({ haptic: vi.fn() }));

const getMock = api.get as unknown as Mock;
const postMock = api.post as unknown as Mock;

function captureResult(title = 'Buy milk'): CaptureResult {
  return {
    language: 'en',
    timezone: 'Europe/Warsaw',
    intents: [
      {
        type: 'task.create',
        confidence: 0.9,
        source_fragment: title,
        fields: { title, priority: 'normal' },
      },
    ],
    needs_confirmation: false,
    clarification_question: null,
  };
}

function operation(overrides: Partial<Operation> = {}): Operation {
  return {
    inbox_item_id: 'op-1',
    status: 'completed',
    input_type: 'text',
    created: [{ entity_type: 'task', entity_id: 't-1' }],
    clarification_question: null,
    error: null,
    transcript: null,
    ai_result: captureResult(),
    processing_ms: 12,
    created_at: '2026-09-18T10:00:00Z',
    ...overrides,
  };
}

function renderCapture(): void {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <CaptureScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function submitCapture(result: Operation): Promise<void> {
  postMock.mockResolvedValueOnce({ inbox_item_id: 'op-1', status: 'queued' });
  getMock.mockResolvedValue(result);
  renderCapture();
  await userEvent.type(screen.getByLabelText('Capture text'), 'Buy milk');
  await userEvent.click(screen.getByRole('button', { name: 'Send' }));
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  vi.stubGlobal('crypto', { ...globalThis.crypto, randomUUID: () => 'uuid-1' });
});

describe('CaptureScreen', () => {
  it('keeps sending disabled until there is text', async () => {
    renderCapture();

    const send = screen.getByRole('button', { name: 'Send' });
    expect(send).toBeDisabled();

    await userEvent.type(screen.getByLabelText('Capture text'), 'Buy milk');

    expect(send).toBeEnabled();
  });

  it('offers voice and photo capture next to text', () => {
    renderCapture();

    expect(screen.getByRole('button', { name: 'Voice' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Photo' })).toBeEnabled();
  });

  it('submits the text capture with an idempotency key', async () => {
    postMock.mockResolvedValue({ inbox_item_id: 'op-1', status: 'queued' });
    getMock.mockResolvedValue(operation({ status: 'queued', created: [], ai_result: null }));

    renderCapture();
    await userEvent.type(screen.getByLabelText('Capture text'), 'Buy milk');
    await userEvent.click(screen.getByRole('button', { name: 'Send' }));

    await waitFor(() =>
      expect(postMock).toHaveBeenCalledWith('/capture/text', {
        text: 'Buy milk',
        idempotency_key: 'web:uuid-1',
      }),
    );
  });

  it('shows the processing state while the worker parses the message', async () => {
    await submitCapture(operation({ status: 'processing', created: [], ai_result: null }));

    expect(await screen.findByText('Parsing your message')).toBeInTheDocument();
    expect(getMock.mock.calls[0]?.[0]).toBe('/operations/op-1');
  });

  it('shows the created records once the capture completes', async () => {
    await submitCapture(operation());

    expect(await screen.findByText('Created')).toBeInTheDocument();
    expect(screen.getByText('task')).toBeInTheDocument();
  });

  it('surfaces a clarification question before saving', async () => {
    await submitCapture(
      operation({
        status: 'needs_confirmation',
        created: [],
        clarification_question: 'Which day did you mean?',
      }),
    );

    expect(await screen.findByText('One question before saving')).toBeInTheDocument();
    expect(screen.getByText('Which day did you mean?')).toBeInTheDocument();
  });

  it('reports a failed capture without pretending anything was saved', async () => {
    await submitCapture(
      operation({ status: 'failed', created: [], error: 'provider_unavailable', ai_result: null }),
    );

    expect(await screen.findByText('provider_unavailable')).toBeInTheDocument();
  });

  it('returns to an empty form after a finished capture', async () => {
    await submitCapture(operation());
    await userEvent.click(await screen.findByRole('button', { name: 'New capture' }));

    expect(screen.getByLabelText('Capture text')).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
  });

  it('opens the correction editor with the detected result', async () => {
    await submitCapture(operation());
    await userEvent.click(await screen.findByRole('button', { name: 'Fix' }));

    const editor = screen.getByLabelText('Structured capture data');
    expect(editor).toHaveValue(expect.stringContaining('Buy milk'));
    expect(screen.getByRole('button', { name: 'Save correction' })).toBeEnabled();
  });

  it('posts a corrected structured result and renders the response', async () => {
    const corrected = captureResult('Buy oat milk');
    await submitCapture(operation());
    postMock.mockResolvedValueOnce(
      operation({
        created: [{ entity_type: 'task', entity_id: 't-2' }],
        ai_result: corrected,
      }),
    );
    await userEvent.click(await screen.findByRole('button', { name: 'Fix' }));
    const editor = screen.getByLabelText('Structured capture data');
    await userEvent.clear(editor);
    await userEvent.type(editor, JSON.stringify(corrected));
    await userEvent.click(screen.getByRole('button', { name: 'Save correction' }));

    await waitFor(() =>
      expect(postMock).toHaveBeenLastCalledWith('/operations/op-1/correction', {
        result: corrected,
      }),
    );
    expect(await screen.findByText('task')).toBeInTheDocument();
    expect(screen.queryByLabelText('Structured capture data')).not.toBeInTheDocument();
  });

  it('keeps the editor open and reports invalid JSON', async () => {
    await submitCapture(operation());
    await userEvent.click(await screen.findByRole('button', { name: 'Fix' }));
    const editor = screen.getByLabelText('Structured capture data');
    await userEvent.clear(editor);
    await userEvent.type(editor, '{invalid');
    await userEvent.click(screen.getByRole('button', { name: 'Save correction' }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Enter valid JSON containing at least one intent.',
    );
    expect(postMock).toHaveBeenCalledTimes(1);
    expect(editor).toBeInTheDocument();
  });
});
