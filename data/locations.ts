import { ChennaiLocation } from '@/types/transit';

export const CHENNAI_LOCATIONS: ChennaiLocation[] = [
  { id: 'loc-1', name: 'Chennai Central (Puratchi Thalaivar Dr. M.G.R.)', tamilName: 'சென்னை சென்ட்ரல்', hubType: 'Railway', zone: 'North/Central' },
  { id: 'loc-2', name: 'Chennai Egmore', tamilName: 'சென்னை எழும்பூர்', hubType: 'Railway', zone: 'Central' },
  { id: 'loc-3', name: 'Guindy', tamilName: 'கிண்டி', hubType: 'Metro', zone: 'South' },
  { id: 'loc-4', name: 'Tambaram', tamilName: 'தாம்பரம்', hubType: 'Railway', zone: 'South Outer' },
  { id: 'loc-5', name: 'Koyambedu (CMBT)', tamilName: 'கோயம்பேடு', hubType: 'Bus Stand', zone: 'West' },
  { id: 'loc-6', name: 'T. Nagar (Panagal Park / Bus Terminus)', tamilName: 'தி. நகர்', hubType: 'Bus Stand', zone: 'Central' },
  { id: 'loc-7', name: 'Velachery', tamilName: 'வேளச்சேரி', hubType: 'Railway', zone: 'South' },
  { id: 'loc-8', name: 'Adyar (L.B. Road)', tamilName: 'அடையாறு', hubType: 'Locality', zone: 'South' },
  { id: 'loc-9', name: 'Chennai Airport (Meenambakkam)', tamilName: 'சென்னை விமானநிலையம்', hubType: 'Metro', zone: 'South' },
  { id: 'loc-10', name: 'Thiruvanmiyur', tamilName: 'திருவான்மியூர்', hubType: 'Railway', zone: 'South' },
  { id: 'loc-11', name: 'Vadapalani', tamilName: 'வடபழனி', hubType: 'Metro', zone: 'West' },
  { id: 'loc-12', name: 'Anna Nagar (Roundtana / Tower)', tamilName: 'அண்ணா நகர்', hubType: 'Metro', zone: 'North West' },
  { id: 'loc-13', name: 'Perambur', tamilName: 'பெரம்பூர்', hubType: 'Railway', zone: 'North' },
  { id: 'loc-14', name: 'Porur Junction', tamilName: 'போரூர்', hubType: 'Locality', zone: 'West' },
  { id: 'loc-15', name: 'Chromepet', tamilName: 'குரோம்பேட்டை', hubType: 'Railway', zone: 'South' },
  { id: 'loc-16', name: 'Sholinganallur (OMR IT Corridor)', tamilName: 'சோழிங்கநல்லூர்', hubType: 'Locality', zone: 'OMR' },
  { id: 'loc-17', name: 'Mylapore (Luz Church)', tamilName: 'மயிலாப்பூர்', hubType: 'Locality', zone: 'Central' },
  { id: 'loc-18', name: 'Siruseri (SIPCOT IT Park)', tamilName: 'சிறுசேரி', hubType: 'Locality', zone: 'OMR' },
  { id: 'loc-19', name: 'Avadi', tamilName: 'ஆவடி', hubType: 'Railway', zone: 'West Outer' },
  { id: 'loc-20', name: 'Broad-way (Parrys Corner)', tamilName: 'பிராட்வே', hubType: 'Bus Stand', zone: 'North' }
];

export const POPULAR_ROUTES = [
  { source: 'Chennai Central (Puratchi Thalaivar Dr. M.G.R.)', destination: 'Guindy' },
  { source: 'Tambaram', destination: 'Chennai Central (Puratchi Thalaivar Dr. M.G.R.)' },
  { source: 'Koyambedu (CMBT)', destination: 'T. Nagar (Panagal Park / Bus Terminus)' },
  { source: 'Chennai Airport (Meenambakkam)', destination: 'Chennai Egmore' },
  { source: 'Velachery', destination: 'Chennai Central (Puratchi Thalaivar Dr. M.G.R.)' },
];
