import cProfile
import random
from app.main import optimize_slotting, OptimizeRequest, LocationInput, InventoryInput, DispatchInput

def generate_data(num_locs, num_items, num_dispatches):
    locations = [LocationInput(id=f"L{i}", grid_x=random.randint(0, 100), grid_y=random.randint(0, 100), grid_z=random.randint(0, 10)) for i in range(num_locs)]
    inventory = [InventoryInput(sku=f"SKU{i}", location_id=f"L{i}") for i in range(num_items)]
    dispatches = [DispatchInput(sku=f"SKU{i}", location_id=f"L{i}", quantity=random.randint(1, 100), date="2023-01-01T12:00:00Z") for i in range(num_dispatches)]
    return OptimizeRequest(locations=locations, inventory=inventory, dispatches=dispatches)

req = generate_data(10000, 10000, 10000)
cProfile.run('optimize_slotting(req)', sort='tottime')
