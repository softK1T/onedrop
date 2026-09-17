import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { CollectionScreen } from '@/screens/CollectionScreen';

type Kind = 'tasks' | 'events' | 'expenses' | 'meals' | 'habits' | 'notes';

function renderCollection(kind: Kind): void {
  render(
    <MemoryRouter>
      <CollectionScreen kind={kind} />
    </MemoryRouter>,
  );
}

describe('CollectionScreen', () => {
  it('titles each collection after its entity', () => {
    const titles: Record<Kind, string> = {
      tasks: 'Tasks',
      events: 'Events',
      expenses: 'Expenses',
      meals: 'Meals',
      habits: 'Habits',
      notes: 'Notes',
    };

    for (const [kind, title] of Object.entries(titles) as [Kind, string][]) {
      const { unmount } = render(
        <MemoryRouter>
          <CollectionScreen kind={kind} />
        </MemoryRouter>,
      );
      expect(screen.getByRole('heading', { level: 1, name: title })).toBeInTheDocument();
      unmount();
    }
  });

  it('sends the user to capture for a new record', () => {
    renderCollection('tasks');

    expect(screen.getByRole('link')).toHaveAttribute('href', '/capture');
  });

  it('explains what the screen is for', () => {
    renderCollection('notes');

    expect(
      screen.getByText(/Manage your notes here/),
    ).toBeInTheDocument();
  });
});
