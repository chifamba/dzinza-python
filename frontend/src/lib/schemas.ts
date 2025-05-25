// Form validation schemas and types

import { z } from "zod";
import { RelationshipType } from "./types";

// Relationship types constants
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

// Person schema
export const personSchema = z.object({
  name: z.string().min(1, "Name is required"),
  gender: z.string().optional(),
  birthDate: z.string().optional(),
  deathDate: z.string().optional(),
  birthPlace: z.string().optional(),
  deathPlace: z.string().optional(),
  occupation: z.string().optional(),
  biography: z.string().optional(),
  customAttributes: z.record(z.string(), z.any()).optional(),
});

export type PersonFormData = z.infer<typeof personSchema>;

// Relationship schema
export const relationshipSchema = z.object({
  person1Id: z.string().min(1, "First person is required"),
  person2Id: z.string().min(1, "Second person is required"),
  type: z.string().min(1, "Relationship type is required"),
  startDate: z.string().optional(),
  endDate: z.string().optional(),
  location: z.string().optional(),
  description: z.string().optional(),
  customAttributes: z.record(z.string(), z.any()).optional(),
});

export type RelationshipFormData = z.infer<typeof relationshipSchema>;

// Event schema
export const eventSchema = z.object({
  title: z.string().min(1, "Title is required"),
  date: z.string().min(1, "Date is required"),
  location: z.string().optional(),
  description: z.string().optional(),
  personIds: z.array(z.string()).min(1, "At least one person must be associated"),
  customAttributes: z.record(z.string(), z.any()).optional(),
});

export type EventFormData = z.infer<typeof eventSchema>;

// Media schema
export const mediaSchema = z.object({
  description: z.string().optional(),
  personIds: z.array(z.string()).min(1, "At least one person must be associated"),
  file: z.any(),
});

export type MediaFormData = z.infer<typeof mediaSchema>;
