import os
import requests

def get_vehicle_tracking(unit_id: str):
    api_key = os.getenv("MOTIVE_API_KEY")
    if not api_key:
        return None
        
    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json"
    }
    
    try:
        res = requests.get("https://api.keeptruckin.com/v1/vehicle_locations", headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            for v_data in data.get("vehicles", []):
                v = v_data.get("vehicle", {})
                if v.get("number") == unit_id:
                    loc = v.get("current_location")
                    if not loc:
                        continue
                    speed_kph = loc.get("speed")
                    speed_mph = int(speed_kph * 0.621371) if speed_kph else 0
                    
                    return {
                        "location": loc.get("description", "Unknown Location"),
                        "speed": speed_mph,
                        "status": "Driving" if speed_mph > 0 else "Idle",
                        "hos": 8.5 # Simplified HOS for tracking modal
                    }
    except Exception as e:
        print(f"Motive API Error: {e}")
        
    return None

def sync_fleet_from_motive():
    import os
    import requests
    api_key = os.getenv("MOTIVE_API_KEY")
    if not api_key:
        return []
        
    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json"
    }
    
    try:
        res = requests.get("https://api.keeptruckin.com/v1/vehicles", headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            vehicles = []
            for v_data in data.get("vehicles", []):
                v = v_data.get("vehicle", {})
                unit_id = v.get("number")
                if not unit_id:
                    continue
                    
                driver_obj = v.get("current_driver")
                driver_name = "Unassigned"
                if driver_obj:
                    driver_name = f"{driver_obj.get('first_name', '')} {driver_obj.get('last_name', '')}".strip()
                
                make = v.get("make", "")
                model = v.get("model", "")
                v_type = f"{make} {model}".strip() or "Semi Truck"
                
                loc = v.get("current_location") or {}
                odometer = loc.get("odometer", 0)
                miles_str = f"{int(odometer):,}" if odometer else "0"
                
                status = "Active" if v.get("status") == "active" else "Maintenance"
                
                vehicles.append({
                    "unit_id": unit_id,
                    "type": v_type,
                    "driver": driver_name,
                    "miles": miles_str,
                    "service": "Synced from Motive",
                    "status": status
                })
            return vehicles
    except Exception as e:
        print(f"Motive Sync Error: {e}")
        
    return []
