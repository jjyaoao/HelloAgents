---
name: VLM
description: Implement vision-based AI chat capabilities using the z-ai-web-dev-sdk. Use this skill when the user needs to analyze images, describe visual content, or create applications that combine image understanding with conversational AI. Supports image URLs and base64 encoded images for multimodal interactions.
license: MIT
---

# VLM(Vision Chat) Skill

This skill guides the implementation of vision chat functionality using the z-ai-web-dev-sdk package, enabling AI models to understand and respond to images combined with text prompts.

## Skills Path

**Skill Location**: `{project_path}/skills/VLM`

this skill is located at above path in your project.

**Reference Scripts**: Example test scripts are available in the `{Skill Location}/scripts/` directory for quick testing and reference. See `{Skill Location}/scripts/vlm.ts` for a working example.

## Overview

Vision Chat allows you to build applications that can analyze images, extract information from visual content, and answer questions about images through natural language conversation.

**IMPORTANT**: z-ai-web-dev-sdk MUST be used in backend code only. Never use it in client-side code.

## Prerequisites

The z-ai-web-dev-sdk package is already installed. Import it as shown in the examples below.

## CLI Usage (For Simple Tasks)

For simple image analysis tasks, you can use the z-ai CLI instead of writing code. This is ideal for quick image descriptions, testing vision capabilities, or simple automation.

### Basic Image Analysis

```bash
# Describe an image from URL
z-ai vision --prompt "What's in this image?" --image "https://example.com/photo.jpg"

# Using short options
z-ai vision -p "Describe this image" -i "https://example.com/image.png"
```

### Analyze Local Images

```bash
# Analyze a local image file
z-ai vision -p "What objects are in this photo?" -i "./photo.jpg"

# Save response to file
z-ai vision -p "Describe the scene" -i "./landscape.png" -o description.json
```

### Multiple Images

```bash
# Analyze multiple images at once
z-ai vision \
  -p "Compare these two images" \
  -i "./photo1.jpg" \
  -i "./photo2.jpg" \
  -o comparison.json

# Multiple images with detailed analysis
z-ai vision \
  --prompt "What are the differences between these images?" \
  --image "https://example.com/before.jpg" \
  --image "https://example.com/after.jpg"
```

### With Thinking (Chain of Thought)

```bash
# Enable thinking for complex visual reasoning
z-ai vision \
  -p "Count the number of people in this image and describe their activities" \
  -i "./crowd.jpg" \
  --thinking \
  -o analysis.json
```

### Streaming Output

```bash
# Stream the vision analysis
z-ai vision -p "Describe this image in detail" -i "./photo.jpg" --stream
```

### CLI Parameters

- `--prompt, -p <text>`: **Required** - Question or instruction about the image(s)
- `--image, -i <URL or path>`: Optional - Image URL or local file path (can be used multiple times)
- `--thinking, -t`: Optional - Enable chain-of-thought reasoning (default: disabled)
- `--output, -o <path>`: Optional - Output file path (JSON format)
- `--stream`: Optional - Stream the response in real-time

### Supported Image Formats

- PNG (.png)
- JPEG (.jpg, .jpeg)
- GIF (.gif)
- WebP (.webp)
- BMP (.bmp)

### When to Use CLI vs SDK

**Use CLI for:**
- Quick image analysis
- Testing vision model capabilities
- One-off image descriptions
- Simple automation scripts

**Use SDK for:**
- Multi-turn conversations with images
- Dynamic image analysis in applications
- Batch processing with custom logic
- Production applications with complex workflows

## Recommended Approach

For better performance and reliability, use base64 encoding to pass images to the model instead of image URLs.

## Supported Content Types

The Vision Chat API supports three types of media content:

### 1. **image_url** - For Image Files
Use this type for static images (PNG, JPEG, GIF, WebP, etc.)
```typescript
{
    role: 'user',
    content: [
        { type: 'text', text: prompt },
        { type: 'image_url', image_url: { url: imageUrl } }
    ]
}
```

### 2. **video_url** - For Video Files
Use this type for video content (MP4, AVI, MOV, etc.)
```typescript
{
    role: 'user',
    content: [
        { type: 'text', text: prompt },
        { type: 'video_url', video_url: { url: videoUrl } }
    ]
}
```

