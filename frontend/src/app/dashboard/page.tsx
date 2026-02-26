'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { propertiesApi, documentsApi, analysisApi } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Building2, FileText, BarChart3, Plus, ArrowRight, Clock } from 'lucide-react';
import { formatDate, getStatusColor } from '@/lib/utils';

interface DashboardStats {
  propertiesCount: number;
  documentsCount: number;
  analysisJobsCount: number;
}

interface RecentJob {
  id: string;
  property_id: string;
  status: string;
  created_at: string;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats>({
    propertiesCount: 0,
    documentsCount: 0,
    analysisJobsCount: 0,
  });
  const [recentJobs, setRecentJobs] = useState<RecentJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [propertiesRes, documentsRes, jobsRes] = await Promise.all([
          propertiesApi.list({ limit: 1 }),
          documentsApi.list({ limit: 1 }),
          analysisApi.listJobs({ limit: 5 }),
        ]);

        setStats({
          propertiesCount: propertiesRes.length || 0,
          documentsCount: documentsRes.total || 0,
          analysisJobsCount: jobsRes.length || 0,
        });

        setRecentJobs(jobsRes || []);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const statCards = [
    {
      title: 'Properties',
      value: stats.propertiesCount,
      icon: Building2,
      href: '/dashboard/properties',
      color: 'bg-blue-100 text-blue-600',
    },
    {
      title: 'Documents',
      value: stats.documentsCount,
      icon: FileText,
      href: '/dashboard/documents',
      color: 'bg-green-100 text-green-600',
    },
    {
      title: 'Analysis Jobs',
      value: stats.analysisJobsCount,
      icon: BarChart3,
      href: '/dashboard/analysis',
      color: 'bg-purple-100 text-purple-600',
    },
  ];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back, {user?.full_name || user?.email?.split('@')[0]}!
        </h1>
        <p className="text-gray-600 mt-1">
          Here's an overview of your property due diligence activities.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {statCards.map((stat) => (
          <Link key={stat.title} href={stat.href}>
            <Card className="hover:shadow-md transition-shadow cursor-pointer">
              <CardContent className="flex items-center justify-between p-6">
                <div>
                  <p className="text-sm font-medium text-gray-600">{stat.title}</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">{stat.value}</p>
                </div>
                <div className={`p-3 rounded-full ${stat.color}`}>
                  <stat.icon className="h-6 w-6" />
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link href="/dashboard/properties/new">
              <Button variant="outline" className="w-full justify-start">
                <Plus className="h-4 w-4 mr-2" />
                Add Property
              </Button>
            </Link>
            <Link href="/dashboard/documents/upload">
              <Button variant="outline" className="w-full justify-start">
                <FileText className="h-4 w-4 mr-2" />
                Upload Documents
              </Button>
            </Link>
            <Link href="/dashboard/analysis">
              <Button variant="outline" className="w-full justify-start">
                <BarChart3 className="h-4 w-4 mr-2" />
                View Analysis
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>

      {/* Recent Analysis Jobs */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Recent Analysis Jobs</CardTitle>
          <Link href="/dashboard/analysis">
            <Button variant="ghost" size="sm">
              View All <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          {recentJobs.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <BarChart3 className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>No analysis jobs yet.</p>
              <Link href="/dashboard/properties">
                <Button variant="outline" className="mt-4">
                  Get Started
                </Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {recentJobs.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center space-x-4">
                    <Clock className="h-5 w-5 text-gray-400" />
                    <div>
                      <p className="font-medium text-gray-900">
                        Property Analysis
                      </p>
                      <p className="text-sm text-gray-500">
                        {formatDate(job.created_at)}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(
                      job.status
                    )}`}
                  >
                    {job.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Credits Info */}
      <Card className="bg-primary-50 border-primary-200">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-primary-900">Your Credits</h3>
              <p className="text-primary-700 mt-1">
                You have <span className="font-bold">{user?.credits_remaining || 0}</span> credits remaining.
                Credits are used for analysis and document processing.
              </p>
            </div>
            <Button>
              Buy More Credits
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
