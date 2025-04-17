import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import EditPersonPage from './components/EditPersonPage';
import EditRelationshipPage from './components/EditRelationshipPage';
import PrivateRoute from './components/PrivateRoute';

function DashboardPage() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  
  const handleLogout = async () => {
      try {
          await logout();
          navigate('/login');
      } catch (error) {
          console.error('Logout failed', error);
      }
  };
  
  return (
    <div>
      <h2>Dashboard Page</h2>
      <button onClick={handleLogout}>Logout</button>
    </div>
  );
}

function App() {
    return (
        <AuthProvider>
            <Router>
                <nav>
                    <ul>
                        <li>
                           <Link to="/login">Login</Link>
                        </li>
                        <li>
                            <Link to="/register">Register</Link>
                        </li>
                        <li>
                            <Link to="/dashboard">Dashboard</Link>
                        </li>
                        <li>
                            <Link to="/edit_person">Edit Person</Link>
                        </li>
                        <li>
                            <Link to="/edit_relationship">Edit Relationship</Link>
                        </li>
                    </ul>
                </nav>
                <Routes>
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/register" element={<RegisterPage />} />
                    <Route path="/dashboard" element={
                        <PrivateRoute>
                            <DashboardPage />
                        </PrivateRoute>
                    } />
                    <Route path="/edit_person" element={<PrivateRoute>
                        <EditPersonPage />
                    </PrivateRoute>} />
                    <Route path="/edit_relationship" element={<PrivateRoute><EditRelationshipPage /></PrivateRoute>} />
                </Routes>
            </Router>
        </AuthProvider>
    );
}

export default App;
