---
name: ASR
description: Implement speech-to-text (ASR/automatic speech recognition) capabilities using the z-ai-web-dev-sdk. Use this skill when the user needs to transcribe audio files, convert speech to text, build voice input features, or process audio recordings. Supports base64 encoded audio files and returns accurate text transcriptions.
license: MIT
---

# ASR (Speech to Text) Skill

This skill guides the implementation of speech-to-text (ASR) functionality using the z-ai-web-dev-sdk package, enabling accurate transcription of spoken audio into text.

## Skills Path

**Skill Location**: `{project_path}/skills/ASR`

this skill is located at above path in your project.

**Reference Scripts**: Example test scripts are available in the `{Skill Location}/scripts/` directory for quick testing and reference. See `{Skill Location}/scripts/asr.ts` for a working example.

## Overview

Speech-to-Text (ASR - Automatic Speech Recognition) allows you to build applications that convert spoken language in audio files into written text, enabling voice-controlled interfaces, transcription services, and audio content analysis.

**IMPORTANT**: z-ai-web-dev-sdk MUST be used in backend code only. Never use it in client-side code.

## Prerequisites

The z-ai-web-dev-sdk package is already installed. Import it as shown in the examples below.

## CLI Usage (For Simple Tasks)

For simple audio transcription tasks, you can use the z-ai CLI instead of writing code. This is ideal for quick transcriptions, testing audio files, or batch processing.

### Basic Transcription from File

```bash
# Transcribe an audio file
z-ai asr --file ./audio.wav

# Save transcription to JSON file
z-ai asr -f ./recording.mp3 -o transcript.json

# Transcribe and view output
z-ai asr --file ./interview.wav --output result.json
```

### Transcription from Base64

```bash
# Transcribe from base64 encoded audio
z-ai asr --base64 "UklGRiQAAABXQVZFZm10..." -o result.json

# Using short option
z-ai asr -b "base64_encoded_audio_data" -o transcript.json
```

### Streaming Output

```bash
# Stream transcription results
z-ai asr -f ./audio.wav --stream
```

### CLI Parameters

- `--file, -f <path>`: **Required** (if not using --base64) - Audio file path
- `--base64, -b <base64>`: **Required** (if not using --file) - Base64 encoded audio
- `--output, -o <path>`: Optional - Output file path (JSON format)
- `--stream`: Optional - Stream the transcription output

### Supported Audio Formats

The ASR service supports various audio formats including:
- WAV (.wav)
- MP3 (.mp3)
- Other common audio formats

### When to Use CLI vs SDK

**Use CLI for:**
- Quick audio file transcriptions
- Testing audio recognition accuracy
- Simple batch processing scripts
- One-off transcription tasks

**Use SDK for:**
- Real-time audio transcription in applications
- Integration with recording systems
- Custom audio processing workflows
- Production applications with streaming audio

## Basic ASR Implementation

### Simple Audio Transcription

```javascript
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

async function transcribeAudio(audioFilePath) {
  const zai = await ZAI.create();

  // Read audio file and convert to base64
  const audioFile = fs.readFileSync(audioFilePath);
  const base64Audio = audioFile.toString('base64');

  const response = await zai.audio.asr.create({
    file_base64: base64Audio
  });

  return response.text;
}

// Usage
const transcription = await transcribeAudio('./audio.wav');
console.log('Transcription:', transcription);
```

### Transcribe Multiple Audio Files

```javascript
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

async function transcribeBatch(audioFilePaths) {
  const zai = await ZAI.create();
  const results = [];

  for (const filePath of audioFilePaths) {
    try {
      const audioFile = fs.readFileSync(filePath);
      const base64Audio = audioFile.toString('base64');

      const response = await zai.audio.asr.create({
        file_base64: base64Audio
      });

      results.push({
        file: filePath,
        success: true,
        transcription: response.text
      });
    } catch (error) {
      results.push({
        file: filePath,
        success: false,
        error: error.message
      });
    }
  }

  return results;
}

// Usage
const files = ['./interview1.wav', './interview2.wav', './interview3.wav'];
const transcriptions = await transcribeBatch(files);

transcriptions.forEach(result => {
  if (result.success) {
    console.log(`${result.file}: ${result.transcription}`);
  } else {
    console.error(`${result.file}: Error - ${result.error}`);
  }
});
```

## Advanced Use Cases

### Audio File Processing with Metadata

```javascript
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';
import path from 'path';

async function transcribeWithMetadata(audioFilePath) {
  const zai = await ZAI.create();

  // Get file metadata
  const stats = fs.statSync(audioFilePath);
  const audioFile = fs.readFileSync(audioFilePath);
  const base64Audio = audioFile.toString('base64');

  const startTime = Date.now();

  const response = await zai.audio.asr.create({
    file_base64: base64Audio
  });

  const endTime = Date.now();

  return {
    filename: path.basename(audioFilePath),
    filepath: audioFilePath,
    fileSize: stats.size,
    transcription: response.text,
    wordCount: response.text.split(/\s+/).length,
    processingTime: endTime - startTime,
    timestamp: new Date().toISOString()
  };
}

// Usage
const result = await transcribeWithMetadata('./meeting_recording.wav');
console.log('Transcription Details:', JSON.stringify(result, null, 2));
```

