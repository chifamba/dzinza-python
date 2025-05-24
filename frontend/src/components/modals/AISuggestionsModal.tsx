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
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { AISuggestedRelationshipSchema } from '@/ai/flows/suggest-relationships'; // Assuming this is the correct path and type
import { Loader2, UserPlus } from 'lucide-react'; // Added UserPlus for "Add" button

export interface AISuggestionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  suggestions: AISuggestedRelationshipSchema[];
  targetPersonName: string;
  isLoading: boolean;
  onAddSuggestion: (suggestion: AISuggestedRelationshipSchema) => void;
}

const AISuggestionsModal: React.FC<AISuggestionsModalProps> = ({
  isOpen,
  onClose,
  suggestions,
  targetPersonName,
  isLoading,
  onAddSuggestion,
}) => {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>AI Suggestions for {targetPersonName}</DialogTitle>
          <DialogDescription>
            Review the AI-generated relationship suggestions below. These are not yet added to the family tree.
          </DialogDescription>
        </DialogHeader>
        <ScrollArea className="max-h-[60vh] p-1 pr-4"> {/* Added p-1 pr-4 for scrollbar padding */}
          {isLoading ? (
            <div className="flex justify-center items-center h-40">
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
            </div>
          ) : suggestions.length === 0 ? (
            <div className="text-center text-muted-foreground py-10">
              No suggestions available at this time.
            </div>
          ) : (
            <div className="space-y-4">
              {suggestions.map((suggestion, index) => (
                <div key={index} className="p-4 border rounded-lg shadow-sm bg-card">
                  <p className="text-sm font-semibold text-primary">
                    Suggests: <span className="font-bold text-foreground">{suggestion.person2Name}</span>
                    {suggestion.person2Gender && ` (${suggestion.person2Gender})`}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    as <span className="font-medium text-foreground">{targetPersonName}</span>'s 
                    <Badge variant="secondary" className="ml-1">{suggestion.relationshipType}</Badge>
                  </p>
                  {suggestion.reasoning && (
                    <p className="mt-2 text-xs text-muted-foreground italic">
                      Reasoning: {suggestion.reasoning}
                    </p>
                  )}
                  <Button
                    size="sm"
                    variant="outline"
                    className="mt-3"
                    onClick={() => onAddSuggestion(suggestion)}
                  >
                    <UserPlus size={16} className="mr-2" />
                    Add this person/relationship
                  </Button>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default AISuggestionsModal;
