import { Link } from 'react-router-dom';

const TITLES: Record<string, string> = { tasks: 'Tasks', events: 'Events', expenses: 'Expenses', meals: 'Meals', habits: 'Habits', notes: 'Notes' };

export function CollectionScreen({ kind }: { kind: keyof typeof TITLES }): JSX.Element {
  return <section className="p-4"><header className="mb-5 flex items-center justify-between"><h1 className="text-2xl font-semibold">{TITLES[kind]}</h1><Link className="od-button-ghost" to="/capture">+</Link></header><div className="od-card text-center text-sm text-ink-muted">Manage your {kind} here. Use the capture button to add a new record.</div></section>;
}
