import asyncio
import aiohttp
import feedparser
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import re

class MediumCollector:
    def __init__(self):
        self.base_url = "https://medium.com/feed"
        self.session = None
        
        # Your specific interests for filtering
        self.interest_topics = [
            'machine-learning', 'artificial-intelligence', 'python', 
            'data-science', 'programming', 'software-development',
            'no-code', 'low-code', 'automation', 'productivity',
            'parenting', 'learning', 'career-change', 'restaurant-management'
        ]
        
        # Popular AI/ML publications on Medium
        self.publications = [
            'towards-data-science',
            'towardsmachinelearning', 
            'the-artificial-intelligence-publication',
            'analytics-vidhya',
            'better-programming',
            'python-in-plain-english',
            'the-startup',
            'hackernoon',
            'freecodecamp'
        ]
    
    async def collect_medium_content(self, hours_back: int = 24) -> Dict[str, Any]:
        """Collect Medium articles from various sources"""
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'MorningDigest/1.0 (Personal Content Aggregator)'}
        ) as session:
            self.session = session
            
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            all_articles = []
            
            # Collect from different sources in parallel
            tasks = []
            
            # Topic-based feeds
            for topic in self.interest_topics:
                tasks.append(self._fetch_topic_feed(topic, cutoff_time))
            
            # Publication feeds
            for pub in self.publications:
                tasks.append(self._fetch_publication_feed(pub, cutoff_time))
            
            # Execute all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logging.error(f"Failed to fetch Medium content: {result}")
                    continue
                
                if result:
                    all_articles.extend(result)
            
            # Remove duplicates based on URL
            seen_urls = set()
            unique_articles = []
            for article in all_articles:
                if article['url'] not in seen_urls:
                    unique_articles.append(article)
                    seen_urls.add(article['url'])
            
            # Sort by relevance and recency
            unique_articles.sort(key=lambda x: (
                x.get('relevance_score', 0),
                x.get('published_timestamp', 0)
            ), reverse=True)
            
            return {
                'articles': unique_articles[:50],  # Limit to top 50
                'total_found': len(unique_articles),
                'collection_time': datetime.now().isoformat(),
                'categories': self._categorize_articles(unique_articles),
                'top_publications': self._get_top_publications(unique_articles)
            }
    
    async def _fetch_topic_feed(self, topic: str, cutoff_time: datetime) -> List[Dict]:
        """Fetch articles from Medium topic feed"""
        url = f"{self.base_url}/tag/{topic}"
        return await self._fetch_feed(url, cutoff_time, f"topic:{topic}")
    
    async def _fetch_publication_feed(self, publication: str, cutoff_time: datetime) -> List[Dict]:
        """Fetch articles from Medium publication feed"""
        url = f"{self.base_url}/@{publication}"
        return await self._fetch_feed(url, cutoff_time, f"publication:{publication}")
    
    async def _fetch_feed(self, url: str, cutoff_time: datetime, source: str) -> List[Dict]:
        """Generic RSS feed fetcher for Medium"""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logging.warning(f"HTTP {response.status} for {url}")
                    return []
                
                content = await response.text()
                feed = feedparser.parse(content)
                
                articles = []
                
                for entry in feed.entries:
                    # Parse publication date
                    published = self._parse_date(entry.get('published', ''))
                    if published and published < cutoff_time:
                        continue
                    
                    # Extract and clean content
                    description = self._clean_description(entry.get('description', ''))
                    
                    # Calculate relevance score
                    relevance = self._calculate_relevance(
                        entry.get('title', ''),
                        description,
                        entry.get('tags', [])
                    )
                    
                    if relevance > 0.3:  # Only include relevant articles
                        article = {
                            'title': entry.get('title', 'No title'),
                            'description': description,
                            'url': entry.get('link', ''),
                            'author': self._extract_author(entry),
                            'published': entry.get('published', ''),
                            'published_timestamp': published.timestamp() if published else 0,
                            'tags': self._extract_tags(entry),
                            'source': source,
                            'relevance_score': relevance,
                            'reading_time': self._estimate_reading_time(description),
                            'category': self._categorize_article(entry.get('title', ''), description),
                            'is_member_only': self._is_member_only(entry)
                        }
                        articles.append(article)
                
                logging.info(f"Collected {len(articles)} relevant articles from {source}")
                return articles
                
        except Exception as e:
            logging.error(f"Error fetching Medium feed {url}: {e}")
            return []
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse Medium's date format"""
        if not date_str:
            return None
        
        formats = [
            '%a, %d %b %Y %H:%M:%S %Z',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%a, %d %b %Y %H:%M:%S %z'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        logging.warning(f"Could not parse Medium date: {date_str}")
        return datetime.now()
    
    def _clean_description(self, description: str) -> str:
        """Clean Medium article description"""
        # Remove HTML tags
        clean = re.sub(r'<.*?>', '', description)
        
        # Remove Medium-specific artifacts
        clean = re.sub(r'Continue reading on.*$', '', clean)
        clean = re.sub(r'Published in.*$', '', clean)
        
        # Clean whitespace
        clean = ' '.join(clean.split())
        
        # Truncate if too long
        return clean[:800] + '...' if len(clean) > 800 else clean
    
    def _calculate_relevance(self, title: str, description: str, tags: List[str]) -> float:
        """Calculate relevance score based on your interests"""
        score = 0.0
        content = f"{title} {description}".lower()
        
        # High-value keywords for your interests
        high_value_keywords = {
            'ai': 1.0, 'artificial intelligence': 1.0, 'machine learning': 1.0,
            'python': 0.8, 'programming': 0.6, 'coding': 0.6,
            'career change': 0.9, 'career transition': 0.9,
            'restaurant': 0.7, 'hospitality': 0.6,
            'parenting': 0.8, 'family': 0.5,
            'automation': 0.7, 'productivity': 0.6,
            'learning': 0.5, 'education': 0.5,
            'no-code': 0.8, 'low-code': 0.8,
            'data science': 0.9, 'analytics': 0.6
        }
        
        # Medium-value keywords
        medium_value_keywords = {
            'technology': 0.4, 'startup': 0.4, 'business': 0.3,
            'innovation': 0.4, 'development': 0.3,
            'leadership': 0.3, 'management': 0.4,
            'beginner': 0.5, 'tutorial': 0.6, 'guide': 0.5
        }
        
        # Check high-value keywords
        for keyword, weight in high_value_keywords.items():
            if keyword in content:
                score += weight
        
        # Check medium-value keywords
        for keyword, weight in medium_value_keywords.items():
            if keyword in content:
                score += weight
        
        # Bonus for practical content
        practical_indicators = ['how to', 'step by step', 'tutorial', 'guide', 'tips']
        if any(indicator in content for indicator in practical_indicators):
            score += 0.3
        
        # Bonus for beginner-friendly content
        beginner_indicators = ['beginner', 'getting started', 'introduction to', 'basics']
        if any(indicator in content for indicator in beginner_indicators):
            score += 0.2
        
        # Penalty for overly technical or advanced content
        advanced_indicators = ['advanced', 'expert', 'deep dive', 'mathematical']
        if any(indicator in content for indicator in advanced_indicators):
            score -= 0.1
        
        return min(score, 2.0)  # Cap at 2.0
    
    def _extract_author(self, entry: Dict) -> str:
        """Extract author name from Medium entry"""
        author = entry.get('author', '')
        if not author:
            # Try to extract from other fields
            authors = entry.get('authors', [])
            if authors:
                author = authors[0].get('name', '')
        
        return author if author else 'Unknown'
    
    def _extract_tags(self, entry: Dict) -> List[str]:
        """Extract tags from Medium entry"""
        tags = []
        
        # Try different tag fields
        if 'tags' in entry:
            for tag in entry['tags']:
                if isinstance(tag, dict):
                    tags.append(tag.get('term', ''))
                else:
                    tags.append(str(tag))
        
        # Extract from categories
        if 'category' in entry:
            tags.append(entry['category'])
        
        return [tag for tag in tags if tag]  # Remove empty tags
    
    def _categorize_article(self, title: str, description: str) -> str:
        """Categorize Medium article"""
        content = f"{title} {description}".lower()
        
        # AI/ML category
        if any(term in content for term in ['ai', 'artificial intelligence', 'machine learning', 'deep learning', 'neural network']):
            return 'ai_ml'
        
        # Programming category
        elif any(term in content for term in ['python', 'programming', 'coding', 'software', 'development']):
            return 'programming'
        
        # Career category
        elif any(term in content for term in ['career', 'job', 'interview', 'resume', 'transition']):
            return 'career'
        
        # Business category
        elif any(term in content for term in ['business', 'startup', 'entrepreneurship', 'management']):
            return 'business'
        
        # Learning category
        elif any(term in content for term in ['learning', 'education', 'tutorial', 'course', 'skill']):
            return 'learning'
        
        # Productivity category
        elif any(term in content for term in ['productivity', 'automation', 'efficiency', 'tools']):
            return 'productivity'
        
        # Personal category
        elif any(term in content for term in ['parenting', 'family', 'personal', 'life']):
            return 'personal'
        
        return 'general'
    
    def _estimate_reading_time(self, description: str) -> int:
        """Estimate reading time in minutes"""
        word_count = len(description.split())
        # Assume 200 words per minute reading speed
        return max(1, word_count // 200)
    
    def _is_member_only(self, entry: Dict) -> bool:
        """Check if article requires Medium membership"""
        # Look for member-only indicators in the content
        content = str(entry).lower()
        return 'member' in content or 'paywall' in content
    
    def _categorize_articles(self, articles: List[Dict]) -> Dict[str, int]:
        """Count articles by category"""
        categories = {}
        for article in articles:
            category = article.get('category', 'general')
            categories[category] = categories.get(category, 0) + 1
        return categories
    
    def _get_top_publications(self, articles: List[Dict]) -> Dict[str, int]:
        """Get top publications by article count"""
        publications = {}
        for article in articles:
            source = article.get('source', 'unknown')
            if source.startswith('publication:'):
                pub = source.replace('publication:', '')
                publications[pub] = publications.get(pub, 0) + 1
        
        # Sort by count and return top 5
        sorted_pubs = sorted(publications.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_pubs[:5])

# Example usage
async def main():
    collector = MediumCollector()
    medium_data = await collector.collect_medium_content(hours_back=48)  # Longer window for Medium
    
    print(f"Collected {len(medium_data['articles'])} relevant articles")
    print(f"Total found: {medium_data['total_found']}")
    print("Categories:", medium_data['categories'])
    print("Top publications:", medium_data['top_publications'])
    
    print("\nTop 5 articles:")
    for i, article in enumerate(medium_data['articles'][:5]):
        print(f"\n{i+1}. {article['title']}")
        print(f"   Author: {article['author']}")
        print(f"   Category: {article['category']}")
        print(f"   Relevance: {article['relevance_score']:.2f}")
        print(f"   Reading time: {article['reading_time']} min")

if __name__ == "__main__":
    asyncio.run(main())