### Real-time Audio Processing Service

```javascript
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

class ASRService {
  constructor() {
    this.zai = null;
    this.transcriptionCache = new Map();
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  generateCacheKey(audioBuffer) {
    const crypto = require('crypto');
    return crypto.createHash('md5').update(audioBuffer).digest('hex');
  }

  async transcribe(audioFilePath, useCache = true) {
    const audioBuffer = fs.readFileSync(audioFilePath);
    const cacheKey = this.generateCacheKey(audioBuffer);

    // Check cache
    if (useCache && this.transcriptionCache.has(cacheKey)) {
      return {
        transcription: this.transcriptionCache.get(cacheKey),
        cached: true
      };
    }

    // Transcribe audio
    const base64Audio = audioBuffer.toString('base64');

    const response = await this.zai.audio.asr.create({
      file_base64: base64Audio
    });

    // Cache result
    if (useCache) {
      this.transcriptionCache.set(cacheKey, response.text);
    }

    return {
      transcription: response.text,
      cached: false
    };
  }

  clearCache() {
    this.transcriptionCache.clear();
  }

  getCacheSize() {
    return this.transcriptionCache.size;
  }
}

// Usage
const asrService = new ASRService();
await asrService.initialize();

const result1 = await asrService.transcribe('./audio.wav');
console.log('First call (not cached):', result1);

const result2 = await asrService.transcribe('./audio.wav');
console.log('Second call (cached):', result2);
```

### Directory Transcription

```javascript
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';
import path from 'path';

async function transcribeDirectory(directoryPath, outputJsonPath) {
  const zai = await ZAI.create();

  // Get all audio files
  const files = fs.readdirSync(directoryPath);
  const audioFiles = files.filter(file => 
    /\.(wav|mp3|m4a|flac|ogg)$/i.test(file)
  );

  const results = {
    directory: directoryPath,
    totalFiles: audioFiles.length,
    processedAt: new Date().toISOString(),
    transcriptions: []
  };

  for (const filename of audioFiles) {
    const filePath = path.join(directoryPath, filename);

    try {
      const audioFile = fs.readFileSync(filePath);
      const base64Audio = audioFile.toString('base64');

      const response = await zai.audio.asr.create({
        file_base64: base64Audio
      });

      results.transcriptions.push({
        filename: filename,
        success: true,
        text: response.text,
        wordCount: response.text.split(/\s+/).length
      });

      console.log(`✓ Transcribed: ${filename}`);
    } catch (error) {
      results.transcriptions.push({
        filename: filename,
        success: false,
        error: error.message
      });

      console.error(`✗ Failed: ${filename} - ${error.message}`);
    }
  }

  // Save results to JSON
  fs.writeFileSync(
    outputJsonPath,
    JSON.stringify(results, null, 2)
  );

  return results;
}

// Usage
const results = await transcribeDirectory(
  './audio-recordings',
  './transcriptions.json'
);

console.log(`\nProcessed ${results.totalFiles} files`);
console.log(`Successful: ${results.transcriptions.filter(t => t.success).length}`);
console.log(`Failed: ${results.transcriptions.filter(t => !t.success).length}`);
```

## Best Practices

### 1. Audio Format Handling

```javascript
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

async function transcribeAnyFormat(audioFilePath) {
  // Supported formats: WAV, MP3, M4A, FLAC, OGG, etc.
  const validExtensions = ['.wav', '.mp3', '.m4a', '.flac', '.ogg'];
  const ext = audioFilePath.toLowerCase().substring(audioFilePath.lastIndexOf('.'));

  if (!validExtensions.includes(ext)) {
    throw new Error(`Unsupported audio format: ${ext}`);
  }

  const zai = await ZAI.create();
  const audioFile = fs.readFileSync(audioFilePath);
  const base64Audio = audioFile.toString('base64');

  const response = await zai.audio.asr.create({
    file_base64: base64Audio
  });

  return response.text;
}
```

### 2. Error Handling

