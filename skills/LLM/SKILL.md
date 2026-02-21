---
name: LLM
description: Implement large language model (LLM) chat completions using the z-ai-web-dev-sdk. Use this skill when the user needs to build conversational AI applications, chatbots, AI assistants, or any text generation features. Supports multi-turn conversations, system prompts, and context management.
license: MIT
---

# LLM (Large Language Model) Skill

This skill guides the implementation of chat completions functionality using the z-ai-web-dev-sdk package, enabling powerful conversational AI and text generation capabilities.

## Skills Path

**Skill Location**: `{project_path}/skills/llm`

this skill is located at above path in your project.

**Reference Scripts**: Example test scripts are available in the `{Skill Location}/scripts/` directory for quick testing and reference. See `{Skill Location}/scripts/chat.ts` for a working example.

## Overview

The LLM skill allows you to build applications that leverage large language models for natural language understanding and generation, including chatbots, AI assistants, content generation, and more.

**IMPORTANT**: z-ai-web-dev-sdk MUST be used in backend code only. Never use it in client-side code.

## Prerequisites

The z-ai-web-dev-sdk package is already installed. Import it as shown in the examples below.

## CLI Usage (For Simple Tasks)

For simple, one-off chat completions, you can use the z-ai CLI instead of writing code. This is ideal for quick tests, simple queries, or automation scripts.

### Basic Chat

```bash
# Simple question
z-ai chat --prompt "What is the capital of France?"

# Save response to file
z-ai chat -p "Explain quantum computing" -o response.json

# Stream the response
z-ai chat -p "Write a short poem" --stream
```

### With System Prompt

```bash
# Custom system prompt for specific behavior
z-ai chat \
  --prompt "Review this code: function add(a,b) { return a+b; }" \
  --system "You are an expert code reviewer" \
  -o review.json
```

### With Thinking (Chain of Thought)

```bash
# Enable thinking for complex reasoning
z-ai chat \
  --prompt "Solve this math problem: If a train travels 120km in 2 hours, what's its speed?" \
  --thinking \
  -o solution.json
```

### CLI Parameters

- `--prompt, -p <text>`: **Required** - User message content
- `--system, -s <text>`: Optional - System prompt for custom behavior
- `--thinking, -t`: Optional - Enable chain-of-thought reasoning (default: disabled)
- `--output, -o <path>`: Optional - Output file path (JSON format)
- `--stream`: Optional - Stream the response in real-time

### When to Use CLI vs SDK

**Use CLI for:**
- Quick one-off questions
- Simple automation scripts
- Testing prompts
- Single-turn conversations

**Use SDK for:**
- Multi-turn conversations with context
- Custom conversation management
- Integration with web applications
- Complex chat workflows
- Production applications

## Basic Chat Completions

### Simple Question and Answer

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function askQuestion(question) {
  const zai = await ZAI.create();

  const completion = await zai.chat.completions.create({
    messages: [
      {
        role: 'assistant',
        content: 'You are a helpful assistant.'
      },
      {
        role: 'user',
        content: question
      }
    ],
    thinking: { type: 'disabled' }
  });

  const response = completion.choices[0]?.message?.content;
  return response;
}

// Usage
const answer = await askQuestion('What is the capital of France?');
console.log('Answer:', answer);
```

### Custom System Prompt

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function customAssistant(systemPrompt, userMessage) {
  const zai = await ZAI.create();

  const completion = await zai.chat.completions.create({
    messages: [
      {
        role: 'assistant',
        content: systemPrompt
      },
      {
        role: 'user',
        content: userMessage
      }
    ],
    thinking: { type: 'disabled' }
  });

  return completion.choices[0]?.message?.content;
}

// Usage - Code reviewer
const codeReview = await customAssistant(
  'You are an expert code reviewer. Analyze code for bugs, performance issues, and best practices.',
  'Review this function: function add(a, b) { return a + b; }'
);

// Usage - Creative writer
const story = await customAssistant(
  'You are a creative fiction writer who writes engaging short stories.',
  'Write a short story about a robot learning to paint.'
);

console.log(codeReview);
console.log(story);
```

