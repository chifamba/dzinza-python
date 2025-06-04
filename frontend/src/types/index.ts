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
  
  // Position in the family tree view
  position?: {
    x: number;
    y: number;
  };

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

export interface Connection {
  id: string;
  sourceId: string;
  targetId: string;
  type: ConnectionType;
  label?: string;
}

export enum ConnectionType {
  PARENT_CHILD = "parent_child",
  SPOUSE = "spouse",
  SIBLING = "sibling",
  CUSTOM = "custom"
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
  // Spouse/Partner relationships
  SPOUSE_CURRENT = "spouse_current",
  SPOUSE_FORMER = "spouse_former",
  PARTNER = "partner",
  
  // Parent/Child relationships
  BIOLOGICAL_PARENT = "biological_parent",
  ADOPTIVE_PARENT = "adoptive_parent",
  STEP_PARENT = "step_parent",
  FOSTER_PARENT = "foster_parent",
  GUARDIAN = "guardian",
  BIOLOGICAL_CHILD = "biological_child",
  ADOPTIVE_CHILD = "adoptive_child",
  STEP_CHILD = "step_child",
  FOSTER_CHILD = "foster_child",
  
  // Sibling relationships
  SIBLING_FULL = "sibling_full",
  SIBLING_HALF = "sibling_half",
  SIBLING_STEP = "sibling_step",
  SIBLING_ADOPTIVE = "sibling_adoptive",
  
  // Extended family
  GRANDPARENT = "grandparent",
  GRANDCHILD = "grandchild",
  AUNT_UNCLE = "aunt_uncle",
  NIECE_NEPHEW = "niece_nephew",
  COUSIN = "cousin",
  
  // In-law relationships
  PARENT_IN_LAW = "parent_in_law",
  CHILD_IN_LAW = "child_in_law",
  SIBLING_IN_LAW = "sibling_in_law",
  
  // Other
  GODPARENT = "godparent",
  GODCHILD = "godchild",
  CUSTOM = "custom"
}

export interface FamilyTreeState {
  persons: Person[];
  connections: Connection[];
}
