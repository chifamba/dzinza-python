# Dzinza Frontend Documentation

## Overview

This document provides information about the frontend architecture, components, and APIs for the Dzinza family tree application. The frontend is built with Next.js, TypeScript, React, and TailwindCSS.

## Table of Contents

1. [Project Structure](#project-structure)
2. [State Management](#state-management)
3. [Authentication](#authentication)
4. [API Integration](#api-integration)
5. [Components](#components)
6. [Routing](#routing)
7. [Media Handling](#media-handling)
8. [Activity Tracking](#activity-tracking)
9. [Tree Sharing & Permissions](#tree-sharing--permissions)
10. [Deployment](#deployment)

## Project Structure

```
frontend/
  ├── src/
  │   ├── api.js               # API client and endpoints
  │   ├── app/                 # Next.js app router pages
  │   ├── components/          # UI components
  │   │   ├── auth/            # Authentication components
  │   │   ├── media/           # Media handling components
  │   │   ├── activity/        # Activity feed components
  │   │   ├── tree/            # Tree management components
  │   │   └── ui/              # Shadcn UI components
  │   ├── contexts/            # React contexts for state management
  │   ├── hooks/               # Custom React hooks
  │   ├── lib/                 # Utility functions and types
  │   └── services/            # Service classes
  ├── public/                  # Static files
  ├── tailwind.config.ts       # Tailwind CSS configuration
  ├── tsconfig.json            # TypeScript configuration
  └── package.json             # NPM dependencies
```

## State Management

The application uses React Context API for state management. The following contexts are available:

- **AuthContext**: Manages user authentication state, roles, and permissions
- **TreeContext**: Manages active tree and tree-related functionality
- **ActivityContext**: Manages activity tracking and notification

### Example: Using AuthContext

```tsx
import { useAuth } from '@/contexts/AuthContext';

function MyComponent() {
  const { user, logout, hasRole } = useAuth();
  
  if (hasRole('admin')) {
    // Show admin functionality
  }
  
  return (
    <button onClick={logout}>Logout</button>
  );
}
```

## Authentication

Authentication is handled through JSON Web Tokens (JWT) stored in HTTP-only cookies. The `AuthContext` provides methods for login, logout, and checking user permissions.

### Role-Based Access Control

The application supports the following user roles:

- **Guest**: Limited read-only access
- **User**: Standard access to own trees
- **Researcher**: Extended access for genealogical research
- **Admin**: Full access to all features

### Route Protection

Routes are protected using the following components:

- `ProtectedRoute`: Requires authentication
- `AdminRoute`: Requires admin role
- `TreeOwnerRoute`: Requires specific permissions for a tree

Example:

```tsx
<ProtectedRoute requiredRole="admin">
  <AdminDashboard />
</ProtectedRoute>
```

## API Integration

API calls are centralized in the `api.js` file. The API client uses Axios for HTTP requests and supports the following features:

- Automatic cookie handling for authentication
- Request/response interceptors
- Error handling
- File uploads

### Example API Call

```js
// Get a list of user's trees
const trees = await api.getUserTrees();
```

## Components

### Core Components

- **PersonForm**: Form for creating/editing person details
- **RelationshipForm**: Form for creating/editing relationships
- **TreeView**: Main tree visualization component
- **ActivityFeed**: Display of recent activities
- **ShareTreeDialog**: Interface for sharing trees with other users

### UI Components

The application uses [Shadcn UI](https://ui.shadcn.com/) as a component library, which provides a set of accessible, reusable, and customizable components.

## Routing

The application uses Next.js App Router for navigation. The main routes are:

- `/`: Home page / landing page
- `/login`: Authentication page
- `/dashboard`: User dashboard
- `/tree/:treeId`: Tree view page
- `/person/:personId`: Person details page
- `/settings`: User settings
- `/admin`: Admin dashboard (admin only)

## Media Handling

### Image Upload

Image uploads are handled using the `ProfilePictureUploader` component, which provides:

- Image selection
- Preview
- Cropping (using react-easy-crop)
- Upload to backend

### Media Gallery

The `MediaGallery` component provides:

- File upload for various document types
- Media browsing
- Tagging
- Filtering

## Activity Tracking

Activities are tracked using the `EventTracker` service, which:

1. Collects user actions
2. Buffers them for batch processing
3. Sends to the server with retry capabilities
4. Handles errors gracefully

The `ActivityFeed` component offers:

- Chronological feed of activities
- Timeline view
- Filtering by type, person, and date
- Activity grouping
- Export capabilities

## Tree Sharing & Permissions

Users can share trees with other users through the `ShareTreeDialog` component. Three permission levels are available:

1. **View**: Read-only access
2. **Edit**: Can modify people and relationships
3. **Admin**: Full access including sharing, deleting, and settings

## Deployment

The frontend is Dockerized for easy deployment. The Dockerfile handles:

- Node.js installation
- Dependency installation
- Building the Next.js application
- Serving the built application

### Development Setup

```bash
# Install dependencies
npm install

# Run development server
npm run dev
```

### Production Build

```bash
# Build the application
npm run build

# Start the production server
npm start
```

## Best Practices

1. **TypeScript**: Use type definitions for all props, state, and function parameters
2. **Error Handling**: Implement proper error handling for API calls
3. **Loading States**: Show loading indicators during async operations
4. **Testing**: Write unit tests for critical components
5. **Accessibility**: Ensure components meet WCAG guidelines
6. **Performance**: Optimize rendering using React.memo, useMemo, and useCallback
7. **Documentation**: Add JSDoc comments to functions and components

## Troubleshooting

Common issues and their solutions:

1. **Authentication Issues**: Clear cookies and reload
2. **API Connection Errors**: Check backend server status
3. **Image Upload Problems**: Check file size and format
4. **Performance Issues**: Check for unnecessary re-renders
