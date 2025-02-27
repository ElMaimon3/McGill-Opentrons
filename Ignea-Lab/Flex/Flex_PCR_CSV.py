# imports
from opentrons import protocol_api
from opentrons.protocol_api import SINGLE, PARTIAL_COLUMN, ALL
from typing import List, Dict, Tuple, Set, Optional, Any


# metadata
metadata = {
    'protocolName': 'Customizable PCR (CSV)',
    "author": "Gabriel Straface (Ignea Lab @ McGill University)",
    'description': '''Fully customizable PCR for the Opentrons Flex.
    The protocol allows you to specify which components (template DNA, primers) 
    are the same across all samples and which are different. The robot will add 
    components that are the same, while different components must be added manually.'''
}
requirements = {"robotType": "Flex", "apiLevel": "2.21"}


# Runtime Parameters
def add_parameters(parameters: protocol_api.Parameters):
    parameters.add_csv_file(
        variable_name="well_csv",
        display_name="PCR locations csv",
        description=(
            "Table with three columns:"
            " rows (e.g. 1), columns (e.g. B)"
            " and wells (e.g. B1)"
        )
    )
    
    # Configuration parameters for what's consistent vs variable
    parameters.add_bool(
        variable_name="same_template_dna",
        display_name="Same Template DNA",
        description="Enable if all samples use the same template DNA (robot will add it)",
        default=False
    )
    parameters.add_bool(
        variable_name="same_primers",
        display_name="Same Primers",
        description="Enable if all samples use the same primers (robot will add them)",
        default=True
    )
    
    # Template DNA parameters
    parameters.add_int(
        variable_name="template_dna_volume",
        display_name="Template DNA Volume",
        description="Volume of template DNA per sample",
        default=1,
        minimum=1,
        maximum=25,
        unit="µL"
    )
    
    # Master mix parameters
    parameters.add_int(
        variable_name="master_volume",
        display_name="Master Mix Volume",
        description="Volume of master mix to add to each sample",
        default=20,
        minimum=10,
        maximum=100,
        unit="µL"
    )
    
    # Primer parameters
    parameters.add_int(
        variable_name="primer_volume",
        display_name="Primer Volume",
        description="Volume of primers for each sample",
        default=20,
        minimum=5,
        maximum=30,
        unit="µL"
    )
    
    # Thermocycler parameters
    parameters.add_int(
        variable_name="denaturation_temp",
        display_name="Denaturation Temperature",
        description="",
        default=98,
        minimum=4,
        maximum=99,
        unit="Celsius"
    )
    parameters.add_int(
        variable_name="annealing_temp",
        display_name="Annealing Temperature",
        description="",
        default=63,
        minimum=4,
        maximum=99,
        unit="Celsius"
    )
    parameters.add_int(
        variable_name="extension_temp",
        display_name="Extension Temperature",
        description="",
        default=72,
        minimum=4,
        maximum=99,
        unit="Celsius"
    )
    parameters.add_int(
        variable_name="init_denaturation_time",
        display_name="Initial Denaturation Time",
        description="",
        default=15,
        minimum=1,
        maximum=999,
        unit="Seconds"
    )
    parameters.add_int(
        variable_name="denaturation_time",
        display_name="Denaturation Time",
        description="For each cycle",
        default=30,
        minimum=1,
        maximum=999,
        unit="Seconds"
    )
    parameters.add_int(
        variable_name="annealing_time",
        display_name="Annealing Time",
        description="For each cycle",
        default=20,
        minimum=1,
        maximum=999,
        unit="Seconds"
    )
    parameters.add_int(
        variable_name="extension_time",
        display_name="Extension Time",
        description="For each cycle",
        default=210,
        minimum=1,
        maximum=999,
        unit="Seconds"
    )
    parameters.add_int(
        variable_name="final_extension_time",
        display_name="Final Extension Time",
        description="",
        default=120,
        minimum=1,
        maximum=999,
        unit="Seconds"
    )
    parameters.add_int(
        variable_name="num_cycles",
        display_name="Number of cycles",
        description="",
        default=30,
        minimum=1,
        maximum=150
    )
    
    # Colony PCR parameters
    parameters.add_bool(
        variable_name="colony_pcr",
        display_name="Colony PCR",
        description="Enable if performing Colony PCR",
        default=False
    )
    parameters.add_int(
        variable_name="lysis_temp",
        display_name="Lysis Temperature",
        description="For colony PCR",
        default=98,
        minimum=4,
        maximum=99,
        unit="Celsius"
    )
    parameters.add_int(
        variable_name="lysis_time",
        display_name="Lysis Time",
        description="For colony PCR",
        default=600,
        minimum=1,
        maximum=999,
        unit="Seconds"
    )
    
    # Debug mode
    parameters.add_bool(
        variable_name="debug",
        display_name="Debugging Mode",
        description="Run in simulation mode only",
        default=False
    )

