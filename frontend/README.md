
# Dzinza - Interactive Family Tree Builder

Dzinza is a web application designed to help users create, visualize, and manage their family trees in an interactive and engaging way. It leverages modern web technologies to provide a dynamic user experience, including drag-and-drop functionality for arranging family members and AI-powered suggestions for potential relationships.

## Core Features

*   **Add, Edit, and Delete Individuals**: Easily manage the members of your family tree.
*   **Define Relationships**: Establish parent-child and spousal relationships.
*   **Interactive Visualization**:
    *   View family members as cards on a canvas.
    *   **Drag-and-Drop**: Rearrange individuals on the canvas to customize the layout.
    *   **Dynamic Connectors**: SVG lines dynamically connect related individuals, updating as cards are moved.
    *   **Generational Layout**: Initial card placement is organized by generation, with older generations at the top.
*   **AI-Powered Relationship Suggestions**: Utilizes Genkit and Google's Gemini models to suggest potential siblings, spouses, or children based on existing family data.
*   **Modal-Based Forms**: Clean and intuitive forms for adding/editing people and relationships.
*   **Responsive Design**: Built with modern UI components for a good experience across devices (though primarily designed for desktop interaction for the tree visualization).
*   **Toast Notifications**: Provides feedback for user actions.

## Technology Stack

*   **Frontend Framework**: Next.js (App Router)
*   **UI Library**: React with TypeScript
*   **Styling**: Tailwind CSS
*   **UI Components**: ShadCN UI
*   **Generative AI**: Genkit with Google Gemini
*   **Icons**: Lucide React

## Project Structure

A brief overview of the key directories:

*   `src/app/`: Contains Next.js pages, server actions (`actions.ts`), and global styles/layout.
    *   `page.tsx`: The main entry point and primary component for the family tree interface.
    *   `actions.ts`: Server-side functions for data manipulation (CRUD operations on people, relationships) and interfacing with AI flows.
    *   `globals.css`: Global styles and Tailwind CSS theme configuration (HSL variables for colors).
    *   `layout.tsx`: Root layout for the application.
*   `src/components/`: Reusable React components.
    *   `AppHeader.tsx`: The main application header.
    *   `FamilyDisplay.tsx`: Responsible for rendering the canvas, `PersonCard`s, and the SVG connecting lines.
    *   `PersonCard.tsx`: Displays information for a single individual and handles its drag-and-drop behavior.
    *   `modals/`: Contains modal dialog components for adding/editing people (`AddEditPersonModal.tsx`), adding relationships (`AddRelationshipModal.tsx`), and displaying AI suggestions (`AISuggestionsModal.tsx`).
    *   `ui/`: ShadCN UI components (button, card, dialog, input, etc.).
*   `src/lib/`: Core logic, type definitions, and utility functions.
    *   `types.ts`: TypeScript type definitions for `Person`, `Gender`, etc.
    *   `utils.ts`: Utility functions (e.g., `cn` for class names).
*   `src/ai/`: Genkit related files.
    *   `genkit.ts`: Genkit configuration and initialization.
    *   `flows/suggest-relationships.ts`: The Genkit flow definition for suggesting relationships.
*   `public/`: Static assets (if any).
*   `package.json`: Project dependencies and scripts.
*   `next.config.ts`: Next.js configuration.
*   `tailwind.config.ts`: Tailwind CSS configuration.
*   `components.json`: ShadCN UI configuration.

## High-Level Plan to Recreate This Site

This section outlines the general steps and architectural considerations if you were to build a similar application from scratch.

### 1. Foundation & Setup

*   **Initialize Next.js Project**:
    ```bash
    npx create-next-app@latest Dzinza --typescript --tailwind --eslint --app
    ```
*   **Install ShadCN UI**: Follow the ShadCN UI documentation to set up the CLI and add necessary base components (Button, Card, Dialog, Input, Label, Select, Toast, etc.).
*   **Install Dependencies**:
    *   `lucide-react` for icons.
    *   `date-fns` for date formatting.
    *   `zod` for schema validation.
    *   `react-hook-form` and `@hookform/resolvers` for form management.
    *   `genkit`, `@genkit-ai/googleai`, `@genkit-ai/next` for AI features.
*   **Setup Tailwind CSS Theme**: Configure `src/app/globals.css` with HSL color variables for light and dark modes, similar to the existing file. Update `tailwind.config.ts` to use these variables.


### 2. AI Integration (Genkit)

*   **Configure Genkit (`src/ai/genkit.ts`)**:
    *   Initialize Genkit with the `googleAI` plugin.
    *   Conditionally enable the plugin based on the presence of a Gemini API key (`.env` file).
