---
name: Video Generation
description: Implement AI-powered video generation capabilities using the z-ai-web-dev-sdk. Use this skill when the user needs to generate videos from text prompts or images, create video content programmatically, or build applications that produce video outputs. Supports asynchronous task management with status polling and result retrieval.
license: MIT
---

# Video Generation Skill

This skill guides the implementation of video generation functionality using the z-ai-web-dev-sdk package, enabling AI models to create videos from text descriptions or images through asynchronous task processing.

## Skills Path

**Skill Location**: `{project_path}/skills/video-generation`

This skill is located at the above path in your project.

**Reference Scripts**: Example test scripts are available in the `{Skill Location}/scripts/` directory for quick testing and reference. See `{Skill Location}/scripts/video.ts` for a working example.

## Overview

Video Generation allows you to build applications that can create video content from text prompts or images, with customizable parameters like resolution, frame rate, duration, and quality settings. The API uses an asynchronous task model where you create a task and poll for results.

**IMPORTANT**: z-ai-web-dev-sdk MUST be used in backend code only. Never use it in client-side code.

## Prerequisites

The z-ai-web-dev-sdk package is already installed. Import it as shown in the examples below.

## CLI Usage (For Simple Tasks)

For simple video generation tasks, you can use the z-ai CLI instead of writing code. The CLI handles task creation and polling automatically, making it ideal for quick tests and simple automation.

### Basic Text-to-Video

```bash
# Generate video with automatic polling
z-ai video --prompt "A cat playing with a ball" --poll

# Using short options
z-ai video -p "Beautiful landscape with mountains" --poll
```

### Custom Quality and Settings

```bash
# Quality mode (speed or quality)
z-ai video -p "Ocean waves at sunset" --quality quality --poll

# Custom resolution and FPS
z-ai video \
  -p "City timelapse" \
  --size "1920x1080" \
  --fps 60 \
  --poll

# Custom duration (5 or 10 seconds)
z-ai video -p "Fireworks display" --duration 10 --poll
```

### Image-to-Video

**IMPORTANT**: For `image_url` parameter, it is **strongly recommended to use base64-encoded image data** instead of URLs. This approach is more reliable and avoids potential network issues or access restrictions.

**Note**: Match the MIME type in the data URI to your actual image format (image/jpeg, image/png, image/webp, etc.) to avoid decoding issues.

```bash
# Generate video from single image using base64 (RECOMMENDED)
# Convert your image to base64 with correct MIME type

# For PNG images
IMAGE_BASE64=$(base64 -i image.png)
z-ai video \
  --image-url "data:image/png;base64,${IMAGE_BASE64}" \
  --prompt "Make the scene come alive" \
  --poll

# For JPEG images
IMAGE_BASE64=$(base64 -i photo.jpg)
z-ai video \
  --image-url "data:image/jpeg;base64,${IMAGE_BASE64}" \
  --prompt "Make the scene come alive" \
  --poll

# For WebP images
IMAGE_BASE64=$(base64 -i image.webp)
z-ai video \
  --image-url "data:image/webp;base64,${IMAGE_BASE64}" \
  --prompt "Make the scene come alive" \
  --poll

# Using URL (less recommended, may have reliability issues)
z-ai video \
  -i "https://example.com/photo.jpg" \
  -p "Add motion to this scene" \
  --poll
```

### First-Last Frame Mode

**IMPORTANT**: For best reliability, use base64-encoded images instead of URLs. Ensure the MIME type matches your actual image format.

```bash
# Generate video between two frames using base64 (RECOMMENDED)
# Make sure to use the correct MIME type for each image

# Example with PNG images
START_BASE64=$(base64 -i start.png)
END_BASE64=$(base64 -i end.png)
z-ai video \
  --image-url "data:image/png;base64,${START_BASE64},data:image/png;base64,${END_BASE64}" \
  --prompt "Smooth transition between frames" \
  --poll

# Example with JPEG images
START_BASE64=$(base64 -i start.jpg)
END_BASE64=$(base64 -i end.jpg)
z-ai video \
  --image-url "data:image/jpeg;base64,${START_BASE64},data:image/jpeg;base64,${END_BASE64}" \
  --prompt "Smooth transition between frames" \
  --poll

# Using URLs (less recommended)
z-ai video \
  --image-url "https://example.com/start.png,https://example.com/end.png" \
  --prompt "Smooth transition between frames" \
  --poll
```

