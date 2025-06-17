# Opentrons Protocol for Pellet-Free Minipreps with Magbeads (Flex, 8-Channel)
from opentrons import protocol_api
from opentrons.protocol_api import SINGLE, PARTIAL_COLUMN, ALL
from typing import List, Dict, Tuple, Optional

metadata = {
    'protocolName': 'Pellet-Free Minipreps with Zyppy MagBead',
    "author": "Gabriel Straface, Dan Voicu (Ignea Lab @ McGill University)",
    'description': '''Opentrons protocol for pellet-free minipreps with Zyppy magbeads (Flex). Uses 8-channel pipettes with intelligent tip management.''',
}
requirements = {"robotType": "Flex", "apiLevel": "2.21"}


def reservoir_vol_to_height(vol: float) -> float:
    '''Convert volume to height for 12-well reservoir (22mL wells).'''
    if vol < 1:
        raise ValueError('Reservoir volume too low!')
    # Approximate function for 22mL reservoir wells
    return round(-2.5*vol + 50)

class NotEnoughTips(Exception):
    '''Exception raised when there aren't enough tips available.'''
    pass

def smart_pick_up(size: int, tips: Optional[Dict[str, bool]] = None) -> Tuple[str, Dict[str, bool]]:
    '''Selects the appropriate tips based on the number needed.'''
    if tips is None:
        tips = {f"{chr(65+row)}{col+1}": True for row in range(8) for col in range(12)}

    def is_column_clear(column, start_row):
        for row in range(start_row):
            loc = f"{chr(65+row)}{column+1}"
            if tips.get(loc, False):
                return False
        return True

    # Iterate over columns
    for col in range(12):
        if size == 1:
            for row in range(7, -1, -1):
                loc = f"{chr(65+row)}{col+1}"
                if tips.get(loc, False) and is_column_clear(col, row):
                    tips[loc] = False
                    return loc, tips

        elif 2 <= size <= 7:
            for row in range(8 - size + 1):
                if all(tips.get(f"{chr(65+row+i)}{col+1}", False) for i in range(size)) and is_column_clear(col, row):
                    loc = f"{chr(65+row+size-1)}{col+1}"
                    for i in range(size):
                        tips[f"{chr(65+row+i)}{col+1}"] = False
                    return loc, tips

        elif size == 8:
            if all(tips.get(f"{chr(65+row)}{col+1}", False) for row in range(8)):
                loc = f"A{col+1}"
                for row in range(8):
                    tips[f"{chr(65+row)}{col+1}"] = False
                return loc, tips

    raise NotEnoughTips("Not enough tips available")

def configure_pipette_for_group(pipette, group_size: int, last_size: int):
    '''Configures the pipette nozzle layout based on the group size.'''
    keep_tips = (group_size == last_size)
    
    if not keep_tips:
        if group_size == 1:
            pipette.configure_nozzle_layout(
                style=SINGLE,
                start="H1"
            )
        elif group_size == 8:
            pipette.configure_nozzle_layout(
                style=ALL
            )
        else:
            last = ["G1", "F1", "E1", "D1", "C1", "B1"][group_size-2]
            pipette.configure_nozzle_layout(
                style=PARTIAL_COLUMN,
                start="H1",
                end=last
            )
    
    return keep_tips, group_size

def group_wells_by_column(wells: List[str]) -> List[List[str]]:
    '''Groups wells by column and sorts by size.'''
    # Group wells by column
    column_groups = {}
    for well in wells:
        col = well[1:]  # Extract column number
        if col not in column_groups:
            column_groups[col] = []
        column_groups[col].append(well)
    
    # Sort wells within each column by row
    for col in column_groups:
        column_groups[col].sort(key=lambda x: ord(x[0]))
    
    # Convert to list of groups and sort by size
    grouped_wells = list(column_groups.values())
    return sorted(grouped_wells, key=len, reverse=True)

