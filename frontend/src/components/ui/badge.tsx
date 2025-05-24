import React from 'react';

export const Badge = ({ children, variant, className, ...props }: { children: React.ReactNode; variant?: string; className?: string; [key: string]: any }) => (
  <span style={{ padding: '0.2em 0.5em', backgroundColor: '#eee', borderRadius: '0.2em' }} className={className} {...props}>
    {children}
  </span>
);
