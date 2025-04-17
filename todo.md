# Project TODO List

## Core Backend/Features (Completed)
- [x] Basic user authentication (login/logout)
- [x] Add person to family tree
- [x] Edit person details
- [x] Add relationships between people
- [x] View family tree structure (basic text representation)
- [x] User roles (Admin, User)
- [x] Admin user management panel
- [x] Search functionality for people
- [x] Password reset functionality
- [x] Audit logging for important actions
- [x] User deletion logic

## Refactoring: React Frontend & Visualization

### Phase 0: Project Structure Cleanup (Completed)
- [x] Create `backend/` directory in project root.
- [x] Move `src/`, `tests/`, `app.py`, `requirements.txt` into `backend/`.
- [x] Move `data/` directory into `backend/`.
- [x] Create `logs/backend/` and `logs/frontend/` directories.
- [x] Update paths in `app.py` for data files (`USERS_FILE`, `FAMILY_TREE_FILE`), audit log (`AUDIT_LOG_FILE`), and app log (`APP_LOG_FILE`) to reflect new locations (e.g., relative to `app.py` inside `backend/` or using absolute paths).
- [x] Update paths in test files (`tests/*`) if they rely on specific relative paths to data or source files.
- [x] Update or remove `devserver.sh` (README now uses direct `flask run` commands).
- [x] Ensure `.gitignore` correctly ignores `venv`, `logs`, potentially `backend/data` if desired, etc.
- [x] Verify backend tests still run correctly from within the `backend/` directory.

### Phase 1: Backend API Preparation
- [x] Review and potentially modify `/api/tree_data` endpoint for optimal React Flow format (check node/edge structure, add photo URLs if needed).
- [ ] Review and improve password reset flow (email, etc)
- [x] Create RESTful API endpoint: `POST /api/register` (return JSON).
- [x] Create RESTful API endpoint: `POST /api/login` (return JSON, handle session/token).
- [x] Create RESTful API endpoint: `GET /api/people`.
- [x] Create RESTful API endpoint: `GET /api/people/{id}`.
- [x] Create RESTful API endpoint: `POST /api/people`.
- [x] Create RESTful API endpoint: `PUT /api/people/{id}`.
- [x] Create RESTful API endpoint: `DELETE /api/people/{id}`.
- [x] Create RESTful API endpoint: `GET /api/relationships`.
- [x] Create RESTful API endpoint: `POST /api/relationships`.
- [x] Create RESTful API endpoint: `PUT /api/relationships/{id}`.
- [x] Create RESTful API endpoint: `DELETE /api/relationships/{id}`.
- [ ] Define and implement API authentication strategy (e.g., session/JWT, CORS).
- [ ] Implement consistent JSON error handling for all API endpoints.

### Phase 2: Frontend Setup & Basic Interaction (React)
- [x] Create `frontend/` directory in project root.
- [x] Initialize React project inside `frontend/` (using Vite or CRA).
- [x] Install core dependencies: `react-router-dom`, `axios`, `reactflow`.
- [x] Set up basic frontend routing (Login, Register, Dashboard, Edit Forms). 
- [x] Create core React components (App, LoginPage, RegisterPage, DashboardPage, PersonDetailsForm, RelationshipForm).
- [x] Create API service module (`api.js`) for frontend-backend communication. 
- [x] Implement basic frontend state management (e.g., Context API) for auth state. 
- [x] Implement frontend login/registration forms and API calls.
- [x] Implement protected routes based on authentication state.

### Phase 3: Visualization Integration (React Flow)
- [x] Create `FamilyTreeVisualization` React component.
- [x] Integrate `<ReactFlow>`, `<Background>`, `<Controls>`, `<MiniMap>`.
- [x] Fetch data from `/api/people` and `/api/relationships` endpoint in the component. 
- [x] Implement layout strategy (Backend pre-computed or Frontend library like Dagre).
- [x] Configure hierarchical layout algorithm (e.g., `rankdir: 'TB'`).
- [x] Implement basic node/edge rendering using fetched data.
- [ ] Ensure basic zoom/pan functionality works via `<Controls>` and default behavior.
### Phase 4: Enhanced Visualization & Interaction (Completed)
- [x] Implement `onNodeClick` handler for node selection in React Flow.
- [x] Fetch detailed person data on node click (`GET /api/people/{id}`). 
- [x] Display person details in a separate sidebar/modal component.
- [x] Define and implement custom React Flow nodes (`PersonNode.js`) to show more details (name, dates, photo placeholder).
- [ ] Implement conditional styling for nodes (e.g., based on gender using `className` or `style`).
- [ ] Implement conditional styling for edges (e.g., based on relationship type using `className` or `style`).
### Phase 5: Editing & Performance
- [ ] Connect node click/action (e.g., double-click or button in custom node) to open `PersonDetailsForm` (e.g., in a modal).
- [ ] Pre-fill form with selected person data.
- [ ] Implement form submission to update person via API (`PUT /api/people/{id}`).
- [ ] Update React Flow state (nodes/edges) or re-fetch data after successful edit.
- [ ] Investigate/Implement performance optimizations for large trees (if needed):
    - [ ] Verify viewport rendering effectiveness provided by React Flow.
    - [ ] Consider lazy loading parts of the tree (requires backend changes).
    - [ ] Evaluate layout performance and consider backend pre-computation if client-side is too slow.

### Phase 6: Cleanup
- [ ] Remove unused Jinja2 templates from `backend/src/templates/` (if they were moved there).
- [ ] Remove Flask routes in `backend/app.py` used only for old server-side rendering and forms.

## General Improvements (Ongoing)
- [x] Improve general backend error handling and logging.
- [ ] Refactor database interactions (potentially use a simple ORM or dedicated data layer) - *this has lower priority during the frontend refactor*.
- [x] Refactor the database layer to use `load_data` and `save_data` properly.
- [ ] Add input validation for all API endpoints.
- [ ] Secure sensitive data (e.g., encryption for stored data beyond passwords).

## Testing (Updated Focus)
- [x] Unit tests for `Person` class (`test_person.py`)
- [x] Unit tests for `Relationship` class (`test_relationship.py`)
- [x] Unit tests for `User` class (`test_user.py`)
- [x] Unit tests for `FamilyTree` class (`test_family_tree.py`)
- [x] Unit tests for `UserManagement` (`test_user_management.py`)
- [x] Unit tests for `encryption` module (`test_encryption.py`)
- [x] Unit tests for `db_utils` module (`test_db_utils.py`)
- [x] Unit tests for `audit_log` module (`test_audit_log.py`)
- [x] Basic integration tests for Flask app (`test_app_integration.py`)
- [x] Basic tests for Flask app routes (`test_app.py`)
- [ ] Add integration tests specifically for the new RESTful API endpoints (run from `backend/`).
- [ ] Implement Frontend unit/integration tests (e.g., using Jest, React Testing Library) (run from `frontend/`).
- [ ] Implement End-to-End tests for UI interactions (e.g., using Cypress or Playwright).

## Documentation
- [x] Basic README.md (updated for new structure).
- [ ] Add detailed usage instructions for the new React frontend.
- [ ] Document API endpoints (e.g., using Swagger/OpenAPI in backend).
- [ ] Document code modules and functions (docstrings in backend).
- [ ] Set up project documentation website (e.g., using Sphinx for backend, Storybook/Styleguidist for frontend).

## Deployment
- [ ] Configure Flask backend for production API deployment (e.g., Gunicorn, Nginx).
- [ ] Configure React frontend build process for production.
- [ ] Set up database/data storage for production.
- [ ] Containerize the application (Docker - backend & frontend services).
