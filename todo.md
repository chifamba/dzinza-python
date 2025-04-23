# Project TODO List

## Core Backend/Features
- [x] Basic user authentication (login/logout/session check)
- [x] User registration
- [x] Add person to family tree
- [x] Edit person details
- [x] Delete person (and related relationships)
- [x] Add relationships between people
- [x] Edit relationship details
- [x] Delete relationship
- [x] View family tree structure (API for visualization)
- [x] User roles (Admin, Basic)
- [x] Admin user management (List, Delete, Change Role via API)
- [x] Search functionality for people (Backend API implemented)
- [x] Password reset functionality (Backend API and email logic implemented)
- [x] Audit logging for important actions
- [x] Data encryption at rest (`users.json`, `family_tree.json`)

## Refactoring: React Frontend & Visualization

### Phase 1: Backend API Preparation
- [x] Review and implement `/api/tree_data` endpoint for React Flow format.
- [x] Create RESTful API endpoint: `POST /api/register`.
- [x] Create RESTful API endpoint: `POST /api/login`.
- [x] Create RESTful API endpoint: `POST /api/logout`.
- [x] Create RESTful API endpoint: `GET /api/session`.
- [x] Create RESTful API endpoint: `GET /api/people`.
- [x] Create RESTful API endpoint: `GET /api/people/{id}`.
- [x] Create RESTful API endpoint: `POST /api/people`.
- [x] Create RESTful API endpoint: `PUT /api/people/{id}`.
- [x] Create RESTful API endpoint: `DELETE /api/people/{id}`.
- [x] Create RESTful API endpoint: `GET /api/relationships`.
- [x] Create RESTful API endpoint: `POST /api/relationships`.
- [x] Create RESTful API endpoint: `PUT /api/relationships/{id}`.
- [x] Create RESTful API endpoint: `DELETE /api/relationships/{id}`.
- [x] Create RESTful API endpoint: `POST /api/request-password-reset`.
- [x] Create RESTful API endpoint: `POST /api/reset-password/<token>`.
- [x] Create RESTful API endpoint: `GET /api/users` (Admin).
- [x] Create RESTful API endpoint: `DELETE /api/users/{id}` (Admin).
- [x] Create RESTful API endpoint: `PUT /api/users/{id}/role` (Admin).
- [x] Define and implement API authentication strategy (Session-based).
- [x] Implement consistent JSON error handling for all API endpoints.
- [x] Implement CORS support.

### Phase 2: Frontend Setup & Basic Interaction (React)
- [x] Create `frontend/` directory and initialize React project (Vite).
- [x] Install core dependencies: `react-router-dom`, `axios`, `reactflow`.
- [x] Set up basic frontend routing (Login, Register, Dashboard, Edit Forms, Admin).
- [x] Create core React components (App, LoginPage, RegisterPage, DashboardPage, Add/Edit Forms, AdminPage, etc.).
- [x] Create API service module (`api.js`) for frontend-backend communication.
- [x] Implement frontend state management (Context API for auth state).
- [x] Implement frontend login/registration forms and API calls.
- [x] Implement protected routes (`PrivateRoute`, `AdminRoute`).

### Phase 3: Visualization Integration (React Flow)
- [x] Create `FamilyTreeVisualization` React component.
- [x] Integrate `<ReactFlow>`, `<Background>`, `<Controls>`, `<MiniMap>`.
- [x] Fetch data from `/api/tree_data` endpoint in the component.
- [x] Implement layout strategy (Using Dagre via backend/frontend).
- [x] Configure hierarchical layout algorithm.
- [x] Implement basic node/edge rendering using fetched data.

### Phase 4: Enhanced Visualization & Interaction
- [x] Implement `onNodeClick` handler for node selection in React Flow.
- [x] Fetch detailed person data on node click (`GET /api/people/{id}`).
- [x] Display person details in a separate sidebar/modal component (`PersonDetails.jsx`).
- [x] Define and implement custom React Flow nodes (`PersonNode.js`) to show name, dates, photo placeholder, edit button.