*   **Create AI Flow (`src/ai/flows/suggest-relationships.ts`)**:
    *   Mark with `'use server'`.
    *   Define input (`SuggestRelationshipsInputSchema`) and output (`SuggestRelationshipsOutputSchema`) Zod schemas.
    *   Define an `ai.definePrompt` with a prompt template that takes person details and asks the LLM to suggest siblings, spouses, and children.
    *   Define an `ai.defineFlow` that takes the input, calls the prompt, and returns the output. Handle potential null output from the prompt.
    *   Export a wrapper async function that calls the flow.

### 3. UI Components - Core Display

*   **`PersonCard.tsx`**:
    *   Accepts `person`, `allPeople`, `position`, `onDrag`, `onEdit`, etc., as props.
    *   Uses ShadCN `Card` to display person's name, image, dates, bio, and basic relations (names of parents, spouses, children).
    *   Implement drag functionality:
        *   Use `onMouseDown` on the card to initiate drag.
        *   Use a `useEffect` hook to add global `mousemove` and `mouseup` listeners to the `document` when dragging starts.
        *   In `mousemove`, calculate new (x, y) based on mouse movement and call `onDrag` prop with the new position.
        *   In `mouseup`, stop dragging and remove global listeners.
    *   Include buttons for Edit, Add Relative, AI Suggest, Delete.
*   **`FamilyDisplay.tsx`**:
    *   Receives `people`, `peoplePositions`, `onPersonDrag`, and other handlers.
    *   Renders an SVG element for drawing connecting lines.
    *   Iterates through `people` to draw lines:
        *   For each person, draw lines to their `children` (e.g., from parent's card bottom-center to child's card top-center).
        *   For each person, draw lines to their `spouses` (e.g., horizontally connecting the mid-points of their cards). Ensure lines are drawn only once per pair.
    *   Renders `PersonCard` components, passing their respective `position` from `peoplePositions`.
    *   Manages the overall canvas size dynamically based on card positions.
*   **`src/app/page.tsx` (Main Page Component)**:
    *   **State Management**:
        *   `people: Person[]`: List of all individuals.
        *   `peoplePositions: { [id: string]: { x: number, y: number } }`: Positions of each person card.
        *   Loading states, modal open states, etc.
    *   **Data Fetching**: Use `useEffect` to call `getPeople()` server action on mount.
    *   **Position Calculation (`calculateInitialPositions`)**:
        *   A function to determine initial (x, y) for each person.
        *   Assigns generations: 0 for root nodes (no parents in dataset), `max(parent.gen) + 1` for others.
        *   Lays out cards in rows by generation, centering each row.
        *   Call this in a `useEffect` when `people` data changes and positions need to be (re)calculated.
    *   **Event Handlers**:
        *   `handlePersonDrag`: Updates `peoplePositions` for the dragged person.
        *   Handlers to open/close modals.
        *   `handleModalSubmit` (for Add/Edit Person): Calls server actions, then re-fetches people data.
        *   `handleDeletePerson`: Calls server action, re-fetches people data.
        *   `handleAddRelationshipModalSubmit`: Calls server action, re-fetches.
        *   `handleShowAISuggestions`: Opens AI suggestions modal.
        *   `onResetView`: Recalculates and sets initial positions.
    *   **Rendering**:
        *   Renders `AppHeader`, `FamilyDisplay`, and various modals.

### 4. UI Components - Modals & Forms

*   **`PersonForm.tsx`**:
    *   A reusable form component for adding/editing person details.
    *   Uses `react-hook-form` with Zod resolver for validation.
    *   Includes inputs for name, dates (using ShadCN Calendar in Popover), gender (Select), bio (Textarea), profile picture URL.
*   **`AddEditPersonModal.tsx`**:
    *   ShadCN `Dialog` wrapper around `PersonForm`.
    *   Manages form submission to the main page's handler.
*   **`AddRelationshipModal.tsx`**:
    *   Dialog to select a target person and relationship type (parent, child, spouse).
    *   Allows searching/selecting from existing people or adding a new person on the fly.
*   **`AISuggestionsModal.tsx`**:
    *   Dialog to display AI-suggested relationships.
    *   Fetches suggestions using `getAISuggestionsAction`.
    *   Lists suggestions with buttons to add them (which would typically involve creating the person if they don't exist and then adding the relationship).

### 5. Styling and Layout

*   **Global Styles (`globals.css`)**: Define base styles, Tailwind directives, and CSS variables for theming.
*   **App Layout (`layout.tsx`)**: Basic HTML structure, include `Toaster`.
*   **Header (`AppHeader.tsx`)**: Contains app title and "Add Person" / "Reset View" buttons.
*   **Tailwind CSS**: Use utility classes extensively for styling components.

### 6. Refinements & Error Handling

*   **Loading States**: Show loaders during data fetching or AI processing.
*   **Error Handling**: Use `try...catch` in server actions and AI flows. Display errors using Toasts.
*   **Empty States**: Provide user-friendly messages when the tree is empty or no AI suggestions are found.
*   **Accessibility**: Use ARIA attributes and semantic HTML where appropriate.
