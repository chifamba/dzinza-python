# Dzinza Family Tree Application Data Model

## Overview

This document provides a comprehensive data model design for the Dzinza Family Tree application. The model is optimized for:

- Complex family relationship querying
- High-performance tree traversals
- Scalability for large family trees
- Data integrity and consistency
- Extensibility for custom genealogical attributes

## Assumptions

1. The application will need to handle family trees with potentially tens of thousands of individuals
2. Users may require complex queries across multiple generations
3. Tree traversals (ancestors, descendants, extended family) are common operations
4. Data needs to be extensible to accommodate various cultural differences in family relationships
5. Media attachments will be stored with references in the database
6. Multiple users may collaborate on the same family tree
7. Performance is critical, especially for tree visualization operations
8. The application requires robust audit trails for genealogical research integrity

## Database Technology

**PostgreSQL 14+** has been selected for several compelling reasons:

- Advanced indexing capabilities (B-tree, GIN, BRIN)
- JSON/JSONB support for flexible attribute storage
- Robust transaction support and ACID compliance
- Excellent performance for relational data and complex joins


## Core Schema Design

### Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    preferences JSONB DEFAULT '{}'::jsonb,
    profile_image_path VARCHAR(255),
    
    CONSTRAINT valid_roles CHECK (role IN ('user', 'admin', 'researcher', 'guest'))
);

CREATE INDEX idx_users_username ON users (username);
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_role ON users (role);
```

### Trees Table

```sql
CREATE TABLE trees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by UUID NOT NULL REFERENCES users(id),
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    default_privacy_level VARCHAR(50) NOT NULL DEFAULT 'private',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_privacy_level CHECK (default_privacy_level IN ('private', 'public', 'connections', 'researchers'))
);

CREATE INDEX idx_trees_created_by ON trees (created_by);
CREATE INDEX idx_trees_public ON trees (is_public) WHERE is_public = TRUE;
```

### TreeAccess Table

```sql
CREATE TABLE tree_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    access_level VARCHAR(50) NOT NULL DEFAULT 'view',
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT tree_user_unique UNIQUE (tree_id, user_id),
    CONSTRAINT valid_access_level CHECK (access_level IN ('view', 'edit', 'admin'))
);

CREATE INDEX idx_tree_access_tree_id ON tree_access (tree_id);
CREATE INDEX idx_tree_access_user_id ON tree_access (user_id);
```

### People Table

```sql
CREATE TABLE people (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    first_name VARCHAR(100),
    middle_names VARCHAR(255),
    last_name VARCHAR(100),
    maiden_name VARCHAR(100),
    nickname VARCHAR(100),
    gender VARCHAR(20),
    birth_date DATE,
    birth_date_approx BOOLEAN NOT NULL DEFAULT FALSE,
    birth_place VARCHAR(255),
    death_date DATE,
    death_date_approx BOOLEAN NOT NULL DEFAULT FALSE,
    death_place VARCHAR(255),
    burial_place VARCHAR(255),
    privacy_level VARCHAR(50) NOT NULL DEFAULT 'inherit',
    is_living BOOLEAN,
    notes TEXT,
    custom_attributes JSONB DEFAULT '{}'::jsonb,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    slug VARCHAR(255) GENERATED ALWAYS AS (
        LOWER(
            REGEXP_REPLACE(
                COALESCE(first_name, '') || '-' || 
                COALESCE(last_name, '') || '-' || 
                SUBSTRING(id::text, 1, 8),
            '[^a-zA-Z0-9]', '-', 'g')
        )
    ) STORED,
    
    CONSTRAINT valid_gender CHECK (gender IN ('male', 'female', 'other', 'unknown')),
    CONSTRAINT valid_privacy_level CHECK (privacy_level IN ('inherit', 'private', 'public', 'connections', 'researchers'))
);

