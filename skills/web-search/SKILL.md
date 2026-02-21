---
name: web-search
description: Implement web search capabilities using the z-ai-web-dev-sdk. Use this skill when the user needs to search for real-time information from the web, retrieve up-to-date content beyond the knowledge cutoff, or find the latest news and data. Returns structured search results with URLs, snippets, and metadata.
license: MIT
---

# Web Search Skill

This skill guides the implementation of web search functionality using the z-ai-web-dev-sdk package, enabling applications to search the web and retrieve current information.

## Installation Path

**Recommended Location**: `{project_path}/skills/web-search`

Extract this skill package to the above path in your project.

**Reference Scripts**: Example test scripts are available in the `{project_path}/skills/web-search/scripts/` directory for quick testing and reference. See `{project_path}/skills/web-search/scripts/web_search.ts` for a working example.

## Overview

The Web Search skill allows you to build applications that can search the internet, retrieve current information, and access real-time data from web sources.

**IMPORTANT**: z-ai-web-dev-sdk MUST be used in backend code only. Never use it in client-side code.

## Prerequisites

The z-ai-web-dev-sdk package is already installed. Import it as shown in the examples below.

## CLI Usage (For Simple Tasks)

For simple web search queries, you can use the z-ai CLI instead of writing code. This is ideal for quick information retrieval, testing search functionality, or command-line automation.

### Basic Web Search

```bash
# Simple search query
z-ai function --name "web_search" --args '{"query": "artificial intelligence"}'

# Using short options
z-ai function -n web_search -a '{"query": "latest tech news"}'
```

### Search with Custom Parameters

```bash
# Limit number of results
z-ai function \
  -n web_search \
  -a '{"query": "machine learning", "num": 5}'

# Search with recency filter (results from last N days)
z-ai function \
  -n web_search \
  -a '{"query": "cryptocurrency news", "num": 10, "recency_days": 7}'
```

### Save Search Results

```bash
# Save results to JSON file
z-ai function \
  -n web_search \
  -a '{"query": "climate change research", "num": 5}' \
  -o search_results.json

# Recent news with file output
z-ai function \
  -n web_search \
  -a '{"query": "AI breakthroughs", "num": 3, "recency_days": 1}' \
  -o ai_news.json
```

### Advanced Search Examples

```bash
# Search for specific topics
z-ai function \
  -n web_search \
  -a '{"query": "quantum computing applications", "num": 8}' \
  -o quantum.json

# Find recent scientific papers
z-ai function \
  -n web_search \
  -a '{"query": "genomics research", "num": 5, "recency_days": 30}' \
  -o genomics.json

# Technology news from last 24 hours
z-ai function \
  -n web_search \
  -a '{"query": "tech industry updates", "recency_days": 1}' \
  -o today_tech.json
```

### CLI Parameters

- `--name, -n`: **Required** - Function name (use "web_search")
- `--args, -a`: **Required** - JSON arguments object with:
  - `query` (string, required): Search keywords
  - `num` (number, optional): Number of results (default: 10)
  - `recency_days` (number, optional): Filter results from last N days
- `--output, -o <path>`: Optional - Output file path (JSON format)

### Search Result Structure

Each result contains:
- `url`: Full URL of the result
- `name`: Title of the page
- `snippet`: Preview text/description
- `host_name`: Domain name
- `rank`: Result ranking
- `date`: Publication/update date
- `favicon`: Favicon URL

### When to Use CLI vs SDK

**Use CLI for:**
- Quick information lookups
- Testing search queries
- Simple automation scripts
- One-off research tasks

**Use SDK for:**
- Dynamic search in applications
- Multi-step search workflows
- Custom result processing and filtering
- Production applications with complex logic

## Search Result Type

Each search result is a `SearchFunctionResultItem` with the following structure:

```typescript
interface SearchFunctionResultItem {
  url: string;          // Full URL of the result
  name: string;         // Title of the page
  snippet: string;      // Preview text/description
  host_name: string;    // Domain name
  rank: number;         // Result ranking
  date: string;         // Publication/update date
  favicon: string;      // Favicon URL
}
```

