// In frontend/src/lib/types.ts

// Gender enum values - matches GENDERS in schemas.ts
export const GENDERS = ["Male", "Female", "Other", "Unknown"] as const;
export type Gender = typeof GENDERS[number];

export interface RelativePerson {
  id: string;
  name: string;
}

export interface Person {
  id: string;
  name: string;
  gender?: Gender;
  imageUrl?: string;
  birthDate?: string; // Keep as string for display/storage, form will handle Date objects
  deathDate?: string; // Keep as string for display/storage, form will handle Date objects
  bio?: string;
  birthPlace?: string;
  isLiving?: boolean;
  parents?: RelativePerson[];
  spouses?: RelativePerson[];
  children?: RelativePerson[];
  customAttributes?: Record<string, string>;
}

// Relationship Types - matches RELATIONSHIP_TYPES in schemas.ts
export const RELATIONSHIP_TYPES = [
  'biological_parent',
  'adoptive_parent',
  'step_parent',
  'foster_parent',
  'guardian',
  'biological_child',
  'adoptive_child',
  'step_child',
  'foster_child',
  'spouse_current',
  'spouse_former',
  'partner',
  'sibling_full',
  'sibling_half',
  'sibling_step',
  'sibling_adoptive',
  'other'
] as const;

export type RelationshipType = typeof RELATIONSHIP_TYPES[number];

export interface Relationship {
  id: string;
  person1Id: string;
  person2Id: string;
  type: RelationshipType;
  startDate?: string;
  endDate?: string;
  description?: string;
  location?: string;
  customAttributes?: Record<string, string>;
}

export type ActivityType = 
  | 'person_create' 
  | 'person_update' 
  | 'person_delete'
  | 'relationship_create'
  | 'relationship_update'
  | 'relationship_delete'
  | 'tree_create'
  | 'tree_update'
  | 'tree_delete'
  | 'tree_share'
  | 'tree_settings';

export interface ActivityEvent {
  type: ActivityType;
  entityId: string;
  details: Record<string, any>;
  timestamp: string;
}
