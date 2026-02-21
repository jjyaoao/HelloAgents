import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';
import path from 'path';

async function main(inputFile: string) {
	if (!fs.existsSync(inputFile)) {
		console.error(`Audio file not found: ${inputFile}`);
        return;
	}

	try {
		const zai = await ZAI.create();

		const audioBuffer = fs.readFileSync(inputFile);
		const file_base64 = audioBuffer.toString('base64');

		const result = await zai.audio.asr.create({ file_base64 });

		console.log('Transcription result:');
		console.log(result.text ?? JSON.stringify(result, null, 2));
	} catch (err: any) {
		console.error('ASR failed:', err?.message || err);
	}
}

main('./output.wav');

