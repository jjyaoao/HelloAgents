---
name: video-understand
description: Implement specialized video understanding capabilities using the z-ai-web-dev-sdk. Use this skill when the user needs to analyze video content, understand motion and temporal sequences, extract information from video frames, describe video scenes, or perform video-based AI analysis. Optimized for MP4, AVI, MOV, and other common video formats.
license: MIT
---

# Video Understanding Skill

This skill provides specialized video understanding functionality using the z-ai-web-dev-sdk package, enabling AI models to analyze, describe, and extract information from video content including motion, temporal sequences, and scene changes.

## Skills Path

**Skill Location**: `{project_path}/skills/video-understand`

this skill is located at above path in your project.

**Reference Scripts**: Example test scripts are available in the `{Skill Location}/scripts/` directory for quick testing and reference. See `{Skill Location}/scripts/video-understand.ts` for a working example.

## Overview

Video Understanding focuses specifically on video content analysis, providing capabilities for:
- Video scene understanding and description
- Action and motion detection
- Temporal sequence analysis
- Event detection in videos
- Video content summarization
- Scene change detection
- People and object tracking across frames
- Audio-visual content analysis (when applicable)

**IMPORTANT**: z-ai-web-dev-sdk MUST be used in backend code only. Never use it in client-side code.

## Prerequisites

The z-ai-web-dev-sdk package is already installed. Import it as shown in the examples below.

## CLI Usage (For Simple Tasks)

For quick video analysis tasks, you can use the z-ai CLI instead of writing code. This is ideal for simple video descriptions, testing, or automation.

### Basic Video Analysis

```bash
# Analyze a video from URL
z-ai vision --prompt "Summarize what happens in this video" --image "https://example.com/video.mp4"

# Note: Use --image flag for video URLs as well
z-ai vision -p "Describe the key events" -i "https://example.com/presentation.mp4"
```

### Analyze Local Videos

```bash
# Analyze a local video file
z-ai vision -p "What activities are shown in this video?" -i "./recording.mp4"

# Save response to file
z-ai vision -p "Provide a detailed summary" -i "./meeting.mp4" -o summary.json
```

### Advanced Video Analysis

```bash
# Complex scene understanding with thinking
z-ai vision \
  -p "Analyze this video and identify: 1) Main events, 2) People and their actions, 3) Timeline of key moments" \
  -i "./event.mp4" \
  --thinking \
  -o analysis.json

# Action detection
z-ai vision \
  -p "Identify all actions performed by people in this video" \
  -i "./sports.mp4" \
  --thinking
```

### Streaming Output

```bash
# Stream the video analysis
z-ai vision -p "Describe this video content" -i "./video.mp4" --stream
```

### CLI Parameters

- `--prompt, -p <text>`: **Required** - Question or instruction about the video
- `--image, -i <URL or path>`: Optional - Video URL or local file path (despite the name, it works for videos too)
- `--thinking, -t`: Optional - Enable chain-of-thought reasoning for complex analysis (default: disabled)
- `--output, -o <path>`: Optional - Output file path (JSON format)
- `--stream`: Optional - Stream the response in real-time

### Supported Video Formats

- MP4 (.mp4) - Most widely supported format
- AVI (.avi) - Audio Video Interleave
- MOV (.mov) - QuickTime format
- WebM (.webm) - Web-optimized format
- MKV (.mkv) - Matroska format
- FLV (.flv) - Flash Video format

### When to Use CLI vs SDK

**Use CLI for:**
- Quick video summaries
- One-off video analysis
- Testing video understanding capabilities
- Simple automation scripts
- Generating video descriptions

**Use SDK for:**
- Multi-turn conversations about videos
- Complex video processing pipelines
- Production applications with error handling
- Custom integration with video processing logic
- Batch video processing with custom workflows

## Recommended Approach

For better performance and reliability with local videos, consider:
1. Uploading videos to a CDN and using URLs
2. For shorter videos, convert key frames to images for faster analysis
3. For long videos, consider chunking or sampling at intervals

## Basic Video Understanding Implementation

