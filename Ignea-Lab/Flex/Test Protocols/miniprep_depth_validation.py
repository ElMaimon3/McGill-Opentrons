# Opentrons Protocol for Pellet-Free Minipreps with Magbeads (Flex, 8-Channel) - PROPERLY FIXED
from opentrons import protocol_api
from opentrons.protocol_api import SINGLE, PARTIAL_COLUMN, ALL
from typing import List, Dict, Tuple, Optional

metadata = {
    'protocolName': 'Miniprep Depth Test',
    "author": "Gabriel Straface (Ignea Lab @ McGill University)",
    'description': '''Opentrons protocol for pellet-free minipreps with Zyppy magbeads (Flex). Uses 8-channel pipettes with intelligent tip management.''',
}
requirements = {"robotType": "Flex", "apiLevel": "2.21"}

# Runtime Parameters
def add_parameters(parameters: protocol_api.Parameters):
    parameters.add_int(
        variable_name="initial_well_depth",
        display_name="Initial plate well depth",
        description="",
        default=20,
        minimum=1,
        maximum=50,
        unit="mm"
    )
    parameters.add_int(
        variable_name="collection_well_depth",
        display_name="Collection plate well depth",
        description="",
        default=30,
        minimum=1,
        maximum=50,
        unit="mm"
    )

def reservoir_vol_to_height(vol: float) -> float:
    '''Convert volume to height for 12-well reservoir (22mL wells).'''
    if vol < 1:
        raise ValueError('Reservoir volume too low!')
    # Approximate function for 22mL reservoir wells
    return round(-2.5*vol + 51)

def extract_well_name(well_str: str) -> str:
    '''
    Extracts the well name (e.g., "A1") from a well string that might contain
    additional information.
    
    Args:
        well_str: Well string that might contain additional information
        
    Returns:
        Clean well name (e.g., "A1")
    '''
    # Extract just the well name (e.g., "A1") from the string
    return well_str.split()[0]

def parse_csv_locations(csv_data: List[List[str]]) -> Tuple[List[str], List[str], List[str]]:
    '''
    Extracts location data from parsed CSV - using PCR protocol style.
    
    Args:
        csv_data: Data from the CSV file parsed with parse_as_csv()
        
    Returns:
        Tuple of lists containing columns, rows, and individual wells
    '''
    sample_columns = []  # eg. ['1', '2']
    sample_rows = []     # eg. ['A', 'B']
    sample_wells = []    # eg. ['A1', 'B1']
    
    # Check if csv_data is valid and has content
    if not csv_data or len(csv_data) < 2:
        raise ValueError("CSV data is empty or missing header row")
    
    # Skip header row
    for row in csv_data[1:]:
        if not row:  # Skip empty rows
            continue
            
        for i in range(3):
            if i < len(row) and len(row[i]) != 0:
                if i == 0:
                    sample_columns.append(row[i])
                elif i == 1:
                    sample_rows.append(row[i])
                elif i == 2:
                    sample_wells.append(row[i])
                    
    return sample_columns, sample_rows, sample_wells

def get_unique_wells(protocol, plate, columns, rows, wells) -> List[str]:
    '''
    Creates a list of unique well names from columns, rows, and individual wells.
    Using PCR protocol approach for consistency.
    
    Args:
        protocol: Protocol context for logging
        plate: The labware containing the wells
        columns: List of column indices
        rows: List of row indices
        wells: List of individual well names
        
    Returns:
        List of unique well names
    '''
    # Get all wells from the specified columns and rows
    destination_wells = []
    for col in columns:
        destination_wells.extend(plate.columns_by_name()[col])
    for row in rows:
        destination_wells.extend(plate.rows_by_name()[row])
    destination_wells.extend([plate.wells_by_name()[well] for well in wells])
    
    # Remove duplicates
    unique_wells_dict = {}
    unique_wells = []
    
    for well in destination_wells:
        well_str = str(well)
        if well_str not in unique_wells_dict:
            unique_wells.append(extract_well_name(well_str))
            unique_wells_dict[well_str] = True
        else:
            protocol.comment(f"Duplicate location found and removed: {well_str}")
            
    return unique_wells

