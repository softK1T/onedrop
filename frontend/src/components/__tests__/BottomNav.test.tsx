import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { BottomNav } from '@/components/BottomNav';

function renderNav(route = '/today'): void {
  render(
    <MemoryRouter initialEntries={[route]}>
      <BottomNav />
    </MemoryRouter>,
  );
}

describe('BottomNav', () => {
  it('exposes exactly five labelled destinations', () => {
    renderNav();

    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(5);
    expect(links.map((link) => link.getAttribute('aria-label'))).toEqual([
      'Today',
      'Inbox',
      'Add',
      'Analytics',
      'Profile',
    ]);
  });

  it('is announced as the main navigation', () => {
    renderNav();

    expect(screen.getByRole('navigation', { name: 'Main navigation' })).toBeInTheDocument();
  });

  it('marks the current destination as active', () => {
    renderNav('/analytics');

    const active = screen.getByRole('link', { name: 'Analytics' });
    expect(active.className).toContain('text-accent');
    expect(screen.getByRole('link', { name: 'Today' }).className).toContain('text-ink-muted');
  });

  it('keeps every destination reachable by href', () => {
    renderNav();

    expect(screen.getAllByRole('link').map((link) => link.getAttribute('href'))).toEqual([
      '/today',
      '/inbox',
      '/capture',
      '/analytics',
      '/profile',
    ]);
  });
});
