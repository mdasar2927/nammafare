import type { Metadata } from 'next';
import './globals.css';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';

export const metadata: Metadata = {
  title: 'NammaFare | Chennai Multimodal Journey Planner & Fare Estimator',
  description:
    'Compare real-time travel times and transparent fare estimates across MTC Buses, Chennai Metro, Suburban Trains, Auto Rickshaws, and Cabs.',
  keywords: [
    'Chennai transit',
    'NammaFare',
    'MTC bus fares',
    'Chennai Metro CMRL',
    'Suburban train',
    'Vidiyal Payana Thittam',
    'Chennai journey planner',
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="flex flex-col min-h-screen bg-[#fcf9fa] text-slate-900 antialiased selection:bg-rose-200 selection:text-brand-900">
        <Navbar />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
