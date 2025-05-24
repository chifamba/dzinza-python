"use client";

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { personSchema, PersonFormData } from '@/lib/schemas';
import { GENDERS } from '@/lib/types'; // Assuming GENDERS is exported from types.ts as well
import { cn } from '@/lib/utils';

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
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
import { Textarea } from "@/components/ui/textarea";
import { Calendar } from "@/components/ui/calendar";
import { CalendarIcon, Loader2, Plus, X } from 'lucide-react';
import { format } from 'date-fns'; // For formatting date in PopoverTrigger

export interface PersonFormProps {
  onSubmit: (data: PersonFormData) => void;
  initialData?: Partial<PersonFormData>;
  isLoading?: boolean;
  submitButtonText?: string;
}

const PersonForm: React.FC<PersonFormProps> = ({
  onSubmit,
  initialData,
  isLoading = false,
  submitButtonText = "Save Person",
}) => {
  const form = useForm<PersonFormData>({
    resolver: zodResolver(personSchema),
    defaultValues: {
      name: "",
      gender: undefined,
      imageUrl: "",
      birthDate: undefined,
      deathDate: undefined,
      bio: "",
      birthPlace: "",
      isLiving: true,
      customAttributes: {},
      ...initialData,
    },
  });

  const [isBirthDatePickerOpen, setIsBirthDatePickerOpen] = useState(false);
  const [isDeathDatePickerOpen, setIsDeathDatePickerOpen] = useState(false);
  
  // Custom attributes state
  const [customAttributeKey, setCustomAttributeKey] = useState("");
  const [customAttributeValue, setCustomAttributeValue] = useState("");
  
  // Get custom attributes from form
  const customAttributes = form.watch("customAttributes") || {};

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Full Name</FormLabel>
              <FormControl>
                <Input placeholder="Enter full name" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="gender"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Gender</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select gender" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {GENDERS.map((gender) => (
                    <SelectItem key={gender} value={gender}>
                      {gender}
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
          name="imageUrl"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Image URL</FormLabel>
              <FormControl>
                <Input placeholder="https://example.com/image.png" {...field} />
              </FormControl>
              <FormDescription>
                URL of the person's profile picture.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="birthDate"
          render={({ field }) => (
            <FormItem className="flex flex-col">
              <FormLabel>Birth Date</FormLabel>
              <Popover open={isBirthDatePickerOpen} onOpenChange={setIsBirthDatePickerOpen}>
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
                        <span>Pick a date</span>
                      )}
                      <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                    </Button>
                  </FormControl>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={field.value ? new Date(field.value) : undefined}
                    onSelect={(date) => {
                      field.onChange(date);
                      setIsBirthDatePickerOpen(false);
                    }}
                    disabled={(date) =>
                      date > new Date() || date < new Date("1000-01-01")
                    }
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="deathDate"
          render={({ field }) => (
            <FormItem className="flex flex-col">
              <FormLabel>Death Date</FormLabel>
              <Popover open={isDeathDatePickerOpen} onOpenChange={setIsDeathDatePickerOpen}>
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
                        <span>Pick a date</span>
                      )}
                      <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                    </Button>
                  </FormControl>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={field.value ? new Date(field.value) : undefined}
                    onSelect={(date) => {
                      field.onChange(date);
                      setIsDeathDatePickerOpen(false);
                    }}
                    disabled={(date) =>
                      (form.getValues("birthDate") && date < new Date(form.getValues("birthDate")!)) ||
                      date > new Date()
                    }
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="bio"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Biography</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Tell us a bit about this person..."
                  className="resize-none"
                  {...field}
                />
              </FormControl>
              <FormDescription>
                A short biography or notes.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Custom Attributes Section */}
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium">Custom Attributes</h3>
          </div>
          
          <div className="space-y-4">
            {Object.entries(form.getValues("customAttributes") || {}).map(([key, value]) => (
              <div key={key} className="flex space-x-2">
                <Input 
                  value={key}
                  onChange={(e) => {
                    const newKey = e.target.value;
                    if (newKey && newKey !== key) {
                      const customAttributes = form.getValues("customAttributes") || {};
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
                    const customAttributes = form.getValues("customAttributes") || {};
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
                    const customAttributes = form.getValues("customAttributes") || {};
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
                if (customAttributeKey) {
                  const customAttributes = form.getValues("customAttributes") || {};
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
        </div>

        <Button type="submit" disabled={isLoading}>
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {submitButtonText}
        </Button>
      </form>
    </Form>
  );
};

export default PersonForm;
