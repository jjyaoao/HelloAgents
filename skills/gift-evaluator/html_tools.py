import os
import argparse
import json
import html
import base64
import mimetypes
import urllib.request

def generate_gift_card(product_name, price, evaluation, thank_you_json, return_gift_json, vibe_code, image_url, output_path="gift_card_result.html"):
    """
    生成现代风格的交互式礼品鉴定卡片。
    """
    
    # --- 图片转 Base64 逻辑 (保持上一步功能) ---
    final_image_src = image_url
    try:
        image_data = None
        mime_type = None
        if image_url.startswith(('http://', 'https://')):
            req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                image_data = response.read()
                mime_type = response.headers.get_content_type()
        else:
            if os.path.exists(image_url):
                mime_type, _ = mimetypes.guess_type(image_url)
                with open(image_url, "rb") as f:
                    image_data = f.read()
        
        if image_data:
            if not mime_type: mime_type = "image/jpeg"
            b64_str = base64.b64encode(image_data).decode('utf-8')
            final_image_src = f"data:{mime_type};base64,{b64_str}"
            
    except Exception as e:
        print(f"⚠️ 图片转换 Base64 失败，使用原链接。错误: {e}")

    # --- 1. 数据解析 ---
    try:
        thank_you_data = json.loads(thank_you_json)
    except:
        thank_you_data = [{"style": "通用版", "content": thank_you_json}]

    try:
        return_gift_data = json.loads(return_gift_json)
    except:
        return_gift_data = [{"target": "通用建议", "item": return_gift_json, "reason": "万能回礼"}]

    # --- 2. 风格配置 ---
    styles = {
        "luxury": { 
            "page_bg": "bg-neutral-900",
            "card_bg": "bg-neutral-900/80 backdrop-blur-xl border border-white/10",
            "text_main": "text-white", "text_sub": "text-neutral-400",
            "accent": "text-amber-400", "tag_bg": "bg-amber-400/20 text-amber-400",
            "btn_hover": "hover:bg-amber-400 hover:text-black",
            "img_bg": "bg-neutral-800" # 图片衬底色
        },
        "standard": { 
            "page_bg": "bg-stone-200",
            "card_bg": "bg-white/95 backdrop-blur-xl border border-stone-200",
            "text_main": "text-stone-800", "text_sub": "text-stone-500",
            "accent": "text-red-600", "tag_bg": "bg-red-50 text-red-600",
            "btn_hover": "hover:bg-red-600 hover:text-white",
            "img_bg": "bg-stone-100"
        },
        "budget": { 
            "page_bg": "bg-yellow-50",
            "card_bg": "bg-white border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]",
            "text_main": "text-black", "text_sub": "text-gray-600",
            "accent": "text-blue-600", "tag_bg": "bg-black text-white",
            "btn_hover": "hover:bg-blue-600 hover:text-white",
            "img_bg": "bg-gray-200"
        }
    }
    st = styles.get(vibe_code, styles["standard"])
    if "img_bg" not in st: st["img_bg"] = "bg-black/5" # 兼容兜底

    # --- 3. 辅助逻辑 ---
    is_dark_mode = "text-white" in st['text_main']
    bubble_bg = "bg-white/10 border-white/10" if is_dark_mode else "bg-black/5 border-black/5"
    bubble_hover = "hover:bg-white/20" if is_dark_mode else "hover:bg-black/10"
    divider_color = "border-white/20" if is_dark_mode else "border-black/10"

    # --- 4. HTML 构建 ---
    thank_you_html = ""
    for item in thank_you_data:
        thank_you_html += f"""
        <div class="group relative p-4 rounded-xl {bubble_bg} border {bubble_hover} transition-all cursor-pointer mb-3" onclick="copyText(this, '{html.escape(item['content'], quote=True)}')">
            <div class="flex justify-between items-center mb-2">
                <span class="text-xs font-bold {st['accent']} border border-current px-2 py-0.5 rounded-full">{item['style']}</span>
                <span class="text-[10px] opacity-60 group-hover:opacity-100 transition-opacity {st['text_sub']} flex items-center gap-1">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                    点击复制
                </span>
            </div>
            <p class="text-sm {st['text_main']} leading-relaxed opacity-95 font-medium">{item['content']}</p>
            <div class="copy-feedback absolute inset-0 bg-{st['accent'].split('-')[1]}-500 text-white flex items-center justify-center rounded-xl opacity-0 pointer-events-none transition-opacity duration-200 font-bold z-10">
                <span>✓ 已复制</span>
            </div>
        </div>
        """

    return_gift_html = ""
    for item in return_gift_data:
        return_gift_html += f"""
        <div class="p-4 rounded-xl {bubble_bg} border flex flex-col justify-between h-full hover:scale-[1.02] transition-transform duration-300">
            <div class="flex items-center gap-2 mb-2">
                 <div class="w-1.5 h-1.5 rounded-full bg-current {st['accent']}"></div>
                 <div class="text-xs font-bold uppercase tracking-wider {st['text_sub']}">{item['target']}</div>
            </div>
            <div class="font-bold {st['text_main']} text-lg mb-2">{item['item']}</div>
            <div class="text-xs {st['text_sub']} opacity-80 leading-snug bg-black/5 dark:bg-white/5 p-2 rounded">{item['reason']}</div>
        </div>
        """

    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>礼品鉴定报告</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Noto+Serif+SC:wght@700;900&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; }} 
        .serif {{ font-family: 'Noto Serif SC', serif; }} 
        /* 通用滚动条样式 */
        .custom-scroll::-webkit-scrollbar {{ width: 4px; }}
        .custom-scroll::-webkit-scrollbar-thumb {{ background-color: rgba(150,150,150,0.3); border-radius: 4px; }}
        .custom-scroll:hover::-webkit-scrollbar-thumb {{ background-color: rgba(150,150,150,0.6); }}
    </style>
