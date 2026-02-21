import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";

async function main(text: string, outFile: string) {
  try {
    const zai = await ZAI.create();

    const response = await zai.audio.tts.create({
      input: text,
      voice: "tongtong",
      speed: 1.0,
      response_format: "wav",
      stream: false,
    });

    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(new Uint8Array(arrayBuffer));
    fs.writeFileSync(outFile, buffer);
    console.log(`TTS audio saved to ${outFile}`);
  } catch (err: any) {
    console.error("TTS failed:", err?.message || err);
  }
}

main("Hello, world!", "./output.wav");