```javascript
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

async function safeTranscribe(audioFilePath) {
  try {
    // Validate file exists
    if (!fs.existsSync(audioFilePath)) {
      throw new Error(`File not found: ${audioFilePath}`);
    }

    // Check file size (e.g., limit to 100MB)
    const stats = fs.statSync(audioFilePath);
    const fileSizeMB = stats.size / (1024 * 1024);
    
    if (fileSizeMB > 100) {
      throw new Error(`File too large: ${fileSizeMB.toFixed(2)}MB (max 100MB)`);
    }

    // Transcribe
    const zai = await ZAI.create();
    const audioFile = fs.readFileSync(audioFilePath);
    const base64Audio = audioFile.toString('base64');

    const response = await zai.audio.asr.create({
      file_base64: base64Audio
    });

    if (!response.text || response.text.trim().length === 0) {
      throw new Error('Empty transcription result');
    }

    return {
      success: true,
      transcription: response.text,
      filePath: audioFilePath,
      fileSize: stats.size
    };
  } catch (error) {
    console.error('Transcription error:', error);
    return {
      success: false,
      error: error.message,
      filePath: audioFilePath
    };
  }
}
```

### 3. Post-Processing Transcriptions

```javascript
function cleanTranscription(text) {
  // Remove excessive whitespace
  text = text.replace(/\s+/g, ' ').trim();

  // Capitalize first letter of sentences
  text = text.replace(/(^\w|[.!?]\s+\w)/g, match => match.toUpperCase());

  // Remove filler words (optional)
  const fillers = ['um', 'uh', 'ah', 'like', 'you know'];
  const fillerPattern = new RegExp(`\\b(${fillers.join('|')})\\b`, 'gi');
  text = text.replace(fillerPattern, '').replace(/\s+/g, ' ');

  return text;
}

async function transcribeAndClean(audioFilePath) {
  const zai = await ZAI.create();
  
  const audioFile = fs.readFileSync(audioFilePath);
  const base64Audio = audioFile.toString('base64');

  const response = await zai.audio.asr.create({
    file_base64: base64Audio
  });

  return {
    raw: response.text,
    cleaned: cleanTranscription(response.text)
  };
}
```

## Common Use Cases

1. **Meeting Transcription**: Convert recorded meetings into searchable text
2. **Interview Processing**: Transcribe interviews for analysis and documentation
3. **Podcast Transcription**: Create text versions of podcast episodes
4. **Voice Notes**: Convert voice memos to text for easier reference
5. **Call Center Analytics**: Analyze customer service calls
6. **Accessibility**: Provide text alternatives for audio content
7. **Voice Commands**: Enable voice-controlled applications
8. **Language Learning**: Transcribe pronunciation practice

## Integration Examples

### Express.js API Endpoint

```javascript
import express from 'express';
import multer from 'multer';
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

const app = express();
const upload = multer({ dest: 'uploads/' });

let zaiInstance;

async function initZAI() {
  zaiInstance = await ZAI.create();
}

app.post('/api/transcribe', upload.single('audio'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No audio file provided' });
    }

    const audioFile = fs.readFileSync(req.file.path);
    const base64Audio = audioFile.toString('base64');

    const response = await zaiInstance.audio.asr.create({
      file_base64: base64Audio
    });

    // Clean up uploaded file
    fs.unlinkSync(req.file.path);

    res.json({
      success: true,
      transcription: response.text,
      wordCount: response.text.split(/\s+/).length
    });
  } catch (error) {
    // Clean up on error
    if (req.file && fs.existsSync(req.file.path)) {
      fs.unlinkSync(req.file.path);
    }

    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

initZAI().then(() => {
  app.listen(3000, () => {
    console.log('ASR API running on port 3000');
  });
});
```

## Troubleshooting

**Issue**: "SDK must be used in backend"
- **Solution**: Ensure z-ai-web-dev-sdk is only imported in server-side code

**Issue**: Empty or incorrect transcription
- **Solution**: Verify audio quality and format. Check if audio contains clear speech

**Issue**: Large file processing fails
- **Solution**: Consider splitting large audio files into smaller segments

**Issue**: Slow transcription speed
- **Solution**: Implement caching for repeated transcriptions, optimize file sizes

**Issue**: Memory errors with large files
- **Solution**: Process files in chunks or increase Node.js memory limit

## Performance Tips

1. **Reuse SDK Instance**: Create once, use multiple times
2. **Implement Caching**: Cache transcriptions for duplicate files
3. **Batch Processing**: Process multiple files efficiently with proper queuing
4. **Audio Optimization**: Compress audio files before processing when possible
5. **Async Operations**: Use Promise.all for parallel processing when appropriate

## Audio Quality Guidelines

For best transcription results:
- **Sample Rate**: 16kHz or higher
- **Format**: WAV, MP3, or M4A recommended
- **Noise Level**: Minimize background noise
- **Speech Clarity**: Clear pronunciation and normal speaking pace
- **File Size**: Under 100MB recommended for individual files

## Remember

- Always use z-ai-web-dev-sdk in backend code only
- The SDK is already installed - import as shown in examples
- Audio files must be converted to base64 before processing
- Implement proper error handling for production applications
- Consider audio quality for best transcription accuracy
- Clean up temporary files after processing
- Cache results for frequently transcribed files
