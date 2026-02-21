---
name: TTS
description: Implement text-to-speech (TTS) capabilities using the z-ai-web-dev-sdk. Use this skill when the user needs to convert text into natural-sounding speech, create audio content, build voice-enabled applications, or generate spoken audio files. Supports multiple voices, adjustable speed, and various audio formats.
license: MIT
---

# TTS (Text to Speech) Skill

This skill guides the implementation of text-to-speech (TTS) functionality using the z-ai-web-dev-sdk package, enabling conversion of text into natural-sounding speech audio.

## Skills Path

**Skill Location**: `{project_path}/skills/TTS`

This skill is located at the above path in your project.

**Reference Scripts**: Example test scripts are available in the `{Skill Location}/scripts/` directory for quick testing and reference. See `{Skill Location}/scripts/tts.ts` for a working example.

## Overview

Text-to-Speech allows you to build applications that generate spoken audio from text input, supporting various voices, speeds, and output formats for diverse use cases.

**IMPORTANT**: z-ai-web-dev-sdk MUST be used in backend code only. Never use it in client-side code.

## API Limitations and Constraints

Before implementing TTS functionality, be aware of these important limitations:

### Input Text Constraints
- **Maximum length**: 1024 characters per request
- Text exceeding this limit must be split into smaller chunks

### Audio Parameters
- **Speed range**: 0.5 to 2.0
  - 0.5 = half speed (slower)
  - 1.0 = normal speed (default)
  - 2.0 = double speed (faster)
- **Volume range**: Greater than 0, up to 10
  - Default: 1.0
  - Values must be greater than 0 (exclusive) and up to 10 (inclusive)

### Format and Streaming
- **Streaming limitation**: When `stream: true` is enabled, only `pcm` format is supported
- **Non-streaming**: Supports `wav`, `pcm`, and `mp3` formats
- **Sample rate**: 24000 Hz (recommended)

### Best Practice for Long Text
```javascript
function splitTextIntoChunks(text, maxLength = 1000) {
  const chunks = [];
  const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
  
  let currentChunk = '';
  for (const sentence of sentences) {
    if ((currentChunk + sentence).length <= maxLength) {
      currentChunk += sentence;
    } else {
      if (currentChunk) chunks.push(currentChunk.trim());
      currentChunk = sentence;
    }
  }
  if (currentChunk) chunks.push(currentChunk.trim());
  
  return chunks;
}
```

## Prerequisites

The z-ai-web-dev-sdk package is already installed. Import it as shown in the examples below.

## CLI Usage (For Simple Tasks)

For simple text-to-speech conversions, you can use the z-ai CLI instead of writing code. This is ideal for quick audio generation, testing voices, or simple automation.

### Basic TTS

```bash
# Convert text to speech (default WAV format)
z-ai tts --input "Hello, world" --output ./hello.wav

# Using short options
z-ai tts -i "Hello, world" -o ./hello.wav
```

### Different Voices and Speed

```bash
# Use specific voice
z-ai tts -i "Welcome to our service" -o ./welcome.wav --voice tongtong

# Adjust speech speed (0.5-2.0)
z-ai tts -i "This is faster speech" -o ./fast.wav --speed 1.5

# Slower speech
z-ai tts -i "This is slower speech" -o ./slow.wav --speed 0.8
```

### Different Output Formats

```bash
# MP3 format
z-ai tts -i "Hello World" -o ./hello.mp3 --format mp3

# WAV format (default)
z-ai tts -i "Hello World" -o ./hello.wav --format wav

# PCM format
z-ai tts -i "Hello World" -o ./hello.pcm --format pcm
```

### Streaming Output

```bash
# Stream audio generation
z-ai tts -i "This is a longer text that will be streamed" -o ./stream.wav --stream
```

### CLI Parameters

- `--input, -i <text>`: **Required** - Text to convert to speech (max 1024 characters)
- `--output, -o <path>`: **Required** - Output audio file path
- `--voice, -v <voice>`: Optional - Voice type (default: tongtong)
- `--speed, -s <number>`: Optional - Speech speed, 0.5-2.0 (default: 1.0)
- `--format, -f <format>`: Optional - Output format: wav, mp3, pcm (default: wav)
- `--stream`: Optional - Enable streaming output (only supports pcm format)

### When to Use CLI vs SDK

**Use CLI for:**
- Quick text-to-speech conversions
- Testing different voices and speeds
- Simple batch audio generation
- Command-line automation scripts

**Use SDK for:**
- Dynamic audio generation in applications
- Integration with web services
- Custom audio processing pipelines
- Production applications with complex requirements

## Basic TTS Implementation

### Simple Text to Speech

