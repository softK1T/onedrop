import { Link } from 'react-router-dom';

export function OnboardingScreen(): JSX.Element {
  return <main className="flex min-h-full items-end p-5"><section className="od-card w-full space-y-4"><p className="text-sm font-medium text-accent">OneDrop</p><h1 className="text-3xl font-semibold">Drop it once. Keep it organized.</h1><p className="text-ink-muted">Text, voice and food photos become records you can edit, undo and revisit.</p><Link className="od-button-primary w-full" to="/today">Continue</Link></section></main>;
}
