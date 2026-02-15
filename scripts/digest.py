#!/usr/bin/env python3
"""
AI Daily Digest - Kimi 2.5 Edition
从 90 个顶级技术博客抓取文章，AI 评分筛选生成日报
使用 Kimi K2.5 (kimi-coding/k2p5) 替代 Gemini
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
import urllib.request
import urllib.parse
import ssl

# ============================================================================
# Configuration Management
# ============================================================================

CONFIG_DIR = Path.home() / '.ai-daily-digest'
CONFIG_FILE = CONFIG_DIR / 'config.json'

def ensure_config_dir():
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[config] Warning: Failed to load config: {e}")
    return {}

def save_config(config: Dict[str, Any]):
    """Save configuration to file."""
    ensure_config_dir()
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"[config] Saved to {CONFIG_FILE}")
    except Exception as e:
        print(f"[config] Error: Failed to save config: {e}")

def interactive_setup():
    """Interactive configuration setup."""
    print("=" * 50)
    print("🚀 AI Daily Digest - First Time Setup")
    print("=" * 50)
    print()
    
    config = load_config()
    
    # API Key
    print("📋 Configuration (press Enter to keep existing value)")
    print()
    
    # API Key
    existing_key = config.get('api_key', '')
    if existing_key:
        masked = existing_key[:4] + '*' * (len(existing_key) - 8) + existing_key[-4:] if len(existing_key) > 8 else '****'
        print(f"API Key [{masked}]: ", end='', flush=True)
    else:
        print("API Key (Moonshot/OpenAI compatible): ", end='', flush=True)
    
    api_key = input().strip()
    if api_key:
        config['api_key'] = api_key
    elif not existing_key:
        print("⚠️  Warning: No API key provided. You'll need to set it via --api-key or MOONSHOT_API_KEY env var.")
    
    # Gateway URL
    existing_gateway = config.get('gateway_url', '')
    print(f"Gateway URL [{existing_gateway or 'None'}]: ", end='', flush=True)
    gateway = input().strip()
    if gateway:
        config['gateway_url'] = gateway
    elif existing_gateway and not gateway:
        # Keep existing
        pass
    
    # Default hours
    existing_hours = config.get('default_hours', 48)
    print(f"Default time window (hours) [{existing_hours}]: ", end='', flush=True)
    hours = input().strip()
    if hours:
        try:
            config['default_hours'] = int(hours)
        except:
            pass
    
    # Default top-n
    existing_topn = config.get('default_top_n', 15)
    print(f"Default number of articles [{existing_topn}]: ", end='', flush=True)
    topn = input().strip()
    if topn:
        try:
            config['default_top_n'] = int(topn)
        except:
            pass
    
    # Language
    existing_lang = config.get('language', 'zh')
    print(f"Output language (zh/en) [{existing_lang}]: ", end='', flush=True)
    lang = input().strip()
    if lang:
        config['language'] = lang
    
    # Output directory
    existing_output = config.get('output_dir', str(Path.home() / 'Desktop'))
    print(f"Default output directory [{existing_output}]: ", end='', flush=True)
    output_dir = input().strip()
    if output_dir:
        config['output_dir'] = output_dir
    
    # Save
    save_config(config)
    print()
    print("✅ Configuration saved!")
    print(f"   Config file: {CONFIG_FILE}")
    print()
    print("You can run 'python3 digest.py --setup' to reconfigure anytime.")
    print()
    
    return config

def get_config_value(config: Dict[str, Any], key: str, default=None):
    """Get config value with priority: env var > config file > default."""
    # Check environment variable
    env_map = {
        'api_key': 'MOONSHOT_API_KEY',
        'gateway_url': 'AI_DIGEST_GATEWAY',
        'default_hours': 'AI_DIGEST_HOURS',
        'default_top_n': 'AI_DIGEST_TOP_N',
    }
    
    if key in env_map:
        env_val = os.environ.get(env_map[key])
        if env_val:
            return env_val
    
    # Check config file
    if key in config:
        return config[key]
    
    return default

# ============================================================================
# Constants
# ============================================================================

FEED_FETCH_TIMEOUT_MS = 15000
FEED_CONCURRENCY = 10
BATCH_SIZE = 10
MAX_CONCURRENT_AI = 2

# 90 RSS feeds from Hacker News Popularity Contest 2025 (curated by Karpathy)
RSS_FEEDS = [
    {"name": "simonwillison.net", "xmlUrl": "https://simonwillison.net/atom/everything/", "htmlUrl": "https://simonwillison.net"},
    {"name": "jeffgeerling.com", "xmlUrl": "https://www.jeffgeerling.com/blog.xml", "htmlUrl": "https://jeffgeerling.com"},
    {"name": "seangoedecke.com", "xmlUrl": "https://www.seangoedecke.com/rss.xml", "htmlUrl": "https://seangoedecke.com"},
    {"name": "krebsonsecurity.com", "xmlUrl": "https://krebsonsecurity.com/feed/", "htmlUrl": "https://krebsonsecurity.com"},
    {"name": "daringfireball.net", "xmlUrl": "https://daringfireball.net/feeds/main", "htmlUrl": "https://daringfireball.net"},
    {"name": "ericmigi.com", "xmlUrl": "https://ericmigi.com/rss.xml", "htmlUrl": "https://ericmigi.com"},
    {"name": "antirez.com", "xmlUrl": "http://antirez.com/rss", "htmlUrl": "http://antirez.com"},
    {"name": "idiallo.com", "xmlUrl": "https://idiallo.com/feed.rss", "htmlUrl": "https://idiallo.com"},
    {"name": "maurycyz.com", "xmlUrl": "https://maurycyz.com/index.xml", "htmlUrl": "https://maurycyz.com"},
    {"name": "pluralistic.net", "xmlUrl": "https://pluralistic.net/feed/", "htmlUrl": "https://pluralistic.net"},
    {"name": "shkspr.mobi", "xmlUrl": "https://shkspr.mobi/blog/feed/", "htmlUrl": "https://shkspr.mobi"},
    {"name": "lcamtuf.substack.com", "xmlUrl": "https://lcamtuf.substack.com/feed", "htmlUrl": "https://lcamtuf.substack.com"},
    {"name": "mitchellh.com", "xmlUrl": "https://mitchellh.com/feed.xml", "htmlUrl": "https://mitchellh.com"},
    {"name": "dynomight.net", "xmlUrl": "https://dynomight.net/feed.xml", "htmlUrl": "https://dynomight.net"},
    {"name": "utcc.utoronto.ca/~cks", "xmlUrl": "https://utcc.utoronto.ca/~cks/space/blog/?atom", "htmlUrl": "https://utcc.utoronto.ca/~cks"},
    {"name": "xeiaso.net", "xmlUrl": "https://xeiaso.net/blog.rss", "htmlUrl": "https://xeiaso.net"},
    {"name": "devblogs.microsoft.com/oldnewthing", "xmlUrl": "https://devblogs.microsoft.com/oldnewthing/feed", "htmlUrl": "https://devblogs.microsoft.com/oldnewthing"},
    {"name": "righto.com", "xmlUrl": "https://www.righto.com/feeds/posts/default", "htmlUrl": "https://righto.com"},
    {"name": "lucumr.pocoo.org", "xmlUrl": "https://lucumr.pocoo.org/feed.atom", "htmlUrl": "https://lucumr.pocoo.org"},
    {"name": "skyfall.dev", "xmlUrl": "https://skyfall.dev/feed.xml", "htmlUrl": "https://skyfall.dev"},
    {"name": "garymarcus.substack.com", "xmlUrl": "https://garymarcus.substack.com/feed", "htmlUrl": "https://garymarcus.substack.com"},
    {"name": "rachelbythebay.com", "xmlUrl": "https://rachelbythebay.com/w/atom.xml", "htmlUrl": "https://rachelbythebay.com"},
    {"name": "overreacted.io", "xmlUrl": "https://overreacted.io/rss.xml", "htmlUrl": "https://overreacted.io"},
    {"name": "timsh.org", "xmlUrl": "https://timsh.org/rss/", "htmlUrl": "https://timsh.org"},
    {"name": "johndcook.com", "xmlUrl": "https://www.johndcook.com/blog/feed/", "htmlUrl": "https://johndcook.com"},
    {"name": "gilesthomas.com", "xmlUrl": "https://gilesthomas.com/feed/rss.xml", "htmlUrl": "https://gilesthomas.com"},
    {"name": "matklad.github.io", "xmlUrl": "https://matklad.github.io/feed.xml", "htmlUrl": "https://matklad.github.io"},
    {"name": "derekthompson.org", "xmlUrl": "https://www.theatlantic.com/feed/author/derek-thompson/", "htmlUrl": "https://derekthompson.org"},
    {"name": "evanhahn.com", "xmlUrl": "https://evanhahn.com/feed.xml", "htmlUrl": "https://evanhahn.com"},
    {"name": "terriblesoftware.org", "xmlUrl": "https://terriblesoftware.org/feed/", "htmlUrl": "https://terriblesoftware.org"},
    {"name": "rakhim.exotext.com", "xmlUrl": "https://rakhim.exotext.com/rss.xml", "htmlUrl": "https://rakhim.exotext.com"},
    {"name": "joanwestenberg.com", "xmlUrl": "https://joanwestenberg.com/rss", "htmlUrl": "https://joanwestenberg.com"},
    {"name": "xania.org", "xmlUrl": "https://xania.org/feed", "htmlUrl": "https://xania.org"},
    {"name": "micahflee.com", "xmlUrl": "https://micahflee.com/feed/", "htmlUrl": "https://micahflee.com"},
    {"name": "nesbitt.io", "xmlUrl": "https://nesbitt.io/feed.xml", "htmlUrl": "https://nesbitt.io"},
    {"name": "construction-physics.com", "xmlUrl": "https://www.construction-physics.com/feed", "htmlUrl": "https://construction-physics.com"},
    {"name": "tedium.co", "xmlUrl": "https://feed.tedium.co/", "htmlUrl": "https://tedium.co"},
    {"name": "susam.net", "xmlUrl": "https://susam.net/feed.xml", "htmlUrl": "https://susam.net"},
    {"name": "entropicthoughts.com", "xmlUrl": "https://entropicthoughts.com/feed.xml", "htmlUrl": "https://entropicthoughts.com"},
    {"name": "buttondown.com/hillelwayne", "xmlUrl": "https://buttondown.com/hillelwayne/rss", "htmlUrl": "https://buttondown.com/hillelwayne"},
    {"name": "dwarkesh.com", "xmlUrl": "https://www.dwarkeshpatel.com/feed", "htmlUrl": "https://dwarkesh.com"},
    {"name": "borretti.me", "xmlUrl": "https://borretti.me/feed.xml", "htmlUrl": "https://borretti.me"},
    {"name": "wheresyoured.at", "xmlUrl": "https://www.wheresyoured.at/rss/", "htmlUrl": "https://wheresyoured.at"},
    {"name": "jayd.ml", "xmlUrl": "https://jayd.ml/feed.xml", "htmlUrl": "https://jayd.ml"},
    {"name": "minimaxir.com", "xmlUrl": "https://minimaxir.com/index.xml", "htmlUrl": "https://minimaxir.com"},
    {"name": "geohot.github.io", "xmlUrl": "https://geohot.github.io/blog/feed.xml", "htmlUrl": "https://geohot.github.io"},
    {"name": "paulgraham.com", "xmlUrl": "http://www.aaronsw.com/2002/feeds/pgessays.rss", "htmlUrl": "https://paulgraham.com"},
    {"name": "filfre.net", "xmlUrl": "https://www.filfre.net/feed/", "htmlUrl": "https://filfre.net"},
    {"name": "blog.jim-nielsen.com", "xmlUrl": "https://blog.jim-nielsen.com/feed.xml", "htmlUrl": "https://blog.jim-nielsen.com"},
    {"name": "dfarq.homeip.net", "xmlUrl": "https://dfarq.homeip.net/feed/", "htmlUrl": "https://dfarq.homeip.net"},
    {"name": "jyn.dev", "xmlUrl": "https://jyn.dev/atom.xml", "htmlUrl": "https://jyn.dev"},
    {"name": "geoffreylitt.com", "xmlUrl": "https://www.geoffreylitt.com/feed.xml", "htmlUrl": "https://geoffreylitt.com"},
    {"name": "downtowndougbrown.com", "xmlUrl": "https://www.downtowndougbrown.com/feed/", "htmlUrl": "https://downtowndougbrown.com"},
    {"name": "brutecat.com", "xmlUrl": "https://brutecat.com/rss.xml", "htmlUrl": "https://brutecat.com"},
    {"name": "eli.thegreenplace.net", "xmlUrl": "https://eli.thegreenplace.net/feeds/all.atom.xml", "htmlUrl": "https://eli.thegreenplace.net"},
    {"name": "abortretry.fail", "xmlUrl": "https://www.abortretry.fail/feed", "htmlUrl": "https://abortretry.fail"},
    {"name": "fabiensanglard.net", "xmlUrl": "https://fabiensanglard.net/rss.xml", "htmlUrl": "https://fabiensanglard.net"},
    {"name": "oldvcr.blogspot.com", "xmlUrl": "https://oldvcr.blogspot.com/feeds/posts/default", "htmlUrl": "https://oldvcr.blogspot.com"},
    {"name": "bogdanthegeek.github.io", "xmlUrl": "https://bogdanthegeek.github.io/blog/index.xml", "htmlUrl": "https://bogdanthegeek.github.io"},
    {"name": "hugotunius.se", "xmlUrl": "https://hugotunius.se/feed.xml", "htmlUrl": "https://hugotunius.se"},
    {"name": "gwern.net", "xmlUrl": "https://gwern.substack.com/feed", "htmlUrl": "https://gwern.net"},
    {"name": "berthub.eu", "xmlUrl": "https://berthub.eu/articles/index.xml", "htmlUrl": "https://berthub.eu"},
    {"name": "chadnauseam.com", "xmlUrl": "https://chadnauseam.com/rss.xml", "htmlUrl": "https://chadnauseam.com"},
    {"name": "simone.org", "xmlUrl": "https://simone.org/feed/", "htmlUrl": "https://simone.org"},
    {"name": "it-notes.dragas.net", "xmlUrl": "https://it-notes.dragas.net/feed/", "htmlUrl": "https://it-notes.dragas.net"},
    {"name": "beej.us", "xmlUrl": "https://beej.us/blog/rss.xml", "htmlUrl": "https://beej.us"},
    {"name": "hey.paris", "xmlUrl": "https://hey.paris/index.xml", "htmlUrl": "https://hey.paris"},
    {"name": "danielwirtz.com", "xmlUrl": "https://danielwirtz.com/rss.xml", "htmlUrl": "https://danielwirtz.com"},
    {"name": "matduggan.com", "xmlUrl": "https://matduggan.com/rss/", "htmlUrl": "https://matduggan.com"},
    {"name": "refactoringenglish.com", "xmlUrl": "https://refactoringenglish.com/index.xml", "htmlUrl": "https://refactoringenglish.com"},
    {"name": "worksonmymachine.substack.com", "xmlUrl": "https://worksonmymachine.substack.com/feed", "htmlUrl": "https://worksonmymachine.substack.com"},
    {"name": "philiplaine.com", "xmlUrl": "https://philiplaine.com/index.xml", "htmlUrl": "https://philiplaine.com"},
    {"name": "steveblank.com", "xmlUrl": "https://steveblank.com/feed/", "htmlUrl": "https://steveblank.com"},
    {"name": "bernsteinbear.com", "xmlUrl": "https://bernsteinbear.com/feed.xml", "htmlUrl": "https://bernsteinbear.com"},
    {"name": "danieldelaney.net", "xmlUrl": "https://danieldelaney.net/feed", "htmlUrl": "https://danieldelaney.net"},
    {"name": "troyhunt.com", "xmlUrl": "https://www.troyhunt.com/rss/", "htmlUrl": "https://troyhunt.com"},
    {"name": "herman.bearblog.dev", "xmlUrl": "https://herman.bearblog.dev/feed/", "htmlUrl": "https://herman.bearblog.dev"},
    {"name": "tomrenner.com", "xmlUrl": "https://tomrenner.com/index.xml", "htmlUrl": "https://tomrenner.com"},
    {"name": "blog.pixelmelt.dev", "xmlUrl": "https://blog.pixelmelt.dev/rss/", "htmlUrl": "https://blog.pixelmelt.dev"},
    {"name": "martinalderson.com", "xmlUrl": "https://martinalderson.com/feed.xml", "htmlUrl": "https://martinalderson.com"},
    {"name": "danielchasehooper.com", "xmlUrl": "https://danielchasehooper.com/feed.xml", "htmlUrl": "https://danielchasehooper.com"},
    {"name": "chiark.greenend.org.uk/~sgtatham", "xmlUrl": "https://www.chiark.greenend.org.uk/~sgtatham/quasiblog/feed.xml", "htmlUrl": "https://chiark.greenend.org.uk/~sgtatham"},
    {"name": "grantslatton.com", "xmlUrl": "https://grantslatton.com/rss.xml", "htmlUrl": "https://grantslatton.com"},
    {"name": "experimental-history.com", "xmlUrl": "https://www.experimental-history.com/feed", "htmlUrl": "https://experimental-history.com"},
    {"name": "anildash.com", "xmlUrl": "https://anildash.com/feed.xml", "htmlUrl": "https://anildash.com"},
    {"name": "aresluna.org", "xmlUrl": "https://aresluna.org/main.rss", "htmlUrl": "https://aresluna.org"},
    {"name": "michael.stapelberg.ch", "xmlUrl": "https://michael.stapelberg.ch/feed.xml", "htmlUrl": "https://michael.stapelberg.ch"},
    {"name": "miguelgrinberg.com", "xmlUrl": "https://blog.miguelgrinberg.com/feed", "htmlUrl": "https://miguelgrinberg.com"},
    {"name": "keygen.sh", "xmlUrl": "https://keygen.sh/blog/feed.xml", "htmlUrl": "https://keygen.sh"},
    {"name": "mjg59.dreamwidth.org", "xmlUrl": "https://mjg59.dreamwidth.org/data/rss", "htmlUrl": "https://mjg59.dreamwidth.org"},
    {"name": "computer.rip", "xmlUrl": "https://computer.rip/rss.xml", "htmlUrl": "https://computer.rip"},
    {"name": "tedunangst.com", "xmlUrl": "https://www.tedunangst.com/flak/rss", "htmlUrl": "https://tedunangst.com"},
]

# 分类元数据
CATEGORY_META = {
    'ai-ml': {'emoji': '🤖', 'label': 'AI / ML'},
    'security': {'emoji': '🔒', 'label': '安全'},
    'engineering': {'emoji': '⚙️', 'label': '工程'},
    'tools': {'emoji': '🛠', 'label': '工具 / 开源'},
    'opinion': {'emoji': '💡', 'label': '观点 / 杂谈'},
    'other': {'emoji': '📝', 'label': '其他'},
}

# ============================================================================
# Types (simplified as dicts for Python)
# ============================================================================

# Article = {
#     'title': str, 'link': str, 'pubDate': datetime,
#     'description': str, 'sourceName': str, 'sourceUrl': str
# }
#
# ScoredArticle = Article + {
#     'score': int, 'scoreBreakdown': {...}, 'category': str,
#     'keywords': List[str], 'titleZh': str, 'summary': str, 'reason': str
# }

# ============================================================================
# Utility Functions
# ============================================================================

def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    if not text:
        return ''
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode common HTML entities
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    text = text.replace('&quot;', '"').replace('&apos;', "'")
    text = text.replace('&#39;', "'")
    return text.strip()

def parse_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats."""
    if not date_str:
        return None
    date_formats = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S %Z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%d %H:%M:%S',
        '%d %b %Y %H:%M:%S %z',
    ]
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    # Try ISO format
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except:
        pass
    return None