CREATE INDEX idx_people_tree_id ON people (tree_id);
CREATE INDEX idx_people_names ON people (tree_id, last_name, first_name);
CREATE INDEX idx_people_birth_date ON people (tree_id, birth_date) WHERE birth_date IS NOT NULL;
CREATE INDEX idx_people_death_date ON people (tree_id, death_date) WHERE death_date IS NOT NULL;
CREATE INDEX idx_people_created_by ON people (created_by);
CREATE INDEX idx_people_is_living ON people (tree_id, is_living) WHERE is_living IS NOT NULL;
CREATE INDEX idx_people_slug ON people (slug);
CREATE INDEX idx_people_custom_attrs ON people USING GIN (custom_attributes);
```

### Relationships Table

```sql
CREATE TYPE relationship_type AS ENUM (
    'biological_parent', 'adoptive_parent', 'step_parent', 'foster_parent', 
    'guardian', 'spouse_current', 'spouse_former', 'partner', 
    'biological_child', 'adoptive_child', 'step_child', 'foster_child',
    'sibling_full', 'sibling_half', 'sibling_step', 'sibling_adoptive',
    'other'
);

CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    person1_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    person2_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    relationship_type relationship_type NOT NULL,
    start_date DATE,
    end_date DATE,
    certainty_level INTEGER CHECK (certainty_level BETWEEN 1 AND 5),
    custom_attributes JSONB DEFAULT '{}'::jsonb,
    notes TEXT,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT different_people CHECK (person1_id != person2_id)
);

CREATE INDEX idx_relationships_tree_id ON relationships (tree_id);
CREATE INDEX idx_relationships_person1_id ON relationships (person1_id);
CREATE INDEX idx_relationships_person2_id ON relationships (person2_id);
CREATE INDEX idx_relationships_dual ON relationships USING btree (
    tree_id, 
    LEAST(person1_id, person2_id), 
    GREATEST(person1_id, person2_id)
);
CREATE INDEX idx_relationships_type ON relationships (tree_id, relationship_type);
CREATE INDEX idx_relationships_custom_attrs ON relationships USING GIN (custom_attributes);
```

### Events Table

```sql
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    person_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    date DATE,
    date_approx BOOLEAN NOT NULL DEFAULT FALSE,
    date_range_start DATE,
    date_range_end DATE,
    place VARCHAR(255),
    place_coordinates POINT,
    description TEXT,
    custom_attributes JSONB DEFAULT '{}'::jsonb,
    privacy_level VARCHAR(50) NOT NULL DEFAULT 'inherit',
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_privacy_level CHECK (privacy_level IN ('inherit', 'private', 'public', 'connections', 'researchers'))
);

CREATE INDEX idx_events_tree_id ON events (tree_id);
CREATE INDEX idx_events_person_id ON events (person_id);
CREATE INDEX idx_events_type ON events (tree_id, event_type);
CREATE INDEX idx_events_date ON events (date) WHERE date IS NOT NULL;
CREATE INDEX idx_events_date_range ON events (date_range_start, date_range_end) 
    WHERE date_range_start IS NOT NULL OR date_range_end IS NOT NULL;
CREATE INDEX idx_events_place ON events (place) WHERE place IS NOT NULL;
CREATE INDEX idx_events_custom_attrs ON events USING GIN (custom_attributes);
```

### RelationshipEvents Table

```sql
CREATE TABLE relationship_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    date DATE,
    date_approx BOOLEAN NOT NULL DEFAULT FALSE,
    date_range_start DATE,
    date_range_end DATE,
    place VARCHAR(255),
    place_coordinates POINT,
    description TEXT,
    custom_attributes JSONB DEFAULT '{}'::jsonb,
    privacy_level VARCHAR(50) NOT NULL DEFAULT 'inherit',
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_privacy_level CHECK (privacy_level IN ('inherit', 'private', 'public', 'connections', 'researchers'))
);

