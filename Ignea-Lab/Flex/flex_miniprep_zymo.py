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

def parse_csv_locations(csv_data: List[List[str]]) -> Tuple[List[str], List[str], List[str]]:
    '''Extracts location data from parsed CSV.'''
    sample_columns = []  # eg. ['1', '2']
    sample_rows = []     # eg. ['A', 'B']
    sample_wells = []    # eg. ['A1', 'B1']
    
    # Skip header row
    for row in csv_data[1:]:
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
    '''Creates a list of unique well names from columns, rows, and individual wells.'''
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
        well_name = well_str.split()[0]  # Extract just the well name
        if well_str not in unique_wells_dict:
            unique_wells.append(well_name)
            unique_wells_dict[well_str] = True
        else:
            protocol.comment(f"Duplicate location found and removed: {well_str}")
            
    return unique_wells

def dispense_and_mix(protocol, plate, grouped_wells, pipette, tips_rack, tips, 
                     source_well, volume, mix_reps, solution_name="solution"):
    '''Dispenses solution and mixes - for reservoir reagents only.'''
    protocol.comment(f"Adding {volume} µL of {solution_name} to each sample and mixing {mix_reps} times")
    
    last_size = 0
    tip_attached = False
    
    for i, group in enumerate(grouped_wells):
        group_size = len(group)
        # Determine the location to dispense to
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
        
        # Dispense and mix
        pipette.aspirate(volume, source_well)
        pipette.dispense(volume, loc)
        pipette.mix(mix_reps, volume * 0.8, loc)
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
    
    # Process each well individually since we need single tip aspiration from tube
    for well in [w for group in grouped_wells for w in group]:
        # Always use single tip for tube aspiration
        pipette.configure_nozzle_layout(style=SINGLE, start="H1")
        
        # Pick up single tip
        tip_loc, tips = smart_pick_up(1, tips)
        pipette.pick_up_tip(tips_rack.wells_by_name()[tip_loc])
        
        # Aspirate from tube with single tip
        pipette.aspirate(volume, tube_well.bottom(37))  # 37mm from bottom for 1.5mL tubes
        
        # Dispense to well and mix
        well_obj = plate.wells_by_name()[well]
        pipette.dispense(volume, well_obj)
        pipette.mix(mix_reps, volume * 0.8, well_obj)
        pipette.blow_out(well_obj.top())
        
        # Drop tip
        pipette.drop_tip()
    
    return tips

