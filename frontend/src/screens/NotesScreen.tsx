import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { EmptyCard, ErrorCard, ScreenHeader } from '@/components/ScreenHeader';
import { noteLabel } from '@/i18n/notes';
import {
  type NoteDraft,
  type NotePage,
  type NoteRecord,
  convertNoteToTask,
  createNote,
  deleteNote,
  listNotes,
  noteListKey,
  parseTags,
  patchNote,
  pinNote,
} from '@/lib/notes';

function draftRecord(draft: NoteDraft): NoteRecord {
  const now = new Date().toISOString();
  return {
    id: `optimistic-${Date.now()}`,
    title: draft.title ?? null,
    content: draft.content,
    tags: draft.tags ?? [],
    pinned: draft.pinned ?? false,
    source_inbox_item_id: null,
    created_at: now,
    updated_at: now,
  };
}

export function NotesScreen(): JSX.Element {
  const client = useQueryClient();
  const [search, setSearch] = useState('');
  const [term, setTerm] = useState('');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [tags, setTags] = useState('');
  const [editing, setEditing] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');

  const key = noteListKey(search);
  const query = useQuery({ queryKey: key, queryFn: () => listNotes(search) });
  const t = (label: string): string => noteLabel(null, label);

  const applyOptimistic = async (
    update: (page: NotePage) => NotePage,
  ): Promise<{ previous: NotePage | undefined }> => {
    await client.cancelQueries({ queryKey: key });
    const previous = client.getQueryData<NotePage>(key);
    if (previous) client.setQueryData<NotePage>(key, update(previous));
    return { previous };
  };

  const rollback = (context: { previous: NotePage | undefined } | undefined): void => {
    if (context?.previous) client.setQueryData<NotePage>(key, context.previous);
  };

  const settle = (): void => void client.invalidateQueries({ queryKey: ['notes'] });

  const create = useMutation({
    mutationFn: (draft: NoteDraft) => createNote(draft),
    onMutate: (draft: NoteDraft) =>
      applyOptimistic((page) => ({ ...page, items: [draftRecord(draft), ...page.items] })),
    onError: (_error, _draft, context) => rollback(context),
    onSettled: settle,
  });

  const edit = useMutation({
    mutationFn: ({ id, value }: { id: string; value: string }) =>
      patchNote(id, { content: value }),
    onMutate: ({ id, value }: { id: string; value: string }) =>
      applyOptimistic((page) => ({
        ...page,
        items: page.items.map((item) => (item.id === id ? { ...item, content: value } : item)),
      })),
    onError: (_error, _variables, context) => rollback(context),
    onSettled: settle,
  });

  const pin = useMutation({
    mutationFn: ({ id, pinned }: { id: string; pinned: boolean }) => pinNote(id, pinned),
    onMutate: ({ id, pinned }: { id: string; pinned: boolean }) =>
      applyOptimistic((page) => ({
        ...page,
        items: page.items.map((item) => (item.id === id ? { ...item, pinned } : item)),
      })),
    onError: (_error, _variables, context) => rollback(context),
    onSettled: settle,
  });

  const convert = useMutation({
    mutationFn: (id: string) => convertNoteToTask(id),
    onSettled: () => {
      void client.invalidateQueries({ queryKey: ['notes'] });
      void client.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteNote(id),
    onMutate: (id: string) =>
      applyOptimistic((page) => ({
        ...page,
        items: page.items.filter((item) => item.id !== id),
      })),
    onError: (_error, _id, context) => rollback(context),
    onSettled: settle,
  });

  const failed = create.isError || edit.isError || pin.isError || remove.isError || convert.isError;

  const submit = (): void => {
    const body = content.trim();
    if (!body) return;
    create.mutate({
      title: title.trim() ? title.trim() : null,
      content: body,
      tags: parseTags(tags),
      pinned: false,
    });
    setTitle('');
    setContent('');
    setTags('');
  };

  return (
    <section className="p-4">
      <ScreenHeader title={t('notes')} actionTo="/capture" actionLabel="+" />

      <form
        className="mb-4 flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          setSearch(term.trim());
        }}
      >
        <input
          className="w-full rounded-card border border-line bg-surface p-3"
          aria-label={t('searchLabel')}
          value={term}
          onChange={(event) => setTerm(event.target.value)}
        />
        <button className="od-button-ghost whitespace-nowrap text-sm">{t('search')}</button>
        {search && (
          <button
            type="button"
            className="od-button-ghost whitespace-nowrap text-sm"
            onClick={() => {
              setTerm('');
              setSearch('');
            }}
          >
            {t('clear')}
          </button>
        )}
      </form>

      <form
        className="od-card space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <p className="od-label">{t('newNote')}</p>
        <input
          className="w-full rounded-card border border-line bg-surface p-3"
          aria-label={t('noteTitle')}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
        <textarea
          className="min-h-24 w-full rounded-card border border-line bg-surface p-3"
          aria-label={t('content')}
          placeholder={t('contentPlaceholder')}
          value={content}
          onChange={(event) => setContent(event.target.value)}
        />
        <input
          className="w-full rounded-card border border-line bg-surface p-3"
          aria-label={t('tags')}
          value={tags}
          onChange={(event) => setTags(event.target.value)}
        />
        <button
          className="od-button-primary w-full disabled:opacity-50"
          disabled={!content.trim()}
        >
          {t('add')}
        </button>
      </form>

      {failed && (
        <p className="mt-3 rounded-card bg-danger/15 p-3 text-sm text-danger" role="alert">
          {t('saveFailed')}
        </p>
      )}
      {convert.isSuccess && (
        <p className="mt-3 rounded-card bg-positive/15 p-3 text-sm text-positive" role="status">
          {t('converted')}
        </p>
      )}

      <div className="mt-4">
        {query.isLoading && <div className="od-skeleton h-20" aria-busy="true" />}
        {query.isError && (
          <ErrorCard message={t('loadFailed')} retry={() => void query.refetch()} />
        )}
        {query.data && query.data.items.length === 0 && (
          <EmptyCard>{search ? t('noMatches') : t('empty')}</EmptyCard>
        )}
        {query.data && query.data.items.length > 0 && (
          <ul className="space-y-3">
            {query.data.items.map((item) => (
              <li className="od-card" key={item.id}>
                {editing === item.id ? (
                  <div className="space-y-3">
                    <textarea
                      className="min-h-24 w-full rounded-card border border-line bg-surface p-3"
                      aria-label={t('edit')}
                      value={editContent}
                      onChange={(event) => setEditContent(event.target.value)}
                    />
                    <div className="flex gap-2">
                      <button
                        className="od-button-primary flex-1"
                        onClick={() => {
                          const value = editContent.trim();
                          if (value && value !== item.content) edit.mutate({ id: item.id, value });
                          setEditing(null);
                        }}
                      >
                        {t('save')}
                      </button>
                      <button className="od-button-ghost flex-1" onClick={() => setEditing(null)}>
                        {t('cancel')}
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    {item.title && <p className="font-medium">{item.title}</p>}
                    <p className="mt-1 whitespace-pre-line text-sm">{item.content}</p>
                    {item.tags.length > 0 && (
                      <p className="mt-2 text-xs text-ink-muted">{item.tags.join(' · ')}</p>
                    )}
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        className="od-button-ghost text-sm"
                        onClick={() => pin.mutate({ id: item.id, pinned: !item.pinned })}
                      >
                        {item.pinned ? t('unpin') : t('pin')}
                      </button>
                      <button
                        className="od-button-ghost text-sm"
                        onClick={() => {
                          setEditing(item.id);
                          setEditContent(item.content);
                        }}
                      >
                        {t('edit')}
                      </button>
                      <button
                        className="od-button-ghost text-sm"
                        disabled={convert.isPending}
                        onClick={() => convert.mutate(item.id)}
                      >
                        {t('convert')}
                      </button>
                      <button
                        className="od-button-ghost text-sm text-danger"
                        onClick={() => remove.mutate(item.id)}
                      >
                        {t('remove')}
                      </button>
                    </div>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
