import React, { useState } from 'react';
import LoginForm from './LoginForm';
import RegisterForm from './RegisterForm';
import PasswordResetForm from './PasswordResetForm';

type AuthView = 'login' | 'register' | 'password-reset' | 'registration-success';

const AuthContainer: React.FC = () => {
  const [currentView, setCurrentView] = useState<AuthView>('login');

  const handleSwitchToLogin = () => setCurrentView('login');
  const handleSwitchToRegister = () => setCurrentView('register');
  const handleSwitchToPasswordReset = () => setCurrentView('password-reset');
  const handleRegistrationSuccess = () => setCurrentView('registration-success');

  if (currentView === 'registration-success') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 flex items-center justify-center rounded-full bg-green-600">
              <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
              Account created successfully!
            </h2>
            <p className="mt-2 text-center text-sm text-gray-600">
              Your account has been created. Please sign in to start building your family tree.
            </p>
          </div>

          <div className="mt-8">
            <button
              onClick={handleSwitchToLogin}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 transition-colors duration-200"
            >
              Sign In to Your Account
            </button>
          </div>
        </div>
      </div>
    );
  }

  switch (currentView) {
    case 'register':
      return (
        <RegisterForm
          onSwitchToLogin={handleSwitchToLogin}
          onRegistrationSuccess={handleRegistrationSuccess}
        />
      );
    case 'password-reset':
      return (
        <PasswordResetForm
          onSwitchToLogin={handleSwitchToLogin}
        />
      );
    case 'login':
    default:
      return (
        <LoginForm
          onSwitchToRegister={handleSwitchToRegister}
          onSwitchToPasswordReset={handleSwitchToPasswordReset}
        />
      );
  }
};

export default AuthContainer;