def parse_rss_items(xml: str) -> List[Dict[str, str]]:
    """Parse RSS/Atom items from XML."""
    items = []
    
    def get_tag_content(xml_text: str, tag: str) -> str:
        pattern = f'<{tag}[^>]*>([^<]*)</{tag}>'
        match = re.search(pattern, xml_text, re.IGNORECASE | re.DOTALL)
        return match.group(1) if match else ''
    
    # Check if it's Atom or RSS
    if '<feed' in xml[:1000] or 'xmlns="http://www.w3.org/2005/Atom"' in xml:
        # Atom format
        entry_pattern = r'<entry[^>]*>(.*?)</entry>'
        entries = re.findall(entry_pattern, xml, re.DOTALL | re.IGNORECASE)
        for entry_xml in entries:
            title = strip_html(get_tag_content(entry_xml, 'title'))
            link = ''
            # Look for link href
            link_match = re.search(r'<link[^>]*href="([^"]*)"', entry_xml, re.IGNORECASE)
            if link_match:
                link = link_match.group(1)
            else:
                link = get_tag_content(entry_xml, 'link')
            
            pub_date = get_tag_content(entry_xml, 'published') or get_tag_content(entry_xml, 'updated')
            description = strip_html(get_tag_content(entry_xml, 'summary') or get_tag_content(entry_xml, 'content'))
            
            if title or link:
                items.append({'title': title, 'link': link, 'pubDate': pub_date, 'description': description[:500]})
    else:
        # RSS format
        item_pattern = r'<item[^>]*>(.*?)</item>'
        items_xml = re.findall(item_pattern, xml, re.DOTALL | re.IGNORECASE)
        for item_xml in items_xml:
            title = strip_html(get_tag_content(item_xml, 'title'))
            link = get_tag_content(item_xml, 'link') or get_tag_content(item_xml, 'guid')
            pub_date = get_tag_content(item_xml, 'pubDate') or get_tag_content(item_xml, 'dc:date') or get_tag_content(item_xml, 'date')
            description = strip_html(get_tag_content(item_xml, 'description') or get_tag_content(item_xml, 'content:encoded'))
            
            if title or link:
                items.append({'title': title, 'link': link, 'pubDate': pub_date, 'description': description[:500]})
    
    return items

