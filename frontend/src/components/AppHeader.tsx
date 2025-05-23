import React from 'react';
import { Button } from "@/components/ui/button"; // Assuming Button is in ui

const AppHeader: React.FC = () => {
  return (
    <header className="bg-card text-card-foreground p-4 shadow-sm">
      <div className="container mx-auto flex justify-between items-center">
        <h1 className="text-2xl font-bold text-primary">Dzinza</h1>
        <div className="space-x-2">
          <Button variant="outline">Add Person</Button>
          <Button variant="ghost">Reset View</Button>
        </div>
      </div>
    </header>
  );
};

export default AppHeader;
