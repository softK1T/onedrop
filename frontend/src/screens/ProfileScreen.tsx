import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import type { UserProfile } from '@/app/types';
import { ErrorCard, ScreenHeader } from '@/components/ScreenHeader';
import { api } from '@/lib/api';

const LINKS = [['/settings','Settings'],['/subscription','Subscription'],['/privacy','Privacy']] as const;
export function ProfileScreen(): JSX.Element { const query=useQuery({queryKey:['me'],queryFn:()=>api.get<UserProfile>('/me')}); if(query.isLoading)return <section className="p-4"><div className="od-skeleton h-8 w-24" /></section>;if(query.isError)return <section className="p-4"><ErrorCard message="Could not load profile." retry={()=>void query.refetch()}/></section>;if(!query.data)return <section className="p-4"><ErrorCard message="Could not load profile." retry={()=>void query.refetch()}/></section>;const user=query.data;return <section className="p-4"><ScreenHeader title="Profile"/><div className="od-card"><p className="text-lg font-semibold">{user.first_name ?? 'OneDrop user'}</p><p className="text-sm text-ink-muted">{user.username ? `@${user.username}` : user.settings.timezone}</p></div><div className="mt-4 space-y-2">{LINKS.map(([to,label])=><Link className="od-card flex items-center justify-between" to={to} key={to}><span>{label}</span><span className="text-ink-muted">›</span></Link>)}</div></section>;
}