## Basic Web Search

### Simple Search Query

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function searchWeb(query) {
  const zai = await ZAI.create();

  const results = await zai.functions.invoke('web_search', {
    query: query,
    num: 10
  });

  return results;
}

// Usage
const searchResults = await searchWeb('What is the capital of France?');
console.log('Search Results:', searchResults);
```

### Search with Custom Result Count

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function searchWithLimit(query, numberOfResults) {
  const zai = await ZAI.create();

  const results = await zai.functions.invoke('web_search', {
    query: query,
    num: numberOfResults
  });

  return results;
}

// Usage - Get top 5 results
const topResults = await searchWithLimit('artificial intelligence news', 5);

// Usage - Get top 20 results
const moreResults = await searchWithLimit('JavaScript frameworks', 20);
```

### Formatted Search Results

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function getFormattedResults(query) {
  const zai = await ZAI.create();

  const results = await zai.functions.invoke('web_search', {
    query: query,
    num: 10
  });

  // Format results for display
  const formatted = results.map((item, index) => ({
    position: index + 1,
    title: item.name,
    url: item.url,
    description: item.snippet,
    domain: item.host_name,
    publishDate: item.date
  }));

  return formatted;
}

// Usage
const results = await getFormattedResults('climate change solutions');
results.forEach(result => {
  console.log(`${result.position}. ${result.title}`);
  console.log(`   ${result.url}`);
  console.log(`   ${result.description}`);
  console.log('');
});
```

## Advanced Use Cases

### Search with Result Processing

```javascript
import ZAI from 'z-ai-web-dev-sdk';