### With Audio Generation

```bash
# Generate video with AI-generated audio effects
z-ai video \
  -p "Thunder storm approaching" \
  --with-audio \
  --poll
```

### Save Output

```bash
# Save task result to JSON file
z-ai video \
  -p "Sunrise over mountains" \
  --poll \
  -o video_result.json
```

### Custom Polling Parameters

```bash
# Customize polling behavior
z-ai video \
  -p "Dancing robot" \
  --poll \
  --poll-interval 10 \
  --max-polls 30

# Create task without polling (get task ID)
z-ai video -p "Abstract art animation" -o task.json
```

### CLI Parameters

- `--prompt, -p <text>`: Optional - Text description of the video
- `--image-url, -i <data>`: Optional - **Preferably base64-encoded image data** (e.g., "data:image/png;base64,iVBORw..."). URLs are also supported but less recommended. For two images, use comma-separated values.
- `--quality, -q <mode>`: Optional - Output mode: `speed` or `quality` (default: speed)
- `--with-audio`: Optional - Generate AI audio effects (default: false)
- `--size, -s <resolution>`: Optional - Video resolution (e.g., "1920x1080")
- `--fps <rate>`: Optional - Frame rate: 30 or 60 (default: 30)
- `--duration, -d <seconds>`: Optional - Duration: 5 or 10 seconds (default: 5)
- `--model, -m <model>`: Optional - Model name to use
- `--poll`: Optional - Auto-poll until task completes
- `--poll-interval <seconds>`: Optional - Polling interval (default: 5)
- `--max-polls <count>`: Optional - Maximum poll attempts (default: 60)
- `--output, -o <path>`: Optional - Output file path (JSON format)

### Supported Resolutions

- `1024x1024`
- `768x1344`
- `864x1152`
- `1344x768`
- `1152x864`
- `1440x720`
- `720x1440`
- `1920x1080` (and other standard resolutions)

### Checking Task Status Later

If you create a task without `--poll`, you can check its status later:

```bash
# Get the task ID from the initial response
z-ai async-result --id "task-id-here" --poll
```

### When to Use CLI vs SDK

**Use CLI for:**
- Quick video generation tests
- Simple one-off video creation
- Command-line automation scripts
- Testing different prompts and settings

**Use SDK for:**
- Batch video generation with custom logic
- Integration with web applications
- Custom task queue management
- Production applications with complex workflows

## Video Generation Workflow

Video generation follows a two-step asynchronous pattern:

1. **Create Task**: Submit video generation request and receive a task ID
2. **Poll Results**: Query the task status until completion and retrieve the video URL

## Basic Video Generation Implementation

### Simple Text-to-Video Generation

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function generateVideo(prompt) {
  try {
    const zai = await ZAI.create();

    // Create video generation task
    const task = await zai.video.generations.create({
      prompt: prompt,
      quality: 'speed', // 'speed' or 'quality'
      with_audio: false,
      size: '1920x1080',
      fps: 30,
      duration: 5
    });

    console.log('Task ID:', task.id);
    console.log('Task Status:', task.task_status);

    // Poll for results
    let result = await zai.async.result.query(task.id);
    let pollCount = 0;
    const maxPolls = 60;
    const pollInterval = 5000; // 5 seconds

    while (result.task_status === 'PROCESSING' && pollCount < maxPolls) {
      pollCount++;
      console.log(`Polling ${pollCount}/${maxPolls}: Status is ${result.task_status}`);
      await new Promise(resolve => setTimeout(resolve, pollInterval));
      result = await zai.async.result.query(task.id);
    }

    if (result.task_status === 'SUCCESS') {
      // Get video URL from multiple possible fields
      const videoUrl = result.video_result?.[0]?.url ||
                      result.video_url ||
                      result.url ||
                      result.video;
      console.log('Video URL:', videoUrl);
      return videoUrl;
    } else {
      console.log('Task failed or still processing');
      return null;
    }
  } catch (error) {
    console.error('Video generation failed:', error.message);
    throw error;
  }
}

