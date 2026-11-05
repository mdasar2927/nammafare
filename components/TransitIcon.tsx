import React from 'react';
import {
  Footprints,
  Bus,
  Train,
  TramFront,
  Car,
  Users,
  Compass,
} from 'lucide-react';
import { TransitMode } from '@/types/transit';

interface TransitIconProps {
  mode: TransitMode;
  className?: string;
  size?: number;
}

export function TransitIcon({ mode, className = '', size = 18 }: TransitIconProps) {
  switch (mode) {
    case 'walking':
      return <Footprints size={size} className={className} />;
    case 'mtc_bus':
      return <Bus size={size} className={className} />;
    case 'metro':
      return <Train size={size} className={className} />;
    case 'suburban_train':
      return <TramFront size={size} className={className} />;
    case 'auto':
      return <Compass size={size} className={className} />;
    case 'share_auto':
      return <Users size={size} className={className} />;
    case 'taxi':
      return <Car size={size} className={className} />;
    default:
      return <Footprints size={size} className={className} />;
  }
}

export function getModeBadgeDetails(mode: TransitMode): {
  label: string;
  bgClass: string;
  textClass: string;
  borderClass: string;
} {
  switch (mode) {
    case 'walking':
      return {
        label: 'Walk',
        bgClass: 'bg-slate-100',
        textClass: 'text-slate-700',
        borderClass: 'border-slate-200',
      };
    case 'mtc_bus':
      return {
        label: 'MTC Bus',
        bgClass: 'bg-orange-50',
        textClass: 'text-orange-700',
        borderClass: 'border-orange-200',
      };
    case 'metro':
      return {
        label: 'CMRL Metro',
        bgClass: 'bg-sky-50',
        textClass: 'text-sky-700',
        borderClass: 'border-sky-200',
      };
    case 'suburban_train':
      return {
        label: 'Suburban Train',
        bgClass: 'bg-indigo-50',
        textClass: 'text-indigo-700',
        borderClass: 'border-indigo-200',
      };
    case 'auto':
      return {
        label: 'Auto Rickshaw',
        bgClass: 'bg-amber-50',
        textClass: 'text-amber-800',
        borderClass: 'border-amber-200',
      };
    case 'share_auto':
      return {
        label: 'Share Auto',
        bgClass: 'bg-purple-50',
        textClass: 'text-purple-700',
        borderClass: 'border-purple-200',
      };
    case 'taxi':
      return {
        label: 'Taxi / Cab',
        bgClass: 'bg-emerald-50',
        textClass: 'text-emerald-700',
        borderClass: 'border-emerald-200',
      };
  }
}