class SearchProcessor {
  constructor() {
    this.zai = null;
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  async search(query, options = {}) {
    const {
      num = 10,
      filterDomain = null,
      minSnippetLength = 0
    } = options;

    const results = await this.zai.functions.invoke('web_search', {
      query: query,
      num: num
    });

    // Filter results
    let filtered = results;

    if (filterDomain) {
      filtered = filtered.filter(item => 
        item.host_name.includes(filterDomain)
      );
    }

    if (minSnippetLength > 0) {
      filtered = filtered.filter(item => 
        item.snippet.length >= minSnippetLength
      );
    }

    return filtered;
  }

  extractDomains(results) {
    return [...new Set(results.map(item => item.host_name))];
  }

  groupByDomain(results) {
    const grouped = {};
    
    results.forEach(item => {
      if (!grouped[item.host_name]) {
        grouped[item.host_name] = [];
      }
      grouped[item.host_name].push(item);
    });

    return grouped;
  }

  sortByDate(results, ascending = false) {
    return results.sort((a, b) => {
      const dateA = new Date(a.date);
      const dateB = new Date(b.date);
      return ascending ? dateA - dateB : dateB - dateA;
    });
  }
}

// Usage
const processor = new SearchProcessor();
await processor.initialize();

const results = await processor.search('machine learning tutorials', {
  num: 15,
  minSnippetLength: 50
});

console.log('Domains found:', processor.extractDomains(results));
console.log('Grouped by domain:', processor.groupByDomain(results));
console.log('Sorted by date:', processor.sortByDate(results));
```

### News Search

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function searchNews(topic, timeframe = 'recent') {
  const zai = await ZAI.create();

  // Add time-based keywords to query
  const timeKeywords = {
    recent: 'latest news',
    today: 'today news',
    week: 'this week news',
    month: 'this month news'
  };

  const query = `${topic} ${timeKeywords[timeframe] || timeKeywords.recent}`;

  const results = await zai.functions.invoke('web_search', {
    query: query,
    num: 10
  });

  // Sort by date (most recent first)
  const sortedResults = results.sort((a, b) => {
    return new Date(b.date) - new Date(a.date);
  });

  return sortedResults;
}

// Usage
const aiNews = await searchNews('artificial intelligence', 'today');
const techNews = await searchNews('technology', 'week');

console.log('Latest AI News:');
aiNews.forEach(item => {
  console.log(`${item.name} (${item.date})`);
  console.log(`${item.snippet}\n`);
});
```

### Research Assistant

```javascript
import ZAI from 'z-ai-web-dev-sdk';

class ResearchAssistant {
  constructor() {
    this.zai = null;
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  async researchTopic(topic, depth = 'standard') {
    const numResults = {
      quick: 5,
      standard: 10,
      deep: 20
    };

    const results = await this.zai.functions.invoke('web_search', {
      query: topic,
      num: numResults[depth] || 10
    });

    // Analyze results
    const analysis = {
      topic: topic,
      totalResults: results.length,
      sources: this.extractDomains(results),
      topResults: results.slice(0, 5).map(r => ({
        title: r.name,
        url: r.url,
        summary: r.snippet
      })),
      dateRange: this.getDateRange(results)
    };

    return analysis;
  }

  extractDomains(results) {
    const domains = {};
    results.forEach(item => {
      domains[item.host_name] = (domains[item.host_name] || 0) + 1;
    });
    return domains;
  }

  getDateRange(results) {
    const dates = results
      .map(r => new Date(r.date))
      .filter(d => !isNaN(d));

    if (dates.length === 0) return null;

    return {
      earliest: new Date(Math.min(...dates)),
      latest: new Date(Math.max(...dates))
    };
  }

  async compareTopics(topic1, topic2) {
    const [results1, results2] = await Promise.all([
      this.zai.functions.invoke('web_search', { query: topic1, num: 10 }),
      this.zai.functions.invoke('web_search', { query: topic2, num: 10 })
    ]);

    const domains1 = new Set(results1.map(r => r.host_name));
    const domains2 = new Set(results2.map(r => r.host_name));

    const commonDomains = [...domains1].filter(d => domains2.has(d));

    return {
      topic1: {
        name: topic1,
        results: results1.length,
        uniqueDomains: domains1.size
      },
      topic2: {
        name: topic2,
        results: results2.length,
        uniqueDomains: domains2.size
      },
      commonDomains: commonDomains
    };
  }
}

// Usage
const assistant = new ResearchAssistant();
await assistant.initialize();

const research = await assistant.researchTopic('quantum computing', 'deep');
console.log('Research Analysis:', research);

const comparison = await assistant.compareTopics(
  'renewable energy',
  'solar power'
);
console.log('Topic Comparison:', comparison);
```

### Search Result Validation

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function validateSearchResults(query) {
  const zai = await ZAI.create();

  const results = await zai.functions.invoke('web_search', {
    query: query,
    num: 10
  });

  // Validate and score results
  const validated = results.map(item => {
    let score = 0;
    let flags = [];

    // Check snippet quality
    if (item.snippet && item.snippet.length > 50) {
      score += 20;
    } else {
      flags.push('short_snippet');
    }

    // Check date availability
    if (item.date && item.date !== 'N/A') {
      score += 20;
    } else {
      flags.push('no_date');
    }

    // Check URL validity
    try {
      new URL(item.url);
      score += 20;
    } catch (e) {
      flags.push('invalid_url');
    }

    // Check domain quality (not perfect, but basic check)
    if (!item.host_name.includes('spam') && 
        !item.host_name.includes('ads')) {
      score += 20;
    } else {
      flags.push('suspicious_domain');
    }

    // Check title quality
    if (item.name && item.name.length > 10) {
      score += 20;
    } else {
      flags.push('short_title');
    }

    return {
      ...item,
      qualityScore: score,
      validationFlags: flags,
      isHighQuality: score >= 80
    };
  });

  // Sort by quality score
  return validated.sort((a, b) => b.qualityScore - a.qualityScore);
}

// Usage
const validated = await validateSearchResults('best programming practices');
console.log('High quality results:', 
  validated.filter(r => r.isHighQuality).length
);
```

## Best Practices

### 1. Query Optimization

```javascript
// Bad: Too vague
const bad = await searchWeb('information');

// Good: Specific and targeted
const good = await searchWeb('JavaScript async/await best practices 2024');

// Good: Include context
const goodWithContext = await searchWeb('React hooks tutorial for beginners');
```

### 2. Error Handling

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function safeSearch(query, retries = 3) {
  let lastError;

  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const zai = await ZAI.create();

      const results = await zai.functions.invoke('web_search', {
        query: query,
        num: 10
      });

      if (!Array.isArray(results) || results.length === 0) {
        throw new Error('No results found or invalid response');
      }

      return {
        success: true,
        results: results,
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

### 3. Result Caching

```javascript
import ZAI from 'z-ai-web-dev-sdk';

class CachedSearch {
  constructor(cacheDuration = 3600000) { // 1 hour default
    this.cache = new Map();
    this.cacheDuration = cacheDuration;
    this.zai = null;
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  getCacheKey(query, num) {
    return `${query}_${num}`;
  }

  async search(query, num = 10) {
    const cacheKey = this.getCacheKey(query, num);
    const cached = this.cache.get(cacheKey);

    // Check if cached and not expired
    if (cached && Date.now() - cached.timestamp < this.cacheDuration) {
      console.log('Returning cached results');
      return {
        ...cached.data,
        cached: true
      };
    }

    // Perform fresh search
    const results = await this.zai.functions.invoke('web_search', {
      query: query,
      num: num
    });

    // Cache results
    this.cache.set(cacheKey, {
      data: results,
      timestamp: Date.now()
    });

    return {
      results: results,
      cached: false
    };
  }

  clearCache() {
    this.cache.clear();
  }

  getCacheSize() {
    return this.cache.size;
  }
}

// Usage
const search = new CachedSearch(1800000); // 30 minutes cache
await search.initialize();

const result1 = await search.search('TypeScript tutorial');
console.log('Cached:', result1.cached); // false

const result2 = await search.search('TypeScript tutorial');
console.log('Cached:', result2.cached); // true
```

### 4. Rate Limiting

```javascript
class RateLimitedSearch {
  constructor(requestsPerMinute = 60) {
    this.zai = null;
    this.requestsPerMinute = requestsPerMinute;
    this.requests = [];
  }

