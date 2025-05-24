import { configureGenkit } from 'genkit';
import { googleAI } from '@genkit-ai/googleai';
import { genkitEval } from '@genkit-ai/evaluator'; // For potential future evaluation
import { dotprompt } from '@genkit-ai/dotprompt'; // If using .prompt files later

export default configureGenkit({
  plugins: [
    // Conditionally enable Google AI plugin if API key is available
    process.env.GEMINI_API_KEY ? googleAI({ apiKey: process.env.GEMINI_API_KEY }) : [],
    genkitEval(), // Optional: for evaluation capabilities
    dotprompt(),  // Optional: for .prompt file support
  ],
  logLevel: 'debug', // Or 'info' for less verbosity
  enableTracing: true,
});
