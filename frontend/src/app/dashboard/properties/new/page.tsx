'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { propertiesApi } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input, Textarea } from '@/components/ui/Input';
import { ArrowLeft, Building2 } from 'lucide-react';
import Link from 'next/link';

export default function NewPropertyPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    property_address: '',
    property_city: '',
    property_zone: '',
    property_description: '',
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const property = await propertiesApi.create(formData);
      router.push(`/dashboard/properties/${property.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create property');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link
          href="/dashboard/properties"
          className="inline-flex items-center text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Properties
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Add New Property</CardTitle>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {error}
              </div>
            )}

            <Input
              label="Property Address"
              name="property_address"
              value={formData.property_address}
              onChange={handleChange}
              placeholder="123 Main Street"
              required
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="City"
                name="property_city"
                value={formData.property_city}
                onChange={handleChange}
                placeholder="New York"
                required
              />

              <Input
                label="Zone/Area"
                name="property_zone"
                value={formData.property_zone}
                onChange={handleChange}
                placeholder="Manhattan"
              />
            </div>

            <Textarea
              label="Description"
              name="property_description"
              value={formData.property_description}
              onChange={handleChange}
              placeholder="Describe the property..."
              rows={4}
            />
          </CardContent>
          <CardFooter className="flex justify-end space-x-4">
            <Link href="/dashboard/properties">
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </Link>
            <Button type="submit" isLoading={isLoading}>
              Create Property
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
