# Opentrons Protocol for Pellet-Free Minipreps with Magbeads (Flex, 8-Channel) - PROPERLY FIXED
from opentrons import protocol_api
from opentrons.protocol_api import SINGLE, PARTIAL_COLUMN, ALL
from typing import List, Dict, Tuple, Optional

metadata = {
    'protocolName': 'Pellet-Free Minipreps with Zyppy MagBead',
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
    return round(-2.5*vol + 50)

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

def dispense_and_mix(protocol, plate, grouped_wells, pipette, tips_rack, tips, 
                     source_well, volume, mix_reps, solution_name="solution"):
    '''Dispenses solution and mixes - for reservoir reagents only.'''
    protocol.comment(f"Adding {volume} µL of {solution_name} to each sample and mixing {mix_reps} times")
    
    # Determine max volume per pipette operation based on tip rack
    max_volume = 50 if pipette.max_volume <= 50 else 200
    
    last_size = 0
    tip_attached = False
    
    for i, group in enumerate(grouped_wells):
        group_size = len(group)
        
        # Validate group has wells
        if group_size == 0:
            continue
            
        # Determine the location to dispense to - using PCR protocol logic
        loc = plate.wells_by_name()[group[-1]]
        if group_size == 8:
            loc = plate.wells_by_name()[group[0]]
        
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
        
        # Dispense using transfer if volume exceeds capacity, otherwise single aspiration
        if volume > max_volume:
            pipette.transfer(volume, source_well, loc, new_tip='never')
        else:
            pipette.aspirate(volume, source_well)
            pipette.dispense(volume, loc)
        
        # Mix
        mix_volume = min(volume * 0.8, max_volume)
        pipette.mix(mix_reps, mix_volume, loc)
        pipette.blow_out(loc.top())
        
        # Only drop the tip at the end of all groups or if we need different tips next time
        is_last_group = (i == len(grouped_wells) - 1)
        needs_different_tips_next = False
        if not is_last_group:
            next_group_size = len(grouped_wells[i+1])
            needs_different_tips_next = (next_group_size != group_size)
            
        if is_last_group or needs_different_tips_next:
            pipette.drop_tip()
            tip_attached = False
    
    return tips

def dispense_tube_reagent_and_mix(protocol, plate, grouped_wells, pipette, tips_rack, tips, 
                                 tube_well, volume, mix_reps, solution_name="solution"):
    '''Dispenses reagent from tube rack (single tip aspiration) and mixes.'''
    protocol.comment(f"Adding {volume} µL of {solution_name} to each sample and mixing {mix_reps} times")
    protocol.comment(f"Note: Using single tip aspiration from tube rack for {solution_name}")
    
    # Determine max volume per pipette operation based on tip rack
    max_volume = 50 if pipette.max_volume <= 50 else 200
    
    # Process each well individually since we need single tip aspiration from tube
    for well in [w for group in grouped_wells for w in group]:
        # Always use single tip for tube aspiration
        pipette.configure_nozzle_layout(style=SINGLE, start="H1")
        
        # Pick up single tip
        tip_loc, tips = smart_pick_up(1, tips)
        pipette.pick_up_tip(tips_rack.wells_by_name()[tip_loc])
        
        # Aspirate from tube with single tip and dispense to well
        well_obj = plate.wells_by_name()[well]
        
        if volume > max_volume:
            pipette.transfer(volume, tube_well, well_obj, new_tip='never')
        else:
            pipette.aspirate(volume, tube_well)
            pipette.dispense(volume, well_obj)
        
        # Mix
        mix_volume = min(volume * 0.8, max_volume)
        pipette.mix(mix_reps, mix_volume, well_obj)
        pipette.blow_out(well_obj.top())
        
        # Drop tip
        pipette.drop_tip()
    
    return tips

def transfer_supernatant(protocol, source_plate, dest_plate, grouped_wells, pipette, 
                        tips_rack, tips, volume, depth, solution_name="supernatant"):
    '''Transfers supernatant from source to destination plate.'''
    protocol.comment(f"Transferring {volume} µL of {solution_name}")
    
    # Determine max volume per pipette operation based on tip rack
    max_volume = 50 if pipette.max_volume <= 50 else 200
    
    last_size = 0
    tip_attached = False
    
    for i, group in enumerate(grouped_wells):
        group_size = len(group)
        
        if group_size == 0:
            continue
        
        # Determine source and destination locations - using PCR protocol logic
        if group_size == 8:
            source_loc = source_plate.wells_by_name()[group[0]]
            dest_loc = dest_plate.wells_by_name()[group[0]]
        else:
            source_loc = source_plate.wells_by_name()[group[-1]]
            dest_loc = dest_plate.wells_by_name()[group[-1]]
        
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
        
        # Transfer using multiple aspirations if needed
        if volume > max_volume:
            pipette.transfer(volume, source_loc.top(-depth), dest_loc, new_tip='never')
        else:
            pipette.aspirate(volume, source_loc.top(-depth))
            pipette.dispense(volume, dest_loc)
        
        pipette.blow_out(dest_loc.top())
        
        # Only drop the tip at the end of all groups or if we need different tips next time
        is_last_group = (i == len(grouped_wells) - 1)
        needs_different_tips_next = False
        if not is_last_group:
            next_group_size = len(grouped_wells[i+1])
            needs_different_tips_next = (next_group_size != group_size)
            
        if is_last_group or needs_different_tips_next:
            pipette.drop_tip()
            tip_attached = False
    
    return tips

def remove_supernatant(protocol, plate, grouped_wells, pipette, tips_rack, tips, 
                      volume, depth, waste_well):
    '''Removes and discards supernatant.'''
    protocol.comment(f"Removing and discarding {volume} µL of supernatant")
    
    last_size = 0
    tip_attached = False
    
    for i, group in enumerate(grouped_wells):
        group_size = len(group)
        
        if group_size == 0:
            continue
        
        # Determine source location - using PCR protocol logic
        if group_size == 8:
            source_loc = plate.wells_by_name()[group[0]]
        else:
            source_loc = plate.wells_by_name()[group[-1]]
        
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
        
        # Remove supernatant
        pipette.aspirate(volume, source_loc.bottom(depth))
        pipette.dispense(volume, waste_well)
        pipette.blow_out(waste_well.top())
        
        # Only drop the tip at the end of all groups or if we need different tips next time
        is_last_group = (i == len(grouped_wells) - 1)
        needs_different_tips_next = False
        if not is_last_group:
            next_group_size = len(grouped_wells[i+1])
            needs_different_tips_next = (next_group_size != group_size)
            
        if is_last_group or needs_different_tips_next:
            pipette.drop_tip()
            tip_attached = False
    
    return tips

def run(protocol: protocol_api.ProtocolContext):
    # Load waste chute
    waste_chute = protocol.load_waste_chute()
    
    # Load labware - optimized for H1 nozzle accessibility
    elute_plate = protocol.load_labware('armadillo_96_wellplate_200ul_pcr_full_skirt', 'A2') 
    initial_plate = protocol.load_labware('nest_96_wellplate_2ml_deep', 'C1')
    small_tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 'B2')
    reservoir = protocol.load_labware('usascientific_12_reservoir_22ml', 'C2')

    # Load modules
    temp_module = protocol.load_module('temperatureModuleV2', 'D1') 
    collection_plate = temp_module.load_labware('nest_96_wellplate_2ml_deep')
    mag_block = protocol.load_module('magneticBlockV1', 'D2')
    heater_shaker = protocol.load_module('heaterShakerModuleV1', 'A3')

    # Load pipettes and tip racks
    p50 = protocol.load_instrument('flex_8channel_50', 'left', tip_racks=[
        protocol.load_labware('opentrons_flex_96_tiprack_50ul', 'C3')
    ])
    p1000 = protocol.load_instrument('flex_8channel_1000', 'right', tip_racks=[
        protocol.load_labware('opentrons_flex_96_tiprack_1000ul', 'B3'),
    ])
    
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
    
    # Small reagents in tube racks
    mag_clear_beads = small_tube_rack['A1'].top(-37)
    mag_bind_beads = small_tube_rack['A3'].top(-37)
    elution_buffer = small_tube_rack['A2'].top(-37)
    
    # Protocol parameters
    depth1 = 20  # Depth to take supernatant from initial plate
    depth2 = 30  # Depth to take supernatant from collection plate
    
    # Initialize tip tracking - EXACTLY LIKE PCR PROTOCOL
    tips_50 = None
    tips_1000 = None

    protocol.comment("Starting pellet-free miniprep protocol...")
    
    # Step 1: Add 100µL of lysis buffer to each sample, then mix 5 times
    protocol.comment("Step 1: Adding lysis buffer...")
    tips_1000 = dispense_and_mix(protocol, initial_plate, grouped_wells, p1000, 
                              p1000.tip_racks[0], tips_1000, lysis_buffer, 100, 5, "lysis buffer")
    
    # Wait 5 minutes (offset to be less the more samples there are, to account for extra pipetting time)
    wait_time = max(60, 300 - len(unique_wells) * 10)  # Minimum 1 minute, reduce by 10s per sample
    protocol.comment(f"Waiting {wait_time} seconds for lysis...")
    protocol.delay(seconds=wait_time)
    
    # Step 2: Add 450µL of neutralization buffer to each sample, then mix 20 times
    protocol.comment("Step 2: Adding neutralization buffer...")
    tips_1000 = dispense_and_mix(protocol, initial_plate, grouped_wells, p1000, 
                               p1000.tip_racks[0], tips_1000, neutralization_buffer, 450, 20, "neutralization buffer")
    # IndexError [line 524]: list index out of range


    # Step 3: Add 50µL mag clear beads to each sample, then mix 5 times
    protocol.comment("Step 3: Adding magnetic clearing beads...")
    tips_50 = dispense_tube_reagent_and_mix(protocol, initial_plate, grouped_wells, p50, 
                                           p50.tip_racks[0], tips_50, mag_clear_beads, 50, 5, "magnetic clearing beads")

    # Step 4: Move the initial plate to the magnetic module with the gripper
    protocol.comment("Step 4: Moving initial plate to magnetic block...")
    protocol.move_labware(initial_plate, mag_block, use_gripper=True)

    # Wait 5 minutes
    protocol.comment("Waiting 5 minutes for magnetic separation...")
    protocol.delay(minutes=5)

    # Step 5: Take 750µL from each sample in the initial plate and move it to the same location collection plate
    protocol.comment("Step 5: Transferring cleared lysate to collection plate...")
    tips_1000 = transfer_supernatant(protocol, initial_plate, collection_plate, grouped_wells, 
                                   p1000, p1000.tip_racks[0], tips_1000, 750, depth1, "cleared lysate")

    # Step 6: Move the initial plate to staging area (no longer needed)
    protocol.comment("Step 6: Moving used initial plate to staging area...")
    protocol.move_labware(initial_plate, 'D4', use_gripper=True)
    
    # Step 6b: Move elution plate to accessible position for later use
    protocol.comment("Step 6b: Moving elution plate to accessible position...")
    protocol.move_labware(elute_plate, 'C1', use_gripper=True)
    
    # Step 7: Add 30µL of mag binding beads to each sample in the collection plate
    protocol.comment("Step 7: Adding magnetic binding beads to collection plate...")
    tips_50 = dispense_tube_reagent_and_mix(protocol, collection_plate, grouped_wells, p50, 
                                           p50.tip_racks[0], tips_50, mag_bind_beads, 30, 5, "magnetic binding beads")
    
    # Step 8: Mix each sample in the collection plate for 10 minutes
    protocol.comment("Step 8: Mixing samples for 10 minutes for DNA binding...")
    
    # Calculate mixing cycles for 10 minutes total
    mix_cycles = 30  # Mix every 20 seconds for 10 minutes
    for cycle in range(mix_cycles):
        if cycle % 5 == 0:  # Progress update every 5 cycles
            protocol.comment(f"Mixing cycle {cycle + 1}/{mix_cycles}")
        
        # Mix each group
        last_size = 0
        tip_attached = False
        
        for i, group in enumerate(grouped_wells):
            group_size = len(group)
            if group_size == 0:
                continue
                
            loc = collection_plate.wells_by_name()[group[-1]]
            if group_size == 8:
                loc = collection_plate.wells_by_name()[group[0]]
            
            # Configure pipette
            keep_tips, last_size = configure_pipette_for_group(p1000, group_size, last_size)
            
            # Pick up tips if needed
            if not keep_tips:
                if tip_attached:
                    p1000.drop_tip()
                    tip_attached = False
                try:
                    tip_loc, tips_1000 = smart_pick_up(group_size, tips_1000)
                    p1000.pick_up_tip(p1000.tip_racks[0].wells_by_name()[tip_loc])
                    tip_attached = True
                except (NotEnoughTips, KeyError):
                    protocol.comment("Warning: Could not pick up tips for mixing, skipping cycle")
                    break
            
            # Quick mix
            p1000.mix(3, 200, loc)
            
            # Drop tips after last group in cycle
            if i == len(grouped_wells) - 1:
                p1000.drop_tip()
                tip_attached = False
        
        # Wait between cycles
        if cycle < mix_cycles - 1:
            protocol.delay(seconds=20)
     
    # Continue with remaining steps...
    # Step 9: Move collection plate to magnetic module
    protocol.comment("Step 9: Moving collection plate to magnetic block...")
    protocol.move_labware(collection_plate, mag_block, use_gripper=True)

    # Wait 5 minutes
    protocol.comment("Waiting 5 minutes for magnetic separation...")
    protocol.delay(minutes=5)

    # Step 10: Remove and discard supernatant
    protocol.comment("Step 10: Removing supernatant...")
    tips_1000 = remove_supernatant(protocol, collection_plate, grouped_wells, p1000, 
                                 p1000.tip_racks[0], tips_1000, 750, depth2, waste1)

    # Step 11: Move collection plate off magnetic block
    protocol.comment("Step 11: Moving collection plate off magnetic block...")
    protocol.move_labware(collection_plate, temp_module, use_gripper=True)

    # Step 12: Add endo wash buffer
    protocol.comment("Step 12: Adding endo wash buffer...")
    tips_1000 = dispense_and_mix(protocol, collection_plate, grouped_wells, p1000, 
                               p1000.tip_racks[0], tips_1000, endo_wash, 200, 15, "endo wash buffer")

    # Step 13: Move to magnetic block
    protocol.comment("Step 13: Moving collection plate to magnetic block...")
    protocol.move_labware(collection_plate, mag_block, use_gripper=True)

    # Wait 2 minutes
    protocol.comment("Waiting 2 minutes for magnetic separation...")
    protocol.delay(minutes=2)

    # Step 14: Remove endo wash supernatant
    protocol.comment("Step 14: Removing endo wash supernatant...")
    tips_1000 = remove_supernatant(protocol, collection_plate, grouped_wells, p1000, 
                                 p1000.tip_racks[0], tips_1000, 200, depth2, waste1)

    # Steps 15-18: Zyppy wash (performed twice)
    for wash_round in range(2):
        protocol.comment(f"Starting Zyppy wash round {wash_round + 1}/2")

        # Move off magnetic block
        protocol.comment(f"Step 15 (round {wash_round + 1}): Moving collection plate off magnetic block...")
        protocol.move_labware(collection_plate, temp_module, use_gripper=True)

        # Add Zyppy wash buffer
        protocol.comment(f"Step 16 (round {wash_round + 1}): Adding Zyppy wash buffer...")
        tips_1000 = dispense_and_mix(protocol, collection_plate, grouped_wells, p1000, 
                                   p1000.tip_racks[0], tips_1000, zyppy_wash, 400, 15, "Zyppy wash buffer")

        # Move to magnetic block
        protocol.comment(f"Step 17 (round {wash_round + 1}): Moving collection plate to magnetic block...")
        protocol.move_labware(collection_plate, mag_block, use_gripper=True)

        # Wait 2 minutes
        protocol.comment("Waiting 2 minutes for magnetic separation...")
        protocol.delay(minutes=2)

        # Remove Zyppy wash supernatant
        protocol.comment(f"Step 18 (round {wash_round + 1}): Removing Zyppy wash supernatant...")
        tips_1000 = remove_supernatant(protocol, collection_plate, grouped_wells, p1000, 
                                     p1000.tip_racks[0], tips_1000, 400, depth2, waste1)

    # Step 19: Set temperature and dry
    protocol.comment("Step 19: Setting temperature module to 65°C and moving collection plate...")
    temp_module.set_temperature(65)
    protocol.move_labware(collection_plate, temp_module, use_gripper=True)

    # Wait 30 minutes
    protocol.comment("Waiting 30 minutes at 65°C for drying...")
    protocol.delay(minutes=30)

    # Step 20: Move off temperature module
    protocol.comment("Step 20: Moving collection plate off temperature module...")
    protocol.move_labware(collection_plate, 'D1', use_gripper=True)

    # Step 21: Add elution buffer
    protocol.comment("Step 21: Adding elution buffer...")
    tips_50 = dispense_tube_reagent_and_mix(protocol, collection_plate, grouped_wells, p50, 
                                           p50.tip_racks[0], tips_50, elution_buffer, 40, 5, "elution buffer")

    # Step 22: Move back to temperature module
    protocol.comment("Step 22: Moving collection plate back to temperature module...")
    protocol.move_labware(collection_plate, temp_module, use_gripper=True)

    # Step 23: Mix for elution
    protocol.comment("Step 23: Mixing samples for 5 minutes for elution...")
    
    # Calculate mixing cycles for 5 minutes total
    mix_cycles = 15  # Mix every 20 seconds for 5 minutes
    for cycle in range(mix_cycles):
        if cycle % 3 == 0:  # Progress update every 3 cycles
            protocol.comment(f"Elution mixing cycle {cycle + 1}/{mix_cycles}")
        
        # Mix each group
        last_size = 0
        tip_attached = False
        
        for i, group in enumerate(grouped_wells):
            group_size = len(group)
            if group_size == 0:
                continue
                
            loc = collection_plate.wells_by_name()[group[-1]]
            if group_size == 8:
                loc = collection_plate.wells_by_name()[group[0]]
            
            # Configure pipette
            keep_tips, last_size = configure_pipette_for_group(p50, group_size, last_size)
            
            # Pick up tips if needed
            if not keep_tips:
                if tip_attached:
                    p50.drop_tip()
                    tip_attached = False
                try:
                    tip_loc, tips_50 = smart_pick_up(group_size, tips_50)
                    p50.pick_up_tip(p50.tip_racks[0].wells_by_name()[tip_loc])
                    tip_attached = True
                except (NotEnoughTips, KeyError):
                    protocol.comment("Warning: Could not pick up tips for mixing, skipping cycle")
                    break
            
            # Quick mix
            p50.mix(3, 30, loc)
            
            # Drop tips after last group in cycle
            if i == len(grouped_wells) - 1:
                p50.drop_tip()
                tip_attached = False
        
        # Wait between cycles
        if cycle < mix_cycles - 1:
            protocol.delay(seconds=20)

    # Step 24: Final magnetic separation
    protocol.comment("Step 24: Moving collection plate to magnetic block for final separation...")
    protocol.move_labware(collection_plate, mag_block, use_gripper=True)

    # Wait 1 minute
    protocol.comment("Waiting 1 minute for final magnetic separation...")
    protocol.delay(minutes=1)

    # Step 25: Transfer purified DNA to elution plate
    protocol.comment("Step 25: Transferring purified DNA to elution plate...")
    tips_50 = transfer_supernatant(protocol, collection_plate, elute_plate, grouped_wells, 
                                  p50, p50.tip_racks[0], tips_50, 30, depth2, "purified DNA")

    # Deactivate temperature module
    temp_module.deactivate()

    protocol.comment("Miniprep protocol complete! Your purified DNA is ready in the elution plate.")