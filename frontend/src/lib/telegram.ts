export type ThemeName = 'light' | 'dark';
interface TelegramThemeParams { bg_color?:string; secondary_bg_color?:string; text_color?:string; hint_color?:string; button_color?:string; button_text_color?:string; }
interface TelegramWebApp { initData:string; colorScheme:ThemeName; themeParams:TelegramThemeParams; isExpanded:boolean; ready:()=>void; expand:()=>void; onEvent:(event:string,handler:()=>void)=>void; offEvent:(event:string,handler:()=>void)=>void; HapticFeedback?:{ notificationOccurred:(type:'error'|'success'|'warning')=>void }; }
declare global { interface Window { Telegram?: { WebApp?: TelegramWebApp } } }
export function getWebApp():TelegramWebApp|null { return window.Telegram?.WebApp ?? null; }
export function isInsideTelegram():boolean { const app=getWebApp(); return Boolean(app&&app.initData.length>0); }
/** Only signed initData is sent to backend; initDataUnsafe is never trusted. */
export function getInitData():string|null { const app=getWebApp(); return app?.initData ? app.initData : null; }
export function detectTheme():ThemeName { const app=getWebApp(); if(app) return app.colorScheme==='dark'?'dark':'light'; return typeof window.matchMedia==='function'&&window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'; }
export function applyTheme(theme:ThemeName):void { const root=document.documentElement; root.dataset.theme=theme; const p=getWebApp()?.themeParams; if(!p)return; const set=(k:string,v:string|undefined):void=>{if(v)root.style.setProperty(k,v)}; set('--od-surface',p.secondary_bg_color); set('--od-surface-raised',p.bg_color); set('--od-ink',p.text_color); set('--od-ink-muted',p.hint_color); set('--od-accent',p.button_color); set('--od-accent-ink',p.button_text_color); }
export function initTelegram(onThemeChange:(theme:ThemeName)=>void):()=>void { const app=getWebApp(); applyTheme(detectTheme()); if(!app)return()=>undefined; app.ready(); if(!app.isExpanded)app.expand(); const handler=():void=>{const theme=detectTheme();applyTheme(theme);onThemeChange(theme)}; app.onEvent('themeChanged',handler); return()=>app.offEvent('themeChanged',handler); }
export function haptic(type:'success'|'error'|'warning'):void { getWebApp()?.HapticFeedback?.notificationOccurred(type); }
