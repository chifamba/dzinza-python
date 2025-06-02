export interface Person {
  id: string;
  firstName: string;
  middleNames?: string;
  lastName: string;
  maidenName?: string;
  nickname?: string;
  gender?: string;
  birthDate?: string;
  birthDateApprox?: boolean;
  birthPlace?: string;
  placeOfBirth?: string;
  deathDate?: string;
  deathDateApprox?: boolean;
  deathPlace?: string;
  placeOfDeath?: string;
  burialPlace?: string;
  privacyLevel?: PrivacyLevel;
  isLiving?: boolean;
  notes?: string;
  biography?: string;
  customAttributes?: Record<string, any>;
  profilePictureUrl?: string;
  customFields?: Record<string, any>;
  createdBy?: string;
  createdAt?: string;
  updatedAt?: string;
  displayOrder?: number;

  // Legacy fields for compatibility with existing code
  name?: string;
  color?: 'blue' | 'green' | 'orange' | 'pink';
  photo?: string;
  parentId?: string;
  spouseId?: string;
  hasImage?: boolean;
  isPlaceholder?: boolean;
  category?: 'olderMale' | 'olderFemale' | 'adultMale' | 'adultFemale' | 'boy' | 'girl';
}

export enum PrivacyLevel {
  INHERIT = "inherit",
  PRIVATE = "private",
  PUBLIC = "public",
  CONNECTIONS = "connections",
  RESEARCHERS = "researchers"
}

export interface Relationship {
  id: string;
  person1Id: string;
  person2Id: string;
  relationshipType: RelationshipType;
  startDate?: string;
  endDate?: string;
  location?: string;
  certaintyLevel?: number;
  customAttributes?: Record<string, any>;
  notes?: string;
  createdBy?: string;
  createdAt?: string;
  updatedAt?: string;
}

export enum RelationshipType {
  BIOLOGICAL_PARENT = "biological_parent",
  ADOPTIVE_PARENT = "adoptive_parent",
  STEP_PARENT = "step_parent",
  FOSTER_PARENT = "foster_parent",
  GUARDIAN = "guardian",
  SPOUSE_CURRENT = "spouse_current",
  SPOUSE_FORMER = "spouse_former",
  PARTNER = "partner",
  BIOLOGICAL_CHILD = "biological_child",
  ADOPTIVE_CHILD = "adoptive_child",
  STEP_CHILD = "step_child",
  FOSTER_CHILD = "foster_child",
  SIBLING_FULL = "sibling_full",
  SIBLING_HALF = "sibling_half",
  SIBLING_STEP = "sibling_step",
  SIBLING_ADOPTIVE = "sibling_adoptive",
  OTHER = "other"
}

export interface FamilyTreeState {
  persons: Person[];
  selectedPersonId: string | null;
}

export interface AppConfig {
  backendUrl: string;
}