## Multi-turn Conversations

### Conversation History Management

```javascript
import ZAI from 'z-ai-web-dev-sdk';

class ConversationManager {
  constructor(systemPrompt = 'You are a helpful assistant.') {
    this.messages = [
      {
        role: 'assistant',
        content: systemPrompt
      }
    ];
    this.zai = null;
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  async sendMessage(userMessage) {
    // Add user message to history
    this.messages.push({
      role: 'user',
      content: userMessage
    });

    // Get completion
    const completion = await this.zai.chat.completions.create({
      messages: this.messages,
      thinking: { type: 'disabled' }
    });

    const assistantResponse = completion.choices[0]?.message?.content;

    // Add assistant response to history
    this.messages.push({
      role: 'assistant',
      content: assistantResponse
    });

    return assistantResponse;
  }

  getHistory() {
    return this.messages;
  }

  clearHistory(systemPrompt = 'You are a helpful assistant.') {
    this.messages = [
      {
        role: 'assistant',
        content: systemPrompt
      }
    ];
  }

  getMessageCount() {
    // Subtract 1 for system message
    return this.messages.length - 1;
  }
}

// Usage
const conversation = new ConversationManager();
await conversation.initialize();

const response1 = await conversation.sendMessage('Hi, my name is John.');
console.log('AI:', response1);

const response2 = await conversation.sendMessage('What is my name?');
console.log('AI:', response2); // Should remember the name is John

console.log('Total messages:', conversation.getMessageCount());
```

### Context-Aware Conversations

```javascript
import ZAI from 'z-ai-web-dev-sdk';

class ContextualChat {
  constructor() {
    this.messages = [];
    this.zai = null;
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  async startConversation(role, context) {
    // Set up system prompt with context
    const systemPrompt = `You are ${role}. Context: ${context}`;
    
    this.messages = [
      {
        role: 'assistant',
        content: systemPrompt
      }
    ];
  }

  async chat(userMessage) {
    this.messages.push({
      role: 'user',
      content: userMessage
    });

    const completion = await this.zai.chat.completions.create({
      messages: this.messages,
      thinking: { type: 'disabled' }
    });

    const response = completion.choices[0]?.message?.content;

    this.messages.push({
      role: 'assistant',
      content: response
    });

    return response;
  }
}

// Usage - Customer support scenario
const support = new ContextualChat();
await support.initialize();

await support.startConversation(
  'a customer support agent for TechCorp',
  'The user has ordered product #12345 which is delayed due to shipping issues.'
);

const reply1 = await support.chat('Where is my order?');
console.log('Support:', reply1);

const reply2 = await support.chat('Can I get a refund?');
console.log('Support:', reply2);
```

## Advanced Use Cases

### Content Generation

```javascript
import ZAI from 'z-ai-web-dev-sdk';

class ContentGenerator {
  constructor() {
    this.zai = null;
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  async generateBlogPost(topic, tone = 'professional') {
    const completion = await this.zai.chat.completions.create({
      messages: [
        {
          role: 'assistant',
          content: `You are a professional content writer. Write in a ${tone} tone.`
        },
        {
          role: 'user',
          content: `Write a blog post about: ${topic}. Include an introduction, main points, and conclusion.`
        }
      ],
      thinking: { type: 'disabled' }
    });

    return completion.choices[0]?.message?.content;
  }

  async generateProductDescription(productName, features) {
    const completion = await this.zai.chat.completions.create({
      messages: [
        {
          role: 'assistant',
          content: 'You are an expert at writing compelling product descriptions for e-commerce.'
        },
        {
          role: 'user',
          content: `Write a product description for "${productName}". Key features: ${features.join(', ')}.`
        }
      ],
      thinking: { type: 'disabled' }
    });

    return completion.choices[0]?.message?.content;
  }

  async generateEmailResponse(originalEmail, intent) {
    const completion = await this.zai.chat.completions.create({
      messages: [
        {
          role: 'assistant',
          content: 'You are a professional email writer. Write clear, concise, and polite emails.'
        },
        {
          role: 'user',
          content: `Original email: "${originalEmail}"\n\nWrite a ${intent} response.`
        }
      ],
      thinking: { type: 'disabled' }
    });

    return completion.choices[0]?.message?.content;
  }
}

// Usage
const generator = new ContentGenerator();
await generator.initialize();

const blogPost = await generator.generateBlogPost(
  'The Future of Artificial Intelligence',
  'informative'
);
console.log('Blog Post:', blogPost);

const productDesc = await generator.generateProductDescription(
  'Smart Watch Pro',
  ['Heart rate monitoring', 'GPS tracking', 'Waterproof', '7-day battery life']
);
console.log('Product Description:', productDesc);
```

