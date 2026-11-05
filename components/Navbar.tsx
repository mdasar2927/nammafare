import React from 'react';
import Link from 'next/link';
import { Compass, Train, ShieldCheck } from 'lucide-react';

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-rose-100/80 shadow-soft-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-900 via-brand-800 to-rose-600 flex items-center justify-center text-white shadow-md shadow-brand-900/20 group-hover:scale-105 transition-transform">
            <Compass size={22} className="text-white" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-xl tracking-tight text-slate-900">
                Namma<span className="text-brand-800">Fare</span>
              </span>
              <span className="bg-rose-50 text-brand-900 text-[10px] font-bold px-2 py-0.5 rounded-full border border-rose-200">
                CHENNAI
              </span>
            </div>
            <span className="text-[11px] text-slate-500 font-medium -mt-1 hidden sm:inline">
              சென்னை வழித்தடம் & கட்டண வழிகாட்டி
            </span>
          </div>
        </Link>

        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 bg-slate-50 px-3 py-1.5 rounded-full border border-slate-200/80 text-xs text-slate-600">
            <ShieldCheck size={14} className="text-emerald-600" />
            <span>MTC & CMRL Verified Fare Standards</span>
          </div>

          <Link
            href="/"
            className="text-xs font-semibold text-brand-900 hover:text-brand-700 px-3 py-1.5 rounded-lg hover:bg-rose-50/80 transition-colors flex items-center gap-1.5"
          >
            <Train size={14} />
            <span>New Journey</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
