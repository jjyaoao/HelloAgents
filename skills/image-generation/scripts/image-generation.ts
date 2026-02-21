import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

async function main(prompt: string, size: '1024x1024' | '768x1344' | '864x1152' | '1344x768' | '1152x864' | '1440x720' | '720x1440', outFile: string) {
	try {
		const zai = await ZAI.create();

		const response = await zai.images.generations.create({
			prompt,
			size
		});

		const base64 = response?.data?.[0]?.base64;
		if (!base64) {
			console.error('No image data returned by the API');
			console.log('Full response:', JSON.stringify(response, null, 2));
			return;
		}

		const buffer = Buffer.from(base64, 'base64');
		fs.writeFileSync(outFile, buffer);
		console.log(`Image saved to ${outFile}`);
	} catch (err: any) {
		console.error('Image generation failed:', err?.message || err);
	}
}

main('A cute kitten', '1024x1024', './output.png');