### Phase 5: Editing & Performance
- [x] Connect "Edit" button in `PersonNode.jsx` to navigate to `EditPersonPage`.
- [x] Implement form submission to update person via API (`PUT /api/people/{id}`) in `EditPersonPage.jsx`.
- [x] Implement form submission to update relationship via API (`PUT /api/relationships/{id}`) in `EditRelationshipPage.jsx`.
- [ ] Add UI element (e.g., button in `PersonDetails` or on edge click) to navigate to `EditRelationshipPage`.
- [ ] Investigate/Implement performance optimizations for large trees (if needed):
    - [ ] Verify viewport rendering effectiveness provided by React Flow.
    - [ ] Consider lazy loading parts of the tree (requires frontend changes to use `/api/tree_data` query params).
    - [ ] Evaluate layout performance and consider backend pre-computation if client-side is too slow.

### Phase 6: Admin UI
- [x] Create `AdminPage.jsx` component.
- [x] Implement fetching and displaying user list (`GET /api/users`).
- [x] Implement role changing functionality (`PUT /api/users/{id}/role`).
- [x] Implement user deletion functionality (`DELETE /api/users/{id}`).
- [x] Protect admin route using `AdminRoute` guard.

### Phase 7: Cleanup
- [x] Remove unused Jinja2 templates from `backend/src/templates/` (if any existed).
- [x] Remove Flask routes in `backend/app.py` used only for old server-side rendering (if any existed).
- [x] Remove duplicate `frontend/README.md`.

## Frontend TODOs (Remaining/Refinement)
- [ ] Implement frontend UI for password reset request and token handling.
- [ ] Implement frontend search interface to use backend search capabilities.
- [ ] Add UI element to trigger navigation to `EditRelationshipPage`.
- [ ] Refactor frontend component structure for better organization/scalability.
- [ ] Improve UI/UX (loading states, error messages, general flow, styling).

## General Improvements (Ongoing)
- [ ] Improve general backend error handling and logging details.
- [ ] Refactor database interactions (potentially use a simple ORM or dedicated data layer) - *Lower priority*.
- [ ] Ensure `load_data`/`save_data` usage is robust, especially error handling during encryption/decryption.
- [ ] Add password complexity rules during registration/reset.

## Testing (Updated Focus)
- **Backend:**
    - [x] Unit tests for core classes (`Person`, `Relationship`, `User`, `FamilyTree`, `UserManagement`).
    - [x] Unit tests for utilities (`encryption`, `db_utils`, `audit_log`).
    - [x] Basic integration tests for Flask app (`test_app.py`).
    - [x] API Integration tests (`test_api.py` - expanded).
- **Frontend:**
    - [x] Basic component tests (`LoginPage.test.jsx`, `DashboardPage.test.jsx`).
    - [ ] Add more component tests (e.g., `AdminPage`, `EditPersonPage`, `FamilyTreeVisualization`).
    - [ ] Add tests for context (`AuthContext`).
    - [ ] Add tests for routing.
- **End-to-End:**
    - [ ] Implement E2E tests for key user workflows (e.g., using Cypress or Playwright).

## Documentation
- [x] Basic `README.md` (updated for new structure, env vars, running tests).
- [x] Document API endpoints in `api_docs.md` (updated).
- [x] Improve backend docstrings (ongoing).
- [ ] Add detailed usage instructions for the React frontend to `README.md`.
- [ ] (Optional) Set up project documentation website (e.g., using Sphinx for backend, Storybook/Styleguidist for frontend).

## Deployment
- [ ] Configure Flask backend for production API deployment (e.g., Gunicorn, Nginx).
- [ ] Configure React frontend build process for production.
- [ ] Set up database/data storage for production (if moving away from JSON).
- [ ] Containerize the application (Docker - backend & frontend services).
