import React from 'react';
import { HelpCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import Button from './Button';

const QuickAccessButton: React.FC = () => {
  return (
    <div className="fixed bottom-4 left-4 z-50">
      <Link to="/help">
        <Button
          className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 shadow-lg"
          icon={HelpCircle}
        >
          <span className="hidden sm:inline">Help & Support</span>
          <span className="sm:hidden">Help</span>
        </Button>
      </Link>
    </div>
  );
};

export default QuickAccessButton;