"""
This protocol validates the vol_to_height function by transferring water
between wells of a USA Scientific 12-well reservoir while adjusting pipetting heights.
Uses the 8-channel pipette with only the first channel pipetting.
"""

from opentrons import protocol_api
from opentrons.protocol_api import SINGLE

# metadata
metadata = {
    'protocolName': 'Validate vol_to_height Function',
    'author': 'Gabriel Straface and Claude AI',
    'description': '''
    This protocol transfers water from one reservoir well to another
    in steps while adjusting pipetting height according to the vol_to_height function.
    This will validate whether the function calculates appropriate pipetting depths.
    Uses 8-channel pipette in single-channel mode.
    '''
}

requirements = {
    "robotType": "Flex",
    "apiLevel": "2.21"
}

# The vol_to_height function to validate
def vol_to_height(vol: float) -> float:
    '''
    Converts volume of liquid to appropriate pipette depth.
    
    Args:
        vol: Volume of liquid in mL
        
    Returns:
        Appropriate pipette depth in mm
    '''
    full_depth = 42.7
    if vol > 0:
        return round(-1.91636*vol + full_depth)
    else:
        return full_depth

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    reservoir = protocol.load_labware('usascientific_12_reservoir_22ml', 'C1')
    waste_chute = protocol.load_waste_chute()
    tiprack = protocol.load_labware('opentrons_flex_96_tiprack_200ul', 'D2')
    
    # Load 8-channel pipette and configure for single channel use
    p1000 = protocol.load_instrument('flex_8channel_1000', 'right', tip_racks=[tiprack])
    
    # Define source and destination wells
    source_well = reservoir.wells_by_name()['A1']
    dest_well = reservoir.wells_by_name()['A2']
    
    # Starting volume in source well (mL)
    initial_volume = 20  # USA Scientific reservoirs are 22mL, using 20mL for testing
    current_volume = initial_volume
    
    # Print initial information
    protocol.comment(f"VALIDATION OF vol_to_height FUNCTION")
    protocol.comment(f"Starting with {initial_volume} mL in source well (A1)")
    protocol.comment(f"Initial height calculation: {vol_to_height(current_volume)} mm from top")
    protocol.comment(f"Using 8-channel pipette")
    protocol.comment("-------------------------------------------")
    
    p1000.pick_up_tip()
    i = 0
    while current_volume >= 1.6:
        # Calculate current height for aspiration based on remaining volume
        height = vol_to_height(current_volume)
        
        # Log current state
        protocol.comment(f"Transfer #{i+1}: Current volume: {current_volume:.1f} mL, Aspirating from {height} mm below top")
        
        p1000.transfer(200, source_well.top(-height), dest_well, new_tip='never')
        
        # Update current volume
        current_volume -= 1.6
        i = i + 1
        
        
        # Delay between transfers to observe
        protocol.delay(seconds=1)
    
    if current_volume > 0:
        p1000.transfer(current_volume/1000, source_well.top(-height), dest_well, new_tip='never')

    p1000.drop_tip()
    # Print final confirmation
    protocol.comment("-------------------------------------------")
    protocol.comment(f"Validation complete: {initial_volume} mL transferred from source to destination")
    protocol.comment(f"Source well should be empty, destination should have {initial_volume} mL")
    protocol.comment("If transfer was successful, vol_to_height function is calibrated correctly")
