import ZAI, { VisionMessage } from 'z-ai-web-dev-sdk';

async function main(imageUrl: string, prompt: string) {
	try {
		const zai = await ZAI.create();

		const messages: VisionMessage[] = [
            {
                role: 'assistant',
                content: [
                    { type: 'text', text: 'Output only text, no markdown.' }
                ]
            },
			{
				role: 'user',
				content: [
					{ type: 'text', text: prompt },
					{ type: 'image_url', image_url: { url: imageUrl } }
				]
			}
		];

		// const messages: VisionMessage[] = [
		// 	{
		// 		role: 'user',
		// 		content: [
		// 			{ type: 'text', text: prompt },
		// 			{ type: 'video_url', video_url: { url: imageUrl } }
		// 		]
		// 	}
		// ];

		// const messages: VisionMessage[] = [
		// 	{
		// 		role: 'user',
		// 		content: [
		// 			{ type: 'text', text: prompt },
		// 			{ type: 'file_url', file_url: { url: imageUrl } }
		// 		]
		// 	}
		// ];

		const response = await zai.chat.completions.createVision({
            model: 'glm-4.6v',
			messages,
			thinking: { type: 'disabled' }
		});

		const reply = response.choices?.[0]?.message?.content;
		console.log('Vision model reply:');
		console.log(reply ?? JSON.stringify(response, null, 2));
	} catch (err: any) {
		console.error('Vision chat failed:', err?.message || err);
	}
}

main("https://cdn.bigmodel.cn/static/logo/register.png", "Please describe this image.");