def group_wells(unique_wells: List[str]) -> List[List[str]]:
    '''
    Groups wells into vertically adjacent groups and sorts them by size.
    Using PCR protocol grouping logic for optimal 8-channel pipetting.
    
    Args:
        unique_wells: List of well names (e.g., ["A1", "B1", "C1"])
        
    Returns:
        List of well groups, sorted by size (largest first)
    '''
    # Sort wells by column, then by row
    sorted_wells = sorted(unique_wells, key=lambda x: (int(x[1:]), ord(x[0])))
    
    grouped_wells = []
    current_group = []
    
    for i, well in enumerate(sorted_wells):
        # Extract row letter and column number
        row = well[0]
        col = well[1:]
        
        # Start a new group or check if this well continues the current group
        if not current_group:
            current_group.append(well)
        elif col == current_group[-1][1:] and ord(row) == ord(current_group[-1][0]) + 1:
            # This well is in the same column and adjacent row as the last well
            current_group.append(well)
        else:
            # This well is not adjacent, so start a new group
            grouped_wells.append(current_group)
            current_group = [well]
    
    # Add the last group if it exists
    if current_group:
        grouped_wells.append(current_group)
    
    # Sort groups by size (largest first)
    return sorted(grouped_wells, key=len, reverse=True)

class NotEnoughTips(Exception):
    '''Exception raised when there aren't enough tips available.'''
    pass

def smart_pick_up(size: int, tips: Optional[Dict[str, bool]] = None) -> Tuple[str, Dict[str, bool]]:
    '''
    Selects the appropriate tips based on the number needed.
    USING EXACT LOGIC FROM WORKING PCR PROTOCOL
    
    Args:
        size: Number of tips needed
        tips: Dictionary tracking available tips
        
    Returns:
        Tuple of (tip location, updated tips dictionary)
        
    Raises:
        NotEnoughTips: If there aren't enough tips available
    '''
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
    '''
    Configures the pipette nozzle layout based on the group size.
    Using PCR protocol logic for consistency.
    
    Args:
        pipette: Pipette instrument to configure
        group_size: Size of the current well group
        last_size: Size of the previous well group
        
    Returns:
        tuple: (keep_tips flag, updated last_size)
    '''
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

def get_reservoir_location(reservoir, base_location, group_size):
    '''
    Get the appropriate reservoir location based on group size.
    For group size 8: use A row (top access)
    For group sizes 1-7: use H row (bottom access)
    
    Args:
        reservoir: The reservoir labware
        base_location: The base location (e.g., reservoir['A1'])
        group_size: Number of wells in the group
        
    Returns:
        Appropriate reservoir well location
    '''
    # Extract column number from base location
    base_well_name = str(base_location).split()[-1]  # Gets 'A1' from the well representation
    column_num = base_well_name[1:]  # Gets '1' from 'A1'
    
    if group_size == 8:
        # Use A row for 8-channel access
        return reservoir[f'A{column_num}']
    else:
        # Use H row for 1-7 channel access
        return reservoir[f'H{column_num}']