CREATE INDEX idx_rel_events_tree_id ON relationship_events (tree_id);
CREATE INDEX idx_rel_events_relationship_id ON relationship_events (relationship_id);
CREATE INDEX idx_rel_events_type ON relationship_events (tree_id, event_type);
CREATE INDEX idx_rel_events_date ON relationship_events (date) WHERE date IS NOT NULL;
CREATE INDEX idx_rel_events_custom_attrs ON relationship_events USING GIN (custom_attributes);
```

### Media Table

```sql
CREATE TABLE media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    file_path VARCHAR(512) NOT NULL,
    storage_bucket VARCHAR(255) NOT NULL,
    media_type VARCHAR(50) NOT NULL,
    original_filename VARCHAR(255),
    file_size INTEGER NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    title VARCHAR(255),
    description TEXT,
    date_taken DATE,
    location VARCHAR(255),
    location_coordinates POINT,
    metadata JSONB DEFAULT '{}'::jsonb,
    privacy_level VARCHAR(50) NOT NULL DEFAULT 'inherit',
    created_by UUID NOT NULL REFERENCES users(id),
    uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_media_type CHECK (media_type IN ('photo', 'document', 'audio', 'video', 'other')),
    CONSTRAINT valid_privacy_level CHECK (privacy_level IN ('inherit', 'private', 'public', 'connections', 'researchers'))
);

CREATE INDEX idx_media_tree_id ON media (tree_id);
CREATE INDEX idx_media_created_by ON media (created_by);
CREATE INDEX idx_media_media_type ON media (tree_id, media_type);
CREATE INDEX idx_media_date_taken ON media (date_taken) WHERE date_taken IS NOT NULL;
CREATE INDEX idx_media_metadata ON media USING GIN (metadata);
```

### PersonMedia Table

```sql
CREATE TABLE person_media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    person_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    media_id UUID NOT NULL REFERENCES media(id) ON DELETE CASCADE,
    is_profile BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_person_media UNIQUE (person_id, media_id)
);

CREATE INDEX idx_person_media_tree_id ON person_media (tree_id);
CREATE INDEX idx_person_media_person_id ON person_media (person_id);
CREATE INDEX idx_person_media_media_id ON person_media (media_id);
CREATE INDEX idx_person_media_profile ON person_media (person_id, is_profile) WHERE is_profile = TRUE;
```

### RelationshipMedia Table

```sql
CREATE TABLE relationship_media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,
    media_id UUID NOT NULL REFERENCES media(id) ON DELETE CASCADE,
    notes TEXT,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_relationship_media UNIQUE (relationship_id, media_id)
);

CREATE INDEX idx_relationship_media_tree_id ON relationship_media (tree_id);
CREATE INDEX idx_relationship_media_relationship_id ON relationship_media (relationship_id);
CREATE INDEX idx_relationship_media_media_id ON relationship_media (media_id);
```

### Sources Table

```sql
CREATE TABLE sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255),
    publication_date DATE,
    publisher VARCHAR(255),
    repository VARCHAR(255),
    call_number VARCHAR(100),
    url VARCHAR(512),
    archive_url VARCHAR(512),
    source_type VARCHAR(100),
    reliability_score INTEGER CHECK (reliability_score BETWEEN 1 AND 5),
    notes TEXT,
    custom_attributes JSONB DEFAULT '{}'::jsonb,
    privacy_level VARCHAR(50) NOT NULL DEFAULT 'inherit',
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_privacy_level CHECK (privacy_level IN ('inherit', 'private', 'public', 'connections', 'researchers'))
);

CREATE INDEX idx_sources_tree_id ON sources (tree_id);
CREATE INDEX idx_sources_title ON sources (tree_id, title);
CREATE INDEX idx_sources_author ON sources (tree_id, author) WHERE author IS NOT NULL;
CREATE INDEX idx_sources_source_type ON sources (tree_id, source_type) WHERE source_type IS NOT NULL;
CREATE INDEX idx_sources_custom_attrs ON sources USING GIN (custom_attributes);
```

### Citations Table

```sql
CREATE TABLE citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    citation_text TEXT NOT NULL,
    page_number VARCHAR(50),
    url_fragment VARCHAR(512),
    confidence_level INTEGER CHECK (confidence_level BETWEEN 1 AND 5),
    notes TEXT,
    custom_attributes JSONB DEFAULT '{}'::jsonb,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_citations_tree_id ON citations (tree_id);
