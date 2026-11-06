'use client';

import React, { Suspense, useState, useEffect, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  ArrowRight,
  Info,
  AlertCircle,
  RotateCcw,
} from 'lucide-react';
import { Gender, SortPreference, MultimodalRoute } from '@/types/transit';
import { searchRoutesApi, fetchHealth } from '@/lib/api';
import { RouteCard } from '@/components/RouteCard';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { EmptyState } from '@/components/EmptyState';

function RoutesContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // Read URL query parameters
  const initialSource = searchParams.get('source') || 'Thirumalai Street, Zone 11';
  const initialDestination = searchParams.get('destination') || 'Guindy B.T';
  const initialGender = (searchParams.get('gender') as Gender) || 'male';
  const initialSort = (searchParams.get('sort') as SortPreference) || 'cost';

  const sLat = searchParams.get('sLat') ? parseFloat(searchParams.get('sLat')!) : undefined;
  const sLng = searchParams.get('sLng') ? parseFloat(searchParams.get('sLng')!) : undefined;
  const dLat = searchParams.get('dLat') ? parseFloat(searchParams.get('dLat')!) : undefined;
  const dLng = searchParams.get('dLng') ? parseFloat(searchParams.get('dLng')!) : undefined;

  // State
  const [source, setSource] = useState(initialSource);
  const [destination, setDestination] = useState(initialDestination);
  const [gender, setGender] = useState<Gender>(initialGender);
  const [sortBy, setSortBy] = useState<SortPreference>(initialSort);

  const [routes, setRoutes] = useState<MultimodalRoute[]>([]);
  const [backendMessage, setBackendMessage] = useState<string | null>(null);
  const [originTaz, setOriginTaz] = useState<string | null>(null);
  const [destTaz, setDestTaz] = useState<string | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);

  // Sync state if URL changes
  useEffect(() => {
    if (searchParams.get('source')) setSource(searchParams.get('source')!);
    if (searchParams.get('destination')) setDestination(searchParams.get('destination')!);
    if (searchParams.get('gender')) setGender(searchParams.get('gender') as Gender);
    if (searchParams.get('sort')) setSortBy(searchParams.get('sort') as SortPreference);
  }, [searchParams]);

  // Check health on mount
  useEffect(() => {
    fetchHealth().then((health) => {
      setIsBackendHealthy(health !== null && health.status === 'ok');
    });
  }, []);

  // Fetch routes from FastAPI backend with strict no-mock policy
  const loadRoutes = useCallback(
    async (
      src: string,
      dst: string,
      g: Gender,
      sort: SortPreference,
      srcC?: { lat: number; lng: number },
      dstC?: { lat: number; lng: number }
    ) => {
      setIsLoading(true);
      setError(null);
      setBackendMessage(null);
      try {
        const result = await searchRoutesApi({
          source: src,
          destination: dst,
          sourceCoords: srcC,
          destCoords: dstC,
          gender: g,
          sortBy: sort,
        });
        setRoutes(result.routes);
        setBackendMessage(result.message || null);
        setOriginTaz(result.originTaz || null);
        setDestTaz(result.destTaz || null);
      } catch (err: any) {
        console.error('Failed to load routes from backend:', err);
        setError(err.message || 'Unable to connect to transit routing engine');
        setRoutes([]);
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  // Fetch on mount or when key parameters change
  useEffect(() => {
    const srcCoords =
      typeof sLat === 'number' && typeof sLng === 'number' && !isNaN(sLat) && !isNaN(sLng)
        ? { lat: sLat, lng: sLng }
        : undefined;
    const dstCoords =
      typeof dLat === 'number' && typeof dLng === 'number' && !isNaN(dLat) && !isNaN(dLng)
        ? { lat: dLat, lng: dLng }
        : undefined;

    loadRoutes(source, destination, gender, sortBy, srcCoords, dstCoords);
  }, [source, destination, gender, sortBy, sLat, sLng, dLat, dLng, loadRoutes]);

  // Update URL search parameters when interactive controls change
  const updateUrlParams = (
    newGender: Gender,
    newSort: SortPreference,
    newSrc = source,
    newDst = destination
  ) => {
    const params = new URLSearchParams({
      source: newSrc,
      destination: newDst,
      gender: newGender,
      sort: newSort,
    });
    if (typeof sLat === 'number' && typeof sLng === 'number') {
      params.set('sLat', sLat.toString());
      params.set('sLng', sLng.toString());
    }
    if (typeof dLat === 'number' && typeof dLng === 'number') {
      params.set('dLat', dLat.toString());
      params.set('dLng', dLng.toString());
    }
    router.replace(`/routes?${params.toString()}`, { scroll: false });
  };

  const handleGenderChange = (newGender: Gender) => {
    setGender(newGender);
    updateUrlParams(newGender, sortBy);
  };

  const handleSortChange = (newSort: SortPreference) => {
    setSortBy(newSort);
    updateUrlParams(gender, newSort);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans selection:bg-rose-200 selection:text-rose-900 pb-20">
      {/* Header Area */}
      <header className="bg-white border-b border-slate-200 pt-6 pb-4 px-4 sm:px-8 sticky top-0 z-20">
        <div className="max-w-4xl mx-auto">
          <button
            onClick={() => router.push('/')}
            className="flex items-center gap-2 text-slate-500 hover:text-slate-900 font-medium text-sm transition-colors mb-4"
          >
            <ArrowLeft size={16} /> Back to Search
          </button>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3 text-lg font-semibold text-slate-800">
              <span>{source}</span>
              <ArrowRight size={18} className="text-slate-400" />
              <span className="text-rose-600">{destination}</span>
            </div>

            <div className="flex items-center gap-2 text-xs font-medium bg-slate-100 px-3 py-1.5 rounded-full text-slate-600">
              <span className="flex items-center gap-1.5">
                <div
                  className={`w-2 h-2 rounded-full ${
                    isBackendHealthy ? 'bg-emerald-500' : 'bg-amber-500'
                  }`}
                />
                {isBackendHealthy ? 'Engine Active' : 'Connecting to API'}
              </span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-8 mt-8">
        {/* Filters */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8 animate-stagger-1">
          <div className="bg-white p-2 rounded-2xl border border-slate-200 shadow-sm flex items-center">
            <button
              onClick={() => handleSortChange('cost')}
              className={`flex-1 py-2.5 text-sm font-medium rounded-xl transition-all ${
                sortBy === 'cost'
                  ? 'bg-slate-100 text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Lowest Cost
            </button>
            <button
              onClick={() => handleSortChange('time')}
              className={`flex-1 py-2.5 text-sm font-medium rounded-xl transition-all ${
                sortBy === 'time'
                  ? 'bg-slate-100 text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Least Time
            </button>
          </div>

          <div className="bg-white p-2 rounded-2xl border border-slate-200 shadow-sm flex items-center">
            <button
              onClick={() => handleGenderChange('male')}
              className={`flex-1 py-2.5 text-sm font-medium rounded-xl transition-all ${
                gender === 'male'
                  ? 'bg-slate-100 text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Standard (Male)
            </button>
            <button
              onClick={() => handleGenderChange('female')}
              className={`flex-1 py-2.5 text-sm font-medium rounded-xl transition-all ${
                gender === 'female'
                  ? 'bg-rose-50 text-rose-700 shadow-sm'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Female (₹0 MTC)
            </button>
          </div>
        </div>

        {/* Results Counter */}
        <div className="flex items-center justify-between mb-4 animate-stagger-2">
          <h2 className="text-lg font-bold text-slate-800">Viable Transit Routes</h2>
          <span className="text-sm text-slate-500">
            Showing {routes.length} option{routes.length === 1 ? '' : 's'}
          </span>
        </div>

        {/* Error Alert Box */}
        {error && (
          <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 flex items-start justify-between gap-3 text-xs mb-6">
            <div className="flex items-center gap-2">
              <AlertCircle size={18} className="text-amber-700 shrink-0" />
              <div>
                <span className="font-bold">Backend Connection Notice:</span> {error}.
              </div>
            </div>
            <button
              type="button"
              onClick={() => loadRoutes(source, destination, gender, sortBy)}
              className="px-3 py-1 bg-white hover:bg-amber-100 border border-amber-300 rounded-lg font-semibold shrink-0 flex items-center gap-1 transition-colors"
            >
              <RotateCcw size={12} />
              Retry
            </button>
          </div>
        )}

        {/* Routes List or Loading / Empty States */}
        {isLoading ? (
          <LoadingSkeleton />
        ) : routes.length === 0 ? (
          <EmptyState
            source={source}
            destination={destination}
            message={backendMessage}
            originTaz={originTaz}
            destTaz={destTaz}
            onReset={() => {
              setSource('Thirumalai Street, Zone 11');
              setDestination('Guindy B.T');
            }}
          />
        ) : (
          <div className="flex flex-col gap-5">
            {routes.map((route, index) => (
              <RouteCard
                key={route.id}
                route={route}
                currentGender={gender}
                isInitiallyExpanded={index === 0}
              />
            ))}
          </div>
        )}

        {/* Informational Footer */}
        <div className="mt-10 bg-blue-50/50 border border-blue-100 p-5 rounded-2xl flex gap-4 animate-stagger-4">
          <Info size={24} className="text-blue-500 shrink-0" />
          <div>
            <h4 className="text-sm font-bold text-blue-900 mb-1">
              Theme7 Strict Data Policy
            </h4>
            <p className="text-sm text-blue-800/80 leading-relaxed">
              MTC routes reflect actual lines traced from official shapefiles. Station names are
              preserved exactly as provided in the dataset without fabricated identifiers.
              Intermediate auto rickshaw and taxi estimates are strictly excluded.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

export default function RoutesPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-4xl mx-auto px-4 py-16">
          <LoadingSkeleton />
        </div>
      }
    >
      <RoutesContent />
    </Suspense>
  );
}
