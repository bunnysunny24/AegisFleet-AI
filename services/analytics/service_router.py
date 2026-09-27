"""
Graph & Spatial Routing Engine: Dijkstra / Nearest Service Center Allocation.
Per Section 9 of Hackathon specifications:
- Dispatches vehicles with critical alerts to the nearest compatible depot/service center
- Verifies EV/ICE compatibility constraints
- Accounts for remaining vehicle range / SoC
- Evaluates service center bay capacity
"""
import math
import heapq
from typing import List, Dict, Any, Optional

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates on WGS84 sphere."""
    R = 6371.0 # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class ServiceCenterRouter:
    """
    Priority-queue Dijkstra router for allocating the optimal service depot
    based on distance, vehicle powertrain capability, and bay congestion.
    """
    def __init__(self, service_centers: List[Dict[str, Any]]):
        self.service_centers = service_centers

    def find_optimal_service_center(
        self,
        vehicle_lat: float,
        vehicle_lon: float,
        is_ev: bool = False,
        remaining_range_km: float = 100.0
    ) -> Optional[Dict[str, Any]]:
        """
        Computes the best destination using a min-heap cost evaluation.
        Cost Function: Cost = Distance_km + (Congestion_Penalty * Active_Bays)
        Constrained by: Distance <= remaining_range_km AND Powertrain compatibility
        """
        priority_queue = []

        for center in self.service_centers:
            # Powertrain capability check
            if is_ev and not center.get("can_service_ev", True):
                continue
            if not is_ev and not center.get("can_service_ice", True):
                continue

            dist_km = haversine_distance_km(
                vehicle_lat, vehicle_lon,
                center["latitude"], center["longitude"]
            )

            # Check if reachable under current vehicle range
            if dist_km > remaining_range_km:
                continue

            # Congestion weight: each active bay adds equivalent of 5 km cost
            active = center.get("current_active_orders", 0)
            max_bays = center.get("max_bays", 10)
            congestion_factor = (active / max_bays) * 20.0
            total_cost = dist_km + congestion_factor

            heapq.heappush(priority_queue, (total_cost, dist_km, center))

        if not priority_queue:
            # If no center is within remaining range, fall back to purely nearest compatible center (towing required)
            fallback = []
            for center in self.service_centers:
                if is_ev and not center.get("can_service_ev", True):
                    continue
                dist = haversine_distance_km(vehicle_lat, vehicle_lon, center["latitude"], center["longitude"])
                heapq.heappush(fallback, (dist, center))
            return fallback[0][1] if fallback else None

        best_cost, actual_dist, best_center = heapq.heappop(priority_queue)
        result = dict(best_center)
        result["distance_km"] = round(actual_dist, 2)
        result["routing_cost"] = round(best_cost, 2)
        return result