// Usage
const videoUrl = await generateVideo('A cat is playing with a ball.');
console.log('Generated video:', videoUrl);
```

### Image-to-Video Generation

**IMPORTANT**: The `image_url` parameter accepts both base64-encoded image data and URLs, but **base64 encoding is strongly recommended** for better reliability and to avoid network-related issues.

**Critical**: Always match the MIME type in your base64 data URI to the actual image format to prevent decoding errors.

```javascript
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';
import path from 'path';

// Helper function to detect MIME type from file extension
function getMimeType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const mimeTypes = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.bmp': 'image/bmp'
  };
  return mimeTypes[ext] || 'image/jpeg'; // Default to JPEG if unknown
}

async function generateVideoFromImage(imagePath, prompt) {
  const zai = await ZAI.create();

  // Method 1: Using base64-encoded image (RECOMMENDED)
  // Automatically detect MIME type from file extension
  const imageBuffer = fs.readFileSync(imagePath);
  const mimeType = getMimeType(imagePath);
  const base64Image = `data:${mimeType};base64,${imageBuffer.toString('base64')}`;

  const task = await zai.video.generations.create({
    image_url: base64Image,  // Base64 data string with correct MIME type
    prompt: prompt,
    quality: 'quality',
    duration: 5,
    fps: 30
  });

  return task;
}

// Method 2: Using URL (less recommended)
async function generateVideoFromImageUrl(imageUrl, prompt) {
  const zai = await ZAI.create();

  const task = await zai.video.generations.create({
    image_url: imageUrl,  // URL string
    prompt: prompt,
    quality: 'quality',
    duration: 5,
    fps: 30
  });

  return task;
}

// Usage examples
const task1 = await generateVideoFromImage(
  './images/photo.jpg',  // Works with JPEG
  'Animate this scene with gentle motion'
);

const task2 = await generateVideoFromImage(
  './images/graphic.png',  // Works with PNG
  'Add dynamic movement'
);

const task3 = await generateVideoFromImage(
  './images/animation.webp',  // Works with WebP
  'Bring this to life'
);
```

### Image-to-Video with Start and End Frames

**IMPORTANT**: For keyframe mode, base64-encoded images are **highly recommended** over URLs to ensure consistent and reliable video generation. Always use the correct MIME type for each image.

```javascript
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';
import path from 'path';

// Helper function to detect MIME type from file extension
function getMimeType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const mimeTypes = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.bmp': 'image/bmp'
  };
  return mimeTypes[ext] || 'image/jpeg';
}

async function generateVideoWithKeyframes(startImagePath, endImagePath, prompt) {
  const zai = await ZAI.create();

  // Method 1: Using base64-encoded images (RECOMMENDED)
  // Automatically detect MIME type for each image
  const startBuffer = fs.readFileSync(startImagePath);
  const endBuffer = fs.readFileSync(endImagePath);
  
  const startMimeType = getMimeType(startImagePath);
  const endMimeType = getMimeType(endImagePath);
  
  const startBase64 = `data:${startMimeType};base64,${startBuffer.toString('base64')}`;
  const endBase64 = `data:${endMimeType};base64,${endBuffer.toString('base64')}`;

  const task = await zai.video.generations.create({
    image_url: [startBase64, endBase64],  // Array of base64 strings with correct MIME types
    prompt: prompt,
    quality: 'quality',
    duration: 10,
    fps: 30
  });

  console.log('Task created with keyframes:', task.id);
  return task;
}

