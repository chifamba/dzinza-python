// In frontend/src/lib/types.ts

// Gender enum values - matches GENDERS in schemas.ts
export const GENDERS = ["Male", "Female", "Other", "Unknown"] as const;
export type Gender = typeof GENDERS[number];

export interface Person {
  id: string;
  name: string;
  gender?: Gender;
  imageUrl?: string;
  birthDate?: string; // Keep as string for display/storage, form will handle Date objects
  deathDate?: string; // Keep as string for display/storage, form will handle Date objects
  bio?: string;
  // Add other fields as needed later
}

// Relationship Types - matches RELATIONSHIP_TYPES in schemas.ts
export const RELATIONSHIP_TYPES = ['Parent', 'Child', 'Spouse'] as const;
export type RelationshipType = typeof RELATIONSHIP_TYPES[number];

export interface Relationship {
  id: string; // Unique ID for the relationship itself
  person1Id: string; // ID of the first person
  person2Id: string; // ID of the second person
  type: RelationshipType; // Type of relationship (e.g., Parent, Child, Spouse)
}