# ============================================================================
# Feed Fetching (Enhanced with retry and better error handling)
# ============================================================================

# Feeds with known issues and their fallback URLs or fixes
FEED_FALLBACKS = {
    'skyfall.dev': {
        'original': 'https://skyfall.dev/rss.xml',
        'fallback': 'https://skyfall.dev/feed.xml',  # Try alternative path
    },
    'dwarkesh.com': {
        'original': 'https://www.dwarkeshpatel.com/feed',
        'note': 'Returns 308, feed may be at different URL',
    },
    'rachelbythebay.com': {
        'note': 'SSL/TLS protocol version issue - requires TLS 1.2+',
    },
    'tedunangst.com': {
        'note': 'SSL handshake issue - may need specific TLS version',
    },
}

def create_ssl_context_legacy() -> ssl.SSLContext:
    """Create SSL context with legacy support for older servers."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    # Enable all TLS versions for compatibility
    context.minimum_version = ssl.TLSVersion.TLSv1
    return context

def create_ssl_context_modern() -> ssl.SSLContext:
    """Create SSL context for modern servers."""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context

def fetch_feed_with_retry(feed: Dict[str, str], max_retries: int = 2) -> List[Dict]:
    """Fetch articles from a single RSS feed with retry logic."""
    urls_to_try = [feed['xmlUrl']]
    
    # Check if there's a fallback URL
    feed_name = feed['name']
    if feed_name in FEED_FALLBACKS:
        fallback = FEED_FALLBACKS[feed_name].get('fallback')
        if fallback and fallback not in urls_to_try:
            urls_to_try.append(fallback)
    
    last_error = None
    
    for attempt, url in enumerate(urls_to_try):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'AI-Daily-Digest/1.0 (RSS Reader; Python urllib)',
                    'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*',
                    'Accept-Encoding': 'identity',
                    'Connection': 'close',
                }
            )
            
            # Choose SSL context based on feed
            if feed_name in ['rachelbythebay.com', 'tedunangst.com']:
                ssl_context = create_ssl_context_legacy()
            else:
                ssl_context = create_ssl_context_modern()
            
            # Open connection with redirect handling
            response = urllib.request.urlopen(
                req, 
                timeout=FEED_FETCH_TIMEOUT_MS/1000, 
                context=ssl_context
            )
            
            # Check if we got redirected
            final_url = response.geturl()
            if final_url != url:
                print(f"[digest] → {feed['name']}: redirected to {final_url[:60]}...")
            
            xml = response.read().decode('utf-8', errors='ignore')
            
            items = parse_rss_items(xml)
            
            articles = []
            for item in items:
                pub_date = parse_date(item['pubDate']) or datetime(1970, 1, 1)
                articles.append({
                    'title': item['title'],
                    'link': item['link'],
                    'pubDate': pub_date,
                    'description': item['description'],
                    'sourceName': feed['name'],
                    'sourceUrl': feed['htmlUrl'],
                })
            
            return articles
            
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}"
            # Handle redirects manually if needed
            if e.code in (301, 302, 307, 308) and 'Location' in e.headers:
                redirect_url = e.headers['Location']
                if redirect_url not in urls_to_try:
                    urls_to_try.append(redirect_url)
                    print(f"[digest] → {feed['name']}: following redirect to {redirect_url[:60]}...")
            else:
                break  # Don't retry on other HTTP errors
                
        except Exception as e:
            last_error = str(e)
            # Continue to next URL or retry
    
    # All attempts failed
    error_msg = last_error or "Unknown error"
    if 'timeout' in error_msg.lower():
        print(f"[digest] ✗ {feed['name']}: timeout")
    elif 'certificate' in error_msg.lower() or 'ssl' in error_msg.lower():
        print(f"[digest] ✗ {feed['name']}: SSL error (skipping)")
    elif '308' in error_msg or 'redirect' in error_msg.lower():
        print(f"[digest] ✗ {feed['name']}: redirect loop or permanent redirect")
    else:
        print(f"[digest] ✗ {feed['name']}: {error_msg[:60]}")
    
    return []

def fetch_feed(feed: Dict[str, str]) -> List[Dict]:
    """Fetch articles from a single RSS feed (wrapper with retry)."""
    return fetch_feed_with_retry(feed, max_retries=2)

def fetch_all_feeds(feeds: List[Dict]) -> List[Dict]:
    """Fetch articles from all feeds with concurrency control."""
    import concurrent.futures
    
    all_articles = []
    success_count = 0
    fail_count = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=FEED_CONCURRENCY) as executor:
        future_to_feed = {executor.submit(fetch_feed, feed): feed for feed in feeds}
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_feed)):
            feed = future_to_feed[future]
            try:
                articles = future.result()
                if articles:
                    all_articles.extend(articles)
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
            
            progress = min(i + 1, len(feeds))
            if (i + 1) % 10 == 0 or i == len(feeds) - 1:
                print(f"[digest] Progress: {progress}/{len(feeds)} feeds processed ({success_count} ok, {fail_count} failed)")
    
    print(f"[digest] Fetched {len(all_articles)} articles from {success_count} feeds ({fail_count} failed)")
    return all_articles

# ============================================================================
# Kimi API (via OpenClaw Gateway or direct)
# ============================================================================

def call_kimi(prompt: str, api_key: str = None, gateway_url: str = None) -> str:
    """Call Kimi K2.5 API via Moonshot API."""
    
    # Moonshot API endpoint
    url = 'https://api.moonshot.cn/v1/chat/completions'
    
    req = urllib.request.Request(
        url,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        },
        data=json.dumps({
            'model': 'kimi-k2-5',
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.3,
            'max_tokens': 4000,
        }).encode('utf-8'),
        method='POST'
    )
    
    # Create SSL context
    ssl_context = ssl.create_default_context()
    
    response = urllib.request.urlopen(req, timeout=120, context=ssl_context)
    data = json.loads(response.read().decode('utf-8'))
    
    return data['choices'][0]['message']['content'] if 'choices' in data else ''

def parse_json_response(text: str) -> Any:
    """Parse JSON response, handling markdown code blocks."""
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
    return json.loads(text)

# ============================================================================
# AI Scoring
# ============================================================================

def build_scoring_prompt(articles: List[Dict]) -> str:
    """Build prompt for scoring articles."""
    articles_list = []
    for i, a in enumerate(articles):
        articles_list.append(f"Index {i}: [{a['sourceName']}] {a['title']}\n{a['description'][:300]}")
    
    articles_text = '\n\n---\n\n'.join(articles_list)
    
    return f"""你是一个技术内容策展人，正在为一份面向技术爱好者的每日精选摘要筛选文章。

