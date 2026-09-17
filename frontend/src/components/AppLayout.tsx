import { Outlet } from 'react-router-dom';

import { BottomNav } from '@/components/BottomNav';

export function AppLayout(): JSX.Element {
  return <main className="mx-auto min-h-full max-w-lg pb-safe-bottom"><Outlet /><BottomNav /></main>;
}