```javascript
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

async function textToSpeech(text, outputPath) {
  const zai = await ZAI.create();

  const response = await zai.audio.tts.create({
    input: text,
    voice: 'tongtong',
    speed: 1.0,
    response_format: 'wav',
    stream: false
  });

  // Get array buffer from Response object
  const arrayBuffer = await response.arrayBuffer();
  const buffer = Buffer.from(new Uint8Array(arrayBuffer));

  fs.writeFileSync(outputPath, buffer);
  console.log(`Audio saved to ${outputPath}`);
  return outputPath;
}

// Usage
await textToSpeech('Hello, world!', './output.wav');
```

### Multiple Voice Options

```javascript
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

async function generateWithVoice(text, voice, outputPath) {
  const zai = await ZAI.create();

  const response = await zai.audio.tts.create({
    input: text,
    voice: voice, // Available voices: tongtong, chuichui, xiaochen, jam, kazi, douji, luodo
    speed: 1.0,
    response_format: 'wav',
    stream: false
  });

  // Get array buffer from Response object
  const arrayBuffer = await response.arrayBuffer();
  const buffer = Buffer.from(new Uint8Array(arrayBuffer));

  fs.writeFileSync(outputPath, buffer);
  return outputPath;
}

// Usage
await generateWithVoice('Welcome to our service', 'tongtong', './welcome.wav');
```

### Adjustable Speed

```javascript
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

async function generateWithSpeed(text, speed, outputPath) {
  const zai = await ZAI.create();

  // Speed range: 0.5 to 2.0 (API constraint)
  // 0.5 = half speed (slower)
  // 1.0 = normal speed (default)
  // 2.0 = double speed (faster)
  // Values outside this range will cause API errors

  const response = await zai.audio.tts.create({
    input: text,
    voice: 'tongtong',
    speed: speed,
    response_format: 'wav',
    stream: false
  });

  // Get array buffer from Response object
  const arrayBuffer = await response.arrayBuffer();
  const buffer = Buffer.from(new Uint8Array(arrayBuffer));

  fs.writeFileSync(outputPath, buffer);
  return outputPath;
}

// Usage - slower narration
await generateWithSpeed('This is an important announcement', 0.8, './slow.wav');

// Usage - faster narration
await generateWithSpeed('Quick update', 1.3, './fast.wav');
```

### Adjustable Volume

```javascript
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

async function generateWithVolume(text, volume, outputPath) {
  const zai = await ZAI.create();

  // Volume range: greater than 0, up to 10 (API constraint)
  // Values must be > 0 (exclusive) and <= 10 (inclusive)
  // Default: 1.0 (normal volume)

  const response = await zai.audio.tts.create({
    input: text,
    voice: 'tongtong',
    speed: 1.0,
    volume: volume, // Optional parameter
    response_format: 'wav',
    stream: false
  });

  // Get array buffer from Response object
  const arrayBuffer = await response.arrayBuffer();
  const buffer = Buffer.from(new Uint8Array(arrayBuffer));

  fs.writeFileSync(outputPath, buffer);
  return outputPath;
}

// Usage - louder audio
await generateWithVolume('This is an announcement', 5.0, './loud.wav');

// Usage - quieter audio
await generateWithVolume('Whispered message', 0.5, './quiet.wav');
```

## Advanced Use Cases

### Batch Processing

```javascript
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';
import path from 'path';

async function batchTextToSpeech(textArray, outputDir) {
  const zai = await ZAI.create();
  const results = [];

  // Ensure output directory exists
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  for (let i = 0; i < textArray.length; i++) {
    try {
      const text = textArray[i];
      const outputPath = path.join(outputDir, `audio_${i + 1}.wav`);

      const response = await zai.audio.tts.create({
        input: text,
        voice: 'tongtong',
        speed: 1.0,
        response_format: 'wav',
        stream: false
      });

      // Get array buffer from Response object
      const arrayBuffer = await response.arrayBuffer();
      const buffer = Buffer.from(new Uint8Array(arrayBuffer));

      fs.writeFileSync(outputPath, buffer);
      results.push({
        success: true,
        text,
        path: outputPath
      });
    } catch (error) {
      results.push({
        success: false,
        text: textArray[i],
        error: error.message
      });
    }
  }

  return results;
}

// Usage
const texts = [
  'Welcome to chapter one',
  'Welcome to chapter two',
  'Welcome to chapter three'
];

const results = await batchTextToSpeech(texts, './audio-output');
console.log('Generated:', results.length, 'audio files');
```

### Dynamic Content Generation