请对以下文章进行三个维度的评分（1-10 整数，10 分最高），并为每篇文章分配一个分类标签和提取 2-4 个关键词。

## 评分维度

### 1. 相关性 (relevance) - 对技术/编程/AI/互联网从业者的价值
- 10: 所有技术人都应该知道的重大事件/突破
- 7-9: 对大部分技术从业者有价值
- 4-6: 对特定技术领域有价值
- 1-3: 与技术行业关联不大

### 2. 质量 (quality) - 文章本身的深度和写作质量
- 10: 深度分析，原创洞见，引用丰富
- 7-9: 有深度，观点独到
- 4-6: 信息准确，表达清晰
- 1-3: 浅尝辄止或纯转述

### 3. 时效性 (timeliness) - 当前是否值得阅读
- 10: 正在发生的重大事件/刚发布的重要工具
- 7-9: 近期热点相关
- 4-6: 常青内容，不过时
- 1-3: 过时或无时效价值

## 分类标签（必须从以下选一个）
- ai-ml: AI、机器学习、LLM、深度学习相关
- security: 安全、隐私、漏洞、加密相关
- engineering: 软件工程、架构、编程语言、系统设计
- tools: 开发工具、开源项目、新发布的库/框架
- opinion: 行业观点、个人思考、职业发展、文化评论
- other: 以上都不太适合的

