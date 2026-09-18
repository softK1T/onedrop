import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { InboxItem, Operation } from '@/app/types';
import { INBOX_MESSAGES, inboxLabel } from '@/i18n/inbox';
import { api } from '@/lib/api';
import { type InboxPage, captureText, shortTitle } from '@/lib/inbox';
import { InboxScreen } from '@/screens/InboxScreen';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

const getMock = api.get as unknown as Mock;
const postMock = api.post as unknown as Mock;

function item(overrides: Partial<InboxItem> = {}): InboxItem {
  return {
    id: 'i-1',
    input_type: 'text',
    status: 'completed',
    raw_text: 'Pay the internet bill tomorrow',
    transcript: null,
    clarification_question: null,
    error: null,
    created_at: '2026-09-17T18:00:00Z',
    ...overrides,
  };
}

function page(items: InboxItem[] = [item()]): InboxPage {
  return { items, limit: 30, offset: 0, has_more: false };
}

function operation(overrides: Partial<Operation> = {}): Operation {
  return {
    inbox_item_id: 'i-1',
    status: 'completed',
    input_type: 'text',
    created: [{ entity_type: 'task', entity_id: 't-1' }],
    clarification_question: null,
    error: null,
    transcript: null,
    ai_result: null,
    processing_ms: null,
    created_at: '2026-09-17T18:00:00Z',
    ...overrides,
  };
}

function renderInbox(route = '/inbox'): HTMLElement {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const { container } = render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/inbox" element={<InboxScreen />} />
          <Route path="/inbox/:id" element={<InboxScreen />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return container;
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  getMock.mockImplementation((path: string) =>
    Promise.resolve(String(path).startsWith('/operations/') ? operation() : page()),
  );
  postMock.mockResolvedValue({});
});