### 3. **file_url** - For Document Files
Use this type for document files (PDF, DOCX, TXT, etc.)
```typescript
{
    role: 'user',
    content: [
        { type: 'text', text: prompt },
        { type: 'file_url', file_url: { url: fileUrl } }
    ]
}
```

**Note**: You can combine multiple content types in a single message. For example, you can include both text and multiple images, or text with both an image and a document.

## Basic Vision Chat Implementation

### Single Image Analysis

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function analyzeImage(imageUrl, question) {
  const zai = await ZAI.create();

  const response = await zai.chat.completions.createVision({
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'text',
            text: question
          },
          {
            type: 'image_url',
            image_url: {
              url: imageUrl
            }
          }
        ]
      }
    ],
    thinking: { type: 'disabled' }
  });

  return response.choices[0]?.message?.content;
}

// Usage
const result = await analyzeImage(
  'https://example.com/product.jpg',
  'Describe this product in detail'
);
console.log('Analysis:', result);
```

### Multiple Images Analysis

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function compareImages(imageUrls, question) {
  const zai = await ZAI.create();

  const content = [
    {
      type: 'text',
      text: question
    },
    ...imageUrls.map(url => ({
      type: 'image_url',
      image_url: { url }
    }))
  ];

  const response = await zai.chat.completions.createVision({
    messages: [
      {
        role: 'user',
        content: content
      }
    ],
    thinking: { type: 'disabled' }
  });

  return response.choices[0]?.message?.content;
}

// Usage
const comparison = await compareImages(
  [
    'https://example.com/before.jpg',
    'https://example.com/after.jpg'
  ],
  'Compare these two images and describe the differences'
);
```

### Base64 Image Support

```javascript
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

async function analyzeLocalImage(imagePath, question) {
  const zai = await ZAI.create();

  // Read image file and convert to base64
  const imageBuffer = fs.readFileSync(imagePath);
  const base64Image = imageBuffer.toString('base64');
  const mimeType = imagePath.endsWith('.png') ? 'image/png' : 'image/jpeg';

  const response = await zai.chat.completions.createVision({
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'text',
            text: question
          },
          {
            type: 'image_url',
            image_url: {
              url: `data:${mimeType};base64,${base64Image}`
            }
          }
        ]
      }
    ],
    thinking: { type: 'disabled' }
  });

  return response.choices[0]?.message?.content;
}
```

## Advanced Use Cases

### Conversational Vision Chat

```javascript
import ZAI from 'z-ai-web-dev-sdk';

class VisionChatSession {
  constructor() {
    this.messages = [];
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  async addImage(imageUrl, initialQuestion) {
    this.messages.push({
      role: 'user',
      content: [
        {
          type: 'text',
          text: initialQuestion
        },
        {
          type: 'image_url',
          image_url: { url: imageUrl }
        }
      ]
    });

    return this.getResponse();
  }

  async followUp(question) {
    this.messages.push({
      role: 'user',
      content: [
        {
          type: 'text',
          text: question
        }
      ]
    });

    return this.getResponse();
  }

  async getResponse() {
    const response = await this.zai.chat.completions.createVision({
      messages: this.messages,
      thinking: { type: 'disabled' }
    });

    const assistantMessage = response.choices[0]?.message?.content;
    
    this.messages.push({
      role: 'assistant',
      content: assistantMessage
    });

    return assistantMessage;
  }
}

// Usage
const session = new VisionChatSession();
await session.initialize();

const initial = await session.addImage(
  'https://example.com/chart.jpg',
  'What does this chart show?'
);
console.log('Initial analysis:', initial);

const followup = await session.followUp('What are the key trends?');
console.log('Follow-up:', followup);
```

