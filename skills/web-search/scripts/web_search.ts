import ZAI from 'z-ai-web-dev-sdk';

interface SearchFunctionResultItem {
  url: string;
  name: string;
  snippet: string;
  host_name: string;
  rank: number;
  date: string;
  favicon: string;
}

async function main(query: string, num: number = 10) {
  try {
    const zai = await ZAI.create();

    const searchResult = await zai.functions.invoke('web_search', {
      query: query,
      num: num
    });

    console.log('Search Results:');
    console.log('================\n');

    if (Array.isArray(searchResult)) {
      searchResult.forEach((item: SearchFunctionResultItem, index: number) => {
        console.log(`${index + 1}. ${item.name}`);
        console.log(`   URL: ${item.url}`);
        console.log(`   Snippet: ${item.snippet}`);
        console.log(`   Host: ${item.host_name}`);
        console.log(`   Date: ${item.date}`);
        console.log('');
      });

      console.log(`\nTotal results: ${searchResult.length}`);
    } else {
      console.log('Unexpected response format:', searchResult);
    }
  } catch (err: any) {
    console.error('Web search failed:', err?.message || err);
  }
}

main('What is the capital of France?', 5);
