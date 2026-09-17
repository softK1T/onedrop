import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { InboxItem, Operation } from '@/app/types';
import { api } from '@/lib/api';
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
    raw_text: 'Meeting tomorrow at 15:00',
    transcript: null,
    clarification_question: null,
    error: null,
    created_at: '2026-09-17T18:00:00Z',
    ...overrides,
  };
}

function operation(overrides: Partial<Operation> = {}): Operation {
  return {
    inbox_item_id: 'i-1',
    status: 'completed',
    input_type: 'text',
    created: [
      { entity_type: 'event', entity_id: 'e-1' },
      { entity_type: 'expense', entity_id: 'x-1' },
    ],
    clarification_question: null,
    error: null,
    transcript: null,
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
  postMock.mockResolvedValue({});
});

describe('InboxScreen list', () => {
  it('shows skeletons while the list loads', () => {
    getMock.mockReturnValue(new Promise(() => undefined));

    const container = renderInbox();

    expect(container.querySelectorAll('.od-skeleton').length).toBeGreaterThan(0);
  });

  it('shows an empty state without captures', async () => {
    getMock.mockResolvedValue({ items: [], has_more: false });

    renderInbox();

    expect(await screen.findByText('No captures yet.')).toBeInTheDocument();
  });

  it('lists captures with a readable status', async () => {
    getMock.mockResolvedValue({
      items: [item(), item({ id: 'i-2', status: 'needs_confirmation', raw_text: 'Lunch' })],
      has_more: false,
    });

    renderInbox();

    expect(await screen.findByText('Meeting tomorrow at 15:00')).toBeInTheDocument();
    expect(screen.getByText('completed')).toBeInTheDocument();
    expect(screen.getByText('needs confirmation')).toBeInTheDocument();
    expect(getMock.mock.calls[0]?.[0]).toBe('/inbox?limit=30');
  });

  it('retries a failed capture from the list', async () => {
    getMock.mockResolvedValue({
      items: [item({ id: 'i-3', status: 'failed', error: 'ai_failed' })],
      has_more: false,
    });

    renderInbox();
    await userEvent.click(await screen.findByRole('button', { name: 'Retry' }));

    await waitFor(() => expect(postMock).toHaveBeenCalledWith('/inbox/i-3/retry'));
  });

  it('offers a retry when the list request fails', async () => {
    getMock.mockRejectedValueOnce(new Error('network down'));
    getMock.mockResolvedValueOnce({ items: [item()], has_more: false });

    renderInbox();

    expect(await screen.findByText('Could not load captures.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByText('Meeting tomorrow at 15:00')).toBeInTheDocument();
  });
});

describe('InboxScreen detail', () => {
  it('lists every entity created by one capture', async () => {
    getMock.mockResolvedValue(operation());

    renderInbox('/inbox/i-1');

    expect(await screen.findByText('Event')).toBeInTheDocument();
    expect(screen.getByText('Expense')).toBeInTheDocument();
    expect(getMock.mock.calls[0]?.[0]).toBe('/operations/i-1');
  });

  it('undoes every record of a completed capture', async () => {
    getMock.mockResolvedValue(operation());

    renderInbox('/inbox/i-1');
    await userEvent.click(await screen.findByRole('button', { name: 'Undo all' }));

    await waitFor(() => expect(postMock).toHaveBeenCalledWith('/inbox/i-1/undo'));
  });

  it('shows the clarification question and no undo for a pending capture', async () => {
    getMock.mockResolvedValue(
      operation({
        status: 'needs_confirmation',
        created: [],
        clarification_question: 'Which currency did you pay in?',
      }),
    );

    renderInbox('/inbox/i-1');

    expect(await screen.findByText('Which currency did you pay in?')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Undo all' })).toBeNull();
  });

  it('lets a failed capture be retried from the detail view', async () => {
    getMock.mockResolvedValue(
      operation({ status: 'failed', created: [], error: 'provider_unavailable' }),
    );

    renderInbox('/inbox/i-1');
    expect(await screen.findByText('provider_unavailable')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }));

    await waitFor(() => expect(postMock).toHaveBeenCalledWith('/inbox/i-1/retry'));
  });
});