### Image Classification and Tagging

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function classifyImage(imageUrl) {
  const zai = await ZAI.create();

  const prompt = `Analyze this image and provide:
1. Main subject/category
2. Key objects detected
3. Scene description
4. Suggested tags (comma-separated)

Format your response as JSON.`;

  const response = await zai.chat.completions.createVision({
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'text',
            text: prompt
          },
          {
            type: 'image_url',
            image_url: { url: imageUrl }
          }
        ]
      }
    ],
    thinking: { type: 'disabled' }
  });

  const content = response.choices[0]?.message?.content;
  
  try {
    return JSON.parse(content);
  } catch (e) {
    return { rawResponse: content };
  }
}
```

### OCR and Text Extraction

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function extractText(imageUrl) {
  const zai = await ZAI.create();

  const response = await zai.chat.completions.createVision({
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'text',
            text: 'Extract all text from this image. Preserve the layout and formatting as much as possible.'
          },
          {
            type: 'image_url',
            image_url: { url: imageUrl }
          }
        ]
      }
    ],
    thinking: { type: 'disabled' }
  });

  return response.choices[0]?.message?.content;
}
```

## Best Practices

### 1. Image Quality and Size
- Use high-quality images for better analysis results
- Optimize image size to balance quality and processing speed
- Supported formats: JPEG, PNG, WebP

### 2. Prompt Engineering
- Be specific about what information you need from the image
- Structure complex requests with numbered lists or bullet points
- Provide context about the image type (photo, diagram, chart, etc.)

### 3. Error Handling
```javascript
async function safeVisionChat(imageUrl, question) {
  try {
    const zai = await ZAI.create();
    
    const response = await zai.chat.completions.createVision({
      messages: [
        {
          role: 'user',
          content: [
            { type: 'text', text: question },
            { type: 'image_url', image_url: { url: imageUrl } }
          ]
        }
      ],
      thinking: { type: 'disabled' }
    });

    return {
      success: true,
      content: response.choices[0]?.message?.content
    };
  } catch (error) {
    console.error('Vision chat error:', error);
    return {
      success: false,
      error: error.message
    };
  }
}
```

### 4. Performance Optimization
- Cache SDK instance creation when processing multiple images
- Use appropriate image formats (JPEG for photos, PNG for diagrams)
- Consider image preprocessing for large batches

### 5. Security Considerations
- Validate image URLs before processing
- Sanitize user-provided image data
- Implement rate limiting for public-facing APIs
- Never expose SDK credentials in client-side code

## Common Use Cases

1. **Product Analysis**: Analyze product images for e-commerce applications
2. **Document Understanding**: Extract information from receipts, invoices, forms
3. **Medical Imaging**: Assist in preliminary analysis (with appropriate disclaimers)
4. **Quality Control**: Detect defects or anomalies in manufacturing
5. **Content Moderation**: Analyze images for policy compliance
6. **Accessibility**: Generate alt text for images automatically
7. **Visual Search**: Understand and categorize images for search functionality

## Integration Examples

### Express.js API Endpoint

```javascript
import express from 'express';
import ZAI from 'z-ai-web-dev-sdk';

const app = express();
app.use(express.json());

let zaiInstance;

// Initialize SDK once
async function initZAI() {
  zaiInstance = await ZAI.create();
}

app.post('/api/analyze-image', async (req, res) => {
  try {
    const { imageUrl, question } = req.body;

    if (!imageUrl || !question) {
      return res.status(400).json({ 
        error: 'imageUrl and question are required' 
      });
    }

    const response = await zaiInstance.chat.completions.createVision({
      messages: [
        {
          role: 'user',
          content: [
            { type: 'text', text: question },
            { type: 'image_url', image_url: { url: imageUrl } }
          ]
        }
      ],
      thinking: { type: 'disabled' }
    });

    res.json({
      success: true,
      analysis: response.choices[0]?.message?.content
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

initZAI().then(() => {
  app.listen(3000, () => {
    console.log('Vision chat API running on port 3000');
  });
});
```

## Troubleshooting

**Issue**: "SDK must be used in backend"
- **Solution**: Ensure z-ai-web-dev-sdk is only imported and used in server-side code

**Issue**: Image not loading or being analyzed
- **Solution**: Verify the image URL is accessible and returns a valid image format

**Issue**: Poor analysis quality
- **Solution**: Provide more specific prompts and ensure image quality is sufficient

**Issue**: Slow response times
- **Solution**: Optimize image size and consider caching frequently analyzed images

## Remember

- Always use z-ai-web-dev-sdk in backend code only
- The SDK is already installed - import as shown in examples
- Structure prompts clearly for best results
- Handle errors gracefully in production applications
- Consider user privacy when processing images
