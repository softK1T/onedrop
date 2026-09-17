import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthGate } from '@/components/AuthGate';
import { ApiError } from '@/lib/api';
import { bootstrapSession, loginWithDev } from '@/lib/auth';

vi.mock('@/lib/auth', () => ({
  bootstrapSession: vi.fn(),
  loginWithDev: vi.fn(),
  DEV_LOGIN_ENABLED: true,
}));

const bootstrapMock = bootstrapSession as unknown as Mock;
const devLoginMock = loginWithDev as unknown as Mock;

function renderGate(): HTMLElement {
  const { container } = render(
    <AuthGate>
      <p>Protected content</p>
    </AuthGate>,
  );
  return container;
}

beforeEach(() => {
  bootstrapMock.mockReset();
  devLoginMock.mockReset();
});

describe('AuthGate', () => {
  it('shows a busy skeleton while the session is being established', () => {
    bootstrapMock.mockReturnValue(new Promise(() => undefined));

    const container = renderGate();

    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(screen.queryByText('Protected content')).toBeNull();
  });

  it('renders the app once the session is ready', async () => {
    bootstrapMock.mockResolvedValue('telegram');

    renderGate();

    expect(await screen.findByText('Protected content')).toBeInTheDocument();
  });

  it('shows the API message and a dev login when bootstrap fails', async () => {
    bootstrapMock.mockRejectedValue(new ApiError(401, 'invalid_init_data', 'Init data expired'));

    renderGate();

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Init data expired')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Continue with dev login' })).toBeInTheDocument();
  });

  it('lets the dev login recover from a failed bootstrap', async () => {
    bootstrapMock.mockRejectedValue(new ApiError(401, 'invalid_init_data', 'Init data expired'));
    devLoginMock.mockResolvedValue('dev');

    renderGate();
    await userEvent.click(await screen.findByRole('button', { name: 'Continue with dev login' }));

    await waitFor(() => expect(screen.getByText('Protected content')).toBeInTheDocument());
    expect(devLoginMock).toHaveBeenCalledTimes(1);
  });

  it('falls back to a generic message for a non API failure', async () => {
    bootstrapMock.mockRejectedValue(new Error('offline'));

    renderGate();

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getAllByText('Could not sign you in').length).toBeGreaterThan(0);
  });
});
