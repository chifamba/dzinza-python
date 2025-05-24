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
  birthPlace: z.string().optional(),
  isLiving: z.boolean().optional(),
  customAttributes: z.record(z.string(), z.string()).optional(),
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

// Expanded relationship types to support more detailed relationships
export const RELATIONSHIP_TYPES = [
  // Parent-child relationships
  'biological_parent',
  'adoptive_parent',
  'step_parent',
  'foster_parent',
  'guardian',
  'biological_child',
  'adoptive_child',
  'step_child',
  'foster_child',
  // Spouse relationships
  'spouse_current',
  'spouse_former',
  'partner',
  // Sibling relationships
  'sibling_full',
  'sibling_half',
  'sibling_step',
  'sibling_adoptive',
  // Other
  'other'
] as const;

export const relationshipSchema = z.object({
  person1Id: z.string().min(1, { message: "First person is required." }),
  person2Id: z.string().min(1, { message: "Second person is required." }),
  type: z.enum(RELATIONSHIP_TYPES, {
    required_error: "Relationship type is required.",
  }),
  startDate: z.date().optional(),
  endDate: z.date().optional(),
  description: z.string().optional(),
  location: z.string().optional(),
  customAttributes: z.record(z.string(), z.string()).optional(),
}).refine(data => {
  if (data.startDate && data.endDate) {
    return data.endDate > data.startDate;
  }
  return true;
}, {
  message: "End date must be after start date.",
  path: ["endDate"],
});

export type RelationshipFormData = z.infer<typeof relationshipSchema>;
