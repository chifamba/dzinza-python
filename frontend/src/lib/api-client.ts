import { Person, RelativePerson, Relationship } from './types';
import axios from 'axios';

export interface TreeMetadata {
  id: string;
  name: string;
  description?: string;
  coverImageUrl?: string;
  privacySettings: {
    visibility: 'public' | 'private' | 'shared';
    sharedWith?: string[];
  };
  createdAt: string;
  updatedAt: string;
  ownerId: string;
}

export interface GetPeopleParams {
  page?: number;
  limit?: number;
  search?: string;
  sort?: 'name' | 'birthDate' | 'deathDate';
  order?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

class ApiClient {
  // Tree Management
  async createTree(data: { name: string; description?: string }): Promise<TreeMetadata> {
    const response = await axios.post<TreeMetadata>('/trees', data);
    return response.data;
  }

  async getTree(treeId: string): Promise<TreeMetadata> {
    const response = await axios.get<TreeMetadata>(`/trees/${treeId}`);
    return response.data;
  }

  async updateTree(treeId: string, data: Partial<TreeMetadata>): Promise<TreeMetadata> {
    const response = await axios.patch<TreeMetadata>(`/trees/${treeId}`, data);
    return response.data;
  }

  async listTrees(): Promise<TreeMetadata[]> {
    const response = await axios.get<TreeMetadata[]>('/trees');
    return response.data;
  }

  // Person Management
  async getPeople(treeId: string, params?: GetPeopleParams): Promise<PaginatedResponse<Person>> {
    const response = await axios.get<PaginatedResponse<Person>>(`/trees/${treeId}/people`, { params });
    return response.data;
  }

  async getPerson(treeId: string, personId: string): Promise<Person> {
    const response = await axios.get<Person>(`/trees/${treeId}/people/${personId}`);
    return response.data;
  }

  async createPerson(treeId: string, data: Omit<Person, 'id'>): Promise<Person> {
    const response = await axios.post<Person>(`/trees/${treeId}/people`, data);
    return response.data;
  }

  async updatePerson(treeId: string, personId: string, data: Partial<Person>): Promise<Person> {
    const response = await axios.patch<Person>(`/trees/${treeId}/people/${personId}`, data);
    return response.data;
  }

  async deletePerson(treeId: string, personId: string): Promise<void> {
    await axios.delete(`/trees/${treeId}/people/${personId}`);
  }

  // Relationship Management
  async getRelationships(treeId: string): Promise<Relationship[]> {
    const response = await axios.get<Relationship[]>(`/trees/${treeId}/relationships`);
    return response.data;
  }

  async createRelationship(treeId: string, data: Omit<Relationship, 'id'>): Promise<Relationship> {
    const response = await axios.post<Relationship>(`/trees/${treeId}/relationships`, data);
    return response.data;
  }

  async updateRelationship(
    treeId: string, 
    relationshipId: string, 
    data: Partial<Relationship>
  ): Promise<Relationship> {
    const response = await axios.patch<Relationship>(
      `/trees/${treeId}/relationships/${relationshipId}`,
      data
    );
    return response.data;
  }

  async deleteRelationship(treeId: string, relationshipId: string): Promise<void> {
    await axios.delete(`/trees/${treeId}/relationships/${relationshipId}`);
  }

  // Family Analysis
  async getRelatives(treeId: string, personId: string): Promise<{
    parents: RelativePerson[];
    children: RelativePerson[];
    spouses: RelativePerson[];
    siblings: RelativePerson[];
  }> {
    const response = await axios.get<{
      parents: RelativePerson[];
      children: RelativePerson[];
      spouses: RelativePerson[];
      siblings: RelativePerson[];
    }>(`/trees/${treeId}/people/${personId}/relatives`);
    return response.data;
  }

  async suggestRelationships(treeId: string, personId: string): Promise<{
    possibleRelatives: Array<{
      person: RelativePerson;
      confidence: number;
      suggestedRelationType: string;
      reason: string;
    }>;
  }> {
    const response = await axios.get(
      `/trees/${treeId}/people/${personId}/suggest-relationships`
    );
    return response.data;
  }

  // Tree Analysis
  async getTreeStatistics(treeId: string): Promise<{
    totalPeople: number;
    totalRelationships: number;
    avgLifespan: number;
    birthDateCoverage: number;
    deathDateCoverage: number;
    genderDistribution: Record<string, number>;
    relationshipTypeDistribution: Record<string, number>;
    timelineCoverage: Array<{
      decade: string;
      birthCount: number;
      deathCount: number;
    }>;
  }> {
    const response = await axios.get(`/trees/${treeId}/statistics`);
    return response.data;
  }
}

export const apiClient = new ApiClient();
export default apiClient;