  async initialize() {
    this.zai = await ZAI.create();
  }

  async search(query, num = 10) {
    await this.checkRateLimit();

    const results = await this.zai.functions.invoke('web_search', {
      query: query,
      num: num
    });

    this.requests.push(Date.now());
    return results;
  }

  async checkRateLimit() {
    const now = Date.now();
    const oneMinuteAgo = now - 60000;

    // Remove requests older than 1 minute
    this.requests = this.requests.filter(time => time > oneMinuteAgo);

    if (this.requests.length >= this.requestsPerMinute) {
      const oldestRequest = this.requests[0];
      const waitTime = 60000 - (now - oldestRequest);
      
      console.log(`Rate limit reached. Waiting ${waitTime}ms`);
      await new Promise(resolve => setTimeout(resolve, waitTime));
      
      // Recheck after waiting
      return this.checkRateLimit();
    }
  }
}
```

## Common Use Cases

1. **Real-time Information Retrieval**: Get current news, stock prices, weather
2. **Research & Analysis**: Gather information on specific topics
3. **Content Discovery**: Find articles, tutorials, documentation
4. **Competitive Analysis**: Research competitors and market trends
5. **Fact Checking**: Verify information against web sources
6. **SEO & Content Research**: Analyze search results for content strategy
7. **News Aggregation**: Collect news from various sources
8. **Academic Research**: Find papers, studies, and academic content

## Integration Examples

### Express.js Search API

```javascript
import express from 'express';
import ZAI from 'z-ai-web-dev-sdk';

const app = express();
app.use(express.json());

let zaiInstance;

async function initZAI() {
  zaiInstance = await ZAI.create();
}

app.get('/api/search', async (req, res) => {
  try {
    const { q: query, num = 10 } = req.query;

    if (!query) {
      return res.status(400).json({ error: 'Query parameter "q" is required' });
    }

    const numResults = Math.min(parseInt(num) || 10, 20);

    const results = await zaiInstance.functions.invoke('web_search', {
      query: query,
      num: numResults
    });

    res.json({
      success: true,
      query: query,
      totalResults: results.length,
      results: results
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/search/news', async (req, res) => {
  try {
    const { topic, timeframe = 'recent' } = req.query;

    if (!topic) {
      return res.status(400).json({ error: 'Topic parameter is required' });
    }

    const timeKeywords = {
      recent: 'latest news',
      today: 'today news',
      week: 'this week news'
    };

    const query = `${topic} ${timeKeywords[timeframe] || timeKeywords.recent}`;

    const results = await zaiInstance.functions.invoke('web_search', {
      query: query,
      num: 15
    });

    // Sort by date
    const sortedResults = results.sort((a, b) => {
      return new Date(b.date) - new Date(a.date);
    });

    res.json({
      success: true,
      topic: topic,
      timeframe: timeframe,
      results: sortedResults
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
    console.log('Search API running on port 3000');
  });
});
```

### Search with AI Summary

```javascript
import ZAI from 'z-ai-web-dev-sdk';

async function searchAndSummarize(query) {
  const zai = await ZAI.create();

  // Step 1: Search the web
  const searchResults = await zai.functions.invoke('web_search', {
    query: query,
    num: 10
  });

  // Step 2: Create summary using chat completions
  const searchContext = searchResults
    .slice(0, 5)
    .map((r, i) => `${i + 1}. ${r.name}\n${r.snippet}`)
    .join('\n\n');

  const completion = await zai.chat.completions.create({
    messages: [
      {
        role: 'assistant',
        content: 'You are a research assistant. Summarize search results clearly and concisely.'
      },
      {
        role: 'user',
        content: `Query: "${query}"\n\nSearch Results:\n${searchContext}\n\nProvide a comprehensive summary of these results.`
      }
    ],
    thinking: { type: 'disabled' }
  });

  const summary = completion.choices[0]?.message?.content;

  return {
    query: query,
    summary: summary,
    sources: searchResults.slice(0, 5).map(r => ({
      title: r.name,
      url: r.url
    })),
    totalResults: searchResults.length
  };
}

// Usage
const result = await searchAndSummarize('benefits of renewable energy');
console.log('Summary:', result.summary);
console.log('Sources:', result.sources);
```

## Troubleshooting

**Issue**: "SDK must be used in backend"
- **Solution**: Ensure z-ai-web-dev-sdk is only imported and used in server-side code

**Issue**: Empty or no results returned
- **Solution**: Try different query terms, check internet connectivity, verify API status

**Issue**: Unexpected response format
- **Solution**: Verify the response is an array, check for API changes, add type validation

**Issue**: Rate limiting errors
- **Solution**: Implement request throttling, add delays between searches, use caching

**Issue**: Low quality search results
- **Solution**: Refine query terms, filter results by domain or date, validate result quality

## Performance Tips

1. **Reuse SDK Instance**: Create ZAI instance once and reuse across searches
2. **Implement Caching**: Cache search results to reduce API calls
3. **Optimize Query Terms**: Use specific, targeted queries for better results
4. **Limit Result Count**: Request only the number of results you need
5. **Parallel Searches**: Use Promise.all for multiple independent searches
6. **Result Filtering**: Filter results on client side when possible

## Security Considerations

1. **Input Validation**: Sanitize and validate user search queries
2. **Rate Limiting**: Implement rate limits to prevent abuse
3. **API Key Protection**: Never expose SDK credentials in client-side code
4. **Result Filtering**: Filter potentially harmful or inappropriate content
5. **URL Validation**: Validate URLs before redirecting users
6. **Privacy**: Don't log sensitive user search queries

## Remember

- Always use z-ai-web-dev-sdk in backend code only
- The SDK is already installed - import as shown in examples
- Search results are returned as an array of SearchFunctionResultItem objects
- Implement proper error handling and retries for production
- Cache results when appropriate to reduce API calls
- Use specific query terms for better search results
- Validate and filter results before displaying to users
- Check `scripts/web_search.ts` for a quick start example