def handle_solution(protocol, working_plate, grouped_wells, pipette, tips_rack, tips, 
                      secondary_location, volume, height_tracker, max_volume, solution_name="solution", supernatant_mode=None, depth=0, mix_after=0):
    '''
    Smart function for handling solutions in the miniprep protocol.
    
    Args:
        protocol: Protocol context
        working_plate: Working plate
        grouped_wells: Grouped well locations
        pipette: Pipette to use
        tips_rack: Tip rack to use
        tips: Dictionary of available tips
        secondary_location: Source well in reservoir or destination of supernatant
        volume: Volume to dispense
        height_tracker: Tracker for liquid height in the source well
        solution_name: Name of the solution (for logging)
        supernatant_mode: For specifying if we are working with supernatant from samples. Accepted values are:
            - None or empty string for regular use
            - "Transfer" to transfer to another plate
            - "Discard" to discard
        depth: bypasses height tracker if working with supernatant
        mix_after: Number of times to mix if pipette mixing is required
        
    Returns:
        Updated tips dictionary and height tracker
    '''
    if not supernatant_mode:
        protocol.comment(f"Adding {volume} µL of {solution_name} to each sample")
    elif supernatant_mode == "Discard":
        protocol.comment(f"Removing {volume} µL of {solution_name} from samples and discarding")
    elif supernatant_mode == "Transfer":
        protocol.comment(f"Transfering {volume} µL of {solution_name}")
    else:
        raise TypeError("Unrecognized supernatant mode")
    
    last_size = 0
    tip_attached = False
    
    # Check if secondary_location is from a reservoir (for dynamic location adjustment)
    is_reservoir = hasattr(secondary_location, 'parent') and 'reservoir' in str(secondary_location.parent).lower()
    
    for i, group in enumerate(grouped_wells):
        group_size = len(group)
        # Determine the location to dispense to
        loc = working_plate.wells_by_name()[group[-1]]
        if group_size == 8:
            loc = working_plate.wells_by_name()[group[0]]
        
        # Configure pipette based on group size
        keep_tips, last_size = configure_pipette_for_group(pipette, group_size, last_size)
        
        # Pick up tips if needed
        if not keep_tips:
            if tip_attached:
                pipette.drop_tip()
                tip_attached = False
            tip_loc, tips = smart_pick_up(group_size, tips)
            pipette.pick_up_tip(tips_rack.wells_by_name()[tip_loc])
            tip_attached = True
        if not tip_attached:
            tip_loc, tips = smart_pick_up(group_size, tips)
            pipette.pick_up_tip(tips_rack.wells_by_name()[tip_loc])
            tip_attached = True

        quotient, remainder = divmod(volume, max_volume)
        if not supernatant_mode:
            # Determine the correct reservoir location based on group size
            if is_reservoir:
                source_location = get_reservoir_location(secondary_location.parent, secondary_location, group_size)
            else:
                source_location = secondary_location
                
            for i in range(quotient):
                # Dispense the solution
                pipette.aspirate(max_volume, source_location.top(-reservoir_vol_to_height(height_tracker)))
                pipette.dispense(max_volume, loc.top(-0.1))
                pipette.blow_out(loc.top(-0.1))
                height_tracker -= group_size * 0.001 * volume
            
            if remainder != 0:
                # Dispense the solution
                pipette.aspirate(remainder, source_location.top(-reservoir_vol_to_height(height_tracker)))
                pipette.dispense(remainder, loc.top(-0.1))
                pipette.blow_out(loc.top(-0.1))
                height_tracker -= group_size * 0.001 * volume

            # Only drop the tip at the end of all groups or if we need different tips next time
            is_last_group = (i == len(grouped_wells) - 1)
            needs_different_tips_next = False
            if not is_last_group:
                next_group_size = len(grouped_wells[i+1])
                needs_different_tips_next = (next_group_size != group_size)
            
            if mix_after:
                pipette.mix(mix_after, max_volume, loc.top(-depth))
                pipette.blow_out(loc.top(-1))
                keep_tips = False
                needs_different_tips_next = True
                
            if is_last_group or needs_different_tips_next:
                pipette.drop_tip()
                tip_attached = False
        elif supernatant_mode == "Transfer":
            dest = secondary_location.wells_by_name()[group[-1]]
            if group_size == 8:
                dest = secondary_location.wells_by_name()[group[0]]
            for i in range(quotient):
                pipette.aspirate(max_volume, loc.top(-depth))
                pipette.dispense(max_volume, dest.top(-1))
                pipette.blow_out(dest.top(-1))
            
            if remainder != 0:
                pipette.aspirate(max_volume, loc.top(-depth))
                pipette.dispense(max_volume, dest.top(-1))
                pipette.blow_out(dest.top(-1))
            pipette.drop_tip()
            tip_attached = False
            keep_tips = False
        elif supernatant_mode == "Discard":
            for i in range(quotient):
                pipette.aspirate(max_volume, loc.top(-depth))
                pipette.dispense(max_volume, secondary_location)
            
            if remainder != 0:
                pipette.aspirate(max_volume, loc.top(-depth))
                pipette.dispense(max_volume, secondary_location)
            pipette.drop_tip()
            tip_attached = False
            keep_tips = False
    
    if tip_attached:
        pipette.drop_tip()
    return tips

def handle_solution_single(protocol, working_plate, unique_wells, pipette, tips_rack, tips, 
                      tube, volume, max_volume, solution_name="solution", depth=0, mix_after=0):
    '''
    Smart function for dispensing solutions from single tubes in the miniprep protocol.
    
    Args:
        protocol: Protocol context
        working_plate: Working plate
        unique_wells: All well locations
        pipette: Pipette to use
        tips_rack: Tip rack to use
        tips: Dictionary of available tips
        tube: Source tube
        volume: Volume to dispense
        solution_name: Name of the solution (for logging)
        depth: depth in plate for mixing
        mix_after: Number of times to mix if pipette mixing is required
        
    Returns:
        Updated tips dictionary
    '''
    protocol.comment(f"Adding {volume} µL of {solution_name} to each sample")
    last_size = 0
    tip_attached = False
    
    for i, well in enumerate(unique_wells):
        group_size = 1
        # Determine the location to dispense to
        loc = working_plate.wells_by_name()[well]
        
        # Configure pipette based on group size
        keep_tips, last_size = configure_pipette_for_group(pipette, group_size, last_size)
        
        # Pick up tips if needed
        if not keep_tips:
            if tip_attached:
                pipette.drop_tip()
                tip_attached = False
            tip_loc, tips = smart_pick_up(group_size, tips)
            pipette.pick_up_tip(tips_rack.wells_by_name()[tip_loc])
            tip_attached = True
        if not tip_attached:
            tip_loc, tips = smart_pick_up(group_size, tips)
            pipette.pick_up_tip(tips_rack.wells_by_name()[tip_loc])
            tip_attached = True        
        quotient, remainder = divmod(volume, max_volume)
        for i in range(quotient):
            # Dispense the solution
            pipette.aspirate(max_volume, tube)
            pipette.dispense(max_volume, loc.top(-0.1))
            pipette.blow_out(loc.top(-0.1))
            
        if remainder != 0:
            # Dispense the solution
            pipette.aspirate(remainder, tube)
            pipette.dispense(remainder, loc.top(-0.1))
            pipette.blow_out(loc.top(-0.1))

        # Only drop the tip at the end of all wells
        is_last_well = (i == len(unique_wells) - 1)
        needs_different_tips_next = False

            
        if mix_after:
            pipette.mix(mix_after, max_volume, loc.top(-depth))
            pipette.blow_out(loc.top(-1))
            keep_tips = False
            needs_different_tips_next = True
                
        if is_last_well or needs_different_tips_next:
            pipette.drop_tip()
            tip_attached = False
    
    if tip_attached:
        pipette.drop_tip()
    return tips