def run(protocol: protocol_api.ProtocolContext):
    # Load waste chute
    waste_chute = protocol.load_waste_chute()
    
    # Load labware
    initial_plate = protocol.load_labware('nest_96_wellplate_2ml_deep', 'A2') # Eventually switch to Zymo 96 well block
    small_tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 'B2')
    reservoir = protocol.load_labware('usascientific_12_reservoir_22ml', 'C2')
    elute_plate = protocol.load_labware('armadillo_96_wellplate_200ul_pcr_full_skirt', 'C1') # Eventually change to zymo elute plate
    
    # Load modules
    temp_module = protocol.load_module('temperatureModuleV2', 'D1') 
    collection_plate = temp_module.load_labware('nest_96_wellplate_2ml_deep', 'A2') # Eventually switch to Zymo 96 collection
    mag_block = protocol.load_module('magneticBlockV1', 'D2')
    heater_shaker = protocol.load_module('heaterShakerModuleV1', 'A3')

    
    # Load pipettes and tip racks
    p50 = protocol.load_instrument('flex_8channel_50', 'left', tip_racks=[
        protocol.load_labware('opentrons_flex_96_tiprack_50ul', 'C3')
    ])
    p300 = protocol.load_instrument('flex_8channel_1000', 'right', tip_racks=[
        protocol.load_labware('opentrons_flex_96_tiprack_1000ul', 'B3'),
    ])
    
    
    # REPLACE SAMPLE WELL DEFINITION WITH THE CSV PARAMETER
    sample_wells = ['D1','D2','D3','E1','E2','E3','E4','F1','F2','F3','F4']
    
    # Group samples by column for efficient pipetting
    grouped_wells = group_wells_by_column(sample_wells)
    
    # Define reagent locations in reservoir
    lysis_buffer = reservoir['A1']
    neutralization_buffer = reservoir['A2'] 
    binding_buffer = reservoir['A3']
    endo_wash = reservoir['A4']
    zyppy_wash = reservoir['A5']
    waste1 = reservoir['A11']
    waste1amount = 0 # If this goes over 21000uL, switch to waste2 to prevent overflowing
    waste2 = reservoir['A12']

    
    # Small reagents in tube racks
    mag_clear_beads = small_tube_rack['A1']
    mag_bind_beads = small_tube_rack['A3']
    elution_buffer = small_tube_rack['A2']

    
    # Protocol parameters
    depth1 = 20  # Depth to take supernatant from initial plate
    depth2 = 30  # Depth to take supernatant from collection plate

    
    # Initialize tip tracking
    tips_50 = None
    tips_300 = None
    
    # Helper function for single well operations
    def transfer_to_single_wells(pipette, source, wells, volume, tip_rack, tips_dict, mix_after=None):
        '''Transfer to individual wells using single tip pickup.'''
        pipette.configure_nozzle_layout(style=SINGLE, start="H1")
        
        for well in wells:
            if tips_dict is None:
                tips_dict = {f"{chr(65+row)}{col+1}": True for row in range(8) for col in range(12)}
            
            tip_loc, tips_dict = smart_pick_up(1, tips_dict)
            pipette.pick_up_tip(tip_rack.wells_by_name()[tip_loc])
            
            if isinstance(source, str):  # Source is a tube rack location
                source_well = small_tube_rack[source]
                pipette.transfer(volume, source_well.top(-37), initial_plate[well], new_tip='never')
            else:
                pipette.transfer(volume, source, initial_plate[well], new_tip='never')
                
            if mix_after:
                pipette.mix(mix_after[0], mix_after[1], initial_plate[well])
            pipette.blow_out(initial_plate[well])
            pipette.drop_tip()
            
        return tips_dict

    protocol.comment("Starting pellet-free miniprep protocol...")
    
    # Step 1: Add 100uL of lysis buffer to each sample, then mix 5 times
    protocol.comment("Adding lysis buffer...")
    
    # Wait 5 minutes (offset to be less the more samples there are, to account for extra pipetting time)
    
    # Step 2: Add 450uL of neutralization buffer to each sample, then mix 20 times
    protocol.comment("Adding neutralization buffer...")
    
    # Step 3: Add 50uL mag clear beads to each sample, then mix 5 times

    # Step 4: Move the initial plate to the magnetic module with the gripper

    # Wait 5 minutes

    # Step 5: Take 750uL from each sample in the initial plate and move it to the same location collection plate, use depth 1

    # Step 6: Move the initial plate off of the magnetic module

    # Step 7: Add 30uL of mag binding beads to each sample in the collection plate
    
    # Step 8: Mix each sample in the collection plate once, repeating for a total of 10 minutes
     
    # Step 9: Move collection plate to magnetic module with the gripper

    # Wait 5 minutes

    # Step 10: remove and discard supernatant from each sample in the collection plate (750uL), use depth 2

    # Step 11: Move collection plate off of the magnetic module with the gripper

    # Step 12: Add 200uL of endowash buffee to each sample in the collection plate, then mix 15 times

    # Step 13: Same as step 9

    # Wait 2 minutes

    # Step 14: Remove and discard supernatant from each sample in the collection plate (200uL), use depth 2

    # Steps 15, 16, 17, 18 are performed twice

    # Step 15: Same as step 11

    # Step 16: Add 400uL of Zyppy wahs buffer to each sample in the collection plate, then mix 15 times

    # Step 17: Same as step 9

    # Wait 2 minutes

    # Step 18: Remove and discard supernatant from each sample in the collection plate (400uL), use depth 2

    # Step 19: Set temperature module to 65C and move collection plate to it with the gripper

    # Wait 30 minutes

    # Step 20: Move collection plate off the temperature module with the gripper

    # Step 21: Add 40uL of elution buffer to each sample in the collection plate, then mix 5 times

    # Step 22: Move collection plate back to the temperature module at 65C

    # Step 23: Mix each sample in the collection plate once, repeating for a total of 5 minutes

    # Step 23: Same as step 9

    # Wait 1 minute

    # Step 24: Transfer 30uL from each sample in the collection plate to the same location in the elution plate, use depth 2


    protocol.comment("Miniprep protocol complete!")