import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { EVENT_MESSAGES, eventLabel } from '@/i18n/events';
import { api } from '@/lib/api';
import type { EventPage, EventRecord } from '@/lib/events';
import { EventsScreen } from '@/screens/EventsScreen';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

const getMock = api.get as unknown as Mock;
const postMock = api.post as unknown as Mock;
const patchMock = api.patch as unknown as Mock;
const delMock = api.del as unknown as Mock;

function event(overrides: Partial<EventRecord> = {}): EventRecord {
  return {
    id: 'e-1',
    title: 'Meeting with Andrew',
    starts_at: '2026-09-18T13:00:00Z',
    ends_at: null,
    location: 'Office',
    description: null,
    reminder_at: null,
    status: 'planned',
    source_inbox_item_id: null,
    created_at: '2026-09-17T10:00:00Z',
    ...overrides,
  };
}

function page(items: EventRecord[] = [event()]): EventPage {
  return {
    items,
    range: 'day',
    anchor_date: '2026-09-18',
    limit: 50,
    offset: 0,
    has_more: false,
  };
}

function renderEvents(): HTMLElement {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const { container } = render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <EventsScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return container;
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  patchMock.mockReset();
  delMock.mockReset();
  getMock.mockResolvedValue(page());
  postMock.mockResolvedValue({ event: event({ id: 'e-2' }), conflicts: [] });
  patchMock.mockResolvedValue({ event: event(), conflicts: [] });
  delMock.mockResolvedValue(undefined);
});

describe('EventsScreen', () => {
  it('loads the day agenda first', async () => {
    renderEvents();

    expect(await screen.findByText('Meeting with Andrew')).toBeInTheDocument();
    expect(getMock.mock.calls[0]?.[0]).toBe('/events?period=day&limit=50');
  });

  it('switches to the week agenda', async () => {
    renderEvents();
    await screen.findByText('Meeting with Andrew');

    await userEvent.click(screen.getByRole('tab', { name: 'Week' }));

    await waitFor(() =>
      expect(getMock).toHaveBeenCalledWith('/events?period=week&limit=50'),
    );
  });

  it('asks the API for a specific date', async () => {
    renderEvents();
    await screen.findByText('Meeting with Andrew');

    await userEvent.type(screen.getByLabelText('Date'), '2026-09-20');

    await waitFor(() =>
      expect(getMock).toHaveBeenCalledWith('/events?period=day&limit=50&date=2026-09-20'),
    );
  });

  it('shows an empty agenda state', async () => {
    getMock.mockResolvedValue(page([]));

    renderEvents();

    expect(await screen.findByText('Nothing scheduled for this period.')).toBeInTheDocument();
  });

  it('keeps the add button disabled without a title and a start', async () => {
    renderEvents();
    await screen.findByText('Meeting with Andrew');

    expect(screen.getByRole('button', { name: 'Add event' })).toBeDisabled();

    await userEvent.type(screen.getByLabelText('Title'), 'Dentist');

    expect(screen.getByRole('button', { name: 'Add event' })).toBeDisabled();
  });

  it('creates an event with an ISO start time', async () => {
    postMock.mockReturnValue(new Promise(() => undefined));

    renderEvents();
    await screen.findByText('Meeting with Andrew');
    await userEvent.type(screen.getByLabelText('Title'), 'Dentist');
    await userEvent.type(screen.getByLabelText('Starts'), '2026-09-20T10:00');
    await userEvent.type(screen.getByLabelText('Location'), 'Clinic');
    await userEvent.click(screen.getByRole('button', { name: 'Add event' }));

    expect(await screen.findByText('Dentist')).toBeInTheDocument();
    const body = postMock.mock.calls[0]?.[1] as Record<string, unknown>;
    expect(postMock.mock.calls[0]?.[0]).toBe('/events');
    expect(body.title).toBe('Dentist');
    expect(body.location).toBe('Clinic');
    expect(String(body.starts_at)).toContain('2026-09-20');
  });

  it('reports an overlap without blocking the save', async () => {
    postMock.mockResolvedValue({ event: event({ id: 'e-2' }), conflicts: ['e-1'] });

    renderEvents();
    await screen.findByText('Meeting with Andrew');
    await userEvent.type(screen.getByLabelText('Title'), 'Dentist');
    await userEvent.type(screen.getByLabelText('Starts'), '2026-09-20T10:00');
    await userEvent.click(screen.getByRole('button', { name: 'Add event' }));

    expect(await screen.findByRole('status')).toHaveTextContent(
      'This event overlaps another one. Nothing was blocked.',
    );
  });

  it('renames an event inline', async () => {
    renderEvents();
    await screen.findByText('Meeting with Andrew');
    await userEvent.click(screen.getByRole('button', { name: 'Edit' }));

    const field = screen.getByLabelText('Edit');
    await userEvent.clear(field);
    await userEvent.type(field, 'Meeting with Anna');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith('/events/e-1', { title: 'Meeting with Anna' }),
    );
    expect(await screen.findByText('Meeting with Anna')).toBeInTheDocument();
  });

  it('marks an event done and cancels another', async () => {
    renderEvents();
    await screen.findByText('Meeting with Andrew');
    await userEvent.click(screen.getByRole('button', { name: 'Done' }));

    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith('/events/e-1', { status: 'done' }),
    );

    getMock.mockResolvedValue(page([event({ id: 'e-3', title: 'Standup' })]));
    await userEvent.click(screen.getByRole('tab', { name: 'Week' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Cancel event' }));

    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith('/events/e-3', { status: 'cancelled' }),
    );
  });

  it('deletes an event optimistically', async () => {
    delMock.mockReturnValue(new Promise(() => undefined));

    renderEvents();
    await screen.findByText('Meeting with Andrew');
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));

    await waitFor(() => expect(screen.queryByText('Meeting with Andrew')).toBeNull());
    expect(delMock).toHaveBeenCalledWith('/events/e-1');
  });

  it('restores a deleted event when the request fails', async () => {
    delMock.mockRejectedValue(new Error('network down'));

    renderEvents();
    await screen.findByText('Meeting with Andrew');
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That change was not saved and has been reverted.',
    );
    await waitFor(() => expect(screen.getByText('Meeting with Andrew')).toBeInTheDocument());
  });

  it('offers a retry when the agenda cannot be loaded', async () => {
    getMock.mockRejectedValueOnce(new Error('network down'));
    getMock.mockResolvedValueOnce(page());

    renderEvents();

    expect(await screen.findByText('Could not load events.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByText('Meeting with Andrew')).toBeInTheDocument();
  });

  it('ships every event label in every locale', () => {
    const keys = Object.keys(EVENT_MESSAGES.en).sort();
    for (const locale of ['en', 'ru', 'pl', 'uk'] as const) {
      expect(Object.keys(EVENT_MESSAGES[locale]).sort()).toEqual(keys);
      for (const key of keys) expect(eventLabel(locale, key)).not.toBe(key);
    }
  });
});
