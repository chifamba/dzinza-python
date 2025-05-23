'use server'; // Important for Next.js server-side modules

import { defineFlow, runFlow } from 'genkit/flow';
import { z } from 'zod';
import { Person } from '@/lib/types'; // Adjust path if necessary
import { generate } from 'genkit/ai';
import * as ai from 'genkit/ai'; // For definePrompt, etc.
// import genkit from '@/ai/genkit'; // This might not be needed here directly if config is auto-loaded by Genkit CLI or runtime

// 1. Define Input Schema (as per README)
export const SuggestRelationshipsInputSchema = z.object({
  person: z.custom<Person>((val) => {
    // Basic validation for Person structure if needed, or assume it's correct
    // For z.custom, you might need to provide a validation function if you want Zod to check it.
    // For now, we'll trust the Person type.
    return typeof val === 'object' && val !== null && 'id' in val && 'name' in val;
  }),
  familyMembers: z.array(z.custom<Person>((val) => {
    return typeof val === 'object' && val !== null && 'id' in val && 'name' in val;
  })),
});
export type SuggestRelationshipsInput = z.infer<typeof SuggestRelationshipsInputSchema>;

// 2. Define Output Schema (as per README)
export const AISuggestedRelationshipSchema = z.object({
  person1Name: z.string(), // Name of the existing person (context person)
  person2Name: z.string(), // Name of the suggested new relative
  person2Gender: z.string().optional(), // Suggested gender for the new relative
  relationshipType: z.enum(['Parent', 'Child', 'Spouse', 'Sibling']), // Type of relationship
  reasoning: z.string().optional(), // Why the AI suggests this
});
export const SuggestRelationshipsOutputSchema = z.object({
  suggestions: z.array(AISuggestedRelationshipSchema),
});
export type SuggestRelationshipsOutput = z.infer<typeof SuggestRelationshipsOutputSchema>;

// 3. Define the Prompt (using definePrompt as per README)
const suggestRelationshipsPrompt = ai.definePrompt(
  {
    name: 'suggestRelationships',
    inputSchema: SuggestRelationshipsInputSchema,
    outputSchema: SuggestRelationshipsOutputSchema, // Genkit uses this for output validation if model supports structured output
  },
  async (input) => {
    let promptText = `You are a helpful genealogy assistant.
Given the primary person:
Name: ${input.person.name}
Birth Date: ${input.person.birthDate || 'N/A'}
Death Date: ${input.person.deathDate || 'N/A'}
Gender: ${input.person.gender || 'N/A'}
Bio: ${input.person.bio || 'N/A'}

And their known family members:
${input.familyMembers.length > 0 ? input.familyMembers.map(p => `- ${p.name} (Born: ${p.birthDate || 'N/A'}, Gender: ${p.gender || 'N/A'})`).join('\n') : 'None known.'}

Suggest potential new family members (specifically Parent, Child, Spouse, or Sibling) for ${input.person.name}.
For each suggestion, provide:
1.  person1Name: The name of the primary person (${input.person.name}).
2.  person2Name: The full name of the suggested new relative.
3.  person2Gender: The suggested gender of the new relative (e.g., Male, Female).
4.  relationshipType: The type of relationship this new person has to ${input.person.name} (must be one of: Parent, Child, Spouse, Sibling).
5.  reasoning: A brief explanation for why this suggestion is plausible based on the provided information.

Return your answer as a JSON object matching the following schema:
{
  "suggestions": [
    {
      "person1Name": "${input.person.name}",
      "person2Name": "Suggested Full Name",
      "person2Gender": "Suggested Gender",
      "relationshipType": "Parent | Child | Spouse | Sibling",
      "reasoning": "Brief reasoning."
    }
  ]
}
Only provide the JSON object. Do not include any other text or explanations outside of the JSON structure.
If you have no suggestions, return an empty "suggestions" array.
`;
    return {
      messages: [{ role: 'user', content: promptText }],
      // Instruct Gemini to output JSON
      // This requires a model that supports JSON output mode, e.g., gemini-1.5-pro-latest or gemini-1.5-flash-latest
      // For gemini-pro (non-1.5), direct JSON output mode might not be supported,
      // so the model would need to be instructed to *format* its output as JSON.
      // The `output: { format: 'json' }` in generate() is preferred if the model supports it.
    };
  }
);

// 4. Define the Flow (as per README)
export const suggestRelationshipsFlow = defineFlow(
  {
    name: 'suggestRelationshipsFlow',
    inputSchema: SuggestRelationshipsInputSchema,
    outputSchema: SuggestRelationshipsOutputSchema,
  },
  async (input) => {
    const llmResponse = await generate({
      prompt: suggestRelationshipsPrompt,
      input: input,
      model: googleAI('gemini-1.5-flash-latest'), // Using a specific model alias from googleAI plugin
      config: { temperature: 0.3 }, // Lower temperature for more factual/predictable output
      output: { format: 'json' }, // Request JSON output from the model
    });

    const structuredOutput = llmResponse.output();
    if (!structuredOutput) {
        console.error("AI did not return structured output. Raw response:", llmResponse.text());
        return { suggestions: [] };
    }

    // Validate the structured output against the Zod schema
    const parsed = SuggestRelationshipsOutputSchema.safeParse(structuredOutput);
    if (parsed.success) {
      return parsed.data;
    } else {
      console.error("AI output validation failed:", parsed.error.toString(), "Raw structured output:", structuredOutput);
      // Attempt to extract suggestions even if the root structure is slightly off,
      // as long as individual suggestions might be parseable.
      // This is a fallback and ideally the model returns perfectly valid data.
      if (Array.isArray(structuredOutput) && structuredOutput.every(s => AISuggestedRelationshipSchema.safeParse(s).success)) {
        // This case might occur if the model returns an array of suggestions directly instead of { suggestions: [...] }
        console.warn("AI returned an array of suggestions directly. Wrapping in output schema.");
        return { suggestions: structuredOutput as z.infer<typeof AISuggestedRelationshipSchema>[] };
      }
      if (typeof structuredOutput === 'object' && structuredOutput !== null && Array.isArray((structuredOutput as any).suggestions)) {
        const validSuggestions = (structuredOutput as any).suggestions.filter(
            (s: any) => AISuggestedRelationshipSchema.safeParse(s).success
        );
        if (validSuggestions.length > 0 && validSuggestions.length !== (structuredOutput as any).suggestions.length) {
            console.warn("Some AI suggestions were invalid and filtered out.");
        }
        return { suggestions: validSuggestions };
      }
      return { suggestions: [] }; // Return empty if parsing/validation fails
    }
  }
);

// 5. Export a wrapper async function to run the flow (as per README)
export async function getAISuggestions(input: SuggestRelationshipsInput): Promise<SuggestRelationshipsOutput> {
  if (!process.env.GEMINI_API_KEY) {
    console.warn("GEMINI_API_KEY not found. AI suggestions are disabled.");
    return { suggestions: [] };
  }
  try {
    return await runFlow(suggestRelationshipsFlow, input);
  } catch (error) {
    console.error("Error running suggestRelationshipsFlow:", error);
    return { suggestions: [] };
  }
}