## 关键词提取
提取 2-4 个最能代表文章主题的关键词（用英文，简短，如 "Rust", "LLM", "database", "performance"）

## 待评分文章

{articles_text}

请严格按 JSON 格式返回，不要包含 markdown 代码块或其他文字：
{{
  "results": [
    {{
      "index": 0,
      "scores": {{"relevance": 8, "quality": 7, "timeliness": 9}},
      "category": "ai-ml",
      "keywords": ["LLM", "OpenAI", "fine-tuning"]
    }},
    ...
  ]
}}"""

def score_articles(articles: List[Dict], api_key: str, gateway_url: str = None) -> List[Dict]:
    """Score articles using Kimi AI."""
    scored = []
    
    for i in range(0, len(articles), BATCH_SIZE):
        batch = articles[i:i + BATCH_SIZE]
        prompt = build_scoring_prompt(batch)
        
        print(f"[digest] Scoring batch {i//BATCH_SIZE + 1}/{(len(articles)-1)//BATCH_SIZE + 1}...")
        
        try:
            response = call_kimi(prompt, api_key, gateway_url)
            result = parse_json_response(response)
            
            for item in result.get('results', []):
                idx = item['index']
                if i + idx < len(articles):
                    article = articles[i + idx].copy()
                    scores = item['scores']
                    article['score'] = round(sum(scores.values()) / 3)
                    article['scoreBreakdown'] = scores
                    article['category'] = item['category']
                    article['keywords'] = item['keywords']
                    scored.append(article)
        except Exception as e:
            print(f"[digest] Scoring error: {e}")
    
    return scored

# ============================================================================
# AI Summarization
# ============================================================================

def build_summary_prompt(articles: List[Dict]) -> str:
    """Build prompt for summarizing top articles."""
    articles_list = []
    for i, a in enumerate(articles):
        articles_list.append(f"Index {i}: [{a['sourceName']}] {a['title']}\n{a['description'][:500]}")
    
    articles_text = '\n\n---\n\n'.join(articles_list)
    
    return f"""你是一个技术内容策展人，正在为一份面向技术爱好者的每日精选摘要生成内容。