CREATE INDEX idx_citations_source_id ON citations (source_id);
CREATE INDEX idx_citations_custom_attrs ON citations USING GIN (custom_attributes);
```

### PersonCitations Table

```sql
CREATE TABLE person_citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    person_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    citation_id UUID NOT NULL REFERENCES citations(id) ON DELETE CASCADE,
    citation_type VARCHAR(100),
    notes TEXT,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_person_citation UNIQUE (person_id, citation_id, citation_type)
);

CREATE INDEX idx_person_citations_tree_id ON person_citations (tree_id);
CREATE INDEX idx_person_citations_person_id ON person_citations (person_id);
CREATE INDEX idx_person_citations_citation_id ON person_citations (citation_id);
CREATE INDEX idx_person_citations_type ON person_citations (tree_id, citation_type) WHERE citation_type IS NOT NULL;
```

### EventCitations Table

```sql
CREATE TABLE event_citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    citation_id UUID NOT NULL REFERENCES citations(id) ON DELETE CASCADE,
    notes TEXT,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_event_citation UNIQUE (event_id, citation_id)
);

CREATE INDEX idx_event_citations_tree_id ON event_citations (tree_id);
CREATE INDEX idx_event_citations_event_id ON event_citations (event_id);
CREATE INDEX idx_event_citations_citation_id ON event_citations (citation_id);
```

### RelationshipCitations Table

```sql
CREATE TABLE relationship_citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,
    citation_id UUID NOT NULL REFERENCES citations(id) ON DELETE CASCADE,
    notes TEXT,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_relationship_citation UNIQUE (relationship_id, citation_id)
);

CREATE INDEX idx_relationship_citations_tree_id ON relationship_citations (tree_id);
CREATE INDEX idx_relationship_citations_relationship_id ON relationship_citations (relationship_id);
CREATE INDEX idx_relationship_citations_citation_id ON relationship_citations (citation_id);
```

### Notes Table

```sql
CREATE TABLE notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    title VARCHAR(255),
    content TEXT NOT NULL,
    privacy_level VARCHAR(50) NOT NULL DEFAULT 'inherit',
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_privacy_level CHECK (privacy_level IN ('inherit', 'private', 'public', 'connections', 'researchers'))
);

CREATE INDEX idx_notes_tree_id ON notes (tree_id);
CREATE INDEX idx_notes_created_by ON notes (created_by);
CREATE INDEX idx_notes_content ON notes USING GIN (to_tsvector('english', COALESCE(title, '') || ' ' || content));
```

### PersonNotes Table

```sql
CREATE TABLE person_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    person_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    note_id UUID NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_person_note UNIQUE (person_id, note_id)
);

