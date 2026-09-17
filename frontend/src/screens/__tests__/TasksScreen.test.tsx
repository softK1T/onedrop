import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { COLLECTION_MESSAGES, collectionLabel } from '@/i18n/collections';
import { api } from '@/lib/api';
import type { TaskPage, TaskRecord } from '@/lib/tasks';
import { TasksScreen } from '@/screens/TasksScreen';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

const getMock = api.get as unknown as Mock;
const postMock = api.post as unknown as Mock;
const patchMock = api.patch as unknown as Mock;
const delMock = api.del as unknown as Mock;

function task(overrides: Partial<TaskRecord> = {}): TaskRecord {
  return {
    id: 't-1',
    title: 'Pay the internet bill',
    description: null,
    due_at: '2026-09-18T15:00:00Z',
    priority: 'high',
    status: 'open',
    category: null,
    reminder_at: null,
    completed_at: null,
    source_inbox_item_id: null,
    created_at: '2026-09-17T10:00:00Z',
    ...overrides,
  };
}

function page(items: TaskRecord[] = [task()]): TaskPage {
  return { items, limit: 50, offset: 0, has_more: false, filter: 'today' };
}

function renderTasks(): HTMLElement {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const { container } = render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <TasksScreen />
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
  postMock.mockResolvedValue(task({ id: 't-2' }));
  patchMock.mockResolvedValue(task());
  delMock.mockResolvedValue(undefined);
});

describe('TasksScreen', () => {
  it('loads the today filter first', async () => {
    renderTasks();

    expect(await screen.findByText('Pay the internet bill')).toBeInTheDocument();
    expect(getMock.mock.calls[0]?.[0]).toBe('/tasks?filter=today&limit=50');
  });

  it('switches the filter and reloads the list', async () => {
    renderTasks();
    await screen.findByText('Pay the internet bill');

    await userEvent.click(screen.getByRole('tab', { name: 'Completed' }));

    await waitFor(() =>
      expect(getMock).toHaveBeenCalledWith('/tasks?filter=completed&limit=50'),
    );
    expect(screen.getByRole('tab', { name: 'Completed' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
  });

  it('shows the empty state for a filter without tasks', async () => {
    getMock.mockResolvedValue(page([]));

    renderTasks();

    expect(
      await screen.findByText('Nothing here yet. Add a task or capture one.'),
    ).toBeInTheDocument();
  });

  it('creates a task and shows it before the server answers', async () => {
    postMock.mockReturnValue(new Promise(() => undefined));

    renderTasks();
    await screen.findByText('Pay the internet bill');
    await userEvent.type(screen.getByLabelText('New task'), 'Call the dentist');
    await userEvent.click(screen.getByRole('button', { name: 'Add task' }));

    expect(await screen.findByText('Call the dentist')).toBeInTheDocument();
    expect(postMock).toHaveBeenCalledWith('/tasks', {
      title: 'Call the dentist',
      due_at: null,
      priority: 'normal',
    });
  });

  it('keeps the add button disabled for an empty title', async () => {
    renderTasks();
    await screen.findByText('Pay the internet bill');

    expect(screen.getByRole('button', { name: 'Add task' })).toBeDisabled();
  });

  it('renames a task inline', async () => {
    renderTasks();
    await screen.findByText('Pay the internet bill');
    await userEvent.click(screen.getByRole('button', { name: 'Edit' }));

    const field = screen.getByLabelText('Edit');
    await userEvent.clear(field);
    await userEvent.type(field, 'Pay the internet');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith('/tasks/t-1', { title: 'Pay the internet' }),
    );
    expect(await screen.findByText('Pay the internet')).toBeInTheDocument();
  });

  it('leaves the task untouched when editing is cancelled', async () => {
    renderTasks();
    await screen.findByText('Pay the internet bill');
    await userEvent.click(screen.getByRole('button', { name: 'Edit' }));
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(patchMock).not.toHaveBeenCalled();
    expect(screen.getByText('Pay the internet bill')).toBeInTheDocument();
  });

  it('completes a task through the dedicated endpoint', async () => {
    renderTasks();
    await screen.findByText('Pay the internet bill');
    await userEvent.click(screen.getByRole('button', { name: 'Done' }));

    await waitFor(() => expect(postMock).toHaveBeenCalledWith('/tasks/t-1/complete'));
  });

  it('removes a task optimistically', async () => {
    delMock.mockReturnValue(new Promise(() => undefined));

    renderTasks();
    await screen.findByText('Pay the internet bill');
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));

    await waitFor(() => expect(screen.queryByText('Pay the internet bill')).toBeNull());
    expect(delMock).toHaveBeenCalledWith('/tasks/t-1');
  });

  it('restores a deleted task when the request fails', async () => {
    delMock.mockRejectedValue(new Error('network down'));

    renderTasks();
    await screen.findByText('Pay the internet bill');
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That change was not saved and has been reverted.',
    );
    await waitFor(() => expect(screen.getByText('Pay the internet bill')).toBeInTheDocument());
  });

  it('offers a retry when the list cannot be loaded', async () => {
    getMock.mockRejectedValueOnce(new Error('network down'));
    getMock.mockResolvedValueOnce(page());

    renderTasks();

    expect(await screen.findByText('Could not load tasks.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByText('Pay the internet bill')).toBeInTheDocument();
  });

  it('ships every collection label in every locale', () => {
    const keys = Object.keys(COLLECTION_MESSAGES.en).sort();
    for (const locale of ['en', 'ru', 'pl', 'uk'] as const) {
      expect(Object.keys(COLLECTION_MESSAGES[locale]).sort()).toEqual(keys);
      for (const key of keys) expect(collectionLabel(locale, key)).not.toBe(key);
    }
  });
});