// Method 2: Using URLs (less recommended)
async function generateVideoWithKeyframesUrl(startImageUrl, endImageUrl, prompt) {
  const zai = await ZAI.create();

  const task = await zai.video.generations.create({
    image_url: [startImageUrl, endImageUrl],  // Array of URL strings
    prompt: prompt,
    quality: 'quality',
    duration: 10,
    fps: 30
  });

  console.log('Task created with keyframes:', task.id);
  return task;
}

// Usage examples with different formats
const task1 = await generateVideoWithKeyframes(
  './frames/start.jpg',  // JPEG start frame
  './frames/end.jpg',    // JPEG end frame
  'Smooth transition between these scenes'
);

const task2 = await generateVideoWithKeyframes(
  './frames/start.png',  // PNG start frame
  './frames/end.webp',   // WebP end frame - different formats work!
  'Morphing effect between images'
);
```

## Asynchronous Result Management

### Query Task Status

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function checkTaskStatus(taskId) {
  try {
    const zai = await ZAI.create();
    const result = await zai.async.result.query(taskId);

    console.log('Task Status:', result.task_status);

    if (result.task_status === 'SUCCESS') {
      // Extract video URL from result
      const videoUrl = result.video_result?.[0]?.url ||
                      result.video_url ||
                      result.url ||
                      result.video;
      if (videoUrl) {
        console.log('Video URL:', videoUrl);
        return { success: true, url: videoUrl };
      }
    } else if (result.task_status === 'PROCESSING') {
      console.log('Task is still processing');
      return { success: false, status: 'processing' };
    } else if (result.task_status === 'FAIL') {
      console.log('Task failed');
      return { success: false, status: 'failed' };
    }
  } catch (error) {
    console.error('Query failed:', error.message);
    throw error;
  }
}

// Usage
const status = await checkTaskStatus('your-task-id-here');
```

### Polling with Exponential Backoff

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function pollWithBackoff(taskId) {
  const zai = await ZAI.create();
  
  let pollInterval = 5000; // Start with 5 seconds
  const maxInterval = 30000; // Max 30 seconds
  const maxPolls = 40;
  let pollCount = 0;

  while (pollCount < maxPolls) {
    const result = await zai.async.result.query(taskId);
    pollCount++;

    if (result.task_status === 'SUCCESS') {
      const videoUrl = result.video_result?.[0]?.url ||
                      result.video_url ||
                      result.url ||
                      result.video;
      return { success: true, url: videoUrl };
    }

    if (result.task_status === 'FAIL') {
      return { success: false, error: 'Task failed' };
    }

    // Exponential backoff
    console.log(`Poll ${pollCount}: Waiting ${pollInterval / 1000}s...`);
    await new Promise(resolve => setTimeout(resolve, pollInterval));
    pollInterval = Math.min(pollInterval * 1.5, maxInterval);
  }

  return { success: false, error: 'Timeout' };
}
```

## Advanced Use Cases

### Video Generation Queue Manager

```javascript
import ZAI from 'z-ai-web-dev-sdk';

