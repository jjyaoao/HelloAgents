import ZAI from 'z-ai-web-dev-sdk';

interface PageReaderFunctionResult {
  code: number;
  data: {
    html: string;
    publishedTime?: string;
    title: string;
    url: string;
    usage: {
      tokens: number;
    };
  };
  meta: {
    usage: {
      tokens: number;
    };
  };
  status: number;
}

async function main(url: string) {
  try {
    const zai = await ZAI.create();

    const results: PageReaderFunctionResult = await zai.functions.invoke('page_reader', {
      url: url
    });

    console.log('Web reader invocation succeeded. Results:');
    console.log(JSON.stringify(results, null, 2));
  } catch (err: any) {
    console.error('page_reader failed:', err?.message || err);
  }
}

main('https://www.google.com');
