sequenceDiagram
    actor Client
    participant Gunicorn as Web Server
    participant FlaskApp as Flask App (main.py)
    participant LimiterExt as Rate Limiter
    participant AuthBP as Auth Blueprint (auth.py)
    participant Decorators as Auth Decorators (decorators.py)
    participant TreesBP as Trees Blueprint (trees.py)
    participant UserService as User Service (user_service.py)
    participant TreeService as Tree Service (tree_service.py)
    participant SessionExt as Session Mgmt (Redis)
    participant Database as SQLAlchemy (database.py)

    %% User Registration
    Client->>Gunicorn: POST /api/register (username, email, password)
    Gunicorn->>FlaskApp: Forward request
    FlaskApp->>LimiterExt: Check rate limit
    LimiterExt-->>FlaskApp: OK
    FlaskApp->>AuthBP: Route to register_endpoint
    AuthBP->>UserService: register_user_db(data)
    UserService->>UserService: Validate password complexity
    UserService->>UserService: Hash password
    UserService->>Database: Create User object
    Database-->>UserService: User object (pre-commit)
    UserService->>Database: Commit session
    Database-->>UserService: Commit OK
    UserService-->>AuthBP: User details (dict)
    AuthBP-->>FlaskApp: JSON Response (201 Created)
    FlaskApp-->>Gunicorn: HTTP Response
    Gunicorn-->>Client: HTTP 201 (User Registered)

    %% User Login
    Client->>Gunicorn: POST /api/login (username, password)
    Gunicorn->>FlaskApp: Forward request
    FlaskApp->>LimiterExt: Check rate limit
    LimiterExt-->>FlaskApp: OK
    FlaskApp->>AuthBP: Route to login_endpoint
    AuthBP->>UserService: authenticate_user_db(username, password)
    UserService->>Database: Query User by username/email
    Database-->>UserService: User object or None
    alt User found and password matches
        UserService->>UserService: Verify password
        UserService->>Database: Update last_login
        Database-->>UserService: Commit OK
        UserService-->>AuthBP: User details (dict)
        AuthBP->>SessionExt: Create/Update session (user_id, role)
        SessionExt-->>AuthBP: Session cookie set
        AuthBP-->>FlaskApp: JSON Response (200 OK)
    else User not found or password mismatch
        UserService-->>AuthBP: None (or error indication)
        AuthBP-->>FlaskApp: JSON Response (401 Unauthorized)
    end
    FlaskApp-->>Gunicorn: HTTP Response
    Gunicorn-->>Client: HTTP 200 OK or 401 Unauthorized

    %% Fetch Trees (Protected Endpoint)
    Client->>Gunicorn: GET /api/trees (with session cookie)
    Gunicorn->>FlaskApp: Forward request
    FlaskApp->>Decorators: @require_auth
    Decorators->>SessionExt: Check session for user_id
    alt Session valid
        SessionExt-->>Decorators: User authenticated
        Decorators-->>FlaskApp: Proceed
        FlaskApp->>TreesBP: Route to get_user_trees_endpoint
        TreesBP->>TreeService: get_user_trees_db(user_id, pagination_params)
        TreeService->>Database: Query Tree & TreeAccess models
        Database-->>TreeService: Tree data
        TreeService->>TreeService: Paginate results
        TreeService-->>TreesBP: Paginated tree list (dict)
        TreesBP-->>FlaskApp: JSON Response (200 OK)
    else Session invalid
        SessionExt-->>Decorators: Authentication failed
        Decorators-->>FlaskApp: Abort(401)
        FlaskApp-->>Gunicorn: HTTP Response (401 Unauthorized)
    end
    FlaskApp-->>Gunicorn: HTTP Response
    Gunicorn-->>Client: HTTP 200 OK (Tree List) or 401 Unauthorized
Explanation of Participants:Client: The user's browser or API client.Web Server (Gunicorn): Handles incoming HTTP requests and forwards them to the Flask application.Flask App (main.py): The central Flask application instance. It handles routing, request/response lifecycle, and coordinates with other components.Rate Limiter (LimiterExt): The Flask-Limiter extension, checking request rates.Auth Blueprint (auth.py): Handles authentication-related routes like login, registration.Auth Decorators (decorators.py): Contains decorators like @require_auth to protect routes.Trees Blueprint (trees.py): Handles routes related to tree management.User Service (user_service.py): Contains business logic for user operations (registration, authentication).Tree Service (tree_service.py): Contains business logic for tree operations.Session Mgmt (Redis): The Flask-Session extension interacting with Redis to manage user sessions.SQLAlchemy (database.py): Represents the database interaction layer (SQLAlchemy ORM, session management).This diagram provides a high-level overview of the request flow for these common scenarios. You can adapt this syntax or use a dedicated diagramming tool to visualize it.