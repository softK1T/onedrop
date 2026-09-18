import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { LocaleProvider } from '@/i18n/LocaleProvider';
import { AdminScreen } from '@/screens/AdminScreen';
import { ProfileScreen } from '@/screens/ProfileScreen';

function wrapper(child: JSX.Element): JSX.Element {
  return <QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><LocaleProvider><MemoryRouter>{child}</MemoryRouter></LocaleProvider></QueryClientProvider>;
}
afterEach(()=>vi.restoreAllMocks());

describe('admin authorization UI',()=>{
  it('does not show admin link to regular users',async()=>{
    vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify({first_name:'Regular',username:null,locale:'en',is_admin:false,settings:{timezone:'UTC'}}),{status:200,headers:{'content-type':'application/json'}}));
    render(wrapper(<ProfileScreen/>));await screen.findByText('Regular');expect(screen.queryByText('Administration')).not.toBeInTheDocument();
  });
  it('shows admin link to configured admins',async()=>{
    vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify({first_name:'Admin',username:null,locale:'en',is_admin:true,settings:{timezone:'UTC'}}),{status:200,headers:{'content-type':'application/json'}}));
    render(wrapper(<ProfileScreen/>));expect(await screen.findByText('Administration')).toBeInTheDocument();
  });
  it('renders unauthorized state without sensitive data',async()=>{
    vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify({error:{code:'forbidden',message:'denied'}}),{status:403,headers:{'content-type':'application/json'}}));
    render(wrapper(<AdminScreen/>));expect(await screen.findByRole('alert')).toHaveTextContent('administrator permission');expect(screen.queryByText('denied')).not.toBeInTheDocument();
  });
});
