import React from 'react';

// Enhanced Tabs component with proper props
export const Tabs = ({ 
  children, 
  value, 
  onValueChange, 
  className, 
  ...props 
}: { 
  children: React.ReactNode; 
  value?: string; 
  onValueChange?: (value: string) => void; 
  className?: string;
  [key: string]: any;
}) => (
  <div className={className} {...props}>{children}</div>
);

// Enhanced TabsContent component with proper props
export const TabsContent = ({ 
  children, 
  value, 
  className, 
  ...props 
}: { 
  children: React.ReactNode; 
  value: string; 
  className?: string;
  [key: string]: any;
}) => (
  <div className={className} {...props}>{children}</div>
);

// Enhanced TabsList component with proper props
export const TabsList = ({ 
  children, 
  className, 
  ...props 
}: { 
  children: React.ReactNode; 
  className?: string;
  [key: string]: any;
}) => (
  <div className={className} {...props}>{children}</div>
);

// Enhanced TabsTrigger component with proper props
export const TabsTrigger = ({ 
  children, 
  value, 
  className, 
  ...props 
}: { 
  children: React.ReactNode; 
  value?: string;
  className?: string;
  [key: string]: any;
}) => (
  <button className={className} {...props}>{children}</button>
);