def run(protocol: protocol_api.ProtocolContext):
    # Load waste chute
    waste_chute = protocol.load_waste_chute()
    
    # Load labware - optimized for H1 nozzle accessibility
    elute_plate = protocol.load_labware('armadillo_96_wellplate_200ul_pcr_full_skirt', 'A2') 
    small_tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 'B3')
    reservoir = protocol.load_labware('custom_22ml_reservoir', 'C2')

    # Load modules
    temp_module = protocol.load_module('temperatureModuleV2', 'D1') 
    temp_adapter = temp_module.load_adapter("opentrons_96_deep_well_temp_mod_adapter")
    collection_plate = protocol.load_labware('zymo_96_collection_plate', 'C1') # NEEDS CUSTOM LABWARE DEFINITON
    mag_block = protocol.load_module('magneticBlockV1', 'D2')
    heater_shaker = protocol.load_module('heaterShakerModuleV1', 'A3')
    hs_adapter = heater_shaker.load_adapter('opentrons_96_deep_well_adapter')
    initial_plate = temp_adapter.load_labware('nest_96_wellplate_2ml_deep')

    # Load pipettes and tip racks
    p50 = protocol.load_instrument('flex_8channel_50', 'left')
    tiprack50 = protocol.load_labware('opentrons_flex_96_tiprack_50ul', 'C3')
    p1000 = protocol.load_instrument('flex_8channel_1000', 'right')
    tiprack1000 = protocol.load_labware('opentrons_flex_96_tiprack_200ul', 'B2')
    
    
    # Small reagents in tube racks
    mag_clear_beads = small_tube_rack['A1'].top(-37)
    mag_bind_beads = small_tube_rack['A3'].top(-37)
    elution_buffer = small_tube_rack['A2'].top(-37)
    
    # Protocol parameters
    depth1 = protocol.params.initial_well_depth  # Depth to take supernatant from initial plate
    depth2 = protocol.params.collection_well_depth  # Depth to take supernatant from collection plate

    protocol.comment("Starting miniprep depth test")

    # Initialize tip tracking
    tips_50 = None
    tips_1000 = None
    group = [['A1']]
    configure_pipette_for_group(p1000, 1, 0)
    tiploc = (smart_pick_up(1, None))[0]
    p1000.pick_up_tip(tiprack1000.wells_by_name()[tiploc])
    p1000.move_to(initial_plate.wells_by_name()['A1'].top(-depth1))
    protocol.pause("Watch depth: 1")
    protocol.home()
    
    protocol.move_labware(initial_plate, mag_block, use_gripper=True)
    p1000.move_to(initial_plate.wells_by_name()['A1'].top(-depth1))
    protocol.pause("Watch depth: 1b")
    protocol.home()

    protocol.move_labware(collection_plate, temp_adapter, use_gripper=True)
    p1000.move_to(collection_plate.wells_by_name()['A1'].top(-depth2))
    protocol.pause("Watch depth: 2")
    protocol.home()
    protocol.move_labware(initial_plate, 'D4', use_gripper=True)
    
    protocol.move_labware(collection_plate, mag_block, use_gripper=True)
    p1000.move_to(collection_plate.wells_by_name()['A1'].top(-depth2))
    protocol.pause("Watch depth: 2b")
    protocol.home()
    p1000.drop_tip()