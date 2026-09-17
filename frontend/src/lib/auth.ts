import { api, clearTokens, setTokens } from '@/lib/api';
import { getInitData, isInsideTelegram } from '@/lib/telegram';
export interface TokenPair { access_token:string;refresh_token:string;expires_in:number;token_type:string }
export type AuthMode='telegram'|'dev';
export const DEV_LOGIN_ENABLED=(import.meta.env.VITE_DEV_LOGIN as string|undefined)!=='false'; export const DEMO_TELEGRAM_ID=100001;
export async function loginWithTelegram(initData:string):Promise<AuthMode>{const tokens=await api.post<TokenPair>('/auth/telegram',{init_data:initData});setTokens(tokens.access_token,tokens.refresh_token);return'telegram'}
export async function loginWithDev(telegramUserId=DEMO_TELEGRAM_ID):Promise<AuthMode>{const tokens=await api.post<TokenPair>('/auth/dev',{telegram_user_id:telegramUserId});setTokens(tokens.access_token,tokens.refresh_token);return'dev'}
export async function bootstrapSession():Promise<AuthMode|null>{const initData=getInitData();if(initData!==null)return loginWithTelegram(initData);if(!isInsideTelegram()&&DEV_LOGIN_ENABLED)return loginWithDev();return null}
export async function logout():Promise<void>{clearTokens()}
