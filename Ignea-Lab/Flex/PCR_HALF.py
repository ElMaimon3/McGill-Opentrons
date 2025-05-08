# imports
from opentrons import protocol_api
from opentrons.protocol_api import SINGLE, PARTIAL_COLUMN, ALL
from typing import List, Dict, Tuple, Set, Optional, Any


# metadata
metadata = {
    'protocolName': 'Customizable PCR with manual pipetting',
    "author": "Gabriel Straface (Ignea Lab @ McGill University)",
    'description': '''Fully customizable PCR for the Opentrons Flex.
    Place your loaded PCR well plate on slot B2'''
}
requirements = {"robotType": "Flex", "apiLevel": "2.21"}


# Runtime Parameters
def add_parameters(parameters: protocol_api.Parameters):
    
    
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
    

    # Debug mode
    parameters.add_bool(
        variable_name="debug",
        display_name="Debugging Mode",
        description="For testing purposes",
        default=False
    )

# Utility functions

def run(protocol: protocol_api.ProtocolContext):
    # Get PCR parameters from runtime inputs
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
    debug = protocol.params.debug

    # Calculate volumes
    total_volume = master_mix_volume
    if same_template_dna:
        total_volume += template_dna_volume
    if same_primers:
        total_volume += primer_volume

    # Load labware
    chute = protocol.load_waste_chute()
    tc_mod = protocol.load_module('thermocyclerModuleV2')
    tc_plate = protocol.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt', 'B2')

    # Load pipettes
    p50 = protocol.load_instrument('flex_8channel_50', 'left')
    p200 = protocol.load_instrument('flex_8channel_1000', 'right')
    

    # Define thermocycling program
    pcr_program = [
        {'temperature': denaturation_temp, 'hold_time_seconds': denaturation_time_seconds},
        {'temperature': annealing_temp, 'hold_time_seconds': annealing_time_seconds},
        {'temperature': extension_temp, 'hold_time_seconds': extension_time_seconds},
    ]

    # Open the thermocycler lid
    tc_mod.open_lid()

    # Print setup information for the user
    protocol.comment("=== PCR SETUP ===")
    
    protocol.comment("===========================")


    
    # Move PCR plate to thermocycler and run program
    if not debug:
        protocol.move_labware(
            labware=tc_plate, new_location=tc_mod, use_gripper=True
        )
        
        # Run thermocycler
        protocol.comment("Running thermocycler...")
        tc_mod.close_lid()
        tc_mod.set_lid_temperature(105)
        
        
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

        tc_mod.set_block_temperature(4)
        protocol.pause("Ready to take out your plate?")
        tc_mod.deactivate_lid()
        tc_mod.open_lid()