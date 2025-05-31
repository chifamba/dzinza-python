import React from 'react';

interface TreeConnectorProps {
  type: 'vertical' | 'horizontal' | 'down-right' | 'down-left';
  length?: number;
}

const TreeConnector: React.FC<TreeConnectorProps> = ({ type, length = 20 }) => {
  switch (type) {
    case 'vertical':
      return (
        <div className="flex justify-center">
          <div className={`w-0.5 bg-gray-300`} style={{ height: `${length}px` }}></div>
        </div>
      );
    
    case 'horizontal':
      return (
        <div className="flex items-center">
          <div className={`h-0.5 bg-gray-300`} style={{ width: `${length}px` }}></div>
        </div>
      );
    
    case 'down-right':
      return (
        <div className="relative" style={{ height: `${length}px`, width: `${length}px` }}>
          <div className="absolute top-0 left-0 w-0.5 h-1/2 bg-gray-300"></div>
          <div className="absolute top-1/2 left-0 h-0.5 w-full bg-gray-300"></div>
        </div>
      );
    
    case 'down-left':
      return (
        <div className="relative" style={{ height: `${length}px`, width: `${length}px` }}>
          <div className="absolute top-0 right-0 w-0.5 h-1/2 bg-gray-300"></div>
          <div className="absolute top-1/2 right-0 h-0.5 w-full bg-gray-300"></div>
        </div>
      );
    
    default:
      return null;
  }
};

export default TreeConnector;