def transfer_supernatant(protocol, source_plate, dest_plate, grouped_wells, pipette, 
                        tips_rack, tips, volume, depth, solution_name="supernatant"):
    '''Transfers supernatant from source to destination plate.'''
    protocol.comment(f"Transferring {volume} µL of {solution_name}")
    
    last_size = 0
    tip_attached = False
    
    for i, group in enumerate(grouped_wells):
        group_size = len(group)
        
        # Determine source and destination locations
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
        
        # Transfer
        pipette.aspirate(volume, source_loc.bottom(depth))
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
        
        # Determine source location
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
    
    # Load labware
    initial_plate = protocol.load_labware('nest_96_wellplate_2ml_deep', 'A2') # Eventually switch to Zymo 96 well block
    small_tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 'B2')
    reservoir = protocol.load_labware('usascientific_12_reservoir_22ml', 'C2')
    elute_plate = protocol.load_labware('armadillo_96_wellplate_200ul_pcr_full_skirt', 'C1') # Eventually change to zymo elute plate
    
    # Load modules
    temp_module = protocol.load_module('temperatureModuleV2', 'D1') 
    collection_plate = temp_module.load_labware('nest_96_wellplate_2ml_deep') # Eventually switch to Zymo 96 collection
    mag_block = protocol.load_module('magneticBlockV1', 'D2')
    heater_shaker = protocol.load_module('heaterShakerModuleV1', 'A3')

    
    # Load pipettes and tip racks
    p50 = protocol.load_instrument('flex_8channel_50', 'left', tip_racks=[
        protocol.load_labware('opentrons_flex_96_tiprack_50ul', 'C3')
    ])
    p300 = protocol.load_instrument('flex_8channel_1000', 'right', tip_racks=[
        protocol.load_labware('opentrons_flex_96_tiprack_1000ul', 'B3'),
    ])
    
    # Parse CSV data for well locations
    well_csv = protocol.params.well_csv
    csv_data = well_csv.parse_as_csv()
    sample_columns, sample_rows, sample_wells = parse_csv_locations(csv_data)
    
    # Get unique wells and group them
    unique_wells = get_unique_wells(protocol, initial_plate, sample_columns, sample_rows, sample_wells)
    grouped_wells = group_wells_by_column(unique_wells)
    
    protocol.comment(f"Processing {len(unique_wells)} samples in {len(grouped_wells)} groups")
    
    # Define reagent locations in reservoir
    lysis_buffer = reservoir['A1']
    neutralization_buffer = reservoir['A2'] 
    endo_wash = reservoir['A3']
    zyppy_wash = reservoir['A4']
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

    protocol.comment("Starting pellet-free miniprep protocol...")
    
    # Step 1: Add 100µL of lysis buffer to each sample, then mix 5 times
    protocol.comment("Step 1: Adding lysis buffer...")
    tips_50 = dispense_and_mix(protocol, initial_plate, grouped_wells, p50, 
                              p50.tip_racks[0], tips_50, lysis_buffer, 100, 5, "lysis buffer")
    
    # Wait 5 minutes (offset to be less the more samples there are, to account for extra pipetting time)
    wait_time = max(60, 300 - len(unique_wells) * 10)  # Minimum 1 minute, reduce by 10s per sample
    protocol.comment(f"Waiting {wait_time} seconds for lysis...")
    protocol.delay(seconds=wait_time)
    
    # Step 2: Add 450µL of neutralization buffer to each sample, then mix 20 times
    protocol.comment("Step 2: Adding neutralization buffer...")
    tips_300 = dispense_and_mix(protocol, initial_plate, grouped_wells, p300, 
                               p300.tip_racks[0], tips_300, neutralization_buffer, 450, 20, "neutralization buffer")
    
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

    # Step 5: Take 750µL from each sample in the initial plate and move it to the same location collection plate, use depth 1
    protocol.comment("Step 5: Transferring cleared lysate to collection plate...")
    tips_300 = transfer_supernatant(protocol, initial_plate, collection_plate, grouped_wells, 
                                   p300, p300.tip_racks[0], tips_300, 750, depth1, "cleared lysate")

    # Step 6: Move the initial plate off of the magnetic module
    protocol.comment("Step 6: Moving initial plate off magnetic block...")
    protocol.move_labware(initial_plate, 'A2', use_gripper=True)

    # Step 7: Add 30µL of mag binding beads to each sample in the collection plate
    protocol.comment("Step 7: Adding magnetic binding beads to collection plate...")
    tips_50 = dispense_tube_reagent_and_mix(protocol, collection_plate, grouped_wells, p50, 
                                           p50.tip_racks[0], tips_50, mag_bind_beads, 30, 5, "magnetic binding beads")
    
    # Step 8: Mix each sample in the collection plate once, repeating for a total of 10 minutes
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
            loc = collection_plate.wells_by_name()[group[-1]]
            if group_size == 8:
                loc = collection_plate.wells_by_name()[group[0]]
            
            # Configure pipette
            keep_tips, last_size = configure_pipette_for_group(p300, group_size, last_size)
            
            # Pick up tips if needed
            if not keep_tips:
                if tip_attached:
                    p300.drop_tip()
                    tip_attached = False
                tip_loc, tips_300 = smart_pick_up(group_size, tips_300)
                p300.pick_up_tip(p300.tip_racks[0].wells_by_name()[tip_loc])
                tip_attached = True
            
            # Quick mix
            p300.mix(3, 200, loc)
            
            # Drop tips after last group in cycle
            if i == len(grouped_wells) - 1:
                p300.drop_tip()
                tip_attached = False
        
        # Wait between cycles
        if cycle < mix_cycles - 1:
            protocol.delay(seconds=20)
     
    # Step 9: Move collection plate to magnetic module with the gripper
    protocol.comment("Step 9: Moving collection plate to magnetic block...")
    protocol.move_labware(collection_plate, mag_block, use_gripper=True)

    # Wait 5 minutes
    protocol.comment("Waiting 5 minutes for magnetic separation...")
    protocol.delay(minutes=5)

    # Step 10: remove and discard supernatant from each sample in the collection plate (750µL), use depth 2
    protocol.comment("Step 10: Removing supernatant...")
    tips_300 = remove_supernatant(protocol, collection_plate, grouped_wells, p300, 
                                 p300.tip_racks[0], tips_300, 750, depth2, waste1)

    # Step 11: Move collection plate off of the magnetic module with the gripper
    protocol.comment("Step 11: Moving collection plate off magnetic block...")
    protocol.move_labware(collection_plate, temp_module, use_gripper=True)

    # Step 12: Add 200µL of endowash buffer to each sample in the collection plate, then mix 15 times
    protocol.comment("Step 12: Adding endo wash buffer...")
    tips_300 = dispense_and_mix(protocol, collection_plate, grouped_wells, p300, 
                               p300.tip_racks[0], tips_300, endo_wash, 200, 15, "endo wash buffer")

    # Step 13: Same as step 9
    protocol.comment("Step 13: Moving collection plate to magnetic block...")
    protocol.move_labware(collection_plate, mag_block, use_gripper=True)

    # Wait 2 minutes
    protocol.comment("Waiting 2 minutes for magnetic separation...")
    protocol.delay(minutes=2)

    # Step 14: Remove and discard supernatant from each sample in the collection plate (200µL), use depth 2
    protocol.comment("Step 14: Removing endo wash supernatant...")
    tips_300 = remove_supernatant(protocol, collection_plate, grouped_wells, p300, 
                                 p300.tip_racks[0], tips_300, 200, depth2, waste1)

    # Steps 15-18 are performed twice for Zyppy wash
    for wash_round in range(2):
        protocol.comment(f"Starting Zyppy wash round {wash_round + 1}/2")

        # Step 15: Same as step 11
        protocol.comment(f"Step 15 (round {wash_round + 1}): Moving collection plate off magnetic block...")
        protocol.move_labware(collection_plate, temp_module, use_gripper=True)

        # Step 16: Add 400µL of Zyppy wash buffer to each sample in the collection plate, then mix 15 times
        protocol.comment(f"Step 16 (round {wash_round + 1}): Adding Zyppy wash buffer...")
        tips_300 = dispense_and_mix(protocol, collection_plate, grouped_wells, p300, 
                                   p300.tip_racks[0], tips_300, zyppy_wash, 400, 15, "Zyppy wash buffer")

        # Step 17: Same as step 9
        protocol.comment(f"Step 17 (round {wash_round + 1}): Moving collection plate to magnetic block...")
        protocol.move_labware(collection_plate, mag_block, use_gripper=True)

        # Wait 2 minutes
        protocol.comment("Waiting 2 minutes for magnetic separation...")
        protocol.delay(minutes=2)

        # Step 18: Remove and discard supernatant from each sample in the collection plate (400µL), use depth 2
        protocol.comment(f"Step 18 (round {wash_round + 1}): Removing Zyppy wash supernatant...")
        tips_300 = remove_supernatant(protocol, collection_plate, grouped_wells, p300, 
                                     p300.tip_racks[0], tips_300, 400, depth2, waste1)

    # Step 19: Set temperature module to 65C and move collection plate to it with the gripper
    protocol.comment("Step 19: Setting temperature module to 65°C and moving collection plate...")
    temp_module.set_temperature(65)
    protocol.move_labware(collection_plate, temp_module, use_gripper=True)

    # Wait 30 minutes
    protocol.comment("Waiting 30 minutes at 65°C for drying...")
    protocol.delay(minutes=30)

    # Step 20: Move collection plate off the temperature module with the gripper
    protocol.comment("Step 20: Moving collection plate off temperature module...")
    protocol.move_labware(collection_plate, 'D1', use_gripper=True)

    # Step 21: Add 40µL of elution buffer to each sample in the collection plate, then mix 5 times
    protocol.comment("Step 21: Adding elution buffer...")
    tips_50 = dispense_tube_reagent_and_mix(protocol, collection_plate, grouped_wells, p50, 
                                           p50.tip_racks[0], tips_50, elution_buffer, 40, 5, "elution buffer")

    # Step 22: Move collection plate back to the temperature module at 65C
    protocol.comment("Step 22: Moving collection plate back to temperature module...")
    protocol.move_labware(collection_plate, temp_module, use_gripper=True)

    # Step 23: Mix each sample in the collection plate once, repeating for a total of 5 minutes
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
                tip_loc, tips_50 = smart_pick_up(group_size, tips_50)
                p50.pick_up_tip(p50.tip_racks[0].wells_by_name()[tip_loc])
                tip_attached = True
            
            # Quick mix
            p50.mix(3, 30, loc)
            
            # Drop tips after last group in cycle
            if i == len(grouped_wells) - 1:
                p50.drop_tip()
                tip_attached = False
        
        # Wait between cycles
        if cycle < mix_cycles - 1:
            protocol.delay(seconds=20)

    # Step 24: Move to magnetic block
    protocol.comment("Step 24: Moving collection plate to magnetic block for final separation...")
    protocol.move_labware(collection_plate, mag_block, use_gripper=True)

    # Wait 1 minute
    protocol.comment("Waiting 1 minute for final magnetic separation...")
    protocol.delay(minutes=1)

    # Step 25: Transfer 30µL from each sample in the collection plate to the same location in the elution plate, use depth 2
    protocol.comment("Step 25: Transferring purified DNA to elution plate...")
    tips_50 = transfer_supernatant(protocol, collection_plate, elute_plate, grouped_wells, 
                                  p50, p50.tip_racks[0], tips_50, 30, depth2, "purified DNA")

    # Deactivate temperature module
    temp_module.deactivate()

    protocol.comment("Miniprep protocol complete! Your purified DNA is ready in the elution plate.")