### Single Video Analysis

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function analyzeVideo(videoUrl, prompt) {
  const zai = await ZAI.create();

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
            type: 'video_url',
            video_url: {
              url: videoUrl
            }
          }
        ]
      }
    ],
    thinking: { type: 'disabled' }
  });

  return response.choices[0]?.message?.content;
}

// Usage examples
const summary = await analyzeVideo(
  'https://example.com/presentation.mp4',
  'Summarize the key points presented in this video'
);

const actionDetection = await analyzeVideo(
  'https://example.com/sports.mp4',
  'Identify and describe all athletic actions performed in this video'
);
```

### Video Scene Understanding

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function understandVideoScenes(videoUrl) {
  const zai = await ZAI.create();

  const prompt = `Analyze this video and provide:
1. Overall summary of the video content
2. Main scenes or segments (with approximate timestamps if possible)
3. Key people or characters and their roles
4. Important actions or events in chronological order
5. Setting and environment description
6. Overall mood or tone`;

  const response = await zai.chat.completions.createVision({
    messages: [
      {
        role: 'user',
        content: [
          { type: 'text', text: prompt },
          { type: 'video_url', video_url: { url: videoUrl } }
        ]
      }
    ],
    thinking: { type: 'enabled' } // Enable for detailed analysis
  });

  return response.choices[0]?.message?.content;
}

// Usage
const sceneAnalysis = await understandVideoScenes(
  'https://example.com/documentary.mp4'
);
```

### Motion and Action Detection

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function detectActions(videoUrl, specificAction = null) {
  const zai = await ZAI.create();

  const prompt = specificAction
    ? `Identify all instances of "${specificAction}" in this video. For each instance, describe when it occurs and provide details about how it's performed.`
    : 'Identify and describe all significant actions and movements in this video. Include who is performing them and when they occur.';

  const response = await zai.chat.completions.createVision({
    messages: [
      {
        role: 'user',
        content: [
          { type: 'text', text: prompt },
          { type: 'video_url', video_url: { url: videoUrl } }
        ]
      }
    ],
    thinking: { type: 'enabled' }
  });

  return response.choices[0]?.message?.content;
}

// Usage
const runningActions = await detectActions(
  'https://example.com/sports.mp4',
  'running'
);

const allActions = await detectActions(
  'https://example.com/activity.mp4'
);
```

### Event Timeline Extraction

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function extractTimeline(videoUrl) {
  const zai = await ZAI.create();

  const prompt = `Create a detailed timeline of events in this video:
- Identify key moments and transitions
- Note approximate timing (beginning, middle, end or specific timestamps if visible)
- Describe what happens at each key point
- Identify any cause-and-effect relationships between events

Format as a chronological list.`;

  const response = await zai.chat.completions.createVision({
    messages: [
      {
        role: 'user',
        content: [
          { type: 'text', text: prompt },
          { type: 'video_url', video_url: { url: videoUrl } }
        ]
      }
    ],
    thinking: { type: 'enabled' }
  });

  return response.choices[0]?.message?.content;
}
```

