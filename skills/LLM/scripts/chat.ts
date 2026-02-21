import ZAI, { ChatMessage } from "z-ai-web-dev-sdk";

async function main(prompt: string) {
  try {
    const zai = await ZAI.create();

    const messages: ChatMessage[] = [
      {
        role: "assistant",
        content: "Hi, I'm a helpful assistant."
      },
      {
        role: "user",
        content: prompt,
      },
    ];

    const response = await zai.chat.completions.create({
      messages,
      stream: false,
      thinking: { type: "disabled" },
    });

    const reply = response.choices?.[0]?.message?.content;
    console.log("Chat reply:");
    console.log(reply ?? JSON.stringify(response, null, 2));
  } catch (err: any) {
    console.error("Chat failed:", err?.message || err);
  }
}

main('What is the capital of France?');
