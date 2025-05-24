import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { relationshipSchema, RelationshipFormData } from '@/lib/schemas';
import { RELATIONSHIP_TYPES, Person } from '@/lib/types';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';

import { Button } from "@/components/ui/button";
import {
  FormProvider,
  FormControl,
  FormDescription,
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
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Calendar } from "@/components/ui/calendar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { CalendarIcon, Loader2, Plus, X } from 'lucide-react';

// Helper to display human-readable relationship types
const relationshipLabels: Record<string, string> = {
  'biological_parent': 'Biological Parent',
  'adoptive_parent': 'Adoptive Parent',
  'step_parent': 'Step Parent',
  'foster_parent': 'Foster Parent',
  'guardian': 'Guardian',
  'biological_child': 'Biological Child',
  'adoptive_child': 'Adoptive Child',
  'step_child': 'Step Child',
  'foster_child': 'Foster Child',
  'spouse_current': 'Current Spouse',
  'spouse_former': 'Former Spouse',
  'partner': 'Partner',
  'sibling_full': 'Full Sibling',
  'sibling_half': 'Half Sibling',
  'sibling_step': 'Step Sibling',
  'sibling_adoptive': 'Adoptive Sibling',
  'other': 'Other Relationship'
};

// Verification status options
export type VerificationStatus = 'verified' | 'unverified' | 'disputed';

const VERIFICATION_STATUSES: VerificationStatus[] = ['verified', 'unverified', 'disputed'];

export interface RelationshipDetailsFormProps {
  onSubmit: (data: RelationshipFormData) => void;
  person1?: Person | null;
  person2?: Person | null;
  initialData?: Partial<RelationshipFormData>;
  selectablePeople: Person[];
  isLoading?: boolean;
}

