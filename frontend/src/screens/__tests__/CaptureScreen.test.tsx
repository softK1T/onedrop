import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Operation } from '@/app/types';
import { api } from '@/lib/api';
import { CaptureScreen } from '@/screens/CaptureScreen';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

vi.mock('@/lib/telegram', () => ({ haptic: vi.fn() }));

const getMock = api.get as unknown as Mock;
const postMock = api.post as unknown as Mock;

function operation(overrides: Partial<Operation> = {}): Operation {
  return {
    inbox_item_id: 'op-1',
    status: 'completed',
    input_type: 'text',
    created: [{ entity_type: 'task', entity_id: 't-1' }],
    clarification_question: null,
    error: null,
    transcript: null,
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
    getMock.mockResolvedValue(operation({ status: 'queued', created: [] }));

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
    postMock.mockResolvedValue({ inbox_item_id: 'op-1', status: 'queued' });
    getMock.mockResolvedValue(operation({ status: 'processing', created: [] }));

    renderCapture();
    await userEvent.type(screen.getByLabelText('Capture text'), 'Buy milk');
    await userEvent.click(screen.getByRole('button', { name: 'Send' }));

    expect(await screen.findByText('Parsing your message')).toBeInTheDocument();
    expect(getMock.mock.calls[0]?.[0]).toBe('/operations/op-1');
  });

  it('shows the created records once the capture completes', async () => {
    postMock.mockResolvedValue({ inbox_item_id: 'op-1', status: 'queued' });
    getMock.mockResolvedValue(operation());

    renderCapture();
    await userEvent.type(screen.getByLabelText('Capture text'), 'Pay the internet bill');
    await userEvent.click(screen.getByRole('button', { name: 'Send' }));

    expect(await screen.findByText('Created')).toBeInTheDocument();
    expect(screen.getByText('task')).toBeInTheDocument();
  });

  it('surfaces a clarification question before saving', async () => {
    postMock.mockResolvedValue({ inbox_item_id: 'op-1', status: 'queued' });
    getMock.mockResolvedValue(
      operation({
        status: 'needs_confirmation',
        created: [],
        clarification_question: 'Which day did you mean?',
      }),
    );

    renderCapture();
    await userEvent.type(screen.getByLabelText('Capture text'), 'meeting');
    await userEvent.click(screen.getByRole('button', { name: 'Send' }));

    expect(await screen.findByText('One question before saving')).toBeInTheDocument();
    expect(screen.getByText('Which day did you mean?')).toBeInTheDocument();
  });

  it('reports a failed capture without pretending anything was saved', async () => {
    postMock.mockResolvedValue({ inbox_item_id: 'op-1', status: 'queued' });
    getMock.mockResolvedValue(
      operation({ status: 'failed', created: [], error: 'provider_unavailable' }),
    );

    renderCapture();
    await userEvent.type(screen.getByLabelText('Capture text'), 'meeting');
    await userEvent.click(screen.getByRole('button', { name: 'Send' }));

    expect(await screen.findByText('provider_unavailable')).toBeInTheDocument();
  });

  it('returns to an empty form after a finished capture', async () => {
    postMock.mockResolvedValue({ inbox_item_id: 'op-1', status: 'queued' });
    getMock.mockResolvedValue(operation());

    renderCapture();
    await userEvent.type(screen.getByLabelText('Capture text'), 'Pay the internet bill');
    await userEvent.click(screen.getByRole('button', { name: 'Send' }));
    await userEvent.click(await screen.findByRole('button', { name: 'New capture' }));

    expect(screen.getByLabelText('Capture text')).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
  });
});