### Video Content Classification

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function classifyVideo(videoUrl) {
  const zai = await ZAI.create();

  const prompt = `Classify this video content:
1. Primary category (e.g., educational, entertainment, sports, news, tutorial)
2. Sub-category or genre
3. Target audience
4. Content style (professional, casual, documentary, etc.)
5. Key themes or topics
6. Suggested tags (10-15 keywords)

Format your response as structured JSON.`;

  const response = await zai.chat.completions.createVision({
    messages: [
      {
        role: 'user',
        content: [
          { type: 'text', text: prompt },
          { type: 'video_url', video_url: { url: videoUrl } }
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

## Advanced Use Cases

### Multi-turn Video Conversation

```javascript
import ZAI from 'z-ai-web-dev-sdk';

class VideoConversation {
  constructor() {
    this.messages = [];
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  async loadVideo(videoUrl, initialQuestion) {
    this.messages.push({
      role: 'user',
      content: [
        { type: 'text', text: initialQuestion },
        { type: 'video_url', video_url: { url: videoUrl } }
      ]
    });

    return this.getResponse();
  }

  async askFollowUp(question) {
    this.messages.push({
      role: 'user',
      content: [
        { type: 'text', text: question }
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
const conversation = new VideoConversation();
await conversation.initialize();

const initial = await conversation.loadVideo(
  'https://example.com/lecture.mp4',
  'What is the main topic of this lecture?'
);

const followup1 = await conversation.askFollowUp(
  'Can you explain the key concepts mentioned?'
);

const followup2 = await conversation.askFollowUp(
  'What examples were used to illustrate these concepts?'
);
```

### Video Quality Assessment

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function assessVideoQuality(videoUrl) {
  const zai = await ZAI.create();

  const prompt = `Assess the quality of this video:
1. Visual quality (resolution, clarity, lighting) - Rate 1-10
2. Audio quality (if audio is present) - Rate 1-10
3. Camera work (stability, framing, composition) - Rate 1-10
4. Production value (editing, transitions, effects) - Rate 1-10
5. Content clarity (is the message clear?) - Rate 1-10
6. Pacing (too fast, too slow, just right)
7. Technical issues (artifacts, blur, audio sync, etc.)
8. Overall rating - 1-10
9. Specific recommendations for improvement

Provide detailed feedback for each criterion.`;

  const response = await zai.chat.completions.createVision({
    messages: [
      {
        role: 'user',
        content: [
          { type: 'text', text: prompt },
          { type: 'video_url', video_url: { url: videoUrl } }
        ]
      }
    ],
    thinking: { type: 'enabled' }
  });

  return response.choices[0]?.message?.content;
}
```

### Video Content Moderation

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function moderateVideo(videoUrl) {
  const zai = await ZAI.create();

  const prompt = `Review this video for content moderation:
1. Check for any inappropriate or sensitive content
2. Identify any potential safety concerns
3. Note any content that might violate common community guidelines
4. Assess age-appropriateness
5. Identify any copyrighted material visible (logos, brands, music)
6. Overall safety rating: Safe / Caution / Review Required

Provide specific examples for any concerns identified.`;

  const response = await zai.chat.completions.createVision({
    messages: [
      {
        role: 'user',
        content: [
          { type: 'text', text: prompt },
          { type: 'video_url', video_url: { url: videoUrl } }
        ]
      }
    ],
    thinking: { type: 'enabled' }
  });

  return response.choices[0]?.message?.content;
}
```

### Video Transcript Generation (Visual Description)

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function generateVisualTranscript(videoUrl) {
  const zai = await ZAI.create();

  const prompt = `Generate a detailed visual transcript of this video:
- Describe what's happening in each scene
- Note any text that appears on screen
- Describe important visual elements
- Mention any scene changes or transitions
- Include descriptions of people's actions and expressions

Format as a time-based narrative (e.g., "At the beginning...", "Then...", "Finally...").`;

  const response = await zai.chat.completions.createVision({
    messages: [
      {
        role: 'user',
        content: [
          { type: 'text', text: prompt },
          { type: 'video_url', video_url: { url: videoUrl } }
        ]
      }
    ],
    thinking: { type: 'disabled' }
  });

  return response.choices[0]?.message?.content;
}
```

### Sports Video Analysis

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function analyzeSportsVideo(videoUrl, sport = null) {
  const zai = await ZAI.create();

  const prompt = sport
    ? `Analyze this ${sport} video in detail:
1. Identify players and their positions
2. Describe key plays and strategies
3. Note scoring events or important moments
4. Assess player performance
5. Identify any rule violations or fouls
6. Describe the pace and flow of the game`
    : `Analyze this sports video:
1. Identify the sport being played
2. Describe the key actions and plays
3. Note any scoring or significant events
4. Describe player movements and strategies
5. Overall assessment of the game or match`;

  const response = await zai.chat.completions.createVision({
    messages: [
      {
        role: 'user',
        content: [
          { type: 'text', text: prompt },
          { type: 'video_url', video_url: { url: videoUrl } }
        ]
      }
    ],
    thinking: { type: 'enabled' }
  });

  return response.choices[0]?.message?.content;
}
```

### Educational Video Summarization

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function summarizeEducationalVideo(videoUrl) {
  const zai = await ZAI.create();

  const prompt = `Summarize this educational video for students:
1. Main topic or learning objective
2. Key concepts explained (in order)
3. Important definitions or terminology
4. Examples used to illustrate concepts
5. Visual aids or demonstrations shown
6. Key takeaways or conclusions
7. Suggested review points

Format as a study guide.`;

  const response = await zai.chat.completions.createVision({
    messages: [
      {
        role: 'user',
        content: [
          { type: 'text', text: prompt },
          { type: 'video_url', video_url: { url: videoUrl } }
        ]
      }
    ],
    thinking: { type: 'enabled' }
  });

  return response.choices[0]?.message?.content;
}
```

## Batch Video Processing

### Process Multiple Videos

```javascript
import ZAI from 'z-ai-web-dev-sdk';

class VideoBatchProcessor {
  constructor() {
    this.zai = null;
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  async processVideo(videoUrl, prompt) {
    const response = await this.zai.chat.completions.createVision({
      messages: [
        {
          role: 'user',
          content: [
            { type: 'text', text: prompt },
            { type: 'video_url', video_url: { url: videoUrl } }
          ]
        }
      ],
      thinking: { type: 'disabled' }
    });

    return response.choices[0]?.message?.content;
  }

  async processBatch(videoUrls, prompt) {
    const results = [];
    
    for (const videoUrl of videoUrls) {
      try {
        console.log(`Processing: ${videoUrl}`);
        const result = await this.processVideo(videoUrl, prompt);
        results.push({ videoUrl, success: true, result });
        
        // Add delay to avoid rate limiting
        await new Promise(resolve => setTimeout(resolve, 1000));
      } catch (error) {
        results.push({ 
          videoUrl, 
          success: false, 
          error: error.message 
        });
      }
    }

    return results;
  }
}

// Usage
const processor = new VideoBatchProcessor();
await processor.initialize();

const videos = [
  'https://example.com/video1.mp4',
  'https://example.com/video2.mp4',
  'https://example.com/video3.mp4'
];

const results = await processor.processBatch(
  videos,
  'Provide a brief summary of this video suitable for a content catalog'
);
```

## Best Practices

### 1. Video Preparation
- Use standard video formats (MP4, MOV, AVI)
- Ensure videos are accessible via public URLs or properly encoded
- For long videos, consider creating shorter clips for specific analysis
- Optimize video size for faster processing
- Ensure good lighting and audio quality in source videos

### 2. Prompt Engineering for Videos
- Be specific about temporal aspects ("beginning", "throughout", "at the end")
- Mention what type of analysis you need (actions, events, scenes, etc.)
- For long videos, ask for summaries or key moments
- Use thinking mode for complex temporal reasoning
- Specify if you need chronological or thematic organization

### 3. Error Handling

```javascript
async function safeVideoAnalysis(videoUrl, prompt) {
  try {
    const zai = await ZAI.create();
    
    const response = await zai.chat.completions.createVision({
      messages: [
        {
          role: 'user',
          content: [
            { type: 'text', text: prompt },
            { type: 'video_url', video_url: { url: videoUrl } }
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
    console.error('Video analysis error:', error);
    return {
      success: false,
      error: error.message
    };
  }
}
```

### 4. Performance Optimization
- Cache SDK instance for batch processing
- Implement request throttling (add delays between requests)
- Process videos asynchronously when possible
- For very long videos, consider analyzing at specific intervals
- Use appropriate thinking mode (disabled for simple descriptions, enabled for complex analysis)

### 5. Security Considerations
- Validate video URLs before processing
- Implement rate limiting for public APIs
- Sanitize user-provided video URLs
- Never expose SDK credentials in client-side code
- Implement content moderation for user-uploaded videos
- Consider video file size limits

## Common Use Cases

1. **Content Moderation**: Automatically review video uploads for policy compliance
2. **Video Cataloging**: Generate descriptions and tags for video libraries
3. **Sports Analysis**: Analyze games, identify plays, assess performance
4. **Educational Content**: Summarize lectures, create study guides
5. **Security & Surveillance**: Detect events, track activities (with appropriate authorization)
6. **Quality Control**: Assess video production quality
7. **Social Media**: Generate video captions and descriptions
8. **Training & Documentation**: Analyze training videos, create documentation
9. **Event Recording**: Summarize meetings, conferences, presentations
10. **Entertainment**: Analyze films, shows for content, themes, scenes

## Integration Examples

### Express.js API Endpoint

```javascript
import express from 'express';
import ZAI from 'z-ai-web-dev-sdk';

const app = express();
app.use(express.json());

let zaiInstance;

async function initZAI() {
  zaiInstance = await ZAI.create();
}

// Analyze video from URL
app.post('/api/analyze-video', async (req, res) => {
  try {
    const { videoUrl, prompt } = req.body;

    if (!videoUrl || !prompt) {
      return res.status(400).json({ 
        error: 'videoUrl and prompt are required' 
      });
    }

    const response = await zaiInstance.chat.completions.createVision({
      messages: [
        {
          role: 'user',
          content: [
            { type: 'text', text: prompt },
            { type: 'video_url', video_url: { url: videoUrl } }
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

// Get video summary
app.post('/api/video-summary', async (req, res) => {
  try {
    const { videoUrl } = req.body;

    if (!videoUrl) {
      return res.status(400).json({ error: 'videoUrl is required' });
    }

    const prompt = 'Provide a comprehensive summary of this video including: 1) Main content/topic, 2) Key events in chronological order, 3) Important people or subjects, 4) Overall takeaway.';

    const response = await zaiInstance.chat.completions.createVision({
      messages: [
        {
          role: 'user',
          content: [
            { type: 'text', text: prompt },
            { type: 'video_url', video_url: { url: videoUrl } }
          ]
        }
      ],
      thinking: { type: 'enabled' }
    });

    res.json({
      success: true,
      summary: response.choices[0]?.message?.content
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
    console.log('Video understanding API running on port 3000');
  });
});
```

### Next.js API Route

```javascript
// pages/api/video-understand.js
import ZAI from 'z-ai-web-dev-sdk';

let zaiInstance = null;

async function getZAI() {
  if (!zaiInstance) {
    zaiInstance = await ZAI.create();
  }
  return zaiInstance;
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { videoUrl, prompt, enableThinking = false } = req.body;

    if (!videoUrl || !prompt) {
      return res.status(400).json({ 
        error: 'videoUrl and prompt are required' 
      });
    }

    const zai = await getZAI();

    const response = await zai.chat.completions.createVision({
      messages: [
        {
          role: 'user',
          content: [
            { type: 'text', text: prompt },
            { type: 'video_url', video_url: { url: videoUrl } }
          ]
        }
      ],
      thinking: { type: enableThinking ? 'enabled' : 'disabled' }
    });

    res.status(200).json({
      success: true,
      analysis: response.choices[0]?.message?.content
    });
  } catch (error) {
    console.error('Error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
}
```

## Troubleshooting

**Issue**: "SDK must be used in backend"
- **Solution**: Ensure z-ai-web-dev-sdk is only imported and used in server-side code, never in client/browser code

**Issue**: Video not loading or being analyzed
- **Solution**: Verify the video URL is accessible, returns correct MIME type, and is in a supported format

**Issue**: Inaccurate temporal analysis
- **Solution**: Enable thinking mode for complex temporal reasoning, provide more specific prompts about time/sequence

**Issue**: Slow response times for videos
- **Solution**: Videos take longer to process than images; consider shorter clips or sampling for long videos

**Issue**: Missing details from video
- **Solution**: Be more specific in your prompt, ask about particular time segments or aspects

**Issue**: Video format not supported
- **Solution**: Convert video to MP4 (most widely supported), check that URL returns proper video MIME type

## Remember

- Always use z-ai-web-dev-sdk in backend code only
- The SDK is already installed - import as shown in examples
- Use `video_url` content type for video files
- Video analysis takes longer than image analysis - be patient
- Enable thinking mode for complex temporal reasoning and event detection
- Structure prompts to include temporal information (beginning, middle, end)
- Handle errors gracefully in production
- Implement rate limiting and delays for batch processing
- Validate and sanitize user inputs
- Consider privacy and security when processing user videos
- For very long videos, consider analyzing specific segments or key frames
