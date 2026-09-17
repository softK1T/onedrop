import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { Mock } from 'vitest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/lib/api';
import { PrivacyScreen } from '@/screens/PrivacyScreen';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

const postMock = api.post as unknown as Mock;
const delMock = api.del as unknown as Mock;

function renderPrivacy(): void {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <PrivacyScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  postMock.mockReset();
  delMock.mockReset();
  postMock.mockResolvedValue({ tasks: [], events: [] });
  delMock.mockResolvedValue(undefined);
  vi.stubGlobal('URL', {
    ...URL,
    createObjectURL: vi.fn(() => 'blob:onedrop'),
    revokeObjectURL: vi.fn(),
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('PrivacyScreen', () => {
  it('explains export and deletion before anything happens', () => {
    renderPrivacy();

    expect(screen.getByRole('heading', { name: 'Privacy' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Export my data' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete account' })).toBeInTheDocument();
  });

  it('exports the account data as a downloadable file', async () => {
    renderPrivacy();
    await userEvent.click(screen.getByRole('button', { name: 'Export my data' }));

    await waitFor(() => expect(postMock).toHaveBeenCalledWith('/me/export'));
  });

  it('asks for confirmation before deleting the account', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);

    renderPrivacy();
    await userEvent.click(screen.getByRole('button', { name: 'Delete account' }));

    expect(confirmSpy).toHaveBeenCalledWith(
      'This deletes every record and all media. It cannot be undone.',
    );
    expect(delMock).not.toHaveBeenCalled();
  });

  it('deletes the account once the warning is accepted', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    renderPrivacy();
    await userEvent.click(screen.getByRole('button', { name: 'Delete account' }));

    await waitFor(() => expect(delMock).toHaveBeenCalledWith('/me'));
  });
});