</head>
<body class="{st['page_bg']} min-h-screen flex items-center justify-center p-2 md:p-8 selection:bg-red-200 selection:text-red-900">
    <div class="w-full max-w-6xl {st['card_bg']} rounded-[2.5rem] shadow-2xl overflow-hidden relative flex flex-col md:flex-row md:h-[750px] transition-all duration-500">
        
        <div class="w-full md:w-[45%] flex flex-col relative shrink-0 border-b md:border-b-0 md:border-r {divider_color}">
            
            <div class="relative h-72 md:h-[55%] group overflow-hidden {st['img_bg']} flex items-center justify-center p-6">
                <img src="{final_image_src}" class="w-full h-full object-contain relative z-10 drop-shadow-xl transition-transform duration-700 group-hover:scale-105">
                
                <div class="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-black/80 to-transparent z-20 pointer-events-none"></div>
                
                <div class="absolute bottom-6 left-6 right-6 z-30">
                    <div class="inline-block px-3 py-1 rounded-lg text-[10px] font-bold uppercase tracking-widest mb-2 {st['tag_bg']} backdrop-blur-md shadow-lg">
                        AI Gift Analysis
                    </div>
                    <h1 class="text-3xl md:text-4xl font-black text-white leading-tight serif mb-1 drop-shadow-md truncate">{product_name}</h1>
                    <div class="flex items-baseline gap-2 text-white/90">
                        <span class="text-sm font-light opacity-80">当前估值</span>
                        <span class="text-3xl font-bold tracking-tight">{price}</span>
                    </div>
                </div>
            </div>

            <div class="flex-1 p-6 md:p-8 flex flex-col min-h-0 bg-inherit relative">
                <div class="absolute top-0 left-8 -mt-5 text-6xl opacity-20 {st['text_main']} font-serif select-none">“</div>
                
                <h3 class="text-xs font-bold uppercase tracking-widest {st['text_sub']} mb-3 flex items-center gap-2 shrink-0">
                    <span class="w-8 h-[1px] bg-current opacity-50"></span>
                    专家鉴定评价
                </h3>
                
                <div class="{st['text_main']} text-base md:text-lg leading-relaxed italic font-medium relative z-10 overflow-y-auto custom-scroll flex-1 pr-2">
                    {evaluation}
                </div>
                
                <div class="mt-4 pt-4 border-t {divider_color} flex items-center gap-3 shrink-0">
                    <div class="w-8 h-8 rounded-full {st['tag_bg']} flex items-center justify-center font-bold text-xs">AI</div>
                    <div class="flex flex-col">
                        <span class="text-xs font-bold {st['text_main']}">首席鉴定官</span>
                        <span class="text-[10px] {st['text_sub']}">Verified Analysis</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="w-full md:w-[55%] overflow-y-auto custom-scroll p-6 md:p-10 flex flex-col gap-8 bg-inherit">
            <div>
                <div class="flex items-center gap-3 mb-5 border-b {divider_color} pb-3">
                    <div class="p-2 rounded-lg {st['tag_bg']}">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"></path></svg>
                    </div>
                    <div>
                        <h2 class="text-xl md:text-2xl font-bold {st['text_main']}">私信回复话术</h2>
                        <p class="text-xs {st['text_sub']}">高情商回复，点击卡片即可复制</p>
                    </div>
                </div>
                <div class="space-y-1">
                    {thank_you_html}
                </div>
            </div>

            <div>
                <div class="flex items-center gap-3 mb-5 mt-2 border-b {divider_color} pb-3">
                    <div class="p-2 rounded-lg {st['tag_bg']}">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7"></path></svg>
                    </div>
                    <div>
                        <h2 class="text-xl md:text-2xl font-bold {st['text_main']}">推荐回礼策略</h2>
                        <p class="text-xs {st['text_sub']}">基于价格区间的最优解</p>
                    </div>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {return_gift_html}
                </div>
            </div>

            <div class="mt-auto pt-8 text-center opacity-40">
                <p class="text-[10px] {st['text_sub']}">Designed by AI Gift Agent • 春节特别版</p>
            </div>
        </div>
    </div>

    <script>
        function copyText(element, text) {{
            navigator.clipboard.writeText(text).then(() => {{
                const feedback = element.querySelector('.copy-feedback');
                feedback.classList.remove('opacity-0');
                feedback.classList.remove('pointer-events-none');
                setTimeout(() => {{ 
                    feedback.classList.add('opacity-0'); 
                    feedback.classList.add('pointer-events-none');
                }}, 1500);
            }});
        }}
    </script>
</body>
</html>
    """

    try:
        directory = os.path.dirname(output_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return os.path.abspath(output_path)
    except Exception as e:
        return f"Error saving HTML file: {str(e)}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Gift Card HTML")
    parser.add_argument("action", nargs="?", help="Action command")
    parser.add_argument("--product_name", required=True)
    parser.add_argument("--price", required=True)
    parser.add_argument("--evaluation", required=True)
    parser.add_argument("--thank_you_json", required=True)
    parser.add_argument("--return_gift_json", required=True)
    parser.add_argument("--vibe_code", required=True)
    parser.add_argument("--image_url", required=True)
    parser.add_argument("--output_path", required=True)

    args = parser.parse_args()

    result_path = generate_gift_card(
        product_name=args.product_name,
        price=args.price,
        evaluation=args.evaluation,
        thank_you_json=args.thank_you_json,
        return_gift_json=args.return_gift_json,
        vibe_code=args.vibe_code,
        image_url=args.image_url,
        output_path=args.output_path
    )

    print(f"HTML Card generated successfully: {result_path}")