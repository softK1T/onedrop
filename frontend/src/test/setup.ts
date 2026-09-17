import '@testing-library/jest-dom/vitest';
beforeEach(()=>{delete window.Telegram;document.documentElement.removeAttribute('data-theme');document.documentElement.style.cssText='';});
if(typeof window.matchMedia!=='function')Object.defineProperty(window,'matchMedia',{writable:true,value:(query:string)=>({matches:false,media:query,onchange:null,addEventListener:()=>undefined,removeEventListener:()=>undefined,addListener:()=>undefined,removeListener:()=>undefined,dispatchEvent:()=>false})});
