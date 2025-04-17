import React, { useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import FamilyTreeVisualization from './FamilyTreeVisualization';

function DashboardPage() {
  const { logout } = useContext(AuthContext);
  const navigate = useNavigate();

  return (
    <div>
        <FamilyTreeVisualization/>
    </div>
  );
}

export default DashboardPage;