```javascript
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

class TTSGenerator {
  constructor() {
    this.zai = null;
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  async generateAudio(text, options = {}) {
    const {
      voice = 'tongtong',
      speed = 1.0,
      format = 'wav'
    } = options;

    const response = await this.zai.audio.tts.create({
      input: text,
      voice: voice,
      speed: speed,
      response_format: format,
      stream: false
    });

    // Get array buffer from Response object
    const arrayBuffer = await response.arrayBuffer();
    return Buffer.from(new Uint8Array(arrayBuffer));
  }

  async saveAudio(text, outputPath, options = {}) {
    const buffer = await this.generateAudio(text, options);
    if (buffer) {
      fs.writeFileSync(outputPath, buffer);
      return outputPath;
    }
    return null;
  }
}

// Usage
const generator = new TTSGenerator();
await generator.initialize();

await generator.saveAudio(
  'Hello, this is a test',
  './output.wav',
  { speed: 1.2 }
);
```

### Next.js API Route Example

```javascript
import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    const { text, voice = 'tongtong', speed = 1.0 } = await req.json();

    // Import ZAI SDK
    const ZAI = (await import('z-ai-web-dev-sdk')).default;

    // Create SDK instance
    const zai = await ZAI.create();

    // Generate TTS audio
    const response = await zai.audio.tts.create({
      input: text.trim(),
      voice: voice,
      speed: speed,
      response_format: 'wav',
      stream: false,
    });

    // Get array buffer from Response object
    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(new Uint8Array(arrayBuffer));

    // Return audio as response
    return new NextResponse(buffer, {
      status: 200,
      headers: {
        'Content-Type': 'audio/wav',
        'Content-Length': buffer.length.toString(),
        'Cache-Control': 'no-cache',
      },
    });
  } catch (error) {
    console.error('TTS API Error:', error);

    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : '生成语音失败，请稍后重试',
      },
      { status: 500 }
    );
  }
}
```

## Best Practices

### 1. Text Preparation
```javascript
function prepareTextForTTS(text) {
  // Remove excessive whitespace
  text = text.replace(/\s+/g, ' ').trim();

  // Expand common abbreviations for better pronunciation
  const abbreviations = {
    'Dr.': 'Doctor',
    'Mr.': 'Mister',
    'Mrs.': 'Misses',
    'etc.': 'et cetera'
  };

  for (const [abbr, full] of Object.entries(abbreviations)) {
    text = text.replace(new RegExp(abbr, 'g'), full);
  }

  return text;
}
```

### 2. Error Handling
```javascript
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

async function safeTTS(text, outputPath) {
  try {
    // Validate input
    if (!text || text.trim().length === 0) {
      throw new Error('Text input cannot be empty');
    }

    if (text.length > 1024) {
      throw new Error('Text input exceeds maximum length of 1024 characters');
    }

    const zai = await ZAI.create();

    const response = await zai.audio.tts.create({
      input: text,
      voice: 'tongtong',
      speed: 1.0,
      response_format: 'wav',
      stream: false
    });

    // Get array buffer from Response object
    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(new Uint8Array(arrayBuffer));

    fs.writeFileSync(outputPath, buffer);

    return {
      success: true,
      path: outputPath,
      size: buffer.length
    };
  } catch (error) {
    console.error('TTS Error:', error);
    return {
      success: false,
      error: error.message
    };
  }
}
```

### 3. SDK Instance Reuse

```javascript
import ZAI from 'z-ai-web-dev-sdk';

// Create a singleton instance
let zaiInstance = null;

async function getZAIInstance() {
  if (!zaiInstance) {
    zaiInstance = await ZAI.create();
  }
  return zaiInstance;
}

// Usage
const zai = await getZAIInstance();
const response = await zai.audio.tts.create({ ... });
```

## Common Use Cases

1. **Audiobooks & Podcasts**: Convert written content to audio format
2. **E-learning**: Create narration for educational content
3. **Accessibility**: Provide audio versions of text content
4. **Voice Assistants**: Generate dynamic responses
5. **Announcements**: Create automated audio notifications
6. **IVR Systems**: Generate phone system prompts
7. **Content Localization**: Create audio in different languages

## Integration Examples

### Express.js API Endpoint

```javascript
import express from 'express';
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';
import path from 'path';

const app = express();
app.use(express.json());

let zaiInstance;
const outputDir = './audio-output';

async function initZAI() {
  zaiInstance = await ZAI.create();
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
}

app.post('/api/tts', async (req, res) => {
  try {
    const { text, voice = 'tongtong', speed = 1.0 } = req.body;

    if (!text) {
      return res.status(400).json({ error: 'Text is required' });
    }

    const filename = `tts_${Date.now()}.wav`;
    const outputPath = path.join(outputDir, filename);

    const response = await zaiInstance.audio.tts.create({
      input: text,
      voice: voice,
      speed: speed,
      response_format: 'wav',
      stream: false
    });

    // Get array buffer from Response object
    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(new Uint8Array(arrayBuffer));

    fs.writeFileSync(outputPath, buffer);

    res.json({
      success: true,
      audioUrl: `/audio/${filename}`,
      size: buffer.length
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.use('/audio', express.static('audio-output'));

initZAI().then(() => {
  app.listen(3000, () => {
    console.log('TTS API running on port 3000');
  });
});
```

