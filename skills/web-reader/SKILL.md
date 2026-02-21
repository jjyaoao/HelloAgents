---
name: web-reader
description: Implement web page content extraction capabilities using the z-ai-web-dev-sdk. Use this skill when the user needs to scrape web pages, extract article content, retrieve page metadata, or build applications that process web content. Supports automatic content extraction with title, HTML, and publication time retrieval.
license: MIT
---

# Web Reader Skill

This skill guides the implementation of web page reading and content extraction functionality using the z-ai-web-dev-sdk package, enabling applications to fetch and process web page content programmatically.

## Skills Path

**Skill Location**: `{project_path}/skills/web-reader`

This skill is located at the above path in your project.

**Reference Scripts**: Example test scripts are available in the `{Skill Location}/scripts/` directory for quick testing and reference. See `{Skill Location}/scripts/web-reader.ts` for a working example.

## Overview

Web Reader allows you to build applications that can extract content from web pages, retrieve article metadata, and process HTML content. The API automatically handles content extraction, providing clean, structured data from any web URL.

**IMPORTANT**: z-ai-web-dev-sdk MUST be used in backend code only. Never use it in client-side code.

## Prerequisites

The z-ai-web-dev-sdk package is already installed. Import it as shown in the examples below.

## CLI Usage (For Simple Tasks)

For simple web page content extraction, you can use the z-ai CLI instead of writing code. This is ideal for quick content scraping, testing URLs, or simple automation tasks.

### Basic Page Reading

```bash
# Extract content from a web page
z-ai function --name "page_reader" --args '{"url": "https://example.com"}'

# Using short options
z-ai function -n page_reader -a '{"url": "https://www.example.com/article"}'
```

### Save Page Content

```bash
# Save extracted content to JSON file
z-ai function \
  -n page_reader \
  -a '{"url": "https://news.example.com/article"}' \
  -o page_content.json

# Extract and save blog post
z-ai function \
  -n page_reader \
  -a '{"url": "https://blog.example.com/post/123"}' \
  -o blog_post.json
```

### Common Use Cases

```bash
# Extract news article
z-ai function \
  -n page_reader \
  -a '{"url": "https://news.site.com/breaking-news"}' \
  -o news.json

# Read documentation page
z-ai function \
  -n page_reader \
  -a '{"url": "https://docs.example.com/getting-started"}' \
  -o docs.json

# Scrape blog content
z-ai function \
  -n page_reader \
  -a '{"url": "https://techblog.com/ai-trends-2024"}' \
  -o blog.json

# Extract research article
z-ai function \
  -n page_reader \
  -a '{"url": "https://research.org/papers/quantum-computing"}' \
  -o research.json
```

### CLI Parameters

- `--name, -n`: **Required** - Function name (use "page_reader")
- `--args, -a`: **Required** - JSON arguments object with:
  - `url` (string, required): The URL of the web page to read
- `--output, -o <path>`: Optional - Output file path (JSON format)

### Response Structure

The CLI returns a JSON object containing:
- `title`: Page title
- `html`: Main content HTML
- `text`: Plain text content
- `publish_time`: Publication timestamp (if available)
- `url`: Original URL
- `metadata`: Additional page metadata

### Example Response

```json
{
  "title": "Introduction to Machine Learning",
  "html": "<article><h1>Introduction to Machine Learning</h1><p>Machine learning is...</p></article>",
  "text": "Introduction to Machine Learning\n\nMachine learning is...",
  "publish_time": "2024-01-15T10:30:00Z",
  "url": "https://example.com/ml-intro",
  "metadata": {
    "author": "John Doe",
    "description": "A comprehensive guide to ML"
  }
}
```

### Processing Multiple URLs

```bash
# Create a simple script to process multiple URLs
for url in \
  "https://site1.com/article1" \
  "https://site2.com/article2" \
  "https://site3.com/article3"
do
  filename=$(echo $url | md5sum | cut -d' ' -f1)
  z-ai function -n page_reader -a "{\"url\": \"$url\"}" -o "${filename}.json"
done
```

### When to Use CLI vs SDK

**Use CLI for:**
- Quick content extraction
- Testing URL accessibility
- Simple web scraping tasks
- One-off content retrieval

**Use SDK for:**
- Batch URL processing with custom logic
- Integration with web applications
- Complex content processing pipelines
- Production applications with error handling

