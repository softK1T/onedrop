import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { OnboardingScreen } from '@/screens/OnboardingScreen';

function renderOnboarding(): void {
  render(
    <MemoryRouter>
      <OnboardingScreen />
    </MemoryRouter>,
  );
}

describe('OnboardingScreen', () => {
  it('states the product promise in one heading', () => {
    renderOnboarding();

    expect(
      screen.getByRole('heading', { name: 'Drop it once. Keep it organized.' }),
    ).toBeInTheDocument();
  });

  it('explains which inputs are supported', () => {
    renderOnboarding();

    expect(
      screen.getByText(
        'Text, voice and food photos become records you can edit, undo and revisit.',
      ),
    ).toBeInTheDocument();
  });

  it('continues into the dashboard', () => {
    renderOnboarding();

    expect(screen.getByRole('link', { name: 'Continue' })).toHaveAttribute('href', '/today');
  });
});
