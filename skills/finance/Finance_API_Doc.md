# Finance API Complete Documentation

## API Overview

Finance API provides comprehensive financial data access interfaces, including real-time market data, historical stock prices, and the latest financial news.

### 🌐 Access via API Gateway

**This API is accessed through the web-dev-ai-gateway unified proxy service.**

**Gateway Configuration:**
- **Gateway Base URL:** `GATEWAY_URL` (e.g., `https://internal-api.z.ai`)
- **API Path Prefix:** `API_PREFIX` (e.g., `/external/finance`)
- **Authentication:** Automatic (gateway injects `x-rapidapi-host` and `x-rapidapi-key`)
- **Required Header:** `X-Z-AI-From: Z`

**URL Structure:**
```
{GATEWAY_URL}{API_PREFIX}/{endpoint}
```

**Example:**
- Full URL: `https://internal-api.z.ai/external/finance/v1/markets/search?search=Apple`
- Breakdown:
  - `https://internal-api.z.ai` - Gateway base URL (`GATEWAY_URL`)
  - `/external/finance` - API path prefix (`API_PREFIX`)
  - `/v1/markets/search` - API endpoint path


### Quick Start

```bash
# Get real-time quote for Apple
curl -X GET "{GATEWAY_URL}{API_PREFIX}/v1/markets/quote?ticker=AAPL&type=STOCKS" \
  -H "X-Z-AI-From: Z"
```


## 1. Market Data API

### 1.1 GET v2/markets/tickers - Get All Available Market Tickers

**Parameters:**
- `page` (optional, Number): Page number, default value is 1
- `type` (required, String): Asset type, optional values:
  - `STOCKS` - Stocks
  - `ETF` - Exchange Traded Funds
  - `MUTUALFUNDS` - Mutual Funds

**curl example (via Gateway):**
```bash
curl -X GET "{GATEWAY_URL}{API_PREFIX}/v2/markets/tickers?page=1&type=STOCKS" \
  -H "X-Z-AI-From: Z"
```

---

### 1.2 GET v1/markets/search - Search Stocks

**Parameters:**
- `search` (required, String): Search keyword (company name or stock symbol)

**curl example (via Gateway):**
```bash
curl -X GET "{GATEWAY_URL}{API_PREFIX}/v1/markets/search?search=Apple" \
  -H "X-Z-AI-From: Z"
```

**Purpose:** Used to find specific stock or company ticker codes

---

### 1.3 GET v1/markets/quote (real-time) - Real-time Quotes

**Parameters:**
- `ticker` (required, String): Stock symbol (only one can be entered)
- `type` (required, String): Asset type
  - `STOCKS` - Stocks
  - `ETF` - Exchange Traded Funds
  - `MUTUALFUNDS` - Mutual Funds

**curl example (via Gateway):**
```bash
curl -X GET "{GATEWAY_URL}{API_PREFIX}/v1/markets/quote?ticker=AAPL&type=STOCKS" \
  -H "X-Z-AI-From: Z"
```

---

### 1.4 GET v1/markets/stock/quotes (snapshots) - Snapshot Quotes

**Parameters:**
- `ticker` (required, String): Stock symbols, separated by commas

**curl example:**
```bash
curl --request GET \
  --url '{GATEWAY_URL}{API_PREFIX}/v1/markets/stock/quotes?ticker=AAPL%2CMSFT%2C%5ESPX%2C%5ENYA%2CGAZP.ME%2CSIBN.ME%2CGEECEE.NS'
```

**Purpose:** Batch get snapshot data for multiple stocks

---


## 2. Historical Data API

### 2.1 GET v1/markets/stock/history - Stock Historical Data

**Parameters:**
- `symbol` (required, String): Stock symbol
- `interval` (required, String): Time interval
  - `5m` - 5 minutes
  - `15m` - 15 minutes
  - `30m` - 30 minutes
  - `1h` - 1 hour
  - `1d` - Daily
  - `1wk` - Weekly
  - `1mo` - Monthly
  - `3mo` - 3 months
- `diffandsplits` (optional, String): Include dividend and split data
  - `true` - Include
  - `false` - Exclude (default)

**curl example:**
```bash
curl --request GET \
  --url '{GATEWAY_URL}{API_PREFIX}/v1/markets/stock/history?symbol=AAPL&interval=1d&diffandsplits=false'
```

**Purpose:** Get historical price data for specific stocks, used for technical analysis and backtesting

---

### 2.2 GET v2/markets/stock/history - Stock Historical Data V2