## How It Works

The Web Reader uses the `page_reader` function to:
1. Fetch the web page content
2. Extract main article content and metadata
3. Parse and clean the HTML
4. Return structured data including title, content, and publication time

## Basic Web Reading Implementation

### Simple Page Reading

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function readWebPage(url) {
  try {
    const zai = await ZAI.create();

    const result = await zai.functions.invoke('page_reader', {
      url: url
    });

    console.log('Title:', result.data.title);
    console.log('URL:', result.data.url);
    console.log('Published:', result.data.publishedTime);
    console.log('HTML Content:', result.data.html);
    console.log('Tokens Used:', result.data.usage.tokens);

    return result.data;
  } catch (error) {
    console.error('Page reading failed:', error.message);
    throw error;
  }
}

// Usage
const pageData = await readWebPage('https://example.com/article');
console.log('Page title:', pageData.title);
```

### Extract Article Text Only

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function extractArticleText(url) {
  const zai = await ZAI.create();

  const result = await zai.functions.invoke('page_reader', {
    url: url
  });

  // Convert HTML to plain text (basic approach)
  const plainText = result.data.html
    .replace(/<[^>]*>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return {
    title: result.data.title,
    text: plainText,
    url: result.data.url,
    publishedTime: result.data.publishedTime
  };
}

// Usage
const article = await extractArticleText('https://news.example.com/story');
console.log(article.title);
console.log(article.text.substring(0, 200) + '...');
```

### Read Multiple Pages

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function readMultiplePages(urls) {
  const zai = await ZAI.create();
  const results = [];

  for (const url of urls) {
    try {
      const result = await zai.functions.invoke('page_reader', {
        url: url
      });

      results.push({
        url: url,
        success: true,
        data: result.data
      });
    } catch (error) {
      results.push({
        url: url,
        success: false,
        error: error.message
      });
    }
  }

  return results;
}

// Usage
const urls = [
  'https://example.com/article1',
  'https://example.com/article2',
  'https://example.com/article3'
];

const pages = await readMultiplePages(urls);
pages.forEach(page => {
  if (page.success) {
    console.log(`✓ ${page.data.title}`);
  } else {
    console.log(`✗ ${page.url}: ${page.error}`);
  }
});
```

## Advanced Use Cases

### Web Content Analyzer

```javascript
import ZAI from 'z-ai-web-dev-sdk';

