"use client";

import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { relationshipSchema, RelationshipFormData, RELATIONSHIP_TYPES } from '@/lib/schemas';
import { Person } from '@/lib/types';

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2 } from 'lucide-react';

export interface AddRelationshipModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: RelationshipFormData) => void;
  currentPerson: Person;
  selectablePeople: Person[];
  isLoading?: boolean;
}

const AddRelationshipModal: React.FC<AddRelationshipModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  currentPerson,
  selectablePeople,
  isLoading = false,
}) => {
  const form = useForm<RelationshipFormData>({
    resolver: zodResolver(relationshipSchema),
    defaultValues: {
      person1Id: currentPerson.id,
      person2Id: '', // Initialize as empty
      type: undefined, // Initialize as empty
    },
  });

  // Reset form when currentPerson changes or modal opens/closes
  useEffect(() => {
    form.reset({
      person1Id: currentPerson.id,
      person2Id: '',
      type: undefined,
    });
  }, [isOpen, currentPerson, form]);

  const filteredSelectablePeople = selectablePeople.filter(
    (person) => person.id !== currentPerson.id
  );

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent 
        className="sm:max-w-[425px]"
        onInteractOutside={(e) => {
          if (isLoading) {
            e.preventDefault();
          }
        }}
      >
        <DialogHeader>
          <DialogTitle>Add Relative for {currentPerson.name}</DialogTitle>
          <DialogDescription>
            Define a new relationship with another person in the tree.
          </DialogDescription>
        </DialogHeader>

        <Form {...form} onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <FormField
              control={form.control}
              name="person2Id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel id="person2Id-label">Select Person</FormLabel> {/* Added id here */}
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      {/* Added aria-labelledby to associate label */}
                      <SelectTrigger aria-labelledby="person2Id-label">
                        <SelectValue placeholder="Choose a person" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {filteredSelectablePeople.map((person) => (
                        <SelectItem key={person.id} value={person.id}>
                          {person.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel id="relationshipType-label">Relationship Type</FormLabel> {/* Added id here */}
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      {/* Added aria-labelledby to associate label */}
                      <SelectTrigger aria-labelledby="relationshipType-label">
                        <SelectValue placeholder="Choose relationship type" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {RELATIONSHIP_TYPES.map((type) => (
                        <SelectItem key={type} value={type}>
                          {type}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button variant="outline" onClick={onClose} type="button" disabled={isLoading}>
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  'Add Relationship' // Corrected button text to 'Add Relationship'
                )}
              </Button>
            </DialogFooter>
        </Form>
      </DialogContent>
    </Dialog>
  );
};

export default AddRelationshipModal;