**Parameters:**
- `symbol` (required, String): Stock symbol
- `interval` (optional, String): Time interval
  - `1m`, `2m`, `3m`, `4m`, `5m`, `15m`, `30m`
  - `1h`, `1d`, `1wk`, `1mo`, `1qty`
- `limit` (optional, Number): Limit the number of candles (1-1000)
- `dividend` (optional, String): Include dividend data (`true` or `false`)

**curl example:**
```bash
curl --request GET \
  --url '{GATEWAY_URL}{API_PREFIX}/v2/markets/stock/history?symbol=AAPL&interval=1m&limit=640'
```

**Purpose:** Enhanced historical data interface

---

## 3. News API

### 3.1 GET v1/markets/news - Market News

**Parameters:**
- `ticker` (optional, String): Stock symbols, comma-separated for multiple stocks

**curl example:**
```bash
# Get general market news
curl --request GET \
  --url '{GATEWAY_URL}{API_PREFIX}/v1/markets/news'

# Get specific stock news
curl --request GET \
  --url '{GATEWAY_URL}{API_PREFIX}/v1/markets/news?ticker=AAPL,TSLA'
```

**Purpose:** Get the latest market news and updates

---

### 3.2 GET v2/markets/news - Market News V2

**Parameters:**
- `ticker` (optional, String): Stock symbol
- `type` (optional, String): News type (`ALL`, `VIDEO`, `PRESS-RELEASE`)

**curl example:**
```bash
curl --request GET \
  --url '{GATEWAY_URL}{API_PREFIX}/v2/markets/news?ticker=AAPL&type=ALL'
```

**Purpose:** Enhanced interface for getting latest market-related news

---

## 5. Stock Detailed Information API

### 5.1 GET v1/markets/stock/modules (asset-profile) - Company Profile

**Parameters:**
- `ticker` (required, String): Stock symbol

**curl example:**
```bash
curl --request GET \
  --url '{GATEWAY_URL}{API_PREFIX}/v1/markets/stock/modules?ticker=AAPL&module=asset-profile'
```

**Purpose:** Get company basic information, business description, management team, etc.

---

### 5.2 GET v1/stock/modules - Stock Module Data

**Parameters:**
- `ticker` (required, String): Stock symbol
- `module` (required, String): Module name (one per request)
  - Acceptable values: `profile`, `income-statement`, `balance-sheet`, `cashflow-statement`,
    `statistics`, `calendar-events`, `sec-filings`, `recommendation-trend`,
    `upgrade-downgrade-history`, `institution-ownership`, `fund-ownership`,
    `major-directHolders`, `major-holders-breakdown`, `insider-transactions`,
    `insider-holders`, `net-share-purchase-activity`, `earnings`, `industry-trend`,
    `index-trend`, `sector-trend`

**curl example:**
```bash
# Get specific module
curl --request GET \
  --url '{GATEWAY_URL}{API_PREFIX}/v1/markets/stock/modules?ticker=AAPL&module=statistics'
```

**Purpose:** Get one data module per request (price, financial, analyst ratings, etc.)

---

### 5.3 GET v1/markets/stock/modules (statistics) - Stock Statistics

**Parameters:**
- `ticker` (required, String): Stock symbol

**curl example:**
```bash
curl --request GET \
  --url '{GATEWAY_URL}{API_PREFIX}/v1/markets/stock/modules?ticker=AAPL&module=statistics'
```

**Purpose:** Get key statistical indicators such as PE ratios, market cap, trading volume

---

### 5.4 GET v1/markets/stock/modules (financial-data) - Get Financial Data

**Parameters:**
- `ticker` (required, String): Stock symbol
- `module` (required, String): `financial-data`

**curl example:**
```bash
curl --request GET \
  --url '{GATEWAY_URL}{API_PREFIX}/v1/markets/stock/modules?ticker=AAPL&module=financial-data'
```

**Purpose:** Get revenue, profit, cash flow and other financial indicators

---

### 5.5 GET v1/markets/stock/modules (sec-filings) - Get SEC Filings

**Parameters:**
- `ticker` (required, String): Stock symbol
- `module` (required, String): `sec-filings`

**curl example:**
```bash
curl --request GET \
  --url '{GATEWAY_URL}{API_PREFIX}/v1/markets/stock/modules?ticker=AAPL&module=sec-filings'
```

**Purpose:** Get files submitted by companies to the U.S. Securities and Exchange Commission

---

### 5.6 GET v1/markets/stock/modules (earnings) - Earnings Data

**Parameters:**
- `ticker` (required, String): Stock symbol

