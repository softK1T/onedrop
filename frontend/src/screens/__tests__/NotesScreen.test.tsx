import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { NOTE_MESSAGES, noteLabel } from '@/i18n/notes';
import { api } from '@/lib/api';
import { type NotePage, type NoteRecord, parseTags } from '@/lib/notes';
import { NotesScreen } from '@/screens/NotesScreen';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

const getMock = api.get as unknown as Mock;
const postMock = api.post as unknown as Mock;
const patchMock = api.patch as unknown as Mock;
const delMock = api.del as unknown as Mock;

function note(overrides: Partial<NoteRecord> = {}): NoteRecord {
  return {
    id: 'n-1',
    title: 'Reading list',
    content: 'Domain-Driven Design',
    tags: ['books'],
    pinned: false,
    source_inbox_item_id: null,
    created_at: '2026-09-17T10:00:00Z',
    updated_at: '2026-09-17T10:00:00Z',
    ...overrides,
  };
}

function page(items: NoteRecord[] = [note()], search: string | null = null): NotePage {
  return { items, search, limit: 50, offset: 0, has_more: false };
}

function renderNotes(): HTMLElement {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const { container } = render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <NotesScreen />
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
  postMock.mockResolvedValue(note({ id: 'n-2' }));
  patchMock.mockResolvedValue(note());
  delMock.mockResolvedValue(undefined);
});

describe('NotesScreen', () => {
  it('lists notes with their tags', async () => {
    renderNotes();

    expect(await screen.findByText('Domain-Driven Design')).toBeInTheDocument();
    expect(screen.getByText('books')).toBeInTheDocument();
    expect(getMock.mock.calls[0]?.[0]).toBe('/notes?limit=50');
  });

  it('searches notes through the API', async () => {
    renderNotes();
    await screen.findByText('Domain-Driven Design');

    await userEvent.type(screen.getByLabelText('Search notes'), 'design');
    await userEvent.click(screen.getByRole('button', { name: 'Search' }));

    await waitFor(() =>
      expect(getMock).toHaveBeenCalledWith('/notes?limit=50&search=design'),
    );
  });

  it('tells the difference between an empty list and an empty search', async () => {
    getMock.mockResolvedValue(page([]));

    renderNotes();
    expect(await screen.findByText('No notes yet.')).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText('Search notes'), 'zzz');
    await userEvent.click(screen.getByRole('button', { name: 'Search' }));

    expect(await screen.findByText('Nothing matches that search.')).toBeInTheDocument();
  });

  it('creates a note and shows it before the server answers', async () => {
    postMock.mockReturnValue(new Promise(() => undefined));

    renderNotes();
    await screen.findByText('Domain-Driven Design');
    await userEvent.type(screen.getByLabelText('Title'), 'Groceries');
    await userEvent.type(screen.getByLabelText('Note'), 'Milk and bread');
    await userEvent.type(screen.getByLabelText('Tags, comma separated'), 'home, shopping');
    await userEvent.click(screen.getByRole('button', { name: 'Add note' }));

    expect(await screen.findByText('Milk and bread')).toBeInTheDocument();
    expect(postMock).toHaveBeenCalledWith('/notes', {
      title: 'Groceries',
      content: 'Milk and bread',
      tags: ['home', 'shopping'],
      pinned: false,
    });
  });

  it('keeps the add button disabled without content', async () => {
    renderNotes();
    await screen.findByText('Domain-Driven Design');

    expect(screen.getByRole('button', { name: 'Add note' })).toBeDisabled();
  });

  it('edits the note body inline', async () => {
    renderNotes();
    await screen.findByText('Domain-Driven Design');
    await userEvent.click(screen.getByRole('button', { name: 'Edit' }));

    const field = screen.getByLabelText('Edit');
    await userEvent.clear(field);
    await userEvent.type(field, 'Refactoring');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith('/notes/n-1', { content: 'Refactoring' }),
    );
    expect(await screen.findByText('Refactoring')).toBeInTheDocument();
  });

  it('pins and unpins a note', async () => {
    renderNotes();
    await screen.findByText('Domain-Driven Design');
    await userEvent.click(screen.getByRole('button', { name: 'Pin' }));

    await waitFor(() =>
      expect(postMock).toHaveBeenCalledWith('/notes/n-1/pin', { pinned: true }),
    );
    expect(await screen.findByRole('button', { name: 'Unpin' })).toBeInTheDocument();
  });

  it('converts a note into a task', async () => {
    renderNotes();
    await screen.findByText('Domain-Driven Design');
    await userEvent.click(screen.getByRole('button', { name: 'Make a task' }));

    await waitFor(() =>
      expect(postMock).toHaveBeenCalledWith('/notes/n-1/convert-to-task', {
        due_at: null,
        keep_note: true,
      }),
    );
    expect(await screen.findByRole('status')).toHaveTextContent(
      'A task was created from this note.',
    );
  });

  it('deletes a note optimistically', async () => {
    delMock.mockReturnValue(new Promise(() => undefined));

    renderNotes();
    await screen.findByText('Domain-Driven Design');
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));

    await waitFor(() => expect(screen.queryByText('Domain-Driven Design')).toBeNull());
    expect(delMock).toHaveBeenCalledWith('/notes/n-1');
  });

  it('restores a deleted note when the request fails', async () => {
    delMock.mockRejectedValue(new Error('network down'));

    renderNotes();
    await screen.findByText('Domain-Driven Design');
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That change was not saved and has been reverted.',
    );
    await waitFor(() => expect(screen.getByText('Domain-Driven Design')).toBeInTheDocument());
  });

  it('offers a retry when notes cannot be loaded', async () => {
    getMock.mockRejectedValueOnce(new Error('network down'));
    getMock.mockResolvedValueOnce(page());

    renderNotes();

    expect(await screen.findByText('Could not load notes.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByText('Domain-Driven Design')).toBeInTheDocument();
  });

  it('trims and caps tags at the backend limit', () => {
    expect(parseTags(' home , shopping ,, ')).toEqual(['home', 'shopping']);
    expect(parseTags('a,b,c,d,e,f,g,h,i,j,k,l')).toHaveLength(10);
  });

  it('ships every note label in every locale', () => {
    const keys = Object.keys(NOTE_MESSAGES.en).sort();
    for (const locale of ['en', 'ru', 'pl', 'uk'] as const) {
      expect(Object.keys(NOTE_MESSAGES[locale]).sort()).toEqual(keys);
      for (const key of keys) expect(noteLabel(locale, key)).not.toBe(key);
    }
  });
});
