import React from 'react';
import { SearchForm } from '@/components/SearchForm';
import {
  Train,
  Bus,
  Sparkles,
  ShieldCheck,
  Compass,
  Zap,
  TrendingDown,
  Clock,
} from 'lucide-react';

export default function HomePage() {
  return (
    <div className="relative overflow-hidden">
      {/* Decorative Gradient Blobs */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-gradient-to-b from-rose-100/60 via-rose-50/20 to-transparent pointer-events-none -z-10 blur-3xl" />
      <div className="absolute top-20 right-10 w-72 h-72 bg-brand-100/40 rounded-full blur-2xl pointer-events-none -z-10" />
      <div className="absolute top-40 left-10 w-72 h-72 bg-pink-100/50 rounded-full blur-2xl pointer-events-none -z-10" />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-16">
        {/* Hero Section */}
        <div className="text-center max-w-3xl mx-auto mb-10 sm:mb-12">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-rose-50 border border-rose-200 text-brand-900 text-xs font-semibold mb-6 shadow-soft-sm">
            <Sparkles size={14} className="text-brand-600" />
            <span>Dedicated Chennai Multimodal Transit Engine</span>
          </div>

          {/* Heading */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-slate-900 tracking-tight leading-[1.1] mb-5">
            Compare Every Route in{' '}
            <span className="bg-gradient-to-r from-brand-900 via-brand-700 to-rose-600 bg-clip-text text-transparent">
              Chennai
            </span>
            . Save Time & Fare.
          </h1>

          <p className="text-slate-600 text-base sm:text-lg leading-relaxed max-w-2xl mx-auto">
            Discover verified fares across <span className="font-semibold text-slate-800">MTC Buses</span>,{' '}
            <span className="font-semibold text-slate-800">CMRL Metro</span>, and{' '}
            <span className="font-semibold text-slate-800">Suburban Trains</span> alongside calibrated Auto, Share Auto, and Cab estimates.
          </p>
        </div>

        {/* Central Search Card (Page 1 Core) */}
        <div className="max-w-3xl mx-auto mb-16">
          <SearchForm />
        </div>

        {/* Value Highlights Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
          {/* Highlight 1: Vidiyal Scheme */}
          <div className="bg-white/90 backdrop-blur-sm p-6 rounded-3xl border border-rose-100 shadow-soft-sm hover:shadow-soft-md transition-shadow">
            <div className="w-12 h-12 rounded-2xl bg-rose-50 text-brand-800 flex items-center justify-center mb-4 border border-rose-200 shadow-inner">
              <Sparkles size={24} className="text-brand-700" />
            </div>
            <h3 className="font-bold text-slate-900 text-base mb-1">
              Vidiyal Payana Thittam
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Standard MTC Ordinary (White-Board) bus fares are automatically calculated as ₹0 for women commuters.
            </p>
          </div>

          {/* Highlight 2: Cost & Time Optimization */}
          <div className="bg-white/90 backdrop-blur-sm p-6 rounded-3xl border border-rose-100 shadow-soft-sm hover:shadow-soft-md transition-shadow">
            <div className="w-12 h-12 rounded-2xl bg-sky-50 text-sky-800 flex items-center justify-center mb-4 border border-sky-200 shadow-inner">
              <TrendingDown size={24} className="text-sky-700" />
            </div>
            <h3 className="font-bold text-slate-900 text-base mb-1">
              Lowest Cost vs Least Time
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Compare ₹5 Suburban train options with rapid CMRL Metro lines or door-to-door auto/cab connections instantly.
            </p>
          </div>

          {/* Highlight 3: Transparent Data */}
          <div className="bg-white/90 backdrop-blur-sm p-6 rounded-3xl border border-rose-100 shadow-soft-sm hover:shadow-soft-md transition-shadow">
            <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-800 flex items-center justify-center mb-4 border border-emerald-200 shadow-inner">
              <ShieldCheck size={24} className="text-emerald-700" />
            </div>
            <h3 className="font-bold text-slate-900 text-base mb-1">
              Transparent Fare Breakdowns
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Every leg is transparently labeled as government-verified or calibrated street estimate with step-by-step guidance.
            </p>
          </div>
        </div>

        {/* Transit Modes Supported Row */}
        <div className="mt-14 pt-8 border-t border-rose-100/70 text-center">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">
            Unified Chennai Multimodal Network
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-6 text-xs font-semibold text-slate-700">
            <span className="flex items-center gap-1.5 bg-white px-3 py-1.5 rounded-full border border-slate-200 shadow-sm">
              <Bus size={15} className="text-orange-600" /> MTC Ordinary & Deluxe
            </span>
            <span className="flex items-center gap-1.5 bg-white px-3 py-1.5 rounded-full border border-slate-200 shadow-sm">
              <Train size={15} className="text-sky-600" /> CMRL Metro Blue & Green
            </span>
            <span className="flex items-center gap-1.5 bg-white px-3 py-1.5 rounded-full border border-slate-200 shadow-sm">
              <Zap size={15} className="text-indigo-600" /> Southern Railway Suburban
            </span>
            <span className="flex items-center gap-1.5 bg-white px-3 py-1.5 rounded-full border border-slate-200 shadow-sm">
              <Compass size={15} className="text-amber-600" /> Chennai Auto & Share Auto
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
