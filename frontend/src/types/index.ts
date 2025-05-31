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
  isLiving?: boolean;
  notes?: string;
  biography?: string;
  customAttributes?: Record<string, any>;
  profilePictureUrl?: string;
  customFields?: Record<string, any>;

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

export interface Relationship {
  id: string;
  person1Id: string;
  person2Id: string;
  relationshipType: string;
  startDate?: string;
  endDate?: string;
  location?: string;
  certaintyLevel?: number;
  customAttributes?: Record<string, any>;
  notes?: string;
}

export interface FamilyTreeState {
  persons: Person[];
  selectedPersonId: string | null;
}

export interface AppConfig {
  backendUrl: string;
}