### Data Analysis and Summarization

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function analyzeData(data, analysisType) {
  const zai = await ZAI.create();

  const prompts = {
    summarize: 'You are a data analyst. Summarize the key insights from the data.',
    trend: 'You are a data analyst. Identify trends and patterns in the data.',
    recommendation: 'You are a business analyst. Provide actionable recommendations based on the data.'
  };

  const completion = await zai.chat.completions.create({
    messages: [
      {
        role: 'assistant',
        content: prompts[analysisType] || prompts.summarize
      },
      {
        role: 'user',
        content: `Analyze this data:\n\n${JSON.stringify(data, null, 2)}`
      }
    ],
    thinking: { type: 'disabled' }
  });

  return completion.choices[0]?.message?.content;
}

// Usage
const salesData = {
  Q1: { revenue: 100000, customers: 250 },
  Q2: { revenue: 120000, customers: 280 },
  Q3: { revenue: 150000, customers: 320 },
  Q4: { revenue: 180000, customers: 380 }
};

const summary = await analyzeData(salesData, 'summarize');
const trends = await analyzeData(salesData, 'trend');
const recommendations = await analyzeData(salesData, 'recommendation');

console.log('Summary:', summary);
console.log('Trends:', trends);
console.log('Recommendations:', recommendations);
```

### Code Generation and Debugging

```javascript
import ZAI from 'z-ai-web-dev-sdk';