export function RelationshipDetailsForm({
  onSubmit,
  person1,
  person2,
  initialData,
  selectablePeople,
  isLoading = false,
}: RelationshipDetailsFormProps) {
  const [isStartDatePickerOpen, setIsStartDatePickerOpen] = useState(false);
  const [isEndDatePickerOpen, setIsEndDatePickerOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("basic");
  const [verificationStatus, setVerificationStatus] = useState<VerificationStatus>(
    initialData?.customAttributes?.verificationStatus as VerificationStatus || 'unverified'
  );
  
  // Custom attributes state
  const [customAttributeKey, setCustomAttributeKey] = useState("");
  const [customAttributeValue, setCustomAttributeValue] = useState("");

  const form = useForm<RelationshipFormData>({
    resolver: zodResolver(relationshipSchema),
    defaultValues: {
      person1Id: person1?.id || initialData?.person1Id || '',
      person2Id: person2?.id || initialData?.person2Id || '',
      type: initialData?.type,
      startDate: initialData?.startDate,
      endDate: initialData?.endDate,
      description: initialData?.description || '',
      location: initialData?.location || '',
      customAttributes: initialData?.customAttributes || {
        verificationStatus: 'unverified'
      },
    },
  });
  
  // Set verification status when form is submitted
  const handleSubmit = (data: RelationshipFormData) => {
    const updatedData = { 
      ...data,
      customAttributes: {
        ...data.customAttributes,
        verificationStatus: verificationStatus
      }
    };
    onSubmit(updatedData);
  };

  // Get relevant person objects
  const getPerson = (id: string) => {
    if (!selectablePeople || !id) return undefined;
    return selectablePeople.find(p => p.id === id);
  };

  // Get person1 and person2 based on form values
  const selectedPerson1 = getPerson(form.watch('person1Id'));
  const selectedPerson2 = getPerson(form.watch('person2Id'));

  // Relationship type options based on context
  const getFilteredRelationshipTypes = () => {
    // You could implement logic here to filter relationship types based on gender, etc.
    return RELATIONSHIP_TYPES;
  };

  // Get custom attributes from form
  const customAttributes = form.watch("customAttributes") || {};

  return (
    <div className="space-y-6">
      <FormProvider {...form}>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="basic">Basic Info</TabsTrigger>
            <TabsTrigger value="details">Details</TabsTrigger>
            <TabsTrigger value="custom">Custom Attributes</TabsTrigger>
          </TabsList>
        
          <TabsContent value="basic" className="space-y-4 pt-4">
            <FormField
              control={form.control}
              name="person1Id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>First Person</FormLabel>
                  <Select
                    disabled={!!person1}
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a person" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {selectablePeople.map((person) => (
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
              name="person2Id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Second Person</FormLabel>
                  <Select
                    disabled={!!person2}
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a person" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {selectablePeople
                        .filter(p => p.id !== form.watch('person1Id')) // Filter out person1
                        .map((person) => (
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
                  <FormLabel>Relationship Type</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select relationship type" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {getFilteredRelationshipTypes().map((type) => (
                        <SelectItem key={type} value={type}>
                          {relationshipLabels[type]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormItem>
              <FormLabel>Verification Status</FormLabel>
              <div className="flex gap-2 mt-2">
                {VERIFICATION_STATUSES.map((status) => (
                  <Badge
                    key={status}
                    variant={verificationStatus === status ? "default" : "outline"}
                    className={cn(
                      "cursor-pointer capitalize",
                      status === 'verified' && "hover:bg-green-100",
                      status === 'unverified' && "hover:bg-yellow-100",
                      status === 'disputed' && "hover:bg-red-100",
                    )}
                    onClick={() => setVerificationStatus(status)}
                  >
                    {status}
                  </Badge>
                ))}
              </div>
              <FormDescription>
                Indicate the verification status of this relationship
              </FormDescription>
            </FormItem>
          </TabsContent>

          <TabsContent value="details" className="space-y-4 pt-4">
            <FormField
              control={form.control}
              name="startDate"
              render={({ field }) => (
                <FormItem className="flex flex-col">
                  <FormLabel>Start Date</FormLabel>
                  <Popover open={isStartDatePickerOpen} onOpenChange={setIsStartDatePickerOpen}>
                    <PopoverTrigger asChild>
                      <FormControl>
                        <Button
                          variant={"outline"}
                          className={cn(
                            "w-full pl-3 text-left font-normal",
                            !field.value && "text-muted-foreground"
                          )}
                        >
                          {field.value ? (
                            format(new Date(field.value), "PPP")
                          ) : (
                            <span>Select a date</span>
                          )}
                          <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                        </Button>
                      </FormControl>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0">
                      <Calendar
                        mode="single"
                        selected={field.value ? new Date(field.value) : undefined}
                        onSelect={(date) => {
                          field.onChange(date);
                          setIsStartDatePickerOpen(false);
                        }}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                  <FormDescription>
                    When did this relationship begin?
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="endDate"
              render={({ field }) => (
                <FormItem className="flex flex-col">
                  <FormLabel>End Date</FormLabel>
                  <Popover open={isEndDatePickerOpen} onOpenChange={setIsEndDatePickerOpen}>
                    <PopoverTrigger asChild>
                      <FormControl>
                        <Button
                          variant={"outline"}
                          className={cn(
                            "w-full pl-3 text-left font-normal",
                            !field.value && "text-muted-foreground"
                          )}
                        >
                          {field.value ? (
                            format(new Date(field.value), "PPP")
                          ) : (
                            <span>Select a date</span>
                          )}
                          <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                        </Button>
                      </FormControl>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0">
                      <Calendar
                        mode="single"
                        selected={field.value ? new Date(field.value) : undefined}
                        onSelect={(date) => {
                          field.onChange(date);
                          setIsEndDatePickerOpen(false);
                        }}
                        disabled={(date) =>
                          form.watch('startDate') && date < new Date(form.watch('startDate'))
                        }
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                  <FormDescription>
                    When did this relationship end? (if applicable)
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="location"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Location</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. New York, USA" {...field} />
                  </FormControl>
                  <FormDescription>
                    Where did this relationship take place?
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea 
                      placeholder="Add notes about this relationship" 
                      className="resize-none" 
                      {...field} 
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </TabsContent>

          <TabsContent value="custom" className="space-y-4 pt-4">
            <div className="space-y-4">
              {Object.entries(customAttributes)
                .filter(([key]) => key !== 'verificationStatus') // Skip verification status
                .map(([key, value]) => (
                <div key={key} className="flex space-x-2">
                  <Input 
                    value={key}
                    onChange={(e) => {
                      const newKey = e.target.value;
                      if (newKey && newKey !== key) {
                        const newAttributes = { ...customAttributes };
                        newAttributes[newKey] = newAttributes[key];
                        delete newAttributes[key];
                        form.setValue("customAttributes", newAttributes);
                      }
                    }}
                    className="w-1/3"
                    placeholder="Attribute name"
                  />
                  <Input 
                    value={value}
                    onChange={(e) => {
                      form.setValue("customAttributes", { 
                        ...customAttributes, 
                        [key]: e.target.value 
                      });
                    }}
                    className="w-2/3"
                    placeholder="Attribute value"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => {
                      const newAttributes = { ...customAttributes };
                      delete newAttributes[key];
                      form.setValue("customAttributes", newAttributes);
                    }}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
            
            <div className="flex space-x-2">
              <Input 
                value={customAttributeKey}
                onChange={(e) => setCustomAttributeKey(e.target.value)}
                className="w-1/3"
                placeholder="New attribute name"
              />
              <Input 
                value={customAttributeValue}
                onChange={(e) => setCustomAttributeValue(e.target.value)}
                className="w-2/3"
                placeholder="New attribute value"
              />
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={() => {
                  if (customAttributeKey && customAttributeKey !== 'verificationStatus') {
                    form.setValue("customAttributes", {
                      ...customAttributes,
                      [customAttributeKey]: customAttributeValue
                    });
                    setCustomAttributeKey("");
                    setCustomAttributeValue("");
                  }
                }}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      </FormProvider>
      
      <Button 
        type="button" 
        onClick={form.handleSubmit(handleSubmit)} 
        disabled={isLoading}
      >
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Save Relationship
      </Button>
    </div>
  );
}
