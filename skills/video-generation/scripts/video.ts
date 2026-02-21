import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";

async function create() {
  try {
    const zai = await ZAI.create();

    console.log("Creating video generation task...");

    const task = await zai.video.generations.create({
      prompt: "A cat is playing with a ball.",
      quality: "speed",
      with_audio: false,
      size: "1920x1080",
      fps: 30,
      duration: 5,
    });

    console.log(`Task created!`);
    console.log(`Task ID: ${task.id}`);
    console.log(`Task Status: ${task.task_status}`);
    console.log(`Model: ${task.model || 'N/A'}`);

    return { zai, task };
  } catch (err: any) {
    console.error("Video generation failed:", err?.message || err);
    throw err;
  }
}

/**
 * Example: Image-to-Video Generation using base64
 * IMPORTANT: Using base64-encoded image data is STRONGLY RECOMMENDED over URLs
 * for better reliability and to avoid network-related issues.
 * 
 * CRITICAL: Always match the MIME type to your actual image format.
 */
async function createFromImage(imagePath: string) {
  try {
    const zai = await ZAI.create();

    console.log("Creating image-to-video generation task...");
    console.log(`Reading image from: ${imagePath}`);

    // Read image file and convert to base64
    const imageBuffer = fs.readFileSync(imagePath);
    
    // Detect MIME type from file extension
    const imageExt = imagePath.split('.').pop()?.toLowerCase() || '';
    const mimeTypeMap: Record<string, string> = {
      'jpg': 'image/jpeg',
      'jpeg': 'image/jpeg',
      'png': 'image/png',
      'gif': 'image/gif',
      'webp': 'image/webp',
      'bmp': 'image/bmp'
    };
    const mimeType = mimeTypeMap[imageExt] || 'image/jpeg';  // Default to JPEG if unknown
    
    const base64Image = `data:${mimeType};base64,${imageBuffer.toString('base64')}`;

    console.log(`Image format detected: ${mimeType}`);
    console.log(`Image converted to base64 (${base64Image.substring(0, 50)}...)`);

    // Create video generation task with base64 image
    const task = await zai.video.generations.create({
      image_url: base64Image,  // Use base64 with correct MIME type
      prompt: "Animate this scene with gentle motion",
      quality: "quality",
      size: "1920x1080",
      fps: 30,
      duration: 5,
    });

    console.log(`Task created!`);
    console.log(`Task ID: ${task.id}`);
    console.log(`Task Status: ${task.task_status}`);
    console.log(`Model: ${task.model || 'N/A'}`);

    return { zai, task };
  } catch (err: any) {
    console.error("Image-to-video generation failed:", err?.message || err);
    throw err;
  }
}

async function query(zai: any, taskId: string) {
  try {
    // 首次查询
    let result = await zai.async.result.query(taskId);
    
    if (result.task_status === 'SUCCESS') {
      // 如果任务立即完成，直接返回结果
      console.log("\nTask completed immediately, fetching result...");
      displayResult(result);
      return result;
    }

    // 轮询查询结果
    console.log("\nPolling for result...");
    let pollCount = 0;
    const maxPolls = 30; // 最多轮询30次
    const pollInterval = 10000; // 每10秒查询一次

    while (result.task_status === 'PROCESSING' && pollCount < maxPolls) {
      pollCount++;
      console.log(`Poll ${pollCount}/${maxPolls}: Status is ${result.task_status}, waiting ${pollInterval / 1000}s...`);
      await new Promise(resolve => setTimeout(resolve, pollInterval));
      result = await zai.async.result.query(taskId);
    }

    displayResult(result);
    return result;
  } catch (err: any) {
    console.error("Query failed:", err?.message || err);
    throw err;
  }
}

async function main() {
  try {
    // Method 1: Text-to-Video (default)
    const { zai, task } = await create();
    
    // Method 2: Image-to-Video with base64 (RECOMMENDED for image input)
    // Uncomment the lines below and comment out the lines above to use image-to-video
    // Make sure to provide a valid image path
    // const { zai, task } = await createFromImage('./path/to/your/image.jpg');
    
    await query(zai, task.id);
  } catch (err: any) {
    console.error("Video generation failed:", err?.message || err);
    process.exit(1);
  }
}

function displayResult(result: any) {
  console.log("\n=== Result ===");
  console.log(`Task Status: ${result.task_status}`);
  console.log(`Model: ${result.model || 'N/A'}`);
  console.log(`Request ID: ${result.request_id || 'N/A'}`);

  if (result.task_status === 'SUCCESS') {
    // 尝试从多种可能的字段中获取视频URL
    const videoUrl = 
      result.video_result?.[0]?.url || 
      result.video_url || 
      result.url || 
      result.video;

    if (videoUrl) {
      console.log(`\n✅ Video generated successfully!`);
      console.log(`Video URL: ${videoUrl}`);
      console.log(`\nYou can open this URL in your browser or download it.`);
    } else {
      console.log(`\n⚠️ Task completed but video URL not found in response.`);
      console.log(`Full response:`, JSON.stringify(result, null, 2));
    }
  } else if (result.task_status === 'PROCESSING') {
    console.log(`\n⏳ Task is still processing. Please try again later.`);
    console.log(`Task ID: ${result.id || 'N/A'}`);
  } else if (result.task_status === 'FAIL') {
    console.log(`\n❌ Task failed.`);
    console.log(`Full response:`, JSON.stringify(result, null, 2));
  }
}

main();