请为以下文章生成：
1. 中文标题翻译（简洁准确）
2. 4-6 句的结构化摘要（覆盖：核心问题/主题 → 关键论点/发现 → 结论/影响）
3. 一句话推荐理由（为什么技术人应该读）

## 待处理文章

{articles_text}

请严格按 JSON 格式返回，不要包含 markdown 代码块或其他文字：
{{
  "summaries": [
    {{
      "index": 0,
      "titleZh": "中文标题",
      "summary": "4-6句的完整摘要...",
      "reason": "一句话推荐理由"
    }},
    ...
  ]
}}"""

def summarize_articles(articles: List[Dict], api_key: str, gateway_url: str = None) -> List[Dict]:
    """Generate summaries for top articles using Kimi."""
    if not articles:
        return articles
    
    prompt = build_summary_prompt(articles)
    print(f"[digest] Summarizing {len(articles)} articles...")
    
    try:
        response = call_kimi(prompt, api_key, gateway_url)
        result = parse_json_response(response)
        
        for item in result.get('summaries', []):
            idx = item['index']
            if idx < len(articles):
                articles[idx]['titleZh'] = item['titleZh']
                articles[idx]['summary'] = item['summary']
                articles[idx]['reason'] = item['reason']
    except Exception as e:
        print(f"[digest] Summarization error: {e}")
    
    return articles

def build_trends_prompt(articles: List[Dict]) -> str:
    """Build prompt for trend analysis."""
    articles_list = []
    for a in articles[:20]:
        articles_list.append(f"- [{a.get('category', 'other')}] {a.get('titleZh', a['title'])}")
    
    articles_text = '\n'.join(articles_list)
    
    return f"""分析以下今日精选技术文章，归纳 2-3 个宏观技术趋势。

