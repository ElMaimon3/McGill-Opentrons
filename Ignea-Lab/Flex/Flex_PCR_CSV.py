# imports
from opentrons import protocol_api
from opentrons.protocol_api import SINGLE
from typing import List, Dict, Tuple, Optional, Any


# metadata
metadata = {
    'protocolName': 'Customizable PCR (CSV)',
    "author": "Gabriel Straface (Ignea Lab @ McGill University)",
    'description': '''Fully customizable PCR for the Opentrons Flex.
    The protocol allows you to specify which components (template DNA, primers) 
    are the same across all samples and which are different. The robot will add 
    components that are the same, while different components must be added manually.
    This version uses the 8-channel pipette in single-tip mode for eppendorf tubes.'''
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

def dispense_solution(protocol, tc_plate, unique_wells, pipette, tips_rack, 
                     solution_well, volume, solution_name="solution", tip_index=0):
    '''
    Dispenses solution from a source well to PCR plate wells using single-tip mode.
    Uses a single tip for all wells when dispensing the same reagent.
    
    Args:
        protocol: Protocol context
        tc_plate: PCR plate labware
        unique_wells: List of unique well names
        pipette: Pipette to use
        tips_rack: Tip rack to use
        solution_well: Source well for the solution
        volume: Volume to dispense
        solution_name: Name of the solution (for logging)
        tip_index: Index of the next available tip to use
        
    Returns:
        Next available tip index
    '''
    protocol.comment(f"Adding {volume} µL of {solution_name} to each sample")
    
    # Configure pipette for single-tip use
    pipette.configure_nozzle_layout(
        style=SINGLE,
        start="H1"
    )
    
    # Calculate which tip to use (moving sequentially through the tip rack)
    row = tip_index % 8  # 0-7 for rows A-H
    col = tip_index // 8  # Column number
    
    if col >= 12:
        protocol.pause(f"Warning: Not enough tips in the rack for {solution_name}. Please replace the tip rack.")
        row = 0
        col = 0
    
    tip_well = f"{chr(65 + row)}{col + 1}"  # Convert to well name like 'A1'
    protocol.comment(f"Using tip at position {tip_well} for {solution_name}")
    
    # Pick up the selected tip
    pipette.pick_up_tip(tips_rack.wells_by_name()[tip_well])
    
    # Process each well with the same tip
    for well in unique_wells:
        # Aspirate and dispense
        pipette.aspirate(volume, solution_well)
        pipette.dispense(volume, tc_plate.wells_by_name()[well])
    
    # Drop the tip after all wells are processed
    pipette.drop_tip()
    
    # Return the next tip index
    return tip_index + 1

def debug_simulate_solution_addition(protocol, tc_plate, unique_wells, pipette, tips_rack, 
                                   solution_name="solution", volume=0, tip_index=0):
    '''
    Debug version that simulates adding solution without actually dispensing.
    Uses a single tip for all wells when dispensing the same reagent.
    
    Args:
        protocol: Protocol context
        tc_plate: PCR plate labware
        unique_wells: List of unique well names
        pipette: Pipette to use
        tips_rack: Tip rack to use
        solution_name: Name of the solution (for logging)
        volume: Volume to dispense
        tip_index: Index of the next available tip to use
        
    Returns:
        Next available tip index
    '''
    protocol.comment(f"DEBUG MODE: Simulating adding {volume} µL of {solution_name} to each sample")
    
    # Configure pipette for single-tip use
    pipette.configure_nozzle_layout(
        style=SINGLE,
        start="H1"
    )
    
    # Calculate which tip to use (moving sequentially through the tip rack)
    row = tip_index % 8  # 0-7 for rows A-H
    col = tip_index // 8  # Column number
    
    if col >= 12:
        protocol.comment(f"DEBUG: Would pause for tip rack replacement for {solution_name}")
        row = 0
        col = 0
    
    tip_well = f"{chr(65 + row)}{col + 1}"  # Convert to well name like 'A1'
    protocol.comment(f"DEBUG: Using tip at position {tip_well} for {solution_name}")
    
    # Pick up the selected tip
    pipette.pick_up_tip(tips_rack.wells_by_name()[tip_well])
    
    # Process each well with the same tip
    for well in unique_wells:
        # Simulate aspirating and dispensing
        protocol.comment(f"DEBUG: Moving to position {well} to simulate dispensing")
        pipette.move_to(tc_plate.wells_by_name()[well].top())
        protocol.delay(seconds=1)  # Wait for 1 second to simulate dispensing
    
    # Drop the tip after all wells are processed
    protocol.comment(f"DEBUG: Dropping tip after dispensing to all wells")
    pipette.drop_tip()
    
    # Return the next tip index
    return tip_index + 1

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
    tiprack50 = protocol.load_labware('opentrons_flex_96_tiprack_50ul', 'D2')
    tiprack200 = protocol.load_labware('opentrons_flex_96_tiprack_200ul', 'C3')
    
    # Load tube rack for reagents instead of reservoir
    tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 'C1')
    
    tc_mod = protocol.load_module('thermocyclerModuleV2')
    tc_plate = protocol.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt', 'B2')

    # Load pipettes
    p50 = protocol.load_instrument('flex_8channel_50', 'left')
    p200 = protocol.load_instrument('flex_8channel_1000', 'right')
    
    # Define reagent locations in tube rack
    master_mix = tube_rack.wells_by_name()['A1']
    template_dna = tube_rack.wells_by_name()['A2']
    primers = tube_rack.wells_by_name()['A3']
    
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
        
        # Get unique wells
        unique_wells = get_unique_wells(protocol, tc_plate, sample_columns, sample_rows, sample_wells)
        
        # Initialize tip trackers
        tip_50_index = 0
        tip_200_index = 0
        
        # Add solutions that are the same across all samples
        
        # 1. Always add master mix
        master_pipette = p50 if master_mix_volume < 50 else p200
        master_rack = tiprack50 if master_mix_volume < 50 else tiprack200
        
        if master_mix_volume < 50:
            tip_50_index = dispense_solution(
                protocol, tc_plate, unique_wells, master_pipette,
                master_rack, master_mix, master_mix_volume, "master mix", tip_50_index
            )
        else:
            tip_200_index = dispense_solution(
                protocol, tc_plate, unique_wells, master_pipette,
                master_rack, master_mix, master_mix_volume, "master mix", tip_200_index
            )
        
        # 2. Add template DNA if it's the same for all samples
        if same_template_dna:
            template_pipette = p50 if template_dna_volume < 50 else p200
            template_rack = tiprack50 if template_dna_volume < 50 else tiprack200
            
            if template_dna_volume < 50:
                tip_50_index = dispense_solution(
                    protocol, tc_plate, unique_wells, template_pipette,
                    template_rack, template_dna, template_dna_volume, "template DNA", tip_50_index
                )
            else:
                tip_200_index = dispense_solution(
                    protocol, tc_plate, unique_wells, template_pipette,
                    template_rack, template_dna, template_dna_volume, "template DNA", tip_200_index
                )
        
        # 3. Add primers if they're the same for all samples
        if same_primers:
            primer_pipette = p50 if primer_volume < 50 else p200
            primer_rack = tiprack50 if primer_volume < 50 else tiprack200
            
            if primer_volume < 50:
                tip_50_index = dispense_solution(
                    protocol, tc_plate, unique_wells, primer_pipette,
                    primer_rack, primers, primer_volume, "primers", tip_50_index
                )
            else:
                tip_200_index = dispense_solution(
                    protocol, tc_plate, unique_wells, primer_pipette,
                    primer_rack, primers, primer_volume, "primers", tip_200_index
                )
                
        # Pause to allow manual additions if needed
        if not same_template_dna or not same_primers:
            manual_additions = []
            if not same_template_dna:
                manual_additions.append(f"template DNA ({template_dna_volume} µL)")
            if not same_primers:
                manual_additions.append(f"primers ({primer_volume} µL)")
                
            manual_text = " and ".join(manual_additions)
            protocol.pause(f"Please add {manual_text} to each sample manually, then resume.")
    else:
        # Debug mode - Parse CSV and simulate pipetting without dispensing
        protocol.comment("=== DEBUG MODE ACTIVATED ===")
        protocol.comment("This will simulate pipetting operations without dispensing liquids")
        
        # Parse CSV data for well locations (same as non-debug mode)
        csv_data = well_csv.parse_as_csv()
        sample_columns, sample_rows, sample_wells = parse_csv_locations(csv_data)
        
        # Get unique wells
        unique_wells = get_unique_wells(protocol, tc_plate, sample_columns, sample_rows, sample_wells)
        
        protocol.comment(f"DEBUG: Found {len(unique_wells)} unique wells")
        
        # Initialize tip trackers
        tip_50_index = 0
        tip_200_index = 0
        
        # 1. Simulate adding master mix
        master_pipette = p50 if master_mix_volume < 50 else p200
        master_rack = tiprack50 if master_mix_volume < 50 else tiprack200
        
        if master_mix_volume < 50:
            tip_50_index = debug_simulate_solution_addition(
                protocol, tc_plate, unique_wells, master_pipette,
                master_rack, "master mix", master_mix_volume, tip_50_index
            )
        else:
            tip_200_index = debug_simulate_solution_addition(
                protocol, tc_plate, unique_wells, master_pipette,
                master_rack, "master mix", master_mix_volume, tip_200_index
            )
        
        # 2. Simulate adding template DNA if it's the same for all samples
        if same_template_dna:
            template_pipette = p50 if template_dna_volume < 50 else p200
            template_rack = tiprack50 if template_dna_volume < 50 else tiprack200
            
            if template_dna_volume < 50:
                tip_50_index = debug_simulate_solution_addition(
                    protocol, tc_plate, unique_wells, template_pipette,
                    template_rack, "template DNA", template_dna_volume, tip_50_index
                )
            else:
                tip_200_index = debug_simulate_solution_addition(
                    protocol, tc_plate, unique_wells, template_pipette,
                    template_rack, "template DNA", template_dna_volume, tip_200_index
                )
        
        # 3. Simulate adding primers if they're the same for all samples
        if same_primers:
            primer_pipette = p50 if primer_volume < 50 else p200
            primer_rack = tiprack50 if primer_volume < 50 else tiprack200
            
            if primer_volume < 50:
                tip_50_index = debug_simulate_solution_addition(
                    protocol, tc_plate, unique_wells, primer_pipette,
                    primer_rack, "primers", primer_volume, tip_50_index
                )
            else:
                tip_200_index = debug_simulate_solution_addition(
                    protocol, tc_plate, unique_wells, primer_pipette,
                    primer_rack, "primers", primer_volume, tip_200_index
                )
        
        # Simulate pause for manual additions if needed
        if not same_template_dna or not same_primers:
            manual_additions = []
            if not same_template_dna:
                manual_additions.append(f"template DNA ({template_dna_volume} µL)")
            if not same_primers:
                manual_additions.append(f"primers ({primer_volume} µL)")
                
            manual_text = " and ".join(manual_additions)
            protocol.comment(f"DEBUG: Would pause here for manual addition of {manual_text}")
        
        # Simulate thermocycler steps
        protocol.comment("DEBUG: Simulating moving PCR plate to thermocycler")
        protocol.comment("DEBUG: Simulating thermocycler program:")
        protocol.comment(f"DEBUG: - Lid temperature: 105°C")
        
        if colony_pcr:
            protocol.comment(f"DEBUG: - Cell lysis: {lysis_temp}°C for {lysis_time_seconds} seconds")
        
        protocol.comment(f"DEBUG: - Initial denaturation: {denaturation_temp}°C for {initial_denaturation_time_seconds} seconds")
        protocol.comment(f"DEBUG: - {num_cycles} PCR cycles:")
        protocol.comment(f"DEBUG:   * Denaturation: {denaturation_temp}°C for {denaturation_time_seconds} seconds")
        protocol.comment(f"DEBUG:   * Annealing: {annealing_temp}°C for {annealing_time_seconds} seconds")
        protocol.comment(f"DEBUG:   * Extension: {extension_temp}°C for {extension_time_seconds} seconds")
        protocol.comment(f"DEBUG: - Final extension: {extension_temp}°C for {final_extension_time_seconds} seconds")
        protocol.comment(f"DEBUG: - Cooling to 4°C")
        
        protocol.comment("=== DEBUG MODE COMPLETE ===")
    
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
        # Make sure to deactivate the lid before setting the final hold temperature
        tc_mod.deactivate_lid()
        tc_mod.set_block_temperature(4)
        protocol.pause("Ready to take out your plate?")
        tc_mod.open_lid()