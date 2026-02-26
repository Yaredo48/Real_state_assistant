'use client';

import { useState, useEffect } from 'react';
import { analysisApi, propertiesApi } from '@/lib/api';
import { AnalysisJob, Property } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Input';
import { BarChart3, Play, Eye, Download, RefreshCw, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { formatDate, getStatusColor } from '@/lib/utils';

export default function AnalysisPage() {
  const [jobs, setJobs] = useState<AnalysisJob[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [selectedProperty, setSelectedProperty] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [jobsRes, propertiesRes] = await Promise.all([
          analysisApi.listJobs(),
          propertiesApi.list(),
        ]);
        setJobs(jobsRes || []);
        setProperties(propertiesRes || []);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleStartAnalysis = async () => {
    if (!selectedProperty) {
      setError('Please select a property');
      return;
    }

    setError('');
    setIsAnalyzing(true);

    try {
      await analysisApi.analyze({ property_id: selectedProperty });
      // Refresh jobs list
      const jobsRes = await analysisApi.listJobs();
      setJobs(jobsRes || []);
      setSelectedProperty('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start analysis');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'processing':
      case 'pending':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analysis</h1>
        <p className="text-gray-600">Run AI-powered analysis on your properties</p>
      </div>

      {/* Start Analysis Card */}
      <Card>
        <CardHeader>
          <CardTitle>Start New Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <Select
                value={selectedProperty}
                onChange={(e) => setSelectedProperty(e.target.value)}
                options={[
                  { value: '', label: 'Select a property...' },
                  ...properties
                    .filter((p) => p.status !== 'analyzing')
                    .map((p) => ({
                      value: p.id,
                      label: p.property_address || p.property_city || 'Untitled Property',
                    })),
                ]}
              />
            </div>
            <Button onClick={handleStartAnalysis} isLoading={isAnalyzing}>
              <Play className="h-4 w-4 mr-2" />
              Start Analysis
            </Button>
          </div>

          <p className="mt-4 text-sm text-gray-500">
            Analysis requires 1 credit. Make sure you have sufficient credits available.
          </p>
        </CardContent>
      </Card>

      {/* Analysis Jobs List */}
      <Card>
        <CardHeader>
          <CardTitle>Analysis History</CardTitle>
        </CardHeader>
        <CardContent>
          {jobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <BarChart3 className="h-12 w-12 text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No analysis yet</h3>
              <p className="text-gray-500">Start an analysis to see results here</p>
            </div>
          ) : (
            <div className="space-y-4">
              {jobs.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center space-x-4">
                    {getStatusIcon(job.status)}
                    <div>
                      <p className="font-medium text-gray-900">
                        Property Analysis
                      </p>
                      <p className="text-sm text-gray-500">
                        {formatDate(job.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(
                        job.status
                      )}`}
                    >
                      {job.status}
                    </span>
                    {job.status === 'completed' && (
                      <div className="flex space-x-2">
                        <Button variant="ghost" size="sm">
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm">
                          <Download className="h-4 w-4" />
                        </Button>
                      </div>
                    )}
                    {job.status === 'failed' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => analysisApi.retryJob(job.id)}
                      >
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
