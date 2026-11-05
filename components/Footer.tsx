import React from 'react';
import { Info, Bus, Sparkles } from 'lucide-react';

export function Footer() {
  return (
    <footer className="bg-slate-50 border-t border-rose-100/70 text-slate-600 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8 text-xs">
          <div>
            <div className="flex items-center gap-2 mb-2 font-bold text-slate-900 text-sm">
              <Bus size={16} className="text-brand-800" />
              <span>NammaFare Chennai Engine</span>
            </div>
            <p className="text-slate-500 leading-relaxed">
              Tailored specifically for Chennai commuters, integrating MTC Buses, Chennai Metro (CMRL),
              Southern Railway Suburban network, Auto Rickshaws, Share Autos, and Taxis into unified itineraries.
            </p>
          </div>

          <div>
            <div className="flex items-center gap-2 mb-2 font-bold text-slate-900 text-sm">
              <Sparkles size={16} className="text-brand-700" />
              <span>Vidiyal Payana Thittam</span>
            </div>
            <p className="text-slate-500 leading-relaxed">
              Standard MTC Ordinary (White-Board) bus fares are automatically calculated as ₹0 for women commuters
              under the Government of Tamil Nadu statutory scheme.
            </p>
          </div>

          <div>
            <div className="flex items-center gap-2 mb-2 font-bold text-slate-900 text-sm">
              <Info size={16} className="text-sky-600" />
              <span>Verified vs Estimated Data</span>
            </div>
            <p className="text-slate-500 leading-relaxed">
              Government-published transit fares (Metro, Suburban Trains, MTC Buses) are verified official rates.
              Auto rickshaws, share autos, and taxis display indicative street & daytime calibrated averages.
            </p>
          </div>
        </div>

        <div className="pt-6 border-t border-slate-200/60 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-400">
          <p>© {new Date().getFullYear()} NammaFare. Designed with pride for Chennai commuters.</p>
          <div className="flex items-center gap-4 text-slate-500">
            <span>MTC Chennai</span>
            <span>•</span>
            <span>CMRL Metro</span>
            <span>•</span>
            <span>Southern Railway</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