## Troubleshooting

**Issue**: "Input text exceeds maximum length"
- **Solution**: Text input is limited to 1024 characters. Split longer text into chunks using the `splitTextIntoChunks` function shown in the API Limitations section

**Issue**: "Invalid speed parameter" or unexpected speed behavior
- **Solution**: Speed must be between 0.5 and 2.0. Check your speed value is within this range

**Issue**: "Invalid volume parameter"
- **Solution**: Volume must be greater than 0 and up to 10. Ensure volume value is in range (0, 10]

**Issue**: "Stream format not supported" with WAV/MP3
- **Solution**: Streaming mode only supports PCM format. Either use `response_format: 'pcm'` with streaming, or disable streaming (`stream: false`) for WAV/MP3 output

**Issue**: "SDK must be used in backend"
- **Solution**: Ensure z-ai-web-dev-sdk is only imported in server-side code

**Issue**: "TypeError: response.audio is undefined"
- **Solution**: The SDK returns a standard Response object, use `await response.arrayBuffer()` instead of accessing `response.audio`

**Issue**: Generated audio file is empty or corrupted
- **Solution**: Ensure you're calling `await response.arrayBuffer()` and properly converting to Buffer: `Buffer.from(new Uint8Array(arrayBuffer))`

**Issue**: Audio sounds unnatural
- **Solution**: Prepare text properly (remove special characters, expand abbreviations)

**Issue**: Long processing times
- **Solution**: Break long text into smaller chunks and process in parallel

**Issue**: Next.js caching old API route
- **Solution**: Create a new API route endpoint or restart the dev server

## Performance Tips

1. **Reuse SDK Instance**: Create ZAI instance once and reuse
2. **Implement Caching**: Cache generated audio for repeated text
3. **Batch Processing**: Process multiple texts efficiently
4. **Optimize Text**: Remove unnecessary content before generation
5. **Async Processing**: Use queues for handling multiple requests

## Important Notes

### API Constraints

**Input Text Length**: Maximum 1024 characters per request. For longer text:
```javascript
// Split long text into chunks
const longText = "..."; // Your long text here
const chunks = splitTextIntoChunks(longText, 1000);

for (const chunk of chunks) {
  const response = await zai.audio.tts.create({
    input: chunk,
    voice: 'tongtong',
    speed: 1.0,
    response_format: 'wav',
    stream: false
  });
  // Process each chunk...
}
```

**Streaming Format Limitation**: When using `stream: true`, only `pcm` format is supported. For `wav` or `mp3` output, use `stream: false`.

**Sample Rate**: Audio is generated at 24000 Hz sample rate (recommended setting for playback).

### Response Object Format

The `zai.audio.tts.create()` method returns a standard **Response** object (not a custom object with an `audio` property). Always use:

```javascript
// ✅ CORRECT
const response = await zai.audio.tts.create({ ... });
const arrayBuffer = await response.arrayBuffer();
const buffer = Buffer.from(new Uint8Array(arrayBuffer));

// ❌ WRONG - This will not work
const response = await zai.audio.tts.create({ ... });
const buffer = Buffer.from(response.audio); // response.audio is undefined
```

### Available Voices

- `tongtong` - 温暖亲切
- `chuichui` - 活泼可爱
- `xiaochen` - 沉稳专业
- `jam` - 英音绅士
- `kazi` - 清晰标准
- `douji` - 自然流畅
- `luodo` - 富有感染力

### Speed Range

- Minimum: `0.5` (half speed)
- Default: `1.0` (normal speed)
- Maximum: `2.0` (double speed)

**Important**: Speed values outside the range [0.5, 2.0] will result in API errors.

### Volume Range

- Minimum: Greater than `0` (exclusive)
- Default: `1.0` (normal volume)
- Maximum: `10` (inclusive)

**Note**: Volume parameter is optional. When not specified, defaults to 1.0.

## Remember

- Always use z-ai-web-dev-sdk in backend code only
- **Input text is limited to 1024 characters maximum** - split longer text into chunks
- **Speed must be between 0.5 and 2.0** - values outside this range will cause errors
- **Volume must be greater than 0 and up to 10** - optional parameter with default 1.0
- **Streaming only supports PCM format** - use non-streaming for WAV or MP3 output
- The SDK returns a standard Response object - use `await response.arrayBuffer()`
- Convert ArrayBuffer to Buffer using `Buffer.from(new Uint8Array(arrayBuffer))`
- Handle audio buffers properly when saving to files
- Implement error handling for production applications
- Consider caching for frequently generated content
- Clean up old audio files periodically to manage storage