describe('InboxScreen list', () => {
  it('lists captures with their status', async () => {
    renderInbox();

    expect(await screen.findByText('Pay the internet bill tomorrow')).toBeInTheDocument();
    expect(screen.getByText('completed')).toBeInTheDocument();
    expect(getMock.mock.calls[0]?.[0]).toBe('/inbox?limit=30');
  });

  it('filters by status through the API', async () => {
    renderInbox();
    await screen.findByText('Pay the internet bill tomorrow');

    await userEvent.click(screen.getByRole('tab', { name: 'Failed' }));

    await waitFor(() =>
      expect(getMock).toHaveBeenCalledWith('/inbox?limit=30&status=failed'),
    );
  });

  it('shows an empty state', async () => {
    getMock.mockImplementation((path: string) =>
      Promise.resolve(String(path).startsWith('/operations/') ? operation() : page([])),
    );

    renderInbox();

    expect(await screen.findByText('No captures yet.')).toBeInTheDocument();
  });

  it('turns a capture into a task', async () => {
    renderInbox();
    await screen.findByText('Pay the internet bill tomorrow');
    await userEvent.click(screen.getByRole('button', { name: 'To task' }));

    await waitFor(() =>
      expect(postMock).toHaveBeenCalledWith('/tasks', {
        title: 'Pay the internet bill tomorrow',
      }),
    );
    expect(await screen.findByText('A task was created from this capture.')).toBeInTheDocument();
  });

  it('turns a capture into a note', async () => {
    renderInbox();
    await screen.findByText('Pay the internet bill tomorrow');
    await userEvent.click(screen.getByRole('button', { name: 'To note' }));

    await waitFor(() =>
      expect(postMock).toHaveBeenCalledWith('/notes', {
        content: 'Pay the internet bill tomorrow',
      }),
    );
  });

  it('asks for a start time before creating an event', async () => {
    renderInbox();
    await screen.findByText('Pay the internet bill tomorrow');
    await userEvent.click(screen.getByRole('button', { name: 'To event' }));

    expect(screen.getByRole('button', { name: 'Create' })).toBeDisabled();
    expect(postMock).not.toHaveBeenCalled();

    await userEvent.type(screen.getByLabelText('Event start'), '2026-09-20T10:00');
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));

    await waitFor(() => expect(postMock).toHaveBeenCalled());
    const [path, body] = postMock.mock.calls[0] as [string, Record<string, unknown>];
    expect(path).toBe('/events');
    expect(body.title).toBe('Pay the internet bill tomorrow');
    expect(String(body.starts_at)).toContain('2026-09-20');
  });

  it('cannot convert a capture without text', async () => {
    getMock.mockImplementation((path: string) =>
      Promise.resolve(
        String(path).startsWith('/operations/')
          ? operation()
          : page([item({ raw_text: null, transcript: null, input_type: 'voice' })]),
      ),
    );

    renderInbox();

    expect(
      await screen.findByText('This capture has no text to convert.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'To task' })).toBeDisabled();
  });

  it('rates a capture result', async () => {
    renderInbox();
    await screen.findByText('Pay the internet bill tomorrow');
    await userEvent.click(screen.getByRole('button', { name: 'Bad result' }));

    await waitFor(() =>
      expect(postMock).toHaveBeenCalledWith('/inbox/i-1/feedback', { rating: -1 }),
    );
    expect(await screen.findByText('Thanks, the rating was saved.')).toBeInTheDocument();
  });

  it('retries a failed capture', async () => {
    getMock.mockImplementation((path: string) =>
      Promise.resolve(
        String(path).startsWith('/operations/')
          ? operation()
          : page([item({ status: 'failed', error: 'ai_failed' })]),
      ),
    );

    renderInbox();
    await userEvent.click(await screen.findByRole('button', { name: 'Retry' }));

    await waitFor(() => expect(postMock).toHaveBeenCalledWith('/inbox/i-1/retry'));
  });

  it('undoes a completed capture', async () => {
    renderInbox();
    await screen.findByText('Pay the internet bill tomorrow');
    await userEvent.click(screen.getByRole('button', { name: 'Undo all' }));

    await waitFor(() => expect(postMock).toHaveBeenCalledWith('/inbox/i-1/undo'));
  });

  it('reports a failed action', async () => {
    postMock.mockRejectedValue(new Error('network down'));

    renderInbox();
    await screen.findByText('Pay the internet bill tomorrow');
    await userEvent.click(screen.getByRole('button', { name: 'To task' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That action did not go through.',
    );
  });

  it('offers a retry when the list cannot be loaded', async () => {
    getMock.mockRejectedValueOnce(new Error('network down'));
    getMock.mockImplementation((path: string) =>
      Promise.resolve(String(path).startsWith('/operations/') ? operation() : page()),
    );

    renderInbox();

    expect(await screen.findByText('Could not load captures.')).toBeInTheDocument();
  });
});

describe('InboxScreen detail', () => {
  it('lists the entities one capture created', async () => {
    renderInbox('/inbox/i-1');

    expect(await screen.findByText('Task')).toBeInTheDocument();
    expect(getMock.mock.calls[0]?.[0]).toBe('/operations/i-1');
  });

  it('undoes everything from the detail view', async () => {
    renderInbox('/inbox/i-1');
    await userEvent.click(await screen.findByRole('button', { name: 'Undo all' }));

    await waitFor(() => expect(postMock).toHaveBeenCalledWith('/inbox/i-1/undo'));
  });

  it('shows the clarification question of a pending capture', async () => {
    getMock.mockImplementation((path: string) =>
      Promise.resolve(
        String(path).startsWith('/operations/')
          ? operation({
              status: 'needs_confirmation',
              created: [],
              clarification_question: 'Which day did you mean?',
            })
          : page(),
      ),
    );

    renderInbox('/inbox/i-1');

    expect(await screen.findByText('Which day did you mean?')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Undo all' })).toBeNull();
  });
});

describe('inbox helpers', () => {
  it('prefers raw text and falls back to the transcript', () => {
    expect(captureText(item())).toBe('Pay the internet bill tomorrow');
    expect(captureText(item({ raw_text: null, transcript: ' spoken text ' }))).toBe(
      'spoken text',
    );
    expect(captureText(item({ raw_text: null, transcript: null }))).toBe('');
  });

  it('keeps a converted title within the backend limit', () => {
    expect(shortTitle('a\n  b')).toBe('a b');
    expect(shortTitle('x'.repeat(250)).length).toBe(200);
  });

  it('ships every inbox label in every locale', () => {
    const keys = Object.keys(INBOX_MESSAGES.en).sort();
    for (const locale of ['en', 'ru', 'pl', 'uk'] as const) {
      expect(Object.keys(INBOX_MESSAGES[locale]).sort()).toEqual(keys);
      for (const key of keys) expect(inboxLabel(locale, key)).not.toBe(key);
    }
  });
});