CREATE INDEX idx_person_notes_tree_id ON person_notes (tree_id);
CREATE INDEX idx_person_notes_person_id ON person_notes (person_id);
CREATE INDEX idx_person_notes_note_id ON person_notes (note_id);
```

### ActivityLog Table

```sql
CREATE TABLE activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID REFERENCES trees(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    previous_state JSONB,
    new_state JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_activity_log_tree_id ON activity_log (tree_id);
CREATE INDEX idx_activity_log_user_id ON activity_log (user_id);
CREATE INDEX idx_activity_log_entity ON activity_log (entity_type, entity_id);
CREATE INDEX idx_activity_log_action_type ON activity_log (action_type);
CREATE INDEX idx_activity_log_created_at ON activity_log (created_at);
```

### FamilyPath Table (Ancestry Closure Table)

```sql
CREATE TABLE family_paths (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    ancestor_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    descendant_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    path_length INTEGER NOT NULL,
    path_type VARCHAR(50) NOT NULL,
    path_certainty INTEGER CHECK (path_certainty BETWEEN 1 AND 5),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_family_path UNIQUE (tree_id, ancestor_id, descendant_id, path_type),
    CONSTRAINT valid_path_type CHECK (path_type IN ('biological', 'adoptive', 'all'))
);

CREATE INDEX idx_family_paths_tree_id ON family_paths (tree_id);
CREATE INDEX idx_family_paths_ancestor_id ON family_paths (ancestor_id);
CREATE INDEX idx_family_paths_descendant_id ON family_paths (descendant_id);
CREATE INDEX idx_family_paths_length ON family_paths (tree_id, path_length);
CREATE INDEX idx_family_paths_type ON family_paths (tree_id, path_type);
```

### GEDCOMImport Table

```sql
CREATE TABLE gedcom_imports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    file_path VARCHAR(512) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    total_records INTEGER,
    processed_records INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    error_log TEXT,
    import_options JSONB DEFAULT '{}'::jsonb,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT valid_status CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

CREATE INDEX idx_gedcom_imports_tree_id ON gedcom_imports (tree_id);
CREATE INDEX idx_gedcom_imports_status ON gedcom_imports (status);
CREATE INDEX idx_gedcom_imports_created_by ON gedcom_imports (created_by);
```

### SearchIndex Table (Optimized for Fast Text Search)

```sql
CREATE TABLE search_index (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    content_tsvector TSVECTOR NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    last_indexed TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_entity_index UNIQUE (tree_id, entity_type, entity_id)
);

CREATE INDEX idx_search_index_tree_id ON search_index (tree_id);
CREATE INDEX idx_search_index_entity ON search_index (entity_type, entity_id);
CREATE INDEX idx_search_index_content ON search_index USING GIN (content_tsvector);
CREATE INDEX idx_search_index_metadata ON search_index USING GIN (metadata);
```



For complex tree traversals:

```sql
CREATE OR REPLACE FUNCTION get_ancestors(
    tree_uuid UUID,
    person_uuid UUID,
    max_depth INTEGER DEFAULT NULL,
    path_type_filter VARCHAR DEFAULT 'all'
)
RETURNS TABLE (
    person_id UUID,
    depth INTEGER,
    path_type VARCHAR,
    path_certainty INTEGER
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE ancestors AS (
        -- Base case: direct parents
        SELECT 
            fp.ancestor_id AS person_id,
            fp.path_length AS depth,
            fp.path_type,
            fp.path_certainty
        FROM 
            family_paths fp
        WHERE 
            fp.tree_id = tree_uuid
            AND fp.descendant_id = person_uuid
            AND fp.path_length = 1
            AND (path_type_filter = 'all' OR fp.path_type = path_type_filter)
        
        UNION ALL
        
        -- Recursive case: parents of parents
        SELECT 
            fp.ancestor_id,
            a.depth + fp.path_length,
            CASE
                WHEN a.path_type = fp.path_type THEN a.path_type
                ELSE 'mixed'
            END AS path_type,
            LEAST(a.path_certainty, fp.path_certainty) AS path_certainty
        FROM 
            ancestors a
        JOIN 
            family_paths fp ON fp.descendant_id = a.person_id
        WHERE 
            fp.tree_id = tree_uuid
            AND fp.path_length = 1
            AND (path_type_filter = 'all' OR fp.path_type = path_type_filter)
            AND (max_depth IS NULL OR a.depth < max_depth)
    )
    SELECT * FROM ancestors ORDER BY depth;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_descendants(
    tree_uuid UUID,
    person_uuid UUID,
    max_depth INTEGER DEFAULT NULL,
    path_type_filter VARCHAR DEFAULT 'all'
)
RETURNS TABLE (
    person_id UUID,
    depth INTEGER,
    path_type VARCHAR,
    path_certainty INTEGER
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE descendants AS (
        -- Base case: direct children
        SELECT 
            fp.descendant_id AS person_id,
            fp.path_length AS depth,
            fp.path_type,
            fp.path_certainty
        FROM 
            family_paths fp
        WHERE 
            fp.tree_id = tree_uuid
            AND fp.ancestor_id = person_uuid
            AND fp.path_length = 1
            AND (path_type_filter = 'all' OR fp.path_type = path_type_filter)
        
        UNION ALL
        
        -- Recursive case: children of children
        SELECT 
            fp.descendant_id,
            d.depth + fp.path_length,
            CASE
                WHEN d.path_type = fp.path_type THEN d.path_type
                ELSE 'mixed'
            END AS path_type,
            LEAST(d.path_certainty, fp.path_certainty) AS path_certainty
        FROM 
            descendants d
        JOIN 
            family_paths fp ON fp.ancestor_id = d.person_id
        WHERE 
            fp.tree_id = tree_uuid
            AND fp