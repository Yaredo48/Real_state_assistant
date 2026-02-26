'use client';

import Link from 'next/link';
import { Building2, Shield, BarChart3, FileText, Zap, Users } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/context/AuthContext';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function HomePage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  const features = [
    {
      icon: FileText,
      title: 'Document Analysis',
      description: 'Automatically extract and analyze key information from property documents.',
    },
    {
      icon: Shield,
      title: 'Risk Assessment',
      description: 'Identify potential risks and issues in real estate transactions.',
    },
    {
      icon: BarChart3,
      title: 'Comprehensive Reports',
      description: 'Generate detailed reports with AI-powered insights and recommendations.',
    },
    {
      icon: Zap,
      title: 'AI-Powered',
      description: 'Leverage advanced AI to process and analyze documents in seconds.',
    },
    {
      icon: Users,
      title: 'Team Collaboration',
      description: 'Work together with your team on property due diligence projects.',
    },
    {
      icon: Building2,
      title: 'Property Management',
      description: 'Organize and manage all your property documents in one place.',
    },
  ];

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="fixed w-full bg-white/80 backdrop-blur-md z-50 border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Building2 className="h-8 w-8 text-primary-600" />
              <span className="ml-2 text-xl font-bold text-gray-900">DealLens</span>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/login">
                <Button variant="ghost">Sign In</Button>
              </Link>
              <Link href="/register">
                <Button>Get Started</Button>
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="text-center">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 tracking-tight">
            AI-Powered Property
            <br />
            <span className="text-primary-600">Due Diligence</span>
          </h1>
          <p className="mt-6 text-xl text-gray-600 max-w-2xl mx-auto">
            Streamline your real estate transactions with AI-powered document analysis,
            risk assessment, and comprehensive reporting.
          </p>
          <div className="mt-10 flex justify-center gap-4">
            <Link href="/register">
              <Button size="lg">Start Free Trial</Button>
            </Link>
            <Link href="/login">
              <Button size="lg" variant="outline">View Demo</Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-gray-900">
              Everything you need for property due diligence
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              Powerful features to help you make better decisions, faster.
            </p>
          </div>
          <div className="mt-16 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="h-12 w-12 bg-primary-100 rounded-lg flex items-center justify-center mb-4">
                  <feature.icon className="h-6 w-6 text-primary-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-gray-900">
            Ready to streamline your due diligence?
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Join thousands of real estate professionals using DealLens AI.
          </p>
          <div className="mt-8">
            <Link href="/register">
              <Button size="lg">Get Started for Free</Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-center">
            <Building2 className="h-8 w-8 text-primary-400" />
            <span className="ml-2 text-xl font-bold">DealLens AI</span>
          </div>
          <p className="mt-4 text-center text-gray-400">
            © {new Date().getFullYear()} DealLens AI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