# Utility functions
def vol_to_height(vol: float) -> float:
    '''
    Converts volume of liquid to appropriate pipette depth.
    
    Args:
        vol: Volume of liquid in mL
        
    Returns:
        Appropriate pipette depth in mm
    '''
    full_depth = 40
    if vol > 0:
        return round(-2.6*vol + full_depth)
    else:
        return full_depth

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
    Extracts location data from parsed CSV.
    
    Args:
        csv_data: Data from the CSV file parsed with parse_as_csv()
        
    Returns:
        Tuple of lists containing columns, rows, and individual wells
    '''
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

def get_unique_wells(protocol, tc_plate, columns, rows, wells) -> List[str]:
    '''
    Creates a list of unique well names from columns, rows, and individual wells.
    
    Args:
        protocol: Protocol context for logging
        tc_plate: The labware containing the wells
        columns: List of column indices
        rows: List of row indices
        wells: List of individual well names
        
    Returns:
        List of unique well names
    '''
    # Get all wells from the specified columns and rows
    destination_wells = []
    for col in columns:
        destination_wells.extend(tc_plate.columns_by_name()[col])
    for row in rows:
        destination_wells.extend(tc_plate.rows_by_name()[row])
    destination_wells.extend([tc_plate.wells_by_name()[well] for well in wells])
    
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

def dispense_solution(protocol, tc_plate, grouped_wells, pipette, tips_rack, tips, 
                      solution_well, volume, height_tracker, solution_name="solution"):
    '''
    Dispenses solution from a reservoir to wells in the PCR plate.
    
    Args:
        protocol: Protocol context
        tc_plate: PCR plate labware
        grouped_wells: Grouped well locations
        pipette: Pipette to use
        tips_rack: Tip rack to use
        tips: Dictionary of available tips
        solution_well: Source well for the solution
        volume: Volume to dispense
        height_tracker: Tracker for liquid height in the source well
        solution_name: Name of the solution (for logging)
        
    Returns:
        Updated tips dictionary and height tracker
    '''
    protocol.comment(f"Adding {volume} µL of {solution_name} to each sample")
    
    last_size = 0
    tip_attached = False
    
    for group in grouped_wells:
        group_size = len(group)
        # Determine the location to dispense to
        loc = tc_plate.wells_by_name()[group[-1]]
        if group_size == 8:
            loc = tc_plate.wells_by_name()[group[0]]
        
        # Configure pipette based on group size
        keep_tips, last_size = configure_pipette_for_group(pipette, group_size, last_size)
        
        # Pick up tips if needed
        if not keep_tips:
            if tip_attached:
                pipette.drop_tip()
            tip_loc, tips = smart_pick_up(group_size, tips)
            pipette.pick_up_tip(tips_rack.wells_by_name()[tip_loc])
            tip_attached = True
        
        # Dispense the solution
        pipette.aspirate(volume, solution_well.top(-vol_to_height(height_tracker)))
        pipette.dispense(volume, loc.top())
        height_tracker -= group_size * 0.001 * volume
        
        # Drop the tip
        pipette.drop_tip()
    
    return tips, height_tracker

def run(protocol: protocol_api.ProtocolContext):
    # Get PCR parameters from runtime inputs
    well_csv = protocol.params.well_csv
    same_template_dna = protocol.params.same_template_dna
    same_primers = protocol.params.same_primers
    template_dna_volume = protocol.params.template_dna_volume
    master_mix_volume = protocol.params.master_volume
    primer_volume = protocol.params.primer_volume
    denaturation_temp = protocol.params.denaturation_temp
    initial_denaturation_time_seconds = protocol.params.init_denaturation_time
    denaturation_time_seconds = protocol.params.denaturation_time
    annealing_temp = protocol.params.annealing_temp
    annealing_time_seconds = protocol.params.annealing_time
    extension_temp = protocol.params.extension_temp
    extension_time_seconds = protocol.params.extension_time
    final_extension_time_seconds = protocol.params.final_extension_time
    num_cycles = protocol.params.num_cycles
    colony_pcr = protocol.params.colony_pcr
    lysis_temp = protocol.params.lysis_temp
    lysis_time_seconds = protocol.params.lysis_time
    debug = protocol.params.debug

    # Calculate volumes
    total_volume = master_mix_volume
    if same_template_dna:
        total_volume += template_dna_volume
    if same_primers:
        total_volume += primer_volume

    # Load labware
    chute = protocol.load_waste_chute()
    tiprack50 = protocol.load_labware('opentrons_flex_96_tiprack_50ul', 'D1')
    tiprack200 = protocol.load_labware('opentrons_flex_96_tiprack_200ul', 'D2')
    res = protocol.load_labware('nest_12_reservoir_15ml','C1')
    tc_mod = protocol.load_module('thermocyclerModuleV2')
    tc_plate = protocol.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt', 'C2')

    # Load pipettes
    p50 = protocol.load_instrument('flex_8channel_50', 'left')
    p200 = protocol.load_instrument('flex_8channel_1000', 'right')
    
    # Define reagent locations and volumes - now specified by position
    master_mix = res.wells_by_name()['A1']
    template_dna = res.wells_by_name()['A2']
    primers = res.wells_by_name()['A3']
    
    # Initialize liquid height trackers
    primer_height_tracker = 4  # mL
    template_height_tracker = 4  # mL
    master_mix_height_tracker = 4  # mL
    
    # Initialize tip tracking
    tips50 = None
    tips200 = None

    # Define thermocycling program
    pcr_program = [
        {'temperature': denaturation_temp, 'hold_time_seconds': denaturation_time_seconds},
        {'temperature': annealing_temp, 'hold_time_seconds': annealing_time_seconds},
        {'temperature': extension_temp, 'hold_time_seconds': extension_time_seconds},
    ]

    # Open the thermocycler lid
    tc_mod.open_lid()

    # Print setup information for the user
    protocol.comment("=== PCR SETUP INFORMATION ===")
    protocol.comment(f"Master Mix: {master_mix_volume} µL (Robot will add to all samples)")
    
    if same_template_dna:
        protocol.comment(f"Template DNA: {template_dna_volume} µL (Robot will add to all samples)")
    else:
        protocol.comment(f"Template DNA: {template_dna_volume} µL (Must be added manually to each sample)")
        
    if same_primers:
        protocol.comment(f"Primers: {primer_volume} µL (Robot will add to all samples)")
    else:
        protocol.comment(f"Primers: {primer_volume} µL (Must be added manually to each sample)")
    
    protocol.comment("===========================")

    if not debug:
        # Parse CSV data for well locations
        csv_data = well_csv.parse_as_csv()
        sample_columns, sample_rows, sample_wells = parse_csv_locations(csv_data)
        
        # Get unique wells and group them
        unique_wells = get_unique_wells(protocol, tc_plate, sample_columns, sample_rows, sample_wells)
        grouped_wells = group_wells(unique_wells)
        
        # Add solutions that are the same across all samples
        
        # 1. Always add master mix
        master_pipette = p50 if master_mix_volume < 50 else p200
        master_rack = tiprack50 if master_mix_volume < 50 else tiprack200
        master_tips = tips50 if master_mix_volume < 50 else tips200
        
        master_tips, master_mix_height_tracker = dispense_solution(
            protocol, tc_plate, grouped_wells, master_pipette,
            master_rack, master_tips, master_mix, master_mix_volume, 
            master_mix_height_tracker, "master mix"
        )
        
        # Update tip tracking
        if master_mix_volume < 50:
            tips50 = master_tips
        else:
            tips200 = master_tips
        
        # 2. Add template DNA if it's the same for all samples
        if same_template_dna:
            template_pipette = p50 if template_dna_volume < 50 else p200
            template_rack = tiprack50 if template_dna_volume < 50 else tiprack200
            template_tips = tips50 if template_dna_volume < 50 else tips200
            
            template_tips, template_height_tracker = dispense_solution(
                protocol, tc_plate, grouped_wells, template_pipette,
                template_rack, template_tips, template_dna, template_dna_volume, 
                template_height_tracker, "template DNA"
            )
            
            # Update tip tracking
            if template_dna_volume < 50:
                tips50 = template_tips
            else:
                tips200 = template_tips
        
        # 3. Add primers if they're the same for all samples
        if same_primers:
            primer_pipette = p50 if primer_volume < 50 else p200
            primer_rack = tiprack50 if primer_volume < 50 else tiprack200
            primer_tips = tips50 if primer_volume < 50 else tips200
            
            primer_tips, primer_height_tracker = dispense_solution(
                protocol, tc_plate, grouped_wells, primer_pipette,
                primer_rack, primer_tips, primers, primer_volume, 
                primer_height_tracker, "primers"
            )
            
            # Update tip tracking
            if primer_volume < 50:
                tips50 = primer_tips
            else:
                tips200 = primer_tips
                
        # Pause to allow manual additions if needed
        if not same_template_dna or not same_primers:
            manual_additions = []
            if not same_template_dna:
                manual_additions.append(f"template DNA ({template_dna_volume} µL)")
            if not same_primers:
                manual_additions.append(f"primers ({primer_volume} µL)")
                
            manual_text = " and ".join(manual_additions)
            protocol.pause(f"Please add {manual_text} to each sample manually, then resume.")
    
    # Move PCR plate to thermocycler and run program
    if not debug:
        protocol.move_labware(
            labware=tc_plate, new_location=tc_mod, use_gripper=True
        )
        
        # Run thermocycler
        protocol.comment("Running thermocycler...")
        tc_mod.close_lid()
        tc_mod.set_lid_temperature(105)
        
        # Colony PCR lysis step if applicable
        if colony_pcr:
            protocol.comment(f"Running cell lysis at {lysis_temp}°C for {lysis_time_seconds} seconds")
            tc_mod.set_block_temperature(
                temperature=lysis_temp,
                hold_time_seconds=lysis_time_seconds,
                block_max_volume=total_volume
            )
        
        # Initial denaturation
        protocol.comment(f"Initial denaturation at {denaturation_temp}°C for {initial_denaturation_time_seconds} seconds")
        tc_mod.set_block_temperature(
            temperature=denaturation_temp,
            hold_time_seconds=initial_denaturation_time_seconds, 
            block_max_volume=total_volume
        )
        
        # PCR cycles
        protocol.comment(f"Running {num_cycles} PCR cycles")
        tc_mod.execute_profile(
            steps=pcr_program, 
            repetitions=num_cycles, 
            block_max_volume=total_volume
        )
        
        # Final extension
        protocol.comment(f"Final extension at {extension_temp}°C for {final_extension_time_seconds} seconds")
        tc_mod.set_block_temperature(
            temperature=extension_temp, 
            hold_time_seconds=final_extension_time_seconds, 
            block_max_volume=total_volume
        )
        
        # Cool down and open lid
        protocol.comment("PCR complete. Cooling down to 4°C")
        tc_mod.deactivate_lid()
        tc_mod.open_lid()
        tc_mod.set_block_temperature(4)