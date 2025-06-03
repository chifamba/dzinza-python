import React from 'react';
import { BookOpen, Users, Settings, ZoomIn, ZoomOut, RefreshCw, Save, RotateCcw } from 'lucide-react'; // Added more icons
import { ZoomControlFunctions, LayoutControlFunctions } from './FamilyTreeView'; // Import interfaces

interface HeaderProps {
  onAddPerson: () => void;
  zoomControls?: ZoomControlFunctions;
  layoutControls?: LayoutControlFunctions; // New prop for layout controls
}

const Header: React.FC<HeaderProps> = ({ onAddPerson, zoomControls, layoutControls }) => {
  return (
    <header className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          {/* Left section: Title and Action Buttons */}
          <div className="flex items-center"> {/* Parent for title and all action buttons */}
            <div className="flex items-center"> {/* Group title and icon */}
              <BookOpen className="w-8 h-8 text-amber-500" />
              <h1 className="ml-2 text-xl font-semibold text-gray-900">Family Tree Explorer</h1>
            </div>

            {/* Container for all action button groups */}
            {(zoomControls || layoutControls) && ( // Only show this container if there are any controls
              <div className="flex items-center ml-6"> {/* ml-6 to space from title */}
                {/* Zoom Buttons Group */}
                {zoomControls && (
                  <div className="flex items-center space-x-1 p-1 bg-gray-50 rounded-lg shadow-inner"> {/* Subtle background and inner shadow for group */}
                    <button
                      onClick={zoomControls.zoomIn}
                      className="p-1.5 text-gray-700 hover:text-gray-900 hover:bg-gray-200 rounded-md"
                      title="Zoom In"
                    >
                      <ZoomIn className="w-5 h-5" />
                    </button>
                    <button
                      onClick={zoomControls.zoomOut}
                      className="p-1.5 text-gray-700 hover:text-gray-900 hover:bg-gray-200 rounded-md"
                      title="Zoom Out"
                    >
                      <ZoomOut className="w-5 h-5" />
                    </button>
                    <button
                      onClick={zoomControls.resetZoom}
                      className="p-1.5 text-gray-700 hover:text-gray-900 hover:bg-gray-200 rounded-md"
                      title="Reset Zoom"
                    >
                      <RefreshCw className="w-5 h-5" />
                    </button>
                  </div>
                )}
                {/* Layout Control Buttons Group */}
                {layoutControls && (
                  // Added ml-3 for spacing between button groups, no border if zoom group is present
                  <div className={`flex items-center space-x-1 p-1 bg-gray-50 rounded-lg shadow-inner ${zoomControls ? 'ml-3' : ''}`}>
                    <button
                      onClick={layoutControls.save}
                      className="p-1.5 text-gray-700 hover:text-gray-900 hover:bg-gray-200 rounded-md"
                      title="Save Layout"
                    >
                      <Save className="w-5 h-5" />
                    </button>
                    <button
                      onClick={layoutControls.reset}
                      className="p-1.5 text-gray-700 hover:text-gray-900 hover:bg-gray-200 rounded-md"
                      title="Reset Layout"
                    >
                      <RotateCcw className="w-5 h-5" />
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right section: Navigation */}
          <nav className="flex space-x-4 items-center">
            <button className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium flex items-center">
              <Users className="w-5 h-5 mr-1" />
              <span>Tree</span>
                </button>
              </div>
            )}
          </div>
          
          <nav className="flex space-x-4 items-center"> {/* Added items-center for vertical alignment */}
            <button className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium flex items-center">
              <Users className="w-5 h-5 mr-1" />
              <span>Tree</span>
            </button>
            
            <button 
              onClick={onAddPerson}
              className="bg-amber-500 text-white hover:bg-amber-600 px-3 py-2 rounded-md text-sm font-medium"
            >
              Add Person
            </button>
            
            <button className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
              <Settings className="w-5 h-5" />
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
};

export default Header;