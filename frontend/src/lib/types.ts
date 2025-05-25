// Types used throughout the application

export type Person = {
  id: string;
  name: string;
  gender?: string;
  birthDate?: string;
  deathDate?: string;
  birthPlace?: string;
  deathPlace?: string;
  occupation?: string;
  biography?: string;
  customAttributes?: Record<string, any>;
  images?: string[];
};

export type RelationshipType = 
  | 'biological_parent'
  | 'adoptive_parent'
  | 'step_parent'
  | 'foster_parent'
  | 'guardian'
  | 'biological_child'
  | 'adoptive_child'
  | 'step_child'
  | 'foster_child'
  | 'spouse_current'
  | 'spouse_former'
  | 'partner'
  | 'sibling_full'
  | 'sibling_half'
  | 'sibling_step'
  | 'sibling_adoptive'
  | 'other';

export type Relationship = {
  id: string;
  person1Id: string;
  person2Id: string;
  type: RelationshipType;
  startDate?: string;
  endDate?: string;
  location?: string;
  description?: string;
  customAttributes?: Record<string, any>;
};

export type Tree = {
  id: string;
  name: string;
  description?: string;
  created: string;
  lastModified: string;
  personCount: number;
  rootPersonId?: string;
};

export type User = {
  id: string;
  username: string;
  email: string;
  fullName?: string;
  role: 'user' | 'admin';
  created: string;
  lastLogin?: string;
};

export type Event = {
  id: string;
  title: string;
  date: string;
  location?: string;
  description?: string;
  personIds: string[];
  mediaIds?: string[];
  customAttributes?: Record<string, any>;
};

export type Media = {
  id: string;
  filename: string;
  filePath: string;
  fileType: string;
  fileSize: number;
  uploaded: string;
  description?: string;
  personIds: string[];
  eventIds?: string[];
};
