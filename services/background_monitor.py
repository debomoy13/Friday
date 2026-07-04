import asyncio
import psutil
from typing import Callable, Optional, Dict, Any

class BackgroundMonitor:
    """
    Background system monitoring service.
    Proactively checks system metrics (battery, CPU usage, RAM)
    and schedules reminders to maintain user well-being.
    """
    def __init__(self, check_interval_seconds: int = 15):
        self.check_interval = check_interval_seconds
        self.running = False
        self._monitor_task = None
        self.callback: Optional[Callable[[Dict[str, Any]], Any]] = None
        
        # Tracking thresholds to avoid duplicate alerts
        self._battery_low_fired = False
        self._high_cpu_fired = False
        self._last_active_time = asyncio.get_event_loop().time()
        self._break_suggested = False

    def start(self, callback: Callable[[Dict[str, Any]], Any]):
        """Starts monitoring system metrics."""
        self.callback = callback
        self.running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    def stop(self):
        """Stops monitoring."""
        self.running = False
        if self._monitor_task:
            self._monitor_task.cancel()

    def reset_activity_timer(self):
        """Called whenever the user interacts to reset break reminders."""
        self._last_active_time = asyncio.get_event_loop().time()
        self._break_suggested = False

    async def _monitor_loop(self):
        # Allow system to settle first
        await asyncio.sleep(5)
        
        while self.running:
            try:
                # 1. Check Battery status
                battery = psutil.sensors_battery()
                if battery:
                    pct = battery.percent
                    plugged = battery.power_plugged
                    
                    if pct <= 20 and not plugged:
                        if not self._battery_low_fired:
                            await self._fire_event({
                                "type": "proactive_battery_low",
                                "title": "Battery Low",
                                "message": f"Battery is at {pct}%. Would you like to enable power saving mode?",
                                "priority": "high"
                            })
                            self._battery_low_fired = True
                    else:
                        # Reset flag if plugged in or charged
                        if plugged or pct > 25:
                            self._battery_low_fired = False

                # 2. Check CPU / RAM status
                cpu_load = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory()
                if cpu_load > 90:
                    if not self._high_cpu_fired:
                        await self._fire_event({
                            "type": "proactive_high_load",
                            "title": "High CPU Usage",
                            "message": f"Warning: CPU usage is at {cpu_load}%. Would you like to check running processes?",
                            "priority": "medium"
                        })
                        self._high_cpu_fired = True
                else:
                    if cpu_load < 80:
                        self._high_cpu_fired = False

                # 3. Check long session active (Break suggestion)
                now = asyncio.get_event_loop().time()
                active_duration_minutes = (now - self._last_active_time) / 60
                
                # Propose a break after 45 minutes of continuous usage
                if active_duration_minutes >= 45 and not self._break_suggested:
                    await self._fire_event({
                        "type": "proactive_break_suggestion",
                        "title": "Time for a Break",
                        "message": "You've been working continuously for 45 minutes. I suggest taking a short 5-minute break to stretch.",
                        "priority": "medium"
                    })
                    self._break_suggested = True

                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in background monitor loop: {str(e)}")
                await asyncio.sleep(self.check_interval * 2)

    async def _fire_event(self, event_data: Dict[str, Any]):
        if self.callback:
            try:
                if asyncio.iscoroutinefunction(self.callback):
                    await self.callback(event_data)
                else:
                    self.callback(event_data)
            except Exception as err:
                print(f"Error executing proactive monitor callback: {str(err)}")
