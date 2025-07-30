# Opentrons Protocol for Pellet-Free Minipreps with Magbeads (Flex, 8-Channel) - PROPERLY FIXED
from opentrons import protocol_api
from opentrons.protocol_api import SINGLE, PARTIAL_COLUMN, ALL
from typing import List, Dict, Tuple, Optional

metadata = {
    'protocolName': 'Pellet-Free Minipreps with Zyppy MagBead v1.0',
    "author": "Gabriel Straface, Dan Voicu (Ignea Lab @ McGill University)",
    'description': '''Opentrons protocol for pellet-free minipreps with Zyppy magbeads (Flex). Uses 8-channel pipettes with intelligent tip management.''',
}
requirements = {"robotType": "Flex", "apiLevel": "2.21"}

# Runtime Parameters
def add_parameters(parameters: protocol_api.Parameters):
    parameters.add_csv_file(
        variable_name="well_csv",
        display_name="Sample locations csv",
        description=(
            "Table with three columns:"
            " rows (e.g. 1), columns (e.g. B)"
            " and wells (e.g. B1)"
        )
    )

def reservoir_vol_to_height(vol: float) -> float:
    '''Convert volume to height for 12-well reservoir (22mL wells).'''
    if vol < 1:
        raise ValueError('Reservoir volume too low!')
    # Approximate function for 22mL reservoir wells
    if vol > 17:
        return 8
    return round(-2.5*vol + 53)

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
                
            for j in range(quotient):
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
        for j in range(quotient):
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
    
    # Parse CSV data for well locations - using PCR protocol approach
    well_csv = protocol.params.well_csv
    csv_data = well_csv.parse_as_csv()
    sample_columns, sample_rows, sample_wells = parse_csv_locations(csv_data)
    
    # Get unique wells and group them using PCR protocol logic
    unique_wells = get_unique_wells(protocol, initial_plate, sample_columns, sample_rows, sample_wells)
    grouped_wells = group_wells(unique_wells)  # Using PCR protocol grouping function
    
    protocol.comment(f"Processing {len(unique_wells)} samples in {len(grouped_wells)} groups")
    
    # Define reagent locations in reservoir
    lysis_buffer = reservoir['A1']
    neutralization_buffer = reservoir['A2'] 
    endo_wash = reservoir['A3']
    zyppy_wash = reservoir['A4']
    waste1 = reservoir['A11']
    waste2 = reservoir['A12']
    waste1_content = 0
    waste = waste1
    
    # Small reagents in tube racks
    mag_clear_beads = small_tube_rack['A1'].top(-36.5)
    mag_bind_beads = small_tube_rack['A3'].top(-36.5)
    elution_buffer = small_tube_rack['A2'].top(-36.5)
    
    # Protocol parameters
    depth1 = 22  # Depth to take supernatant from initial plate
    depth2 = 28  # Depth to take supernatant from collection plate
    depthmix1 = 30
    depthmix2 = depth2
    
    # Initialize tip tracking
    tips_50 = None
    tips_1000 = None

    protocol.comment("Starting pellet-free miniprep protocol...")
    heater_shaker.open_labware_latch()

    # Step 3: Add 50µL mag clear beads to each sample, then shake 10 seconds
    protocol.comment("Step 3: Adding magnetic clearing beads...")
    tips_50 = handle_solution_single(protocol, initial_plate, unique_wells, p50, tiprack50, tips_50, 
                      mag_clear_beads, 50, 50, solution_name="MagClear beads")
    protocol.move_labware(initial_plate, hs_adapter, use_gripper=True)
    heater_shaker.close_labware_latch()
    heater_shaker.set_and_wait_for_shake_speed(1200)
    protocol.delay(seconds=10)
    heater_shaker.deactivate_shaker()
    heater_shaker.open_labware_latch()

    # Step 4: Move the initial plate to the magnetic module with the gripper
    protocol.comment("Step 4: Moving initial plate to magnetic block...")
    protocol.move_labware(initial_plate, mag_block, use_gripper=True)

    protocol.move_labware(collection_plate, temp_adapter, use_gripper=True)

    # Wait 5 minutes
    protocol.comment("Waiting 5 minutes for magnetic separation...")
    protocol.delay(minutes=5)

    # Step 5: Take 750µL from each sample in the initial plate and move it to the same location collection plate
    protocol.comment("Step 5: Transferring cleared lysate to collection plate...")
    tips_1000 = handle_solution(protocol, initial_plate, grouped_wells, p1000, tiprack1000,
                                tips_1000, collection_plate, 750, 0, 200, "cleared lysate", "Transfer", depth1)

    # Step 6: Move the initial plate to staging area (no longer needed)
    protocol.comment("Step 6: Moving used initial plate to staging area...")
    protocol.move_labware(initial_plate, 'D4', use_gripper=True)
    
    
    # Step 7: Add 30µL of mag binding beads to each sample in the collection plate
    protocol.comment("Step 7: Adding magnetic binding beads to collection plate...")
    tips_50 = handle_solution_single(protocol, collection_plate, unique_wells, p50, tiprack50, tips_50, mag_bind_beads, 
                                     30, 50, "magnetic binding beads")
    
    # Step 8: Mix each sample in the collection plate for 10 minutes, hopefully use shaker
    protocol.comment("Step 8: Mixing samples for 10 minutes for DNA binding...")
    protocol.move_labware(collection_plate, hs_adapter, use_gripper=True)
    heater_shaker.close_labware_latch()
    heater_shaker.set_and_wait_for_shake_speed(1200)
    protocol.delay(seconds=10)
    heater_shaker.deactivate_shaker()
    for i in range(17):
            heater_shaker.set_and_wait_for_shake_speed(1200)
            protocol.delay(seconds=5)
            heater_shaker.deactivate_shaker()
            protocol.delay(seconds=30)
    heater_shaker.open_labware_latch()
     
    # Step 9: Move collection plate to magnetic module
    protocol.comment("Step 9: Moving collection plate to magnetic block...")
    protocol.move_labware(collection_plate, mag_block, use_gripper=True)

    # Wait 5 minutes
    protocol.comment("Waiting 5 minutes for magnetic separation...")
    protocol.delay(minutes=5)

    # Step 10: Remove and discard supernatant
    protocol.comment("Step 10: Removing supernatant...")
    tips_1000 = handle_solution(protocol, collection_plate, grouped_wells, p1000, tiprack1000, tips_1000, waste_chute, 750, 0, 200, 
                                "cleared lysate", "Discard", depth2)
    
    # Step 11: Move collection plate off magnetic block
    protocol.comment("Step 11: Moving collection plate off magnetic block...")
    protocol.move_labware(collection_plate, temp_adapter, use_gripper=True)

    # Step 12: Add endo wash buffer, then shake 30 seconds
    protocol.comment("Step 12: Adding endo wash buffer...")
    tips_1000 = handle_solution(protocol, collection_plate, grouped_wells, p1000, tiprack1000, 
                                tips_1000, endo_wash, 200, 15, 200, "endo wash buffer")
    protocol.move_labware(collection_plate, hs_adapter, use_gripper=True)
    heater_shaker.close_labware_latch()
    heater_shaker.set_and_wait_for_shake_speed(1200)
    protocol.delay(seconds=30)
    heater_shaker.deactivate_shaker()
    heater_shaker.open_labware_latch()

    # Step 13: Move to magnetic block
    protocol.comment("Step 13: Moving collection plate to magnetic block...")
    protocol.move_labware(collection_plate, mag_block, use_gripper=True)

    # Wait 2 minutes
    protocol.comment("Waiting 2 minutes for magnetic separation...")
    protocol.delay(minutes=2)

    # Step 14: Remove endo wash supernatant
    protocol.comment("Step 14: Removing endo wash supernatant...")
    tips_1000 = handle_solution(protocol, collection_plate, grouped_wells, p1000, tiprack1000, tips_1000, waste_chute, 200, 
                                0, 200, "endo wash buffer", "Discard", depth2)

    # Steps 15-18: Zyppy wash (performed twice)
    for wash_round in range(2):
        ht = 15
        protocol.comment(f"Starting Zyppy wash round {wash_round + 1}/2")

        # Move off magnetic block
        protocol.comment(f"Step 15 (round {wash_round + 1}): Moving collection plate off magnetic block...")
        protocol.move_labware(collection_plate, temp_adapter, use_gripper=True)

        # Add Zyppy wash buffer
        protocol.comment(f"Step 16 (round {wash_round + 1}): Adding Zyppy wash buffer...")
        tips_1000 = handle_solution(protocol, collection_plate, grouped_wells, p1000, tiprack1000, tips_1000, zyppy_wash, 400, 
                                    ht, 200, "zyppy wash")
        ht = ht - (0.4 * len(unique_wells))
        
        protocol.move_labware(collection_plate, hs_adapter, use_gripper=True)
        heater_shaker.close_labware_latch()
        heater_shaker.set_and_wait_for_shake_speed(1200)
        protocol.delay(seconds=30)
        heater_shaker.deactivate_shaker()
        heater_shaker.open_labware_latch()

        # Move to magnetic block
        protocol.comment(f"Step 17 (round {wash_round + 1}): Moving collection plate to magnetic block...")
        protocol.move_labware(collection_plate, mag_block, use_gripper=True)

        # Wait 2 minutes
        protocol.comment("Waiting 2 minutes for magnetic separation...")
        protocol.delay(minutes=2)

        # Remove Zyppy wash supernatant
        protocol.comment(f"Step 18 (round {wash_round + 1}): Removing Zyppy wash supernatant...")
        tips_1000 = handle_solution(protocol, collection_plate, grouped_wells, p1000, tiprack1000, tips_1000, waste_chute, 400, 
                                    0, 200, "zyppy wash", "Discard", depth2)


    # Step 19: Set temperature and dry
    protocol.comment("Step 19: Setting temperature module to 65°C and moving collection plate...")
    temp_module.set_temperature(65)
    protocol.move_labware(collection_plate, temp_adapter, use_gripper=True)

    # Step 20: Wait 30 minutes
    protocol.comment("Step 20: Waiting 30 minutes at 65°C for drying...")
    protocol.delay(minutes=30)
    temp_module.deactivate()

    # Step 21: Add elution buffer
    protocol.comment("Step 21: Adding elution buffer...")
    tips_50 = handle_solution_single(protocol, collection_plate, unique_wells, p50, tiprack50, tips_50, elution_buffer, 40, 50, "elution buffer", 
                                     depthmix2, 5)

    # Step 22: Move to heater-shaker
    protocol.comment("Step 22: Moving collection plate to heater-shaker module...")
    protocol.move_labware(collection_plate, hs_adapter, use_gripper=True)
    # Step 23: Mix for elution
    protocol.comment("Step 23: Mixing samples for 5 minutes for elution...")
    heater_shaker.close_labware_latch()
    heater_shaker.set_and_wait_for_temperature(65)
    heater_shaker.deactivate_shaker()
    for i in range(5):
            heater_shaker.set_and_wait_for_shake_speed(1200)
            protocol.delay(seconds=5)
            heater_shaker.deactivate_shaker()
            protocol.delay(seconds=60)
    heater_shaker.deactivate_heater()
    heater_shaker.open_labware_latch()

    
    # Step 24: Final magnetic separation
    protocol.comment("Step 24: Moving collection plate to magnetic block for final separation...")
    protocol.move_labware(collection_plate, mag_block, use_gripper=True)

    # Wait 1 minute
    protocol.comment("Waiting 1 minute for final magnetic separation...")
    protocol.delay(minutes=1)

    protocol.move_labware(tiprack1000, 'C1', use_gripper=True)
    protocol.move_labware(elute_plate, 'B2', use_gripper=True)

    # Step 25: Transfer purified DNA to elution plate
    protocol.comment("Step 25: Transferring purified DNA to elution plate...")
    tips_50 = handle_solution(protocol, collection_plate, grouped_wells, p50, tiprack50, tips_50, elute_plate, 30, 0, 50, 
                              "miniprep", "Transfer", depth2)


    # Deactivate temperature module
    temp_module.deactivate()

    protocol.comment("Miniprep protocol complete! Your purified DNA is ready in the elution plate.")