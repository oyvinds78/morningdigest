import asyncio
import aiohttp
import feedparser
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

class NewsCollector:
    def __init__(self, config_path: str = "config/news_sources.json"):
        self.config_path = config_path
        self.sources = self._load_sources()
        self.session = None
        
    def _load_sources(self) -> Dict:
        """Load news sources from configuration"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"News sources config not found: {self.config_path}")
            return self._get_your_sources()
    
    def _get_your_sources(self) -> Dict:
        """Your specific news sources"""
        return {
            "norwegian_local": [
                {"name": "NRK Trøndelag", "rss": "https://www.nrk.no/trondelag/toppsaker.rss", "priority": "high"},
                {"name": "Adressa", "rss": "https://www.adressa.no/rss.xml", "priority": "high"}
            ],
            "norwegian_national": [
                {"name": "NRK Hovedsaker", "rss": "https://www.nrk.no/toppsaker.rss", "priority": "medium"},
                {"name": "VG Innenriks", "rss": "https://www.vg.no/rss/feed/?categories=1069", "priority": "medium"},
                {"name": "Aftenposten Hovedsaker", "rss": "https://www.aftenposten.no/rss/", "priority": "medium"}
            ],
            "international": [
                {"name": "BBC World", "rss": "http://feeds.bbci.co.uk/news/world/rss.xml", "priority": "medium"},
                {"name": "Al Jazeera English", "rss": "https://www.aljazeera.com/xml/rss/all.xml", "priority": "medium"}
            ],
            "international_tabloid": [
                {"name": "VG Utenriks", "rss": "https://www.vg.no/rss/feed/?categories=1070", "priority": "low"}
            ],
            "tech_sources": [
                {"name": "Kode24", "rss": "https://www.kode24.no/rss", "priority": "high"}
            ]
        }
    
    async def collect_all_news(self, hours_back: int = 24) -> Dict[str, Any]:
        """Collect news from all configured sources"""
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'MorningDigest/1.0 (Personal News Aggregator)'}
        ) as session:
            self.session = session
            
            results = {}
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            for category, sources in self.sources.items():
                category_articles = []
                
                # Process sources in parallel within each category
                tasks = [self._fetch_rss_feed(source, cutoff_time) for source in sources]
                source_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, result in enumerate(source_results):
                    if isinstance(result, Exception):
                        logging.error(f"Failed to fetch {sources[i]['name']}: {result}")
                        continue
                    
                    if result:
                        category_articles.extend(result)
                
                # Sort by priority and recency
                category_articles.sort(key=lambda x: (
                    x.get('priority_score', 0), 
                    x.get('published_timestamp', 0)
                ), reverse=True)
                
                results[category] = category_articles
            
            return {
                'articles': results,
                'collection_time': datetime.now().isoformat(),
                'total_articles': sum(len(articles) for articles in results.values()),
                'source_status': self._get_source_status(results)
            }
    
    async def _fetch_rss_feed(self, source: Dict, cutoff_time: datetime) -> List[Dict]:
        """Fetch and parse a single RSS feed"""
        try:
            async with self.session.get(source['rss']) as response:
                if response.status != 200:
                    logging.warning(f"HTTP {response.status} for {source['name']}")
                    return []
                
                content = await response.text()
                feed = feedparser.parse(content)
                
                articles = []
                priority_score = {'high': 3, 'medium': 2, 'low': 1}.get(source.get('priority', 'medium'), 2)
                
                for entry in feed.entries:
                    # Parse publication date
                    published = self._parse_date(entry.get('published', ''))
                    if published and published < cutoff_time:
                        continue  # Skip old articles
                    
                    article = {
                        'title': entry.get('title', 'No title'),
                        'description': self._clean_description(entry.get('description', '')),
                        'link': entry.get('link', ''),
                        'source': source['name'],
                        'source_priority': source.get('priority', 'medium'),
                        'published': entry.get('published', ''),
                        'published_timestamp': published.timestamp() if published else 0,
                        'priority_score': priority_score,
                        'category': self._categorize_article(entry),
                        'language': self._detect_language(source['name'])
                    }
                    
                    articles.append(article)
                
                logging.info(f"Collected {len(articles)} articles from {source['name']}")
                return articles
                
        except Exception as e:
            logging.error(f"Error fetching RSS from {source['name']}: {e}")
            return []
    
    def _detect_language(self, source_name: str) -> str:
        """Detect article language based on source"""
        norwegian_sources = ['NRK', 'Adressa', 'VG', 'Aftenposten', 'Kode24']
        
        if any(norw_src in source_name for norw_src in norwegian_sources):
            return 'norwegian'
        return 'english'
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats from RSS feeds"""
        if not date_str:
            return None
        
        # Common RSS date formats
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',
            '%a, %d %b %Y %H:%M:%S %Z',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%d %H:%M:%S',
            '%a, %d %b %Y %H:%M:%S GMT',
            '%a, %d %b %Y %H:%M:%S',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Fallback: return current time if parsing fails
        logging.warning(f"Could not parse date: {date_str}")
        return datetime.now()
    
    def _clean_description(self, description: str) -> str:
        """Clean HTML and formatting from description"""
        import re
        # Remove HTML tags
        clean = re.sub('<.*?>', '', description)
        # Remove extra whitespace
        clean = ' '.join(clean.split())
        # Remove common RSS artifacts
        clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        # Truncate if too long
        return clean[:500] + '...' if len(clean) > 500 else clean
    
    def _categorize_article(self, entry: Dict) -> str:
        """Enhanced categorization for Norwegian and international sources"""
        title = entry.get('title', '').lower()
        description = entry.get('description', '').lower()
        content = f"{title} {description}"
        
        # Technology
        tech_keywords = [
            'teknologi', 'ai', 'kunstig intelligens', 'machine learning', 'programming',
            'technology', 'artificial intelligence', 'coding', 'software', 'app',
            'python', 'utvikler', 'developer', 'data', 'cloud', 'cybersecurity'
        ]
        
        # Politics
        politics_keywords = [
            'politikk', 'regjering', 'storting', 'valg', 'minister', 'parti',
            'politics', 'government', 'election', 'parliament', 'democracy',
            'høyre', 'arbeiderpartiet', 'sp', 'venstre', 'frp'
        ]
        
        # Economy
        economy_keywords = [
            'økonomi', 'marked', 'finans', 'krone', 'bank', 'aksje', 'investering',
            'economy', 'market', 'finance', 'stock', 'investment', 'inflation',
            'rente', 'interest', 'trade', 'handel'
        ]
        
        # Family & Education
        family_keywords = [
            'familie', 'barn', 'skole', 'utdanning', 'barnehage', 'foreldre',
            'family', 'children', 'school', 'education', 'parenting', 'kids',
            'ungdom', 'teenager', 'lærer', 'teacher'
        ]
        
        # Local Trondheim
        local_keywords = [
            'trondheim', 'trøndelag', 'ntnu', 'nidaros', 'selbu', 'klæbu',
            'malvik', 'melhus', 'orkland', 'stjørdal'
        ]
        
        # Health
        health_keywords = [
            'helse', 'sykehus', 'lege', 'behandling', 'medisin', 'covid',
            'health', 'hospital', 'doctor', 'medical', 'treatment', 'wellness'
        ]
        
        if any(word in content for word in local_keywords):
            return 'local'
        elif any(word in content for word in tech_keywords):
            return 'technology'
        elif any(word in content for word in politics_keywords):
            return 'politics'
        elif any(word in content for word in economy_keywords):
            return 'economy'
        elif any(word in content for word in family_keywords):
            return 'family_education'
        elif any(word in content for word in health_keywords):
            return 'health'
        else:
            return 'general'
    
    def _get_source_status(self, results: Dict) -> Dict:
        """Get status of each source for debugging"""
        status = {}
        for category, articles in results.items():
            sources_in_category = {}
            for article in articles:
                source = article['source']
                if source not in sources_in_category:
                    sources_in_category[source] = 0