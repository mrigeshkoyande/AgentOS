import express from 'express';
import cors from 'cors';
import { GoogleGenAI } from '@google/genai';
import open from 'open';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

// Initialize Gemini SDK. It automatically uses process.env.GEMINI_API_KEY
const ai = new GoogleGenAI({});

app.post('/api/task', async (req, res) => {
  const { task } = req.body;
  
  if (!task) {
    return res.status(400).json({ error: 'Task is required' });
  }

  try {
    console.log(`Received task: ${task}`);
    // 1. Ask Gemini to extract email intent and details
    const prompt = `
    Analyze the following user task and determine if it's asking to send an email or draft a message. 
    If it is, extract the intended recipients, subject, and body. 
    If the user gives a generic number like "5 people", invent 5 realistic looking email addresses (e.g. alice@example.com).
    Format your response EXACTLY as a JSON object with these keys: 
    - "isEmail" (boolean)
    - "recipients" (string of comma-separated email addresses)
    - "subject" (string)
    - "body" (string)

    Task: "${task}"
    `;

    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: prompt,
      config: {
        responseMimeType: "application/json"
      }
    });

    const result = JSON.parse(response.text);

    if (result.isEmail) {
      console.log('Detected email intent! Opening native mail client...');
      // 2. Build mailto link
      const mailto = `mailto:${result.recipients}?subject=${encodeURIComponent(result.subject)}&body=${encodeURIComponent(result.body)}`;
      
      // 3. Open native mail client
      await open(mailto);

      res.json({ success: true, message: 'Opened native mail client!', details: result });
    } else {
      res.json({ success: true, message: 'Task processed, but no email action detected.', details: result });
    }

  } catch (error) {
    console.error("Error processing task:", error);
    res.status(500).json({ error: 'Failed to process task' });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`SPARK Backend running on http://localhost:${PORT}`);
  console.log(`Make sure you have GEMINI_API_KEY set in your .env file!`);
});
