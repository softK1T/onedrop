import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

import { ScreenHeader } from '@/components/ScreenHeader';
import { api } from '@/lib/api';

export function PrivacyScreen(): JSX.Element { const navigate=useNavigate();const exportData=useMutation({mutationFn:()=>api.post('/me/export')});const remove=useMutation({mutationFn:()=>api.del('/me'),onSuccess:()=>navigate('/onboarding')});const download=()=>{if(!exportData.data)return;const blob=new Blob([JSON.stringify(exportData.data,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='onedrop-export.json';a.click();URL.revokeObjectURL(url)};return <section className="p-4"><ScreenHeader title="Privacy"/><div className="od-card space-y-4"><p className="text-sm text-ink-muted">You can export everything stored in OneDrop or permanently delete your account and uploaded media.</p><button className="od-button-ghost w-full" onClick={()=>void exportData.mutateAsync().then(download)}>Export my data</button><button className="od-button-ghost w-full text-danger" onClick={()=>{if(window.confirm('This deletes every record and all media. It cannot be undone.'))remove.mutate()}}>Delete account</button></div></section>;
}