要求：
- 每个趋势用 1-2 句话描述
- 点明该趋势对技术行业的影响
- 可以涉及技术方向、行业动态、开发范式等

文章列表：
{articles_text}

请直接返回趋势列表，不要包含其他内容：
1. 趋势一...
2. 趋势二...
3. 趋势三（如有）..."""

def analyze_trends(articles: List[Dict], api_key: str, gateway_url: str = None) -> str:
    """Analyze trends from articles."""
    if not articles:
        return "暂无趋势分析"
    
    prompt = build_trends_prompt(articles)
    print("[digest] Analyzing trends...")
    
    try:
        response = call_kimi(prompt, api_key, gateway_url)
        return response.strip()
    except Exception as e:
        print(f"[digest] Trends analysis error: {e}")
        return "暂无趋势分析"

# ============================================================================
# Markdown Generation
# ============================================================================

def generate_markdown(articles: List[Dict], trends: str, hours: int, top_n: int) -> str:
    """Generate final Markdown digest."""
    now = datetime.now()
    date_str = now.strftime('%Y年%m月%d日')
    
    # Sort by score
    sorted_articles = sorted(articles, key=lambda x: x.get('score', 0), reverse=True)
    top_articles = sorted_articles[:top_n]
    
    # Group by category
    by_category = {}
    for a in sorted_articles:
        cat = a.get('category', 'other')
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(a)
    
    # Build markdown
    lines = []
    lines.append(f"# 🚀 技术日报 | {date_str}")
    lines.append("")
    lines.append(f"*从 90 个顶级技术博客精选 | 近 {hours} 小时 | Top {top_n} 必读*")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Trends section
    lines.append("## 📝 今日看点")
    lines.append("")
    lines.append(trends)
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Top 3 detailed
    lines.append("## 🏆 今日必读")
    lines.append("")
    
    for i, a in enumerate(top_articles[:3], 1):
        meta = CATEGORY_META.get(a.get('category', 'other'), {'emoji': '📝', 'label': '其他'})
        lines.append(f"### {i}. {a.get('titleZh', a['title'])}")
        lines.append("")
        lines.append(f"**{meta['emoji']} {meta['label']}** | 评分: {a.get('score', 0)}/10")
        lines.append("")
        lines.append(f"📰 **来源**: [{a['sourceName']}]({a['sourceUrl']})")
        lines.append("")
        lines.append(f"🔗 **原文**: [{a['title']}]({a['link']})")
        lines.append("")
        if a.get('summary'):
            lines.append(f"📝 **摘要**: {a['summary']}")
            lines.append("")
        if a.get('reason'):
            lines.append(f"💡 **推荐**: {a['reason']}")
            lines.append("")
        if a.get('keywords'):
            lines.append(f"🏷️ **标签**: {', '.join(a['keywords'])}")
            lines.append("")
        lines.append("---")
        lines.append("")
    
    # Category lists
    lines.append("## 📊 分类速览")
    lines.append("")
    
    for cat_id, meta in CATEGORY_META.items():
        if cat_id in by_category:
            cat_articles = by_category[cat_id][:5]  # Top 5 per category
            lines.append(f"### {meta['emoji']} {meta['label']}")
            lines.append("")
            for a in cat_articles:
                title = a.get('titleZh', a['title'])
                lines.append(f"- [{title}]({a['link']}) - {a['sourceName']} (评分: {a.get('score', 0)})")
            lines.append("")
    
    # Footer
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated at {now.strftime('%Y-%m-%d %H:%M:%S')} by AI Daily Digest (Kimi Edition)*")
    lines.append("")
    lines.append("*Sources: 90 top tech blogs curated by Andrej Karpathy*")
    
    return '\n'.join(lines)

# ============================================================================
# Main
# ============================================================================

def main():
    import argparse
    
    # Load config for defaults
    config = load_config()
    
    parser = argparse.ArgumentParser(description='AI Daily Digest - Kimi Edition')
    parser.add_argument('--hours', type=int, default=get_config_value(config, 'default_hours', 48),
                        help='Time window in hours (default: from config or 48)')
    parser.add_argument('--top-n', type=int, default=get_config_value(config, 'default_top_n', 15),
                        help='Number of top articles (default: from config or 15)')
    parser.add_argument('--lang', default=get_config_value(config, 'language', 'zh'),
                        help='Output language (default: from config or zh)')
    parser.add_argument('--output', '-o', default=None,
                        help='Output file path (default: auto-generated in output_dir)')
    parser.add_argument('--api-key', default=get_config_value(config, 'api_key', None),
                        help='Kimi/Moonshot API Key (default: from config or env)')
    parser.add_argument('--gateway', default=get_config_value(config, 'gateway_url', None),
                        help='OpenClaw Gateway URL (default: from config)')
    parser.add_argument('--setup', action='store_true',
                        help='Run interactive configuration setup')
    parser.add_argument('--config', action='store_true',
                        help='Show current configuration')
    
    args = parser.parse_args()
    
    # Handle setup
    if args.setup:
        interactive_setup()
        return 0
    
    # Handle config display
    if args.config:
        print("Current configuration:")
        print(f"  Config file: {CONFIG_FILE}")
        print(f"  API Key: {'***' + config.get('api_key', '')[-4:] if config.get('api_key') else 'Not set'}")
        print(f"  Gateway URL: {config.get('gateway_url', 'Not set')}")
        print(f"  Default hours: {config.get('default_hours', 48)}")
        print(f"  Default top-n: {config.get('default_top_n', 15)}")
        print(f"  Language: {config.get('language', 'zh')}")
        print(f"  Output dir: {config.get('output_dir', str(Path.home() / 'Desktop'))}")
        return 0
    
    # Auto-generate output path if not specified
    if not args.output:
        output_dir = Path(get_config_value(config, 'output_dir', str(Path.home() / 'Desktop')))
        date_str = datetime.now().strftime('%Y-%m-%d')
        args.output = str(output_dir / f'ai-daily-digest-{date_str}.md')
    
    print(f"[digest] Starting AI Daily Digest (Kimi Edition)")
    print(f"[digest] Time window: {args.hours}h | Top N: {args.top_n}")
    print("")
    
    # Check API key
    if not args.api_key:
        print("[digest] Error: API key required.")
        print("[digest] Run 'python3 digest.py --setup' to configure, or use --api-key")
        print("[digest] Or set MOONSHOT_API_KEY environment variable")
        return 1
    
    # Step 1: Fetch feeds
    print("[digest] Step 1/5: Fetching RSS feeds...")
    all_articles = fetch_all_feeds(RSS_FEEDS)
    
    if not all_articles:
        print("[digest] No articles fetched. Exiting.")
        return 1
    
    # Step 2: Time filter
    from datetime import timezone
    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    recent_articles = []
    for a in all_articles:
        try:
            pub_date = a['pubDate']
            if pub_date:
                # Ensure both dates are offset-aware
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                if pub_date >= cutoff:
                    recent_articles.append(a)
        except:
            pass
    print(f"[digest] Step 2/5: Filtered to {len(recent_articles)} articles from last {args.hours}h")
    
    if not recent_articles:
        print("[digest] No recent articles. Try increasing --hours.")
        return 1
    
    # Step 3: AI Scoring
    print("[digest] Step 3/5: AI scoring articles...")
    scored_articles = score_articles(recent_articles, args.api_key, args.gateway)
    
    if not scored_articles:
        print("[digest] Scoring failed. Exiting.")
        return 1
    
    # Step 4: AI Summarization
    print("[digest] Step 4/5: Generating summaries...")
    sorted_articles = sorted(scored_articles, key=lambda x: x.get('score', 0), reverse=True)
    top_articles = sorted_articles[:args.top_n]
    summarized = summarize_articles(top_articles, args.api_key, args.gateway)
    
    # Step 5: Trend Analysis
    print("[digest] Step 5/5: Analyzing trends...")
    trends = analyze_trends(summarized, args.api_key, args.gateway)
    
    # Generate Markdown
    print("[digest] Generating Markdown...")
    markdown = generate_markdown(summarized, trends, args.hours, args.top_n)
    
    # Write output
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print(f"[digest] Done! Output: {args.output}")
    print(f"[digest] Total: {len(summarized)} articles scored, top {len(summarized[:args.top_n])} included")
    
    return 0

if __name__ == '__main__':
    exit(main())
