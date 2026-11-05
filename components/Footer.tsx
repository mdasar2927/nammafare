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
              <span>Theme7 Chennai Transit Engine</span>
            </div>
            <p className="text-slate-500 leading-relaxed">
              Spatial journey planner driven strictly by official Chennai Theme7 GIS datasets,
              integrating MTC Bus routes, Chennai Metro corridors, and Southern Railway suburban networks.
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
              <span>Strict Data Integrity Policy</span>
            </div>
            <p className="text-slate-500 leading-relaxed">
              All routes and station stops are traced directly from official shapefiles and verified fare structures.
              Disconnected locations report honest empty states without simulated intermediate connections.
            </p>
          </div>
        </div>

        <div className="pt-6 border-t border-slate-200/60 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-400">
          <p>© {new Date().getFullYear()} NammaFare. Built with Chennai Theme7 Transit GIS Data.</p>
          <div className="flex items-center gap-4 text-slate-500">
            <span>MTC Chennai</span>
            <span>•</span>
            <span>Chennai Metro (CMRL)</span>
            <span>•</span>
            <span>Southern Railway</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
