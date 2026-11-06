import React from 'react';
import { SearchForm } from '@/components/SearchForm';
import {
  Sparkles,
  TrendingDown,
  ShieldCheck,
  Bus,
  Train,
  Zap,
  Footprints,
} from 'lucide-react';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#F8F9FA] font-sans text-slate-800 selection:bg-rose-100 selection:text-rose-900 flex flex-col relative overflow-hidden">
      {/* Decorative ambient background blur */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-rose-200/20 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute top-[20%] right-[-5%] w-[30%] h-[40%] bg-blue-200/20 rounded-full blur-[100px] pointer-events-none" />

      {/* Main Layout */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 pt-12 pb-24 relative z-10">
        {/* Hero Section */}
        <div className="text-center max-w-3xl mx-auto mb-10 sm:mb-12">
          {/* Provenance Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-rose-50 border border-rose-200/80 text-rose-800 text-xs font-semibold mb-6 shadow-sm">
            <Sparkles size={14} className="text-rose-600" />
            <span>Theme7 Verified Chennai Transit Datasets</span>
          </div>

          {/* Heading */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 tracking-tight leading-[1.1] mb-5">
            Seamless Transit in{' '}
            <span className="bg-gradient-to-r from-rose-800 via-rose-700 to-rose-600 bg-clip-text text-transparent">
              Chennai
            </span>
          </h1>

          <p className="text-slate-600 text-base sm:text-lg leading-relaxed max-w-2xl mx-auto font-medium">
            Find connected routes across <span className="font-semibold text-slate-800">MTC Buses</span>,{' '}
            <span className="font-semibold text-slate-800">Chennai Metro (CMRL)</span>, and{' '}
            <span className="font-semibold text-slate-800">Suburban Railway</span> with official stage fares and statutory women free travel rules.
          </p>
        </div>

        {/* Central Search Card & Popular Corridors */}
        <SearchForm />

        {/* Value Highlights Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto mt-16 mb-14 w-full">
          {/* Highlight 1: Vidiyal Scheme */}
          <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-2xl bg-rose-50 text-rose-700 flex items-center justify-center mb-4 border border-rose-200 shadow-inner">
              <Sparkles size={24} className="text-rose-700" />
            </div>
            <h3 className="font-bold text-slate-900 text-base mb-1">
              Vidiyal Payana Thittam
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Standard MTC Ordinary (White-Board) bus fares are automatically calculated as ₹0 for women commuters under Tamil Nadu statutory scheme.
            </p>
          </div>

          {/* Highlight 2: Cost & Time Optimization */}
          <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-2xl bg-sky-50 text-sky-800 flex items-center justify-center mb-4 border border-sky-200 shadow-inner">
              <TrendingDown size={24} className="text-sky-700" />
            </div>
            <h3 className="font-bold text-slate-900 text-base mb-1">
              Lowest Cost vs Least Time
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Dynamically compare economical Suburban train options with rapid CMRL Metro lines or direct MTC corridors.
            </p>
          </div>

          {/* Highlight 3: Transparent Data */}
          <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-800 flex items-center justify-center mb-4 border border-emerald-200 shadow-inner">
              <ShieldCheck size={24} className="text-emerald-700" />
            </div>
            <h3 className="font-bold text-slate-900 text-base mb-1">
              Pure Theme7 Spatial Data
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Every route leg is traced from official GIS shapefiles with exact route identifiers and genuine data provenance.
            </p>
          </div>
        </div>

        {/* Transit Modes Supported Row */}
        <div className="pt-8 border-t border-slate-200 text-center w-full max-w-4xl mx-auto">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">
            Supported Public Transit Network
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-6 text-xs font-semibold text-slate-700">
            <span className="flex items-center gap-1.5 bg-white px-3.5 py-2 rounded-full border border-slate-200 shadow-sm">
              <Bus size={15} className="text-orange-600" /> MTC Bus Network
            </span>
            <span className="flex items-center gap-1.5 bg-white px-3.5 py-2 rounded-full border border-slate-200 shadow-sm">
              <Train size={15} className="text-sky-600" /> Chennai Metro Rail
            </span>
            <span className="flex items-center gap-1.5 bg-white px-3.5 py-2 rounded-full border border-slate-200 shadow-sm">
              <Zap size={15} className="text-indigo-600" /> Suburban Rail
            </span>
            <span className="flex items-center gap-1.5 bg-white px-3.5 py-2 rounded-full border border-slate-200 shadow-sm">
              <Footprints size={15} className="text-slate-600" /> Walking Transfers
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}