class VideoGenerationQueue {
  constructor() {
    this.tasks = new Map();
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  async createVideo(params) {
    const task = await this.zai.video.generations.create(params);
    
    this.tasks.set(task.id, {
      taskId: task.id,
      status: task.task_status,
      params: params,
      createdAt: new Date()
    });

    return task.id;
  }

  async checkTask(taskId) {
    const result = await this.zai.async.result.query(taskId);
    
    const taskInfo = this.tasks.get(taskId);
    if (taskInfo) {
      taskInfo.status = result.task_status;
      taskInfo.lastChecked = new Date();
      
      if (result.task_status === 'SUCCESS') {
        taskInfo.videoUrl = result.video_result?.[0]?.url ||
                          result.video_url ||
                          result.url ||
                          result.video;
      }
    }

    return result;
  }

  async pollTask(taskId, options = {}) {
    const maxPolls = options.maxPolls || 60;
    const pollInterval = options.pollInterval || 5000;
    
    let pollCount = 0;

    while (pollCount < maxPolls) {
      const result = await this.checkTask(taskId);
      
      if (result.task_status === 'SUCCESS' || result.task_status === 'FAIL') {
        return result;
      }

      pollCount++;
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    throw new Error('Task polling timeout');
  }

  getTask(taskId) {
    return this.tasks.get(taskId);
  }

  getAllTasks() {
    return Array.from(this.tasks.values());
  }
}

// Usage
const queue = new VideoGenerationQueue();
await queue.initialize();

const taskId = await queue.createVideo({
  prompt: 'A sunset over the ocean',
  quality: 'quality',
  duration: 5
});

const result = await queue.pollTask(taskId);
console.log('Video ready:', result.video_result?.[0]?.url);
```

### Batch Video Generation

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function generateMultipleVideos(prompts) {
  const zai = await ZAI.create();
  const tasks = [];

  // Create all tasks
  for (const prompt of prompts) {
    const task = await zai.video.generations.create({
      prompt: prompt,
      quality: 'speed',
      duration: 5
    });
    tasks.push({ taskId: task.id, prompt: prompt });
  }

  console.log(`Created ${tasks.length} video generation tasks`);

  // Poll all tasks
  const results = [];
  for (const task of tasks) {
    const result = await pollTaskUntilComplete(zai, task.taskId);
    results.push({
      prompt: task.prompt,
      taskId: task.taskId,
      ...result
    });
  }

  return results;
}

async function pollTaskUntilComplete(zai, taskId) {
  let pollCount = 0;
  const maxPolls = 60;

  while (pollCount < maxPolls) {
    const result = await zai.async.result.query(taskId);
    
    if (result.task_status === 'SUCCESS') {
      return {
        success: true,
        url: result.video_result?.[0]?.url ||
             result.video_url ||
             result.url ||
             result.video
      };
    }

    if (result.task_status === 'FAIL') {
      return { success: false, error: 'Generation failed' };
    }

    pollCount++;
    await new Promise(resolve => setTimeout(resolve, 5000));
  }

  return { success: false, error: 'Timeout' };
}

// Usage
const prompts = [
  'A cat playing with yarn',
  'A dog running in a park',
  'A bird flying in the sky'
];

const videos = await generateMultipleVideos(prompts);
videos.forEach(video => {
  console.log(`${video.prompt}: ${video.success ? video.url : video.error}`);
});
```

## Configuration Parameters

### Video Generation Parameters

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `prompt` | string | Optional* | Text description of the video | - |
| `image_url` | string \| string[] | Optional* | Image URL(s) for generation | - |
| `quality` | string | Optional | Output mode: `'speed'` or `'quality'` | `'speed'` |
| `with_audio` | boolean | Optional | Generate AI audio effects | `false` |
| `size` | string | Optional | Video resolution (e.g., `'1920x1080'`) | - |
| `fps` | number | Optional | Frame rate: `30` or `60` | `30` |
| `duration` | number | Optional | Duration in seconds: `5` or `10` | `5` |
| `model` | string | Optional | Model name | - |

*Note: At least one of `prompt` or `image_url` must be provided.

### Image URL Formats

```javascript
// Single image (starting frame)
image_url: 'https://example.com/image.jpg'

// Multiple images (start and end frames)
image_url: [
  'https://example.com/start.jpg',
  'https://example.com/end.jpg'
]
```

### Task Status Values

- `PROCESSING`: Task is being processed
- `SUCCESS`: Task completed successfully
- `FAIL`: Task failed

## Response Formats

### Task Creation Response

```json
{
  "id": "task-12345",
  "task_status": "PROCESSING",
  "model": "video-model-v1"
}
```

### Task Query Response (Success)

```json
{
  "task_status": "SUCCESS",
  "model": "video-model-v1",
  "request_id": "req-67890",
  "video_result": [
    {
      "url": "https://cdn.example.com/generated-video.mp4"
    }
  ]
}
```

### Task Query Response (Processing)

```json
{
  "task_status": "PROCESSING",
  "id": "task-12345",
  "model": "video-model-v1"
}
```

## Best Practices

### 1. Polling Strategy

```javascript
// Recommended polling implementation
async function smartPoll(zai, taskId) {
  // Check immediately (some tasks complete fast)
  let result = await zai.async.result.query(taskId);
  
  if (result.task_status !== 'PROCESSING') {
    return result;
  }

  // Start polling with reasonable intervals
  let interval = 5000; // 5 seconds
  let maxPolls = 60; // 5 minutes total
  
  for (let i = 0; i < maxPolls; i++) {
    await new Promise(resolve => setTimeout(resolve, interval));
    result = await zai.async.result.query(taskId);
    
    if (result.task_status !== 'PROCESSING') {
      return result;
    }
  }
  
  throw new Error('Task timeout');
}
```

### 2. Error Handling

```javascript
async function safeVideoGeneration(params) {
  try {
    const zai = await ZAI.create();
    
    // Validate parameters
    if (!params.prompt && !params.image_url) {
      throw new Error('Either prompt or image_url is required');
    }
    
    const task = await zai.video.generations.create(params);
    const result = await smartPoll(zai, task.id);
    
    if (result.task_status === 'SUCCESS') {
      const videoUrl = result.video_result?.[0]?.url ||
                      result.video_url ||
                      result.url ||
                      result.video;
      
      if (!videoUrl) {
        throw new Error('Video URL not found in response');
      }
      
      return {
        success: true,
        url: videoUrl,
        taskId: task.id
      };
    } else {
      return {
        success: false,
        error: 'Video generation failed',
        taskId: task.id
      };
    }
  } catch (error) {
    console.error('Video generation error:', error);
    return {
      success: false,
      error: error.message
    };
  }
}
```

### 3. Resource Management

- Cache the ZAI instance for multiple video generations
- Implement task ID storage for long-running operations
- Clean up completed tasks from your tracking system
- Implement timeout mechanisms to prevent infinite polling

### 4. Quality vs Speed Trade-offs

```javascript
// Fast generation for previews or high volume
const quickVideo = await zai.video.generations.create({
  prompt: 'A cat playing',
  quality: 'speed',
  duration: 5,
  fps: 30
});

// High quality for final production
const qualityVideo = await zai.video.generations.create({
  prompt: 'A cat playing',
  quality: 'quality',
  duration: 10,
  fps: 60,
  size: '1920x1080'
});
```

### 5. Security Considerations

- Validate all user inputs before creating tasks
- Implement rate limiting for video generation endpoints
- Store and validate task IDs securely
- Never expose SDK credentials in client-side code
- Set reasonable timeouts for polling operations

## Common Use Cases

1. **Social Media Content**: Generate short video clips for posts and stories
2. **Marketing Materials**: Create product demonstration videos
3. **Education**: Generate visual explanations and tutorials
4. **Entertainment**: Create animated content from descriptions
5. **Prototyping**: Quick video mockups for presentations
6. **Game Development**: Generate cutscene or background videos
7. **Content Automation**: Bulk video generation for various purposes

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

// Create video generation task
app.post('/api/video/create', async (req, res) => {
  try {
    const { prompt, image_url, quality, duration } = req.body;

    if (!prompt && !image_url) {
      return res.status(400).json({ 
        error: 'Either prompt or image_url is required' 
      });
    }

    // Note: image_url should preferably be base64-encoded image data
    // Format: "data:image/jpeg;base64,..." or array of such strings
    // URLs are also supported but less recommended
    const task = await zaiInstance.video.generations.create({
      prompt,
      image_url,  // Accepts base64 data or URL
      quality: quality || 'speed',
      duration: duration || 5,
      fps: 30
    });

    res.json({
      success: true,
      taskId: task.id,
      status: task.task_status
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Query task status
app.get('/api/video/status/:taskId', async (req, res) => {
  try {
    const { taskId } = req.params;
    const result = await zaiInstance.async.result.query(taskId);

    const response = {
      taskId: taskId,
      status: result.task_status
    };

    if (result.task_status === 'SUCCESS') {
      response.videoUrl = result.video_result?.[0]?.url ||
                         result.video_url ||
                         result.url ||
                         result.video;
    }

    res.json(response);
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

initZAI().then(() => {
  app.listen(3000, () => {
    console.log('Video generation API running on port 3000');
  });
});
```

### WebSocket Real-time Updates

```javascript
import WebSocket from 'ws';
import ZAI from 'z-ai-web-dev-sdk';

const wss = new WebSocket.Server({ port: 8080 });
let zaiInstance;

async function initZAI() {
  zaiInstance = await ZAI.create();
}

wss.on('connection', (ws) => {
  ws.on('message', async (message) => {
    try {
      const data = JSON.parse(message);

      if (data.action === 'generate') {
        // Create task
        const task = await zaiInstance.video.generations.create(data.params);
        
        ws.send(JSON.stringify({
          type: 'task_created',
          taskId: task.id
        }));

        // Poll for results and send updates
        pollAndNotify(ws, task.id);
      }
    } catch (error) {
      ws.send(JSON.stringify({
        type: 'error',
        message: error.message
      }));
    }
  });
});

async function pollAndNotify(ws, taskId) {
  let pollCount = 0;
  const maxPolls = 60;

  while (pollCount < maxPolls) {
    const result = await zaiInstance.async.result.query(taskId);
    
    ws.send(JSON.stringify({
      type: 'status_update',
      taskId: taskId,
      status: result.task_status
    }));

    if (result.task_status === 'SUCCESS') {
      ws.send(JSON.stringify({
        type: 'complete',
        taskId: taskId,
        videoUrl: result.video_result?.[0]?.url ||
                 result.video_url ||
                 result.url ||
                 result.video
      }));
      break;
    }

    if (result.task_status === 'FAIL') {
      ws.send(JSON.stringify({
        type: 'failed',
        taskId: taskId
      }));
      break;
    }

    pollCount++;
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
}

initZAI();
```

## Troubleshooting

**Issue**: "SDK must be used in backend"
- **Solution**: Ensure z-ai-web-dev-sdk is only imported and used in server-side code

**Issue**: Task stays in PROCESSING status indefinitely
- **Solution**: Implement proper timeout mechanisms and consider the video complexity and duration

**Issue**: Video URL not found in response
- **Solution**: Check multiple possible response fields (video_result, video_url, url, video) as shown in examples

**Issue**: Task fails immediately
- **Solution**: Verify that parameters meet requirements (valid prompt/image_url, supported values for quality/fps/duration)

**Issue**: Slow video generation
- **Solution**: Use 'speed' quality mode, reduce duration/fps, or consider simpler prompts

**Issue**: Polling timeout
- **Solution**: Increase maxPolls value or pollInterval based on video duration and quality settings

## Performance Tips

1. **Use appropriate quality settings**: Choose 'speed' for quick results, 'quality' for final production
2. **Start with shorter durations**: Test with 5-second videos before generating longer content
3. **Implement intelligent polling**: Use exponential backoff to reduce API calls
4. **Cache ZAI instance**: Reuse the same instance for multiple video generations
5. **Parallel processing**: Create multiple tasks simultaneously and poll them independently
6. **Monitor and log**: Track task completion times to optimize your polling strategy

## Remember

- Always use z-ai-web-dev-sdk in backend code only
- Video generation is asynchronous - always implement proper polling
- Check multiple response fields for video URL to ensure compatibility
- Implement timeouts to prevent infinite polling loops
- Handle all three task statuses: PROCESSING, SUCCESS, and FAIL
- Consider rate limits and implement appropriate delays between requests
- The SDK is already installed - import as shown in examples
