import aiohttp
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

class WeatherCollector:
    def __init__(self, api_key: str, city: str = "Trondheim", country_code: str = "NO"):
        self.api_key = api_key
        self.city = city
        self.country_code = country_code
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
    async def collect_weather_data(self) -> Dict[str, Any]:
        """Collect current weather and forecast for Trondheim"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get current weather and 5-day forecast in parallel
                current_task = self._get_current_weather(session)
                forecast_task = self._get_forecast(session)
                
                current_weather, forecast = await asyncio.gather(
                    current_task, forecast_task, return_exceptions=True
                )
                
                if isinstance(current_weather, Exception):
                    logging.error(f"Current weather error: {current_weather}")
                    current_weather = None
                
                if isinstance(forecast, Exception):
                    logging.error(f"Forecast error: {forecast}")
                    forecast = None
                
                return {
                    'current': current_weather,
                    'today_forecast': self._extract_today_forecast(forecast),
                    'week_outlook': self._extract_week_outlook(forecast),
                    'collection_time': datetime.now().isoformat(),
                    'location': f"{self.city}, {self.country_code}"
                }
                
        except Exception as e:
            logging.error(f"Weather collection failed: {e}")
            return {'error': f'Weather collection failed: {str(e)}'}
    
    async def _get_current_weather(self, session: aiohttp.ClientSession) -> Optional[Dict]:
        """Get current weather conditions"""
        url = f"{self.base_url}/weather"
        params = {
            'q': f"{self.city},{self.country_code}",
            'appid': self.api_key,
            'units': 'metric',
            'lang': 'no'  # Norwegian language for descriptions
        }
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._format_current_weather(data)
                else:
                    logging.error(f"Current weather API error: {response.status}")
                    return None
        except Exception as e:
            logging.error(f"Current weather request failed: {e}")
            return None
    
    async def _get_forecast(self, session: aiohttp.ClientSession) -> Optional[Dict]:
        """Get 5-day weather forecast"""
        url = f"{self.base_url}/forecast"
        params = {
            'q': f"{self.city},{self.country_code}",
            'appid': self.api_key,
            'units': 'metric',
            'lang': 'no'
        }
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logging.error(f"Forecast API error: {response.status}")
                    return None
        except Exception as e:
            logging.error(f"Forecast request failed: {e}")
            return None
    
    def _format_current_weather(self, data: Dict) -> Dict:
        """Format current weather data"""
        main = data.get('main', {})
        weather = data.get('weather', [{}])[0]
        wind = data.get('wind', {})
        
        return {
            'temperature': round(main.get('temp', 0)),
            'feels_like': round(main.get('feels_like', 0)),
            'humidity': main.get('humidity', 0),
            'pressure': main.get('pressure', 0),
            'description': weather.get('description', '').title(),
            'icon': weather.get('icon', ''),
            'wind_speed': wind.get('speed', 0),
            'wind_direction': wind.get('deg', 0),
            'visibility': data.get('visibility', 0) / 1000,  # Convert to km
            'clothing_advice': self._get_clothing_advice(main.get('temp', 0), wind.get('speed', 0))
        }
    
    def _extract_today_forecast(self, forecast_data: Optional[Dict]) -> Dict:
        """Extract today's hourly forecast"""
        if not forecast_data or 'list' not in forecast_data:
            return {}
        
        today = datetime.now().date()
        today_forecasts = []
        
        for item in forecast_data['list']:
            forecast_time = datetime.fromtimestamp(item['dt'])
            if forecast_time.date() == today:
                today_forecasts.append({
                    'time': forecast_time.strftime('%H:%M'),
                    'temperature': round(item['main']['temp']),
                    'description': item['weather'][0]['description'].title(),
                    'rain_probability': item.get('pop', 0) * 100,
                    'rain_amount': item.get('rain', {}).get('3h', 0)
                })
        
        return {
            'hourly': today_forecasts,
            'summary': self._summarize_today(today_forecasts)
        }
    
    def _extract_week_outlook(self, forecast_data: Optional[Dict]) -> Dict:
        """Extract week outlook from forecast"""
        if not forecast_data or 'list' not in forecast_data:
            return {}
        
        daily_forecasts = {}
        
        for item in forecast_data['list']:
            forecast_time = datetime.fromtimestamp(item['dt'])
            date_key = forecast_time.strftime('%Y-%m-%d')
            
            if date_key not in daily_forecasts:
                daily_forecasts[date_key] = {
                    'date': forecast_time.strftime('%A, %d %B'),
                    'min_temp': item['main']['temp'],
                    'max_temp': item['main']['temp'],
                    'conditions': [],
                    'rain_probability': 0
                }
            
            # Update min/max temperatures
            daily_forecasts[date_key]['min_temp'] = min(
                daily_forecasts[date_key]['min_temp'], 
                item['main']['temp']
            )
            daily_forecasts[date_key]['max_temp'] = max(
                daily_forecasts[date_key]['max_temp'], 
                item['main']['temp']
            )
            
            # Collect conditions
            condition = item['weather'][0]['description']
            if condition not in daily_forecasts[date_key]['conditions']:
                daily_forecasts[date_key]['conditions'].append(condition)
            
            # Update rain probability
            daily_forecasts[date_key]['rain_probability'] = max(
                daily_forecasts[date_key]['rain_probability'],
                item.get('pop', 0) * 100
            )
        
        # Format for output
        week_outlook = []
        for date_key in sorted(daily_forecasts.keys())[:5]:  # Next 5 days
            day = daily_forecasts[date_key]
            week_outlook.append({
                'date': day['date'],
                'min_temp': round(day['min_temp']),
                'max_temp': round(day['max_temp']),
                'conditions': ', '.join(day['conditions'][:2]),  # Top 2 conditions
                'rain_probability': round(day['rain_probability'])
            })
        
        return {'daily': week_outlook}
    
    def _get_clothing_advice(self, temp: float, wind_speed: float) -> str:
        """Provide clothing advice based on weather"""
        feels_like = temp - (wind_speed * 2)  # Simple wind chill approximation
        
        if feels_like < -10:
            return "Vinterjakke, lue, hansker og skjerf anbefales"
        elif feels_like < 0:
            return "Varm jakke og vinterutstyr"
        elif feels_like < 10:
            return "Mellomtykk jakke eller genser"
        elif feels_like < 20:
            return "Lett jakke eller cardigan"
        else:
            return "T-skjorte eller lett skjorte"
    
    def _summarize_today(self, hourly_forecasts: List[Dict]) -> str:
        """Create a summary of today's weather"""
        if not hourly_forecasts:
            return "Ingen værdata tilgjengelig"
        
        temps = [f['temperature'] for f in hourly_forecasts]
        rain_probs = [f['rain_probability'] for f in hourly_forecasts]
        
        min_temp = min(temps)
        max_temp = max(temps)
        max_rain_prob = max(rain_probs)
        
        summary = f"Temperatur: {min_temp}°C til {max_temp}°C"
        
        if max_rain_prob > 50:
            summary += f", {max_rain_prob:.0f}% sjanse for regn"
        elif max_rain_prob > 20:
            summary += f", liten sjanse for regn ({max_rain_prob:.0f}%)"
        
        return summary

# Example usage
async def main():
    # You'll need to get an API key from OpenWeatherMap
    api_key = "your_openweathermap_api_key"
    collector = WeatherCollector(api_key)
    
    weather_data = await collector.collect_weather_data()
    print(json.dumps(weather_data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())