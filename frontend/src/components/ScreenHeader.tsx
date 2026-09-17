import { Link } from 'react-router-dom';

export function ScreenHeader({ title, actionTo, actionLabel }: { title: string; actionTo?: string; actionLabel?: string }): JSX.Element {
  return <header className="mb-5 flex items-center justify-between"><h1 className="text-2xl font-semibold tracking-tight">{title}</h1>{actionTo && actionLabel ? <Link className="od-button-ghost text-sm" to={actionTo}>{actionLabel}</Link> : null}</header>;
}

export function ErrorCard({ message, retry }: { message: string; retry?: () => void }): JSX.Element {
  return <section className="od-card border-danger/30 text-sm"><p className="text-danger">{message}</p>{retry ? <button className="od-button-ghost mt-3" onClick={retry}>Try again</button> : null}</section>;
}

export function EmptyCard({ children }: { children: React.ReactNode }): JSX.Element {
  return <section className="od-card py-8 text-center text-sm text-ink-muted">{children}</section>;
}
