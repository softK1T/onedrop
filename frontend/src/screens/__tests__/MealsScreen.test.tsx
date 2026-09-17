import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MEAL_MESSAGES, mealLabel } from '@/i18n/meals';
import { api } from '@/lib/api';
import {
  type DailyNutrition,
  type MealPage,
  type MealRecord,
  optionalNumber,
} from '@/lib/meals';
import { MealsScreen } from '@/screens/MealsScreen';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

const getMock = api.get as unknown as Mock;
const postMock = api.post as unknown as Mock;
const patchMock = api.patch as unknown as Mock;
const delMock = api.del as unknown as Mock;

function meal(overrides: Partial<MealRecord> = {}): MealRecord {
  return {
    id: 'm-1',
    title: 'Chicken and rice',
    meal_type: 'lunch',
    eaten_at: '2026-09-18T12:00:00Z',
    calories: 620,
    protein: 45,
    fat: 18,
    carbohydrates: 70,
    estimated: true,
    source_inbox_item_id: null,
    created_at: '2026-09-18T12:00:00Z',
    ...overrides,
  };
}

function page(items: MealRecord[] = [meal()]): MealPage {
  return { items, day: '2026-09-18', limit: 50, offset: 0, has_more: false };
}

function daily(overrides: Partial<DailyNutrition> = {}): DailyNutrition {
  return {
    day: '2026-09-18',
    meals_count: 2,
    calories: 1850,
    protein: 90,
    fat: 60,
    carbohydrates: 200,
    contains_estimates: true,
    disclaimer: 'Approximate values. Not medical or dietary advice.',
    ...overrides,
  };
}

function route(path: string): unknown {
  return path.startsWith('/meals/daily') ? daily() : page();
}

function renderMeals(): HTMLElement {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const { container } = render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <MealsScreen />
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
  getMock.mockImplementation((path: string) => Promise.resolve(route(path)));
  postMock.mockResolvedValue(meal({ id: 'm-2' }));
  patchMock.mockResolvedValue(meal({ estimated: false }));
  delMock.mockResolvedValue(undefined);
});

describe('MealsScreen', () => {
  it('loads the day list and the daily totals', async () => {
    renderMeals();

    expect(await screen.findByText('Chicken and rice')).toBeInTheDocument();
    const paths = getMock.mock.calls.map((call) => String(call[0]));
    expect(paths).toContain('/meals?limit=50');
    expect(paths).toContain('/meals/daily');
  });

  it('shows the totals with the API disclaimer, not our own claim', async () => {
    const container = renderMeals();
    await screen.findByText('Chicken and rice');

    expect(container.textContent).toContain('1850');
    expect(
      screen.getByText('Approximate values. Not medical or dietary advice.'),
    ).toBeInTheDocument();
  });

  it('hides the disclaimer when nothing is estimated', async () => {
    getMock.mockImplementation((path: string) =>
      Promise.resolve(
        path.startsWith('/meals/daily') ? daily({ contains_estimates: false }) : page(),
      ),
    );

    renderMeals();
    await screen.findByText('Chicken and rice');

    expect(
      screen.queryByText('Approximate values. Not medical or dietary advice.'),
    ).toBeNull();
  });

  it('marks an estimated meal as approximate', async () => {
    renderMeals();

    expect(await screen.findByText(/approximate/)).toBeInTheDocument();
  });

  it('asks for another day when the date changes', async () => {
    renderMeals();
    await screen.findByText('Chicken and rice');

    await userEvent.type(screen.getByLabelText('Day'), '2026-09-19');

    await waitFor(() =>
      expect(
        getMock.mock.calls.some((call) => String(call[0]).includes('day=2026-09-19')),
      ).toBe(true),
    );
  });

  it('shows an empty state for a day without meals', async () => {
    getMock.mockImplementation((path: string) =>
      Promise.resolve(path.startsWith('/meals/daily') ? daily() : page([])),
    );

    renderMeals();

    expect(await screen.findByText('Nothing logged for this day.')).toBeInTheDocument();
  });

  it('keeps the add button disabled without a title', async () => {
    renderMeals();
    await screen.findByText('Chicken and rice');

    expect(screen.getByRole('button', { name: 'Add meal' })).toBeDisabled();
  });

  it('creates a meal and keeps unknown macros null', async () => {
    postMock.mockReturnValue(new Promise(() => undefined));

    renderMeals();
    await screen.findByText('Chicken and rice');
    await userEvent.type(screen.getByLabelText('What did you eat?'), 'Oatmeal');
    await userEvent.selectOptions(screen.getByLabelText('Meal'), 'breakfast');
    await userEvent.type(screen.getByLabelText('Calories'), '320');
    await userEvent.click(screen.getByRole('button', { name: 'Add meal' }));

    expect(await screen.findByText('Oatmeal')).toBeInTheDocument();
    expect(postMock).toHaveBeenCalledWith('/meals', {
      title: 'Oatmeal',
      meal_type: 'breakfast',
      calories: 320,
      protein: null,
      fat: null,
      carbohydrates: null,
      estimated: true,
    });
  });

  it('corrects the calories by hand', async () => {
    renderMeals();
    await screen.findByText('Chicken and rice');
    await userEvent.click(screen.getByRole('button', { name: 'Correct calories' }));

    const field = screen.getByLabelText('Correct calories');
    await userEvent.clear(field);
    await userEvent.type(field, '700');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith('/meals/m-1', { calories: 700 }),
    );
  });

  it('deletes a meal optimistically', async () => {
    delMock.mockReturnValue(new Promise(() => undefined));

    renderMeals();
    await screen.findByText('Chicken and rice');
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));

    await waitFor(() => expect(screen.queryByText('Chicken and rice')).toBeNull());
    expect(delMock).toHaveBeenCalledWith('/meals/m-1');
  });

  it('restores a deleted meal when the request fails', async () => {
    delMock.mockRejectedValue(new Error('network down'));

    renderMeals();
    await screen.findByText('Chicken and rice');
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That change was not saved and has been reverted.',
    );
    await waitFor(() => expect(screen.getByText('Chicken and rice')).toBeInTheDocument());
  });

  it('offers a retry when meals cannot be loaded', async () => {
    getMock.mockImplementation((path: string) =>
      path.startsWith('/meals/daily')
        ? Promise.resolve(daily())
        : Promise.reject(new Error('network down')),
    );

    renderMeals();

    expect(await screen.findByText('Could not load meals.')).toBeInTheDocument();
  });

  it('parses optional macros within the backend limits', () => {
    expect(optionalNumber('', 20_000)).toBeNull();
    expect(optionalNumber('320', 20_000)).toBe(320);
    expect(optionalNumber('320.6', 20_000)).toBe(321);
    expect(optionalNumber('-1', 20_000)).toBeNull();
    expect(optionalNumber('99999', 20_000)).toBeNull();
    expect(optionalNumber('abc', 20_000)).toBeNull();
  });

  it('ships every meal label in every locale', () => {
    const keys = Object.keys(MEAL_MESSAGES.en).sort();
    for (const locale of ['en', 'ru', 'pl', 'uk'] as const) {
      expect(Object.keys(MEAL_MESSAGES[locale]).sort()).toEqual(keys);
      for (const key of keys) expect(mealLabel(locale, key)).not.toBe(key);
    }
  });
});