class WebContentAnalyzer {
  constructor() {
    this.cache = new Map();
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  async readPage(url, useCache = true) {
    // Check cache
    if (useCache && this.cache.has(url)) {
      console.log('Returning cached result for:', url);
      return this.cache.get(url);
    }

    // Fetch fresh content
    const result = await this.zai.functions.invoke('page_reader', {
      url: url
    });

    // Cache the result
    if (useCache) {
      this.cache.set(url, result.data);
    }

    return result.data;
  }

  async getPageMetadata(url) {
    const data = await this.readPage(url);

    return {
      title: data.title,
      url: data.url,
      publishedTime: data.publishedTime,
      contentLength: data.html.length,
      wordCount: this.estimateWordCount(data.html)
    };
  }

  estimateWordCount(html) {
    const text = html.replace(/<[^>]*>/g, ' ');
    const words = text.split(/\s+/).filter(word => word.length > 0);
    return words.length;
  }

  async comparePages(url1, url2) {
    const [page1, page2] = await Promise.all([
      this.readPage(url1),
      this.readPage(url2)
    ]);

    return {
      page1: {
        title: page1.title,
        wordCount: this.estimateWordCount(page1.html),
        published: page1.publishedTime
      },
      page2: {
        title: page2.title,
        wordCount: this.estimateWordCount(page2.html),
        published: page2.publishedTime
      }
    };
  }

  clearCache() {
    this.cache.clear();
  }
}

// Usage
const analyzer = new WebContentAnalyzer();
await analyzer.initialize();

const metadata = await analyzer.getPageMetadata('https://example.com/article');
console.log('Article Metadata:', metadata);

const comparison = await analyzer.comparePages(
  'https://example.com/article1',
  'https://example.com/article2'
);
console.log('Comparison:', comparison);
```

### RSS Feed Reader

```javascript
import ZAI from 'z-ai-web-dev-sdk';

class FeedReader {
  constructor() {
    this.articles = [];
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  async fetchArticlesFromUrls(urls) {
    const articles = [];

    for (const url of urls) {
      try {
        const result = await this.zai.functions.invoke('page_reader', {
          url: url
        });

        articles.push({
          title: result.data.title,
          url: result.data.url,
          publishedTime: result.data.publishedTime,
          content: result.data.html,
          fetchedAt: new Date().toISOString()
        });

        console.log(`Fetched: ${result.data.title}`);
      } catch (error) {
        console.error(`Failed to fetch ${url}:`, error.message);
      }
    }

    this.articles = articles;
    return articles;
  }

  getRecentArticles(limit = 10) {
    return this.articles
      .sort((a, b) => {
        const dateA = new Date(a.publishedTime || a.fetchedAt);
        const dateB = new Date(b.publishedTime || b.fetchedAt);
        return dateB - dateA;
      })
      .slice(0, limit);
  }

  searchArticles(keyword) {
    return this.articles.filter(article => {
      const searchText = `${article.title} ${article.content}`.toLowerCase();
      return searchText.includes(keyword.toLowerCase());
    });
  }
}

// Usage
const reader = new FeedReader();
await reader.initialize();

const feedUrls = [
  'https://example.com/article1',
  'https://example.com/article2',
  'https://example.com/article3'
];

await reader.fetchArticlesFromUrls(feedUrls);
const recent = reader.getRecentArticles(5);
console.log('Recent articles:', recent.map(a => a.title));
```

### Content Aggregator

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function aggregateContent(urls, options = {}) {
  const zai = await ZAI.create();
  const aggregated = {
    sources: [],
    totalWords: 0,
    aggregatedAt: new Date().toISOString()
  };

  for (const url of urls) {
    try {
      const result = await zai.functions.invoke('page_reader', {
        url: url
      });

      const text = result.data.html.replace(/<[^>]*>/g, ' ');
      const wordCount = text.split(/\s+/).filter(w => w.length > 0).length;

      aggregated.sources.push({
        title: result.data.title,
        url: result.data.url,
        publishedTime: result.data.publishedTime,
        wordCount: wordCount,
        excerpt: text.substring(0, 200).trim() + '...'
      });

      aggregated.totalWords += wordCount;

      if (options.delay) {
        await new Promise(resolve => setTimeout(resolve, options.delay));
      }
    } catch (error) {
      console.error(`Failed to fetch ${url}:`, error.message);
    }
  }

  return aggregated;
}

// Usage
const sources = [
  'https://example.com/news1',
  'https://example.com/news2',
  'https://example.com/news3'
];

const aggregated = await aggregateContent(sources, { delay: 1000 });
console.log(`Aggregated ${aggregated.sources.length} sources`);
console.log(`Total words: ${aggregated.totalWords}`);
```

### Web Scraping Pipeline

```javascript
import ZAI from 'z-ai-web-dev-sdk';

class ScrapingPipeline {
  constructor() {
    this.processors = [];
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  addProcessor(name, processorFn) {
    this.processors.push({ name, fn: processorFn });
  }

  async scrape(url) {
    // Fetch the page
    const result = await this.zai.functions.invoke('page_reader', {
      url: url
    });

    let data = {
      raw: result.data,
      processed: {}
    };

    // Run through processors
    for (const processor of this.processors) {
      try {
        data.processed[processor.name] = await processor.fn(data.raw);
        console.log(`✓ Processed with ${processor.name}`);
      } catch (error) {
        console.error(`✗ Failed ${processor.name}:`, error.message);
        data.processed[processor.name] = null;
      }
    }

    return data;
  }
}

// Processor functions
function extractLinks(pageData) {
  const linkRegex = /href=["'](https?:\/\/[^"']+)["']/g;
  const links = [];
  let match;

  while ((match = linkRegex.exec(pageData.html)) !== null) {
    links.push(match[1]);
  }

  return [...new Set(links)]; // Remove duplicates
}

function extractImages(pageData) {
  const imgRegex = /src=["'](https?:\/\/[^"']+\.(jpg|jpeg|png|gif|webp))["']/gi;
  const images = [];
  let match;

  while ((match = imgRegex.exec(pageData.html)) !== null) {
    images.push(match[1]);
  }

  return [...new Set(images)];
}

function extractPlainText(pageData) {
  return pageData.html
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<[^>]*>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

// Usage
const pipeline = new ScrapingPipeline();
await pipeline.initialize();

pipeline.addProcessor('links', extractLinks);
pipeline.addProcessor('images', extractImages);
pipeline.addProcessor('plainText', extractPlainText);

const result = await pipeline.scrape('https://example.com/article');
console.log('Links found:', result.processed.links.length);
console.log('Images found:', result.processed.images.length);
console.log('Text length:', result.processed.plainText.length);
```

## Response Format

### Successful Response

```typescript
{
  code: 200,
  status: 200,
  data: {
    title: "Article Title",
    url: "https://example.com/article",
    html: "<div>Article content...</div>",
    publishedTime: "2025-01-15T10:30:00Z",
    usage: {
      tokens: 1500
    }
  },
  meta: {
    usage: {
      tokens: 1500
    }
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `code` | number | Response status code |
| `status` | number | HTTP status code |
| `data.title` | string | Page title |
| `data.url` | string | Page URL |
| `data.html` | string | Extracted HTML content |
| `data.publishedTime` | string | Publication date (optional) |
| `data.usage.tokens` | number | Tokens used for processing |
| `meta.usage.tokens` | number | Total tokens used |

## Best Practices

### 1. Error Handling

```javascript
async function safeReadPage(url) {
  try {
    const zai = await ZAI.create();

    // Validate URL
    if (!url || !url.startsWith('http')) {
      throw new Error('Invalid URL format');
    }

    const result = await zai.functions.invoke('page_reader', {
      url: url
    });

    // Check response status
    if (result.code !== 200) {
      throw new Error(`Failed to fetch page: ${result.code}`);
    }

    // Verify essential data
    if (!result.data.html || !result.data.title) {
      throw new Error('Incomplete page data received');
    }

    return {
      success: true,
      data: result.data
    };
  } catch (error) {
    console.error('Page reading error:', error);
    return {
      success: false,
      error: error.message
    };
  }
}
```

### 2. Rate Limiting

```javascript
class RateLimitedReader {
  constructor(requestsPerMinute = 10) {
    this.requestsPerMinute = requestsPerMinute;
    this.requestTimes = [];
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  async readPage(url) {
    await this.waitForRateLimit();

    const result = await this.zai.functions.invoke('page_reader', {
      url: url
    });

    this.requestTimes.push(Date.now());
    return result.data;
  }

  async waitForRateLimit() {
    const now = Date.now();
    const oneMinuteAgo = now - 60000;

    // Remove old timestamps
    this.requestTimes = this.requestTimes.filter(time => time > oneMinuteAgo);

    // Check if we need to wait
    if (this.requestTimes.length >= this.requestsPerMinute) {
      const oldestRequest = this.requestTimes[0];
      const waitTime = 60000 - (now - oldestRequest);

      if (waitTime > 0) {
        console.log(`Rate limit reached. Waiting ${waitTime}ms...`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
      }
    }
  }
}

// Usage
const reader = new RateLimitedReader(10); // 10 requests per minute
await reader.initialize();

const urls = ['https://example.com/1', 'https://example.com/2'];
for (const url of urls) {
  const data = await reader.readPage(url);
  console.log('Fetched:', data.title);
}
```

### 3. Caching Strategy

```javascript
import ZAI from 'z-ai-web-dev-sdk';

class CachedWebReader {
  constructor(cacheDuration = 3600000) { // 1 hour default
    this.cache = new Map();
    this.cacheDuration = cacheDuration;
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  async readPage(url, forceRefresh = false) {
    const cacheKey = url;
    const cached = this.cache.get(cacheKey);

    // Return cached if valid and not forcing refresh
    if (cached && !forceRefresh) {
      const age = Date.now() - cached.timestamp;
      if (age < this.cacheDuration) {
        console.log('Returning cached content for:', url);
        return cached.data;
      }
    }

    // Fetch fresh content
    const result = await this.zai.functions.invoke('page_reader', {
      url: url
    });

    // Update cache
    this.cache.set(cacheKey, {
      data: result.data,
      timestamp: Date.now()
    });

    return result.data;
  }

  clearCache() {
    this.cache.clear();
  }

  getCacheStats() {
    return {
      size: this.cache.size,
      entries: Array.from(this.cache.keys())
    };
  }
}

// Usage
const reader = new CachedWebReader(3600000); // 1 hour cache
await reader.initialize();

const data1 = await reader.readPage('https://example.com'); // Fresh fetch
const data2 = await reader.readPage('https://example.com'); // From cache
const data3 = await reader.readPage('https://example.com', true); // Force refresh
```

### 4. Parallel Processing

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function readPagesInParallel(urls, concurrency = 3) {
  const zai = await ZAI.create();
  const results = [];
  
  // Process in batches
  for (let i = 0; i < urls.length; i += concurrency) {
    const batch = urls.slice(i, i + concurrency);
    
    const batchResults = await Promise.allSettled(
      batch.map(url =>
        zai.functions.invoke('page_reader', { url })
          .then(result => ({
            url: url,
            success: true,
            data: result.data
          }))
          .catch(error => ({
            url: url,
            success: false,
            error: error.message
          }))
      )
    );

    results.push(...batchResults.map(r => r.value));
    console.log(`Completed batch ${Math.floor(i / concurrency) + 1}`);
  }

  return results;
}

// Usage
const urls = [
  'https://example.com/1',
  'https://example.com/2',
  'https://example.com/3',
  'https://example.com/4',
  'https://example.com/5'
];

const results = await readPagesInParallel(urls, 2); // 2 concurrent requests
results.forEach(result => {
  if (result.success) {
    console.log(`✓ ${result.data.title}`);
  } else {
    console.log(`✗ ${result.url}: ${result.error}`);
  }
});
```

### 5. Content Processing

```javascript
import ZAI from 'z-ai-web-dev-sdk';

class ContentProcessor {
  static extractMainContent(html) {
    // Remove scripts, styles, and comments
    let content = html
      .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
      .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
      .replace(/<!--[\s\S]*?-->/g, '');

    return content;
  }

  static htmlToPlainText(html) {
    return html
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/p>/gi, '\n\n')
      .replace(/<[^>]*>/g, '')
      .replace(/&nbsp;/g, ' ')
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"')
      .replace(/\s+/g, ' ')
      .trim();
  }

  static extractMetadata(html) {
    const metadata = {};

    // Extract meta description
    const descMatch = html.match(/<meta\s+name=["']description["']\s+content=["']([^"']+)["']/i);
    if (descMatch) metadata.description = descMatch[1];

    // Extract keywords
    const keywordsMatch = html.match(/<meta\s+name=["']keywords["']\s+content=["']([^"']+)["']/i);
    if (keywordsMatch) metadata.keywords = keywordsMatch[1].split(',').map(k => k.trim());

    // Extract author
    const authorMatch = html.match(/<meta\s+name=["']author["']\s+content=["']([^"']+)["']/i);
    if (authorMatch) metadata.author = authorMatch[1];

    return metadata;
  }
}

// Usage
async function processWebPage(url) {
  const zai = await ZAI.create();
  const result = await zai.functions.invoke('page_reader', { url });

  return {
    title: result.data.title,
    url: result.data.url,
    mainContent: ContentProcessor.extractMainContent(result.data.html),
    plainText: ContentProcessor.htmlToPlainText(result.data.html),
    metadata: ContentProcessor.extractMetadata(result.data.html),
    publishedTime: result.data.publishedTime
  };
}

const processed = await processWebPage('https://example.com/article');
console.log('Processed content:', processed.title);
```

## Common Use Cases

1. **News Aggregation**: Collect and aggregate news articles from multiple sources
2. **Content Monitoring**: Track changes on specific web pages
3. **Research Tools**: Extract information from academic or reference websites
4. **Price Tracking**: Monitor product pages for price changes
5. **SEO Analysis**: Extract page metadata and content for SEO purposes
6. **Archive Creation**: Create local copies of web content
7. **Content Curation**: Collect and organize web content by topic
8. **Competitive Intelligence**: Monitor competitor websites for updates

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

app.post('/api/read-page', async (req, res) => {
  try {
    const { url } = req.body;

    if (!url) {
      return res.status(400).json({ 
        error: 'URL is required' 
      });
    }

    const result = await zaiInstance.functions.invoke('page_reader', {
      url: url
    });

    res.json({
      success: true,
      data: {
        title: result.data.title,
        url: result.data.url,
        content: result.data.html,
        publishedTime: result.data.publishedTime,
        tokensUsed: result.data.usage.tokens
      }
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/read-multiple', async (req, res) => {
  try {
    const { urls } = req.body;

    if (!urls || !Array.isArray(urls)) {
      return res.status(400).json({ 
        error: 'URLs array is required' 
      });
    }

    const results = await Promise.allSettled(
      urls.map(url =>
        zaiInstance.functions.invoke('page_reader', { url })
          .then(result => ({
            url: url,
            success: true,
            data: result.data
          }))
          .catch(error => ({
            url: url,
            success: false,
            error: error.message
          }))
      )
    );

    res.json({
      success: true,
      results: results.map(r => r.value)
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
    console.log('Web reader API running on port 3000');
  });
});
```

### Scheduled Content Fetcher

```javascript
import ZAI from 'z-ai-web-dev-sdk';
import cron from 'node-cron';

class ScheduledFetcher {
  constructor() {
    this.urls = [];
    this.results = [];
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  addUrl(url, schedule) {
    this.urls.push({ url, schedule });
  }

  async fetchContent(url) {
    try {
      const result = await this.zai.functions.invoke('page_reader', {
        url: url
      });

      return {
        url: url,
        success: true,
        title: result.data.title,
        content: result.data.html,
        fetchedAt: new Date().toISOString()
      };
    } catch (error) {
      return {
        url: url,
        success: false,
        error: error.message,
        fetchedAt: new Date().toISOString()
      };
    }
  }

  startScheduledFetch(url, schedule) {
    cron.schedule(schedule, async () => {
      console.log(`Fetching ${url}...`);
      const result = await this.fetchContent(url);
      this.results.push(result);
      
      // Keep only last 100 results
      if (this.results.length > 100) {
        this.results = this.results.slice(-100);
      }
      
      console.log(`Fetched: ${result.success ? result.title : result.error}`);
    });
  }

  start() {
    for (const { url, schedule } of this.urls) {
      this.startScheduledFetch(url, schedule);
    }
  }

  getResults() {
    return this.results;
  }
}

// Usage
const fetcher = new ScheduledFetcher();
await fetcher.initialize();

// Fetch every hour
fetcher.addUrl('https://example.com/news', '0 * * * *');

// Fetch every day at midnight
fetcher.addUrl('https://example.com/daily', '0 0 * * *');

fetcher.start();
console.log('Scheduled fetching started');
```

## Troubleshooting

**Issue**: "SDK must be used in backend"
- **Solution**: Ensure z-ai-web-dev-sdk is only imported and used in server-side code

**Issue**: Failed to fetch page (404, 403, etc.)
- **Solution**: Verify the URL is accessible and not behind authentication/paywall

**Issue**: Incomplete or missing content
- **Solution**: Some pages may have dynamic content that requires JavaScript. The reader extracts static HTML content.

**Issue**: High token usage
- **Solution**: The token usage depends on page size. Consider caching frequently accessed pages.

**Issue**: Slow response times
- **Solution**: Implement caching, use parallel processing for multiple URLs, and consider rate limiting

**Issue**: Empty HTML content
- **Solution**: Check if the page requires authentication or has anti-scraping measures. Verify the URL is correct.

## Performance Tips

1. **Implement caching**: Cache frequently accessed pages to reduce API calls
2. **Use parallel processing**: Fetch multiple pages concurrently (with rate limiting)
3. **Process content efficiently**: Extract only needed information from HTML
4. **Set timeouts**: Implement reasonable timeouts for page fetching
5. **Monitor token usage**: Track usage to optimize costs
6. **Batch operations**: Group multiple URL fetches when possible

## Security Considerations

- Validate all URLs before processing
- Sanitize extracted HTML content before displaying
- Implement rate limiting to prevent abuse
- Never expose SDK credentials in client-side code
- Be respectful of robots.txt and website terms of service
- Handle user data according to privacy regulations
- Implement proper error handling for failed requests

## Remember

- Always use z-ai-web-dev-sdk in backend code only
- The SDK is already installed - import as shown in examples
- Implement proper error handling for robust applications
- Use caching to improve performance and reduce costs
- Respect website terms of service and rate limits
- Process HTML content carefully to extract meaningful data
- Monitor token usage for cost optimization
