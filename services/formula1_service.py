import traceback
import aiohttp
from datetime import datetime, timezone

class Formula1Service():
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    # Get the full schedule for the specified year    
    async def get_full_schedule_raw(self, year):
        url = f"https://api.openf1.org/v1/meetings?year={year}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                resp.raise_for_status()
                meetings = await resp.json()
                
                races = [m for m in meetings if 'Grand Prix' in m.get('meeting_name', '')]

        schedule = []
        for i, r in enumerate(races, start=1):
            schedule.append({
                "round": i,
                "name": r.get("meeting_name"),
                "start": r.get("date_start"),
                "end": r.get("date_end"),
                "location": r.get("location"),
                "country": r.get("country_name"),
                "circuit": r.get("circuit_short_name"),
                "circuit_key": r.get("circuit_key"),
                "meeting_name": r.get("meeting_name"),
                "year": r.get("year")
            })

        return schedule
    
    # Store season data in DB
    async def store_season_data(self, year):
        schedule = await self.get_full_schedule_raw(year)
        
        try:
            async with self.db_pool.acquire() as conn:
                # Save the race weekend data as tuples
                data = [
                    (
                    s["round"],
                    s["circuit_key"],
                    s["circuit"],
                    s["meeting_name"],
                    datetime.fromisoformat(s["start"]) if s["start"] else None,
                    datetime.fromisoformat(s["end"]) if s["end"] else None,
                    s["year"]
                    )
                    for s in schedule
                ]
                
                # Insert the tuples above in a single batch
                await conn.executemany("""
                    INSERT INTO f1_seasons
                    (round, circuit_key, circuit, meeting_name, date_start, date_end, year)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (circuit_key, year) DO NOTHING
                    """, data)
                
                print(f"Successfully added the F1 schedule for the {year} season!")
                return True
                
        except Exception as e:
            print(f"Failed to add {year} season: {e}")
            traceback.print_exc()
            return False
    
    # Get the time and date for each session of the race weekend
    async def get_sessions_raw(self, year):
        url = f"https://api.openf1.org/v1/sessions?year={year}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                resp.raise_for_status()
                return await resp.json()

    # Parse the session data then save to DB
    async def store_session_data(self, year):
        sessions = await self.get_sessions_raw(year)
        
        try:
            async with self.db_pool.acquire() as conn:
                data = [
                    (
                    s.get("circuit_key"),
                    s.get("circuit_short_name"),
                    datetime.fromisoformat(s["date_start"]) if s.get("date_start") else None,
                    datetime.fromisoformat(s["date_end"]) if s.get("date_end") else None,
                    s.get("session_name"),
                    s.get("session_key"),
                    s.get("location"),
                    s.get("year") 
                    )
                    for s in sessions
                ]
                await conn.executemany("""
                    INSERT INTO f1_sessions
                    (circuit_key, circuit, date_start, date_end, session_name, session_key, location, year)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (circuit_key, session_name, year) DO NOTHING
                    """, data)
                
                print(f"Successfully added all race weekend sessions for the {year} season!")
                return True
            
        except Exception as e:
            print(f"Failed to add sessions: {e}")
            traceback.print_exc()
            return False
    
    # Get race sessions
    async def get_race_sessions(self, circuit_key, year):
        async with self.db_pool.acquire() as conn:
            return await conn.fetch("""
                SELECT * FROM f1_sessions
                WHERE circuit_key = $1
                AND year = $2
                ORDER BY date_start
                """, circuit_key, year)
    
    # Determine next race weekend based on current date
    async def determine_next_race(self):
        try:
            now = datetime.now(timezone.utc) # Get current date in UTC tz
            
            # Get the next race weekend details
            async with self.db_pool.acquire() as conn:
                # Start with identifying the next race weekend
                next_race = await conn.fetchrow("""
                    SELECT * FROM f1_seasons
                    WHERE date_start > $1
                    ORDER BY date_start
                    LIMIT 1
                    """, now)
            
            if not next_race:
                print("[F1 Cog] No upcoming race found")
                return

            # Get sessions based on next race found above
            race_sessions = await self.get_race_sessions(next_race["circuit_key"], next_race["year"])
            
            if not race_sessions:
                await self.store_session_data(next_race["year"])
                race_sessions = await self.get_race_sessions(next_race["circuit_key"], next_race["year"])
            
            return {
                'race': next_race['meeting_name'],
                'round':next_race['round'],
                'track': next_race['circuit'],
                'start': next_race['date_start'],
                'end': next_race['date_end'],
                'sessions': race_sessions
                }
            
        except Exception as e:
            traceback.print_exc()
            
    # Helper method to get season rows from DB
    async def _fetch_season_rows(self, year):
        async with self.db_pool.acquire() as conn:
            return await conn.fetch("""
                SELECT * FROM f1_seasons
                WHERE year = $1
                ORDER BY round ASC
            """, year)
            
    # Method to get all data for the current F1 season
    async def get_current_season(self):
        try:
            year = datetime.now(timezone.utc).year # Get the current year
            
            # get the data from the DB using the current year
            rows = await self._fetch_season_rows(year)
                
            if not rows:
                await self.store_season_data(year)
                rows = await self._fetch_season_rows(year)
                
            return [dict(row) for row in rows]
        
        except Exception as e:
            print(f"[F1] Failed to fetch {year} season data: {e}")
            traceback.print_exc()
            return []