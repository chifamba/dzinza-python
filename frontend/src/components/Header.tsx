import React from 'react';
import { BookOpen, Users, Settings } from 'lucide-react';

interface HeaderProps {
  onAddPerson: () => void;
}

const Header: React.FC<HeaderProps> = ({ onAddPerson }) => {
  return (
    <header className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <div className="flex items-center">
            <BookOpen className="w-8 h-8 text-amber-500" />
            <h1 className="ml-2 text-xl font-semibold text-gray-900">Family Tree Explorer</h1>
          </div>
          
          <nav className="flex space-x-4">
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