**curl example:**
```bash
curl --request GET \
  --url '{GATEWAY_URL}{API_PREFIX}/v1/markets/stock/modules?ticker=AAPL&module=earnings'
```

**Purpose:** Get quarterly and annual earnings information

---

### 5.7 GET v1/markets/stock/modules (calendar-events) - Get Calendar Events

**Parameters:**
- `ticker` (required, String): Stock symbol
- `module` (required, String): `calendar-events`

**curl example:**
```bash
curl --request GET \
  --url '{GATEWAY_URL}{API_PREFIX}/v1/markets/stock/modules?ticker=AAPL&module=calendar-events'
```

**Purpose:** Get upcoming earnings release dates, dividend dates, etc.

---

## 6. Financial Statements API

### 7.1 GET v1/markets/stock/modules (balance-sheet) - Balance Sheet

**Parameters:**
- `ticker` (required, String): Stock symbol

**curl example:**
```bash
curl --request GET \
  --url '{GATEWAY_URL}{API_PREFIX}/v1/markets/stock/modules?ticker=AAPL&module=balance-sheet'
```

**Purpose:** Get company balance sheet data

---

### 7.3 GET v1/markets/stock/modules (income-statement) - Income Statement

**Parameters:**
- `ticker` (required, String): Stock symbol

**curl example:**
```bash
curl --request GET \
  --url '{GATEWAY_URL}{API_PREFIX}/v1/markets/stock/modules?ticker=AAPL&module=income-statement'
```

**Purpose:** Get company income statement data

---

### 7.4 GET v1/markets/stock/modules (cashflow-statement) - Cash Flow Statement

**Parameters:**
- `ticker` (required, String): Stock symbol

**curl example:**
```bash
curl --request GET \
  --url '{GATEWAY_URL}{API_PREFIX}/v1/markets/stock/modules?ticker=AAPL&module=cashflow-statement'
```

**Purpose:** Get company cash flow statement data

---

## Usage Flow Examples

### Example 1: Find and Get Real-time Stock Data

```bash
# 1. Search company
GET /v1/markets/search?search=Apple

# 2. Get real-time quote
GET /v1/markets/quote?ticker=AAPL&type=STOCKS

# 3. Get detailed information
GET /v1/markets/stock/modules?ticker=AAPL&module=asset-profile
```

### Example 2: Analyze Stock Investment Value

```bash
# 1. Get financial data
GET /v1/markets/stock/modules?ticker=AAPL&module=financial-data

# 2. Get earnings data
GET /v1/markets/stock/modules?ticker=AAPL&module=earnings
```

---

## Usage Tips

### 1. Batch Query Optimization
```bash
# Get data for multiple stocks at once (snapshots endpoint) via Gateway
curl -X GET "{GATEWAY_URL}{API_PREFIX}/v1/markets/stock/quotes?ticker=AAPL,MSFT,GOOGL,AMZN,TSLA" \
  -H "X-Z-AI-From: Z"
```

### 2. Time Range Query
```bash
# Get historical data with specific interval via Gateway
curl -X GET "{GATEWAY_URL}{API_PREFIX}/v1/markets/stock/history?symbol=AAPL&interval=1d&diffandsplits=false" \
  -H "X-Z-AI-From: Z"
```

### 3. Combined Query Example
### 3. Combined Query Example

**Python example (via Gateway):**
```python
import requests

# Gateway automatically handles authentication
headers = {
    'X-Z-AI-From': 'Z'
}

gateway_url = '{GATEWAY_URL}{API_PREFIX}/v1'
symbol = 'AAPL'

# Get real-time price
quote = requests.get(f'{gateway_url}/markets/quote?ticker={symbol}&type=STOCKS', headers=headers)

# Get company profile
profile = requests.get(f'{gateway_url}/markets/stock/modules?ticker={symbol}&module=asset-profile', headers=headers)

# Get financial data
financials = requests.get(f'{gateway_url}/markets/stock/modules?ticker={symbol}&module=financial-data', headers=headers)
```


---

## Best Practices

### Gateway Usage

1. **Authentication Header** - Always include `X-Z-AI-From: Z` header

### API Usage

1. **Rate Limiting:** Pay attention to API call frequency limits to avoid being throttled
2. **Error Handling:** Implement comprehensive error handling mechanisms
3. **Data Caching:** Consider caching common requests to optimize performance
4. **Batch Queries:** Use comma-separated symbols parameter to query multiple stocks at once
5. **Timestamps:** Use Unix timestamps for historical data queries
6. **Parameter Validation:** Validate all required parameters before sending requests
7. **Response Parsing:** Implement robust JSON parsing and data validation

---
