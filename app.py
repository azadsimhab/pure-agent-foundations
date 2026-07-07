import datetime
import requests
import pytz
import yaml
import re
from smolagents import CodeAgent, DuckDuckGoSearchTool, load_tool, tool
from tools.final_answer import FinalAnswerTool
from tools.currency_tracker import LiveCurrencyTrackerTool
from Gradio_UI import GradioUI

# --- SELF-HEALING BACKEND IMPORT ADAPTER ---
try:
    from smolagents import HfApiModel as InferenceClientModel
except ImportError:
    try:
        from smolagents import InferenceClientModel
    except ImportError:
        from smolagents import LiteLLMModel as InferenceClientModel

# --- ARCHITECTURAL TOOLS ---

@tool
def get_current_time_in_timezone(timezone: str) -> str:
    """A tool that fetches the current local time in a specified timezone.
    Args:
        timezone: A string representing a valid timezone (e.g., 'America/New_York', 'Asia/Kolkata').
    """
    try:
        tz = pytz.timezone(timezone.strip())
        local_time = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        return f"The current local time in {timezone} is: {local_time}"
    except Exception as e:
        return f"Error fetching time for timezone '{timezone}': {str(e)}"

@tool
def web_search_resilient(query: str) -> str:
    """A resilient multi-tier web search engine that scrapes DuckDuckGo Lite HTML text parameters when direct API endpoints throw connectivity constraints.
    Args:
        query: The string search keywords to query across public search engines.
    """
    cleaned_query = query.strip()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    # Try DuckDuckGo Lite Form Fallback (Bypasses Javascript challenge mitigations)
    try:
        url = "https://lite.duckduckgo.com/lite/"
        payload = {"q": cleaned_query}
        response = requests.post(url, headers=headers, data=payload, timeout=12)
        response.raise_for_status()
        
        # Pull text using explicit regex patterns to ensure quick runtime extraction
        text = response.text
        links = re.findall(r'<td class="result-snippet">(.*?)<\/td>', text, re.DOTALL)[:4]
        snippets = [re.sub(r'<[^>]+>', '', s).strip() for s in links]
        
        if snippets:
            return "\n\n--- Unified Search Results Extracted ---\n" + "\n* ".join(snippets)
    except Exception:
        pass

    # Standard Tool Fallback Routing
    try:
        fallback_ddg = DuckDuckGoSearchTool()
        return fallback_ddg(cleaned_query)
    except Exception as e:
        return f"Search Pipeline Interrupted: High network density on Space IPs. Detail: {str(e)}"

@tool
def get_live_stock_data(tickers: str) -> str:
    """Queries live market percentage updates and current spot evaluations directly from the public Yahoo Finance API interface.
    Args:
        tickers: Comma-separated financial stock identifiers, e.g., 'AAPL, TSLA, NVDA, MSFT'.
    """
    clean_tickers = ",".join([t.strip().upper() for t in tickers.split(",")])
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={clean_tickers}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=12)
        response.raise_for_status()
        result = response.json()
        quotes = result.get("quoteResponse", {}).get("result", [])
        
        if not quotes:
            return f"Market Data Error: No active data found for tickers [{clean_tickers}]."
            
        summary = "### 📈 Live Yahoo Finance Market Feed:\n"
        for quote in quotes:
            symbol = quote.get("symbol", "N/A")
            price = quote.get("regularMarketPrice", 0.0)
            change = quote.get("regularMarketChangePercent", 0.0)
            name = quote.get("longName", symbol)
            sign = "+" if change >= 0 else ""
            summary += f"* **{name} ({symbol}):** `${price:.2f}` | `{sign}{change:.2f}%` today\n"
        return summary
    except Exception as e:
        return f"Financial API Connection Error: Direct data parsing failed. Logs: {str(e)}"

@tool
def scrape_url_to_markdown(url: str) -> str:
    """Downloads the raw HTML content of any URL, strip-filters tags, and converts the core text into clean Markdown.
    Args:
        url: The complete target URL to extract text from (e.g., 'https://en.wikipedia.org/wiki/Artificial_intelligence').
    """
    target_url = url.strip()
    if not target_url.startswith(("http://", "https://")):
        return "Validation Error: Target URL must begin with http:// or https://"
        
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(target_url, headers=headers, timeout=12)
        response.raise_for_status()
        html = response.text
        
        html = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', html, flags=re.I)
        html = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', html, flags=re.I)
        text = re.sub(r'<[^>]+>', ' ', html)
        
        lines = [line.strip() for line in text.splitlines()]
        clean_text = "\n".join(chunk for chunk in lines if chunk)[:3000]
        return clean_text + "\n\n... [Content Truncated due to Context Limits] ..."
    except Exception as e:
        return f"Scraping Transaction Failed: {str(e)}"

