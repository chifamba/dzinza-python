"use client";

import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import PersonForm from "@/components/PersonForm";
import { PersonFormData } from "@/lib/schemas";

export interface AddEditPersonModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: PersonFormData) => void;
  initialData?: Partial<PersonFormData>;
  isLoading?: boolean;
  mode: 'add' | 'edit';
}

const AddEditPersonModal: React.FC<AddEditPersonModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  isLoading = false,
  mode,
}) => {
  const title = mode === 'add' ? 'Add New Person' : 'Edit Person';
  const description = mode === 'add' 
    ? "Enter the details of the new family member." 
    : "Update the details of this person.";
  const submitButtonText = mode === 'add' ? 'Add Person' : 'Save Changes';

  // This handler ensures that the form submission also triggers modal closure if successful
  // However, the actual success/failure logic and when to close would typically be handled
  // by the parent component calling this modal, by setting `isOpen` to false based on
  // the `onSubmit` promise resolution.
  // For now, we'll assume `onSubmit` from props handles everything including state for `isLoading`.
  const handleFormSubmit = (data: PersonFormData) => {
    onSubmit(data);
    // Note: `onClose()` might be called prematurely here if `onSubmit` is async and fails.
    // It's often better to let the parent component manage closing the modal after successful submission.
    // For this implementation, we'll stick to the subtask and just call onSubmit.
  };


  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent 
        className="sm:max-w-[425px]"
        onInteractOutside={(e) => {
          // Prevent closing on overlay click if form is loading/submitting
          if (isLoading) {
            e.preventDefault();
          }
        }}
      >
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        
        <PersonForm
          onSubmit={handleFormSubmit} // The form inside PersonForm will call this
          initialData={initialData}
          isLoading={isLoading}
          submitButtonText={submitButtonText}
        />
        
        {/* 
          The primary action button is within PersonForm.
          DialogFooter is used here only if we need an explicit "Cancel" button,
          which is good practice.
        */}
        <DialogFooter className="sm:justify-start"> 
          {/* Added sm:justify-start to align cancel button left on larger screens if form button is also in footer */}
          {/* However, PersonForm's button is not in the footer. This footer is separate. */}
          {/* If PersonForm's button was meant to be here, we'd need to lift its onClick. */}
          {/* For now, a simple explicit cancel button. */}
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default AddEditPersonModal;
