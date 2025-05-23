import { z } from 'zod';

// Gender enum values - will also be added to types.ts
export const GENDERS = ["Male", "Female", "Other", "Unknown"] as const;

export const personSchema = z.object({
  name: z.string().min(1, { message: "Name is required." }),
  gender: z.enum(GENDERS).optional(),
  imageUrl: z.string().url({ message: "Invalid URL." }).optional().or(z.literal('')), // Allow empty string
  birthDate: z.date().optional(),
  deathDate: z.date().optional(),
  bio: z.string().optional(),
}).refine(data => {
  if (data.birthDate && data.deathDate) {
    return data.deathDate > data.birthDate;
  }
  return true;
}, {
  message: "Death date must be after birth date.",
  path: ["deathDate"],
});

export type PersonFormData = z.infer<typeof personSchema>;

// Relationship Schema
export const RELATIONSHIP_TYPES = ['Parent', 'Child', 'Spouse'] as const;

export const relationshipSchema = z.object({
  person1Id: z.string().min(1, { message: "Source person ID is required." }),
  person2Id: z.string().min(1, { message: "Target person ID is required." }),
  type: z.enum(RELATIONSHIP_TYPES, {
    required_error: "Relationship type is required.",
  }),
});

export type RelationshipFormData = z.infer<typeof relationshipSchema>;