class CodeAssistant {
  constructor() {
    this.zai = null;
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  async generateCode(description, language) {
    const completion = await this.zai.chat.completions.create({
      messages: [
        {
          role: 'assistant',
          content: `You are an expert ${language} programmer. Write clean, efficient, and well-commented code.`
        },
        {
          role: 'user',
          content: `Write ${language} code to: ${description}`
        }
      ],
      thinking: { type: 'disabled' }
    });

    return completion.choices[0]?.message?.content;
  }

  async debugCode(code, issue) {
    const completion = await this.zai.chat.completions.create({
      messages: [
        {
          role: 'assistant',
          content: 'You are an expert debugger. Identify bugs and suggest fixes.'
        },
        {
          role: 'user',
          content: `Code:\n${code}\n\nIssue: ${issue}\n\nFind the bug and suggest a fix.`
        }
      ],
      thinking: { type: 'disabled' }
    });

    return completion.choices[0]?.message?.content;
  }

  async explainCode(code) {
    const completion = await this.zai.chat.completions.create({
      messages: [
        {
          role: 'assistant',
          content: 'You are a programming teacher. Explain code clearly and simply.'
        },
        {
          role: 'user',
          content: `Explain what this code does:\n\n${code}`
        }
      ],
      thinking: { type: 'disabled' }
    });

    return completion.choices[0]?.message?.content;
  }
}

// Usage
const codeAssist = new CodeAssistant();
await codeAssist.initialize();

const newCode = await codeAssist.generateCode(
  'Create a function that sorts an array of objects by a specific property',
  'JavaScript'
);
console.log('Generated Code:', newCode);

const bugFix = await codeAssist.debugCode(
  'function add(a, b) { return a - b; }',
  'This function should add numbers but returns wrong results'
);
console.log('Debug Suggestion:', bugFix);
```

## Best Practices

### 1. Prompt Engineering

```javascript
// Bad: Vague prompt
const bad = await askQuestion('Tell me about AI');

// Good: Specific and structured prompt
async function askWithContext(topic, format, audience) {
  const zai = await ZAI.create();
  
  const completion = await zai.chat.completions.create({
    messages: [
      {
        role: 'assistant',
        content: `You are an expert educator. Explain topics clearly for ${audience}.`
      },
      {
        role: 'user',
        content: `Explain ${topic} in ${format} format. Include practical examples.`
      }
    ],
    thinking: { type: 'disabled' }
  });

  return completion.choices[0]?.message?.content;
}

const good = await askWithContext('artificial intelligence', 'bullet points', 'beginners');
```

### 2. Error Handling

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function safeCompletion(messages, retries = 3) {
  let lastError;

  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const zai = await ZAI.create();

      const completion = await zai.chat.completions.create({
        messages: messages,
        thinking: { type: 'disabled' }
      });

      const response = completion.choices[0]?.message?.content;

      if (!response || response.trim().length === 0) {
        throw new Error('Empty response from AI');
      }

      return {
        success: true,
        content: response,
        attempts: attempt
      };
    } catch (error) {
      lastError = error;
      console.error(`Attempt ${attempt} failed:`, error.message);

      if (attempt < retries) {
        // Wait before retry (exponential backoff)
        await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
      }
    }
  }

  return {
    success: false,
    error: lastError.message,
    attempts: retries
  };
}
```

### 3. Context Management

```javascript
class ManagedConversation {
  constructor(maxMessages = 20) {
    this.maxMessages = maxMessages;
    this.systemPrompt = '';
    this.messages = [];
    this.zai = null;
  }

  async initialize(systemPrompt) {
    this.zai = await ZAI.create();
    this.systemPrompt = systemPrompt;
    this.messages = [
      {
        role: 'assistant',
        content: systemPrompt
      }
    ];
  }

  async chat(userMessage) {
    // Add user message
    this.messages.push({
      role: 'user',
      content: userMessage
    });

    // Trim old messages if exceeding limit (keep system prompt)
    if (this.messages.length > this.maxMessages) {
      this.messages = [
        this.messages[0], // Keep system prompt
        ...this.messages.slice(-(this.maxMessages - 1))
      ];
    }

    const completion = await this.zai.chat.completions.create({
      messages: this.messages,
      thinking: { type: 'disabled' }
    });

    const response = completion.choices[0]?.message?.content;

    this.messages.push({
      role: 'assistant',
      content: response
    });

    return response;
  }

  getTokenEstimate() {
    // Rough estimate: ~4 characters per token
    const totalChars = this.messages
      .map(m => m.content.length)
      .reduce((a, b) => a + b, 0);
    return Math.ceil(totalChars / 4);
  }
}
```

### 4. Response Processing

```javascript
async function getStructuredResponse(query, format = 'json') {
  const zai = await ZAI.create();

  const formatInstructions = {
    json: 'Respond with valid JSON only. No additional text.',
    list: 'Respond with a numbered list.',
    markdown: 'Respond in Markdown format.'
  };

  const completion = await zai.chat.completions.create({
    messages: [
      {
        role: 'assistant',
        content: `You are a helpful assistant. ${formatInstructions[format]}`
      },
      {
        role: 'user',
        content: query
      }
    ],
    thinking: { type: 'disabled' }
  });

  const response = completion.choices[0]?.message?.content;

  // Parse JSON if requested
  if (format === 'json') {
    try {
      return JSON.parse(response);
    } catch (e) {
      console.error('Failed to parse JSON response');
      return { raw: response };
    }
  }

  return response;
}

// Usage
const jsonData = await getStructuredResponse(
  'List three programming languages with their primary use cases',
  'json'
);
console.log(jsonData);
```

## Common Use Cases

1. **Chatbots & Virtual Assistants**: Build conversational interfaces for customer support
2. **Content Generation**: Create articles, product descriptions, marketing copy
3. **Code Assistance**: Generate, explain, and debug code
4. **Data Analysis**: Analyze and summarize complex data sets
5. **Language Translation**: Translate text between languages
6. **Educational Tools**: Create tutoring and learning applications
7. **Email Automation**: Generate professional email responses
8. **Creative Writing**: Story generation, poetry, and creative content

## Integration Examples

### Express.js Chatbot API

```javascript
import express from 'express';
import ZAI from 'z-ai-web-dev-sdk';

const app = express();
app.use(express.json());

// Store conversations in memory (use database in production)
const conversations = new Map();

let zaiInstance;

async function initZAI() {
  zaiInstance = await ZAI.create();
}

app.post('/api/chat', async (req, res) => {
  try {
    const { sessionId, message, systemPrompt } = req.body;

    if (!message) {
      return res.status(400).json({ error: 'Message is required' });
    }

    // Get or create conversation history
    let history = conversations.get(sessionId) || [
      {
        role: 'assistant',
        content: systemPrompt || 'You are a helpful assistant.'
      }
    ];

    // Add user message
    history.push({
      role: 'user',
      content: message
    });

    // Get completion
    const completion = await zaiInstance.chat.completions.create({
      messages: history,
      thinking: { type: 'disabled' }
    });

    const aiResponse = completion.choices[0]?.message?.content;

    // Add AI response to history
    history.push({
      role: 'assistant',
      content: aiResponse
    });

    // Save updated history
    conversations.set(sessionId, history);

    res.json({
      success: true,
      response: aiResponse,
      messageCount: history.length - 1
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.delete('/api/chat/:sessionId', (req, res) => {
  const { sessionId } = req.params;
  conversations.delete(sessionId);
  res.json({ success: true, message: 'Conversation cleared' });
});

initZAI().then(() => {
  app.listen(3000, () => {
    console.log('Chatbot API running on port 3000');
  });
});
```

## Troubleshooting

**Issue**: "SDK must be used in backend"
- **Solution**: Ensure z-ai-web-dev-sdk is only imported and used in server-side code

**Issue**: Empty or incomplete responses
- **Solution**: Check that completion.choices[0]?.message?.content exists and is not empty

**Issue**: Conversation context getting too long
- **Solution**: Implement message trimming to keep only recent messages

**Issue**: Inconsistent responses
- **Solution**: Use more specific system prompts and provide clear instructions

**Issue**: Rate limiting errors
- **Solution**: Implement retry logic with exponential backoff

## Performance Tips

1. **Reuse SDK Instance**: Create ZAI instance once and reuse across requests
2. **Manage Context Length**: Trim old messages to avoid token limits
3. **Implement Caching**: Cache responses for common queries
4. **Use Specific Prompts**: Clear prompts lead to faster, better responses
5. **Handle Errors Gracefully**: Implement retry logic and fallback responses

## Security Considerations

1. **Input Validation**: Always validate and sanitize user input
2. **Rate Limiting**: Implement rate limits to prevent abuse
3. **API Key Protection**: Never expose SDK credentials in client-side code
4. **Content Filtering**: Filter sensitive or inappropriate content
5. **Session Management**: Implement proper session handling and cleanup

## Remember

- Always use z-ai-web-dev-sdk in backend code only
- The SDK is already installed - import as shown in examples
- Use the 'assistant' role for system prompts
- Set thinking to { type: 'disabled' } for standard completions
- Implement proper error handling and retries for production
- Manage conversation history to avoid token limits
- Clear and specific prompts lead to better results
- Check `scripts/chat.ts` for a quick start example
