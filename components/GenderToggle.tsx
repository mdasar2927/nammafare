import React from 'react';
import { Gender } from '@/types/transit';
import { Sparkles, User } from 'lucide-react';

interface GenderToggleProps {
  gender: Gender;
  onChange: (gender: Gender) => void;
  size?: 'sm' | 'md';
  showHelpText?: boolean;
}

export function GenderToggle({
  gender,
  onChange,
  size = 'md',
  showHelpText = true,
}: GenderToggleProps) {
  const isSm = size === 'sm';

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold text-slate-700 tracking-wide uppercase">
          Commuter Profile
        </label>
        {showHelpText && (
          <span className="text-[11px] text-brand-700 font-medium flex items-center gap-1">
            <Sparkles size={12} className="text-brand-600" />
            Vidiyal Payana Thittam Free MTC Bus for Women
          </span>
        )}
      </div>

      <div className="inline-flex p-1 bg-slate-100/90 rounded-xl border border-slate-200/80 w-full sm:w-auto">
        <button
          type="button"
          onClick={() => onChange('male')}
          className={`flex-1 sm:flex-none flex items-center justify-center gap-1.5 rounded-lg font-medium transition-all duration-200 ${
            isSm ? 'px-3 py-1 text-xs' : 'px-4 py-2 text-sm'
          } ${
            gender === 'male'
              ? 'bg-white text-brand-900 shadow-sm font-semibold'
              : 'text-slate-600 hover:text-slate-900'
          }`}
          aria-pressed={gender === 'male'}
        >
          <User size={isSm ? 13 : 15} />
          <span>Male (Default)</span>
        </button>

        <button
          type="button"
          onClick={() => onChange('female')}
          className={`flex-1 sm:flex-none flex items-center justify-center gap-1.5 rounded-lg font-medium transition-all duration-200 ${
            isSm ? 'px-3 py-1 text-xs' : 'px-4 py-2 text-sm'
          } ${
            gender === 'female'
              ? 'bg-brand-800 text-white shadow-sm font-semibold'
              : 'text-slate-600 hover:text-slate-900'
          }`}
          aria-pressed={gender === 'female'}
        >
          <Sparkles size={isSm ? 13 : 15} className={gender === 'female' ? 'text-pink-200' : 'text-brand-600'} />
          <span>Female (₹0 MTC Ordinary)</span>
        </button>
      </div>
    </div>
  );
}