@tool
def generate_data_visualization_svg(chart_title: str, categories: str, values: str) -> str:
    """Generates an elegant vector SVG column bar chart supporting both positive (Green) and negative (Red) values safely.
    Args:
        chart_title: The header name of your visualization chart (e.g., 'Q3 Global Market Growth').
        categories: A comma-separated string containing item names (e.g., 'NVIDIA, Amazon, Google').
        values: A comma-separated string containing matching numerical floats/percentages (e.g., '4.2, -2.1, 1.8').
    """
    try:
        cat_list = [c.strip() for c in categories.split(",")]
        val_list = [float(v.strip()) for v in values.split(",")]
        
        if len(cat_list) != len(val_list):
            return "Configuration Error: Category count must match value count."
            
        min_val = min(val_list)
        max_val = max(val_list)
        
        val_min_bound = min(0.0, min_val)
        val_max_bound = max(0.0, max_val)
        val_range = val_max_bound - val_min_bound
        if val_range == 0: val_range = 1.0

        svg_width, svg_height = 500, 300
        padding_left, padding_right, padding_top, padding_bottom = 60, 20, 40, 50
        chart_w = svg_width - padding_left - padding_right
        chart_h = svg_height - padding_top - padding_bottom
        
        y_zero = padding_top + chart_h - ((0.0 - val_min_bound) / val_range) * chart_h
        
        svg = f'<svg viewBox="0 0 {svg_width} {svg_height}" width="100%" height="100%" style="background-color:#1e293b; border-radius:8px; font-family:sans-serif;" xmlns="http://www.w3.org/2000/svg">\n'
        svg += f'  <text x="{svg_width/2}" y="25" text-anchor="middle" fill="#f8fafc" font-size="16" font-weight="bold">{chart_title}</text>\n'
        
        grid_lines = 4
        for i in range(grid_lines + 1):
            val_grid = val_min_bound + (val_range / grid_lines) * i
            y_grid = padding_top + chart_h - (i / grid_lines) * chart_h
            svg += f'  <line x1="{padding_left}" y1="{y_grid}" x2="{svg_width - padding_right}" y2="{y_grid}" stroke="#334155" stroke-dasharray="4" stroke-width="1" />\n'
            svg += f'  <text x="{padding_left - 10}" y="{y_grid + 4}" text-anchor="end" fill="#94a3b8" font-size="10">{val_grid:.1f}</text>\n'
            
        svg += f'  <line x1="{padding_left}" y1="{y_zero}" x2="{svg_width - padding_right}" y2="{y_zero}" stroke="#94a3b8" stroke-width="1.5" />\n'
        
        num_bars = len(cat_list)
        bar_width = (chart_w / num_bars) * 0.6
        spacing = (chart_w / num_bars) * 0.4
        
        for idx, (cat, val) in enumerate(zip(cat_list, val_list)):
            y_val = padding_top + chart_h - ((val - val_min_bound) / val_range) * chart_h
            x_pos = padding_left + (idx * (bar_width + spacing)) + (spacing / 2)
            
            if val >= 0:
                bar_h = y_zero - y_val
                y_pos = y_val
                label_y_offset = -6
                color = "#10b981"  # Emerald Green for Gains
            else:
                bar_h = y_val - y_zero
                y_pos = y_zero
                label_y_offset = 12
                color = "#ef4444"  # Rose Red for Losses
                
            if bar_h < 1.0: bar_h = 1.0
                
            svg += f'  <rect x="{x_pos}" y="{y_pos}" width="{bar_width}" height="{bar_h}" rx="3" ry="3" fill="{color}" />\n'
            svg += f'  <text x="{x_pos + bar_width/2}" y="{y_pos + label_y_offset}" text-anchor="middle" fill="#f1f5f9" font-size="10" font-weight="bold">{val:.2f}%</text>\n'
            svg += f'  <text x="{x_pos + bar_width/2}" y="{svg_height - 20}" text-anchor="middle" fill="#94a3b8" font-size="10" transform="rotate(15, {x_pos + bar_width/2}, {svg_height - 20})">{cat}</text>\n'
            
        svg += '</svg>'
        return f"### SVG Vector Visualizer Success:\n\n```xml\n{svg}\n```"
    except Exception as e:
        return f"Visualization construction failed: {str(e)}"

# --- INITIALIZE SYSTEM ---
final_answer = FinalAnswerTool()
currency_tool = LiveCurrencyTrackerTool()

model = InferenceClientModel(
    max_tokens=2096,
    temperature=0.4,
    model_id='Qwen/Qwen2.5-Coder-32B-Instruct',
    custom_role_conversions=None,
)

try:
    image_generation_tool = load_tool("agents-course/text-to-image", trust_remote_code=True)
    active_tools = [final_answer, web_search_resilient, get_live_stock_data, currency_tool, image_generation_tool, get_current_time_in_timezone, scrape_url_to_markdown, generate_data_visualization_svg]
except Exception:
    active_tools = [final_answer, web_search_resilient, get_live_stock_data, currency_tool, get_current_time_in_timezone, scrape_url_to_markdown, generate_data_visualization_svg]

with open("prompts.yaml", 'r') as stream:
    prompt_templates = yaml.safe_load(stream)

agent = CodeAgent(
    model=model,
    tools=active_tools,
    max_steps=6,
    verbosity_level=1,
    grammar=None,
    planning_interval=None,
    name="Elite_Universal_Intelligence_Agent",
    description="A senior-grade multi-modal administrative agent serving deep search, global rates calculations, and automated vector diagrams.",
    prompt_templates=prompt_templates
)

GradioUI(agent).launch()