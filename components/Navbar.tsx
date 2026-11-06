import React from 'react';
import Link from 'next/link';
import { Compass, CheckCircle2, Plus, LayoutDashboard } from 'lucide-react';

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-slate-200/50 px-4 sm:px-6 py-4 flex items-center justify-between">
      <Link href="/" className="flex items-center gap-2 cursor-pointer group">
        <div className="bg-rose-700 p-2 rounded-xl text-white shadow-sm group-hover:bg-rose-800 transition-colors">
          <Compass size={20} strokeWidth={2.5} />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 leading-none">
            NammaFare <span className="text-rose-700 text-[10px] uppercase tracking-widest font-bold align-top ml-1">Chennai</span>
          </h1>
        </div>
      </Link>

      <div className="flex items-center gap-3">
        <span className="hidden sm:flex items-center gap-1.5 text-xs font-medium text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-100">
          <CheckCircle2 size={14} /> Official Fares
        </span>

        <Link
          href="/"
          className="flex items-center gap-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-200 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700 px-4 py-2 rounded-full transition-all shadow-sm"
        >
          <Plus size={16} /> New Journey
        </Link>

        <a
          href="https://admin-panel-mauve-nu.vercel.app/"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-200 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700 px-4 py-2 rounded-full transition-all shadow-sm"
          title="Open Admin Panel"
        >
          <LayoutDashboard size={15} />
          <span>Admin</span>
        </a>
      </div>
    </header>
  );
}
