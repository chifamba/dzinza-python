'use client';

import React from 'react';
import { ActivityFeed } from '@/components/ActivityFeed';
import { useActivity } from '@/lib/activity';

export default function FamilyTreePage() {
  const { activities, loading, error } = useActivity();

  return (
    <div className="grid grid-cols-3 gap-6 p-6">
      <div className="col-span-2">
        {/* Family tree visualization will go here */}
      </div>
      <div>
        <ActivityFeed activities={activities} className="sticky top-6" />
      </div>
    </div>
  );
}
