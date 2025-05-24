import React from 'react';
import { ActivityType } from '@/lib/types';
import { Check, ChevronsUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Command, CommandGroup, CommandItem } from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import { Input } from "@/components/ui/input";

interface ActivityFiltersProps {
  selectedTypes: ActivityType[];
  startDate: Date | null;
  endDate: Date | null;
  searchTerm: string;
  onTypeChange: (types: ActivityType[]) => void;
  onStartDateChange: (date: Date | null) => void;
  onEndDateChange: (date: Date | null) => void;
  onSearchChange: (term: string) => void;
}

const activityTypeLabels: Record<ActivityType, string> = {
  'person_create': 'Person Added',
  'person_update': 'Person Updated',
  'person_delete': 'Person Deleted',
  'relationship_create': 'Relationship Added',
  'relationship_update': 'Relationship Updated',
  'relationship_delete': 'Relationship Deleted',
  'tree_create': 'Tree Created',
  'tree_update': 'Tree Updated',
  'tree_delete': 'Tree Deleted',
  'tree_share': 'Tree Shared',
  'tree_settings': 'Tree Settings Changed',
};

export function ActivityFilters({
  selectedTypes,
  startDate,
  endDate,
  searchTerm,
  onTypeChange,
  onStartDateChange,
  onEndDateChange,
  onSearchChange,
}: ActivityFiltersProps) {
  const [typesPopoverOpen, setTypesPopoverOpen] = React.useState(false);
  const [startDatePopoverOpen, setStartDatePopoverOpen] = React.useState(false);
  const [endDatePopoverOpen, setEndDatePopoverOpen] = React.useState(false);

  const toggleType = (type: ActivityType) => {
    const newTypes = selectedTypes.includes(type)
      ? selectedTypes.filter(t => t !== type)
      : [...selectedTypes, type];
    onTypeChange(newTypes);
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Popover open={typesPopoverOpen} onOpenChange={setTypesPopoverOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              role="combobox"
              aria-expanded={typesPopoverOpen}
              className="justify-between"
            >
              {selectedTypes.length === 0
                ? "Select types"
                : `${selectedTypes.length} type${selectedTypes.length === 1 ? '' : 's'} selected`}
              <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="p-0">
            <Command>
              <CommandGroup>
                {Object.entries(activityTypeLabels).map(([type, label]) => (
                  <CommandItem
                    key={type}
                    onSelect={() => toggleType(type as ActivityType)}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        selectedTypes.includes(type as ActivityType) ? "opacity-100" : "opacity-0"
                      )}
                    />
                    {label}
                  </CommandItem>
                ))}
              </CommandGroup>
            </Command>
          </PopoverContent>
        </Popover>

        <Popover open={startDatePopoverOpen} onOpenChange={setStartDatePopoverOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              className={cn(
                "justify-start text-left font-normal",
                !startDate && "text-muted-foreground"
              )}
            >
              {startDate ? format(startDate, "PPP") : "Start date"}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="single"
              selected={startDate || undefined}
              onSelect={(date) => {
                onStartDateChange(date);
                setStartDatePopoverOpen(false);
              }}
              initialFocus
            />
          </PopoverContent>
        </Popover>

        <Popover open={endDatePopoverOpen} onOpenChange={setEndDatePopoverOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              className={cn(
                "justify-start text-left font-normal",
                !endDate && "text-muted-foreground"
              )}
            >
              {endDate ? format(endDate, "PPP") : "End date"}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="single"
              selected={endDate || undefined}
              onSelect={(date) => {
                onEndDateChange(date);
                setEndDatePopoverOpen(false);
              }}
              initialFocus
            />
          </PopoverContent>
        </Popover>
      </div>

      <Input
        placeholder="Search by name..."
        value={searchTerm}
        onChange={(e) => onSearchChange(e.target.value)}
        className="w-full"
      />
    </div>
  );
