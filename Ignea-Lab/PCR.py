# imports
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'PCR',
    "author": "Gabriel Straface (Ignea Lab @ McGill University)",
    'description': '''OT-2 PCR with template DNA pre loaded on the PCR plate.
    Depending on the use case, primers have to be added to each sample or left in the tube rack'''
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

def add_locations():
    # Define sample locations by column, row and/or well
    # Any duplicated locations will be removed and raise a warning
    sample_columns = ['1','2'] # eg. ['1', '2']
    sample_rows = [] #eg. ['A', 'B']
    sample_wells = ['A3'] # eg. ['A1', 'B1']

    return sample_columns, sample_rows, sample_wells

# Runtime Parameters (Recommended)
def add_parameters(parameters: protocol_api.Parameters):
    parameters.add_int(
        variable_name = "sample_volume",
        display_name = "Sample Volume",
        description = "The volume of template DNA (or colony for colony PCR)",
        default = 40,
        minimum = 20,
        maximum = 100,
        unit = "µL"
    )
    parameters.add_int(
        variable_name = "master_volume",
        display_name = "Master Mix Volume",
        description = "The volume of master mix to add to each sample",
        default = 40,
        minimum = 20,
        maximum = 100,
        unit = "µL"
    )
    parameters.add_bool(
        variable_name = "primers_loaded",
        display_name = "Primers Loaded in each sample",
        description = "Turn on if you need different primers for eaach sample. In this case, you must add them by hand",
        default = False
    )
    parameters.add_int(
        variable_name = "primer_volume",
        display_name = "Primer Volume",
        description = "The volume of primers for each sample. Either added by robot or pre loaded",
        default = 40,
        minimum = 20,
        maximum = 100,
        unit = "µL"
    )
    parameters.add_int(
        variable_name = "denaturation_temp",
        display_name = "Denaturation Temperature",
        description = "",
        default = 98,
        minimum = 4,
        maximum = 99,
        unit = "Celsius"
    )
    parameters.add_int(
        variable_name = "annealing_temp",
        display_name = "Annealing Temperature",
        description = "",
        default = 63,
        minimum = 4,
        maximum = 99,
        unit = "Celsius"
    )
    parameters.add_int(
        variable_name = "extension_temp",
        display_name = "Extension Temperature",
        description = "",
        default = 72,
        minimum = 4,
        maximum = 99,
        unit = "Celsius"
    )
    parameters.add_int(
        variable_name = "init_denaturation_time",
        display_name = "Initial Denaturation Time",
        description = "",
        default = 15,
        minimum = 1,
        maximum = 999,
        unit = "Seconds"
    )
    parameters.add_int(
        variable_name = "denaturation_time",
        display_name = "Denaturation Time",
        description = "For each cycle",
        default = 30,
        minimum = 1,
        maximum = 999,
        unit = "Seconds"
    )
    parameters.add_int(
        variable_name = "annealing_time",
        display_name = "Annealing Time",
        description = "For each cycle",
        default = 20,
        minimum = 1,
        maximum = 999,
        unit = "Seconds"
    )
    parameters.add_int(
        variable_name = "extension_time",
        display_name = "Extension Time",
        description = "For each cycle",
        default = 210,
        minimum = 1,
        maximum = 999,
        unit = "Seconds"
    )
    parameters.add_int(
        variable_name = "final_extension_time",
        display_name = "Final Extension Time",
        description = "",
        default = 120,
        minimum = 1,
        maximum = 999,
        unit = "Seconds"
    )
    parameters.add_int(
        variable_name = "num_cycles",
        display_name = "Number of cycles",
        description = "",
        default = 30,
        minimum = 1,
        maximum = 150
    )
    parameters.add_bool(
        variable_name = "colony_pcr",
        display_name = "Colony PCR",
        description = "",
        default = False
    )
    parameters.add_int(
        variable_name = "lysis_temp",
        display_name = "Lysis Temperature",
        description = "For colony PCR",
        default = 98,
        minimum = 4,
        maximum = 99,
        unit = "Celsius"
    )
    parameters.add_int(
        variable_name = "lysis_time",
        display_name = "Lysis Time",
        description = "For colony PCR",
        default = 600,
        minimum = 1,
        maximum = 999,
        unit = "Seconds"
    )

def run(protocol: protocol_api.ProtocolContext):

    sample_columns, sample_rows, sample_wells = add_locations()


    # PCR parameters
    sample_volume = protocol.params.sample_volume # Volume of sample loaded in each well, uL
    master_mix_volume = protocol.params.master_volume # Volume of master mix to add to each well, uL
    primer_volume = protocol.params.primer_volume # Volume of primers for each well, uL. Depending on primers_loaded it might be pre-loaded or might be added by the robot
    denaturation_temp = protocol.params.denaturation_temp
    initial_denaturation_time_seconds = protocol.params.init_denaturation_time
    denaturation_time_seconds = protocol.params.denaturation_time
    annealing_temp = protocol.params.annealing_temp
    annealing_time_seconds = protocol.params.annealing_time
    extension_temp = protocol.params.extension_temp
    extension_time_seconds = protocol.params.extension_time
    final_extension_time_seconds = protocol.params.final_extension_time
    num_cycles = protocol.params.num_cycles
    primers_loaded = protocol.params.primers_loaded # Set to True if the appropriate primer is already in each well (aplicable if different primers are being used in each sample)
    # Otherwise, the robot will load the same primers in each well
    colony_pcr = protocol.params.colony_pcr # Set to True for Colony PCR
    # The following parameters are applicable if colony PCR is set to True
    lysis_temp = 98
    lysis_time_seconds = 600



    # Labware definitions
    tiprack = protocol.load_labware('opentrons_96_tiprack_300ul', '1')
    tiprack2 = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '3')
    tc_mod = protocol.load_module('thermocyclerModuleV2')
    tc_plate = tc_mod.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt')

    # Define wells and remove duplicates
    destination_wells = []
    destination_wells.extend([tc_plate.columns_by_name()[col] for col in sample_columns])
    destination_wells.extend([tc_plate.rows_by_name()[row] for row in sample_rows])
    destination_wells.extend([tc_plate.wells_by_name()[well] for well in sample_wells])
    # Initialize an empty dictionary to track occurrences
    occurrences = {}
    # Initialize an empty list to store the unique wells
    unique_wells = []
    for well in destination_wells:
        # Convert the well object to a string to use it as a dictionary key
        well_str = well.well_name
        if well_str not in occurrences:
            # If the well is not in the dictionary, add it to unique_wells
            unique_wells.append(well)
            # And add it to the dictionary
            occurrences[well_str] = True
        else:
            # If the well is already in the dictionary, it's a duplicate
            protocol.comment(f"Duplicate location found and removed: {well_str}")
    # Replace destination_wells with the list of unique wells
    destination_wells = unique_wells
    num_samples = len(destination_wells)

    # Pipettes
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'left', tip_racks=[tiprack])
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack2])
    pcr_volume = sample_volume + master_mix_volume + primer_volume

    # Commands
    tc_mod.open_lid()
    master_mix = tube_rack.wells_by_name()['A1'].top(-34)
    master_mix2 = tube_rack.wells_by_name()['B1'].top(-34)
    master_mix3 = tube_rack.wells_by_name()['C1'].top(-34)
    master_mix4 = tube_rack.wells_by_name()['D1'].top(-34)
    primers = tube_rack.wells_by_name()['A2'].top(-34)
    primers2 = tube_rack.wells_by_name()['B2'].top(-34)
    mm1 = 1470
    mm2 = 1470
    mm3 = 1470
    p1 = 1470
    
    # Transfer appropriate reagents to pcr plate
    if not primers_loaded:
        if primer_volume < 20:
            primer_pipette = p20
        else:
            primer_pipette = p300
        primer_pipette.pick_up_tip()
        for well in destination_wells:
            if p1 >= primer_volume:
                primer_pipette.aspirate(primer_volume,primers)
                primer_pipette.dispense(primer_volume,well.top())
                p1 -= primer_volume
            else:
                primer_pipette.aspirate(primer_volume,primers2)
                primer_pipette.dispense(primer_volume,well.top())
        primer_pipette.drop_tip()

    p300.pick_up_tip()
    for well in destination_wells:
        if mm1 >= master_mix_volume:
            p300.mix(1,10,master_mix)
            p300.aspirate(master_mix_volume, master_mix)
            p300.dispense(master_mix_volume, well.top())
            mm1 -= master_mix_volume
        elif mm2 >= master_mix_volume:
            p300.mix(1,10,master_mix2)
            p300.aspirate(master_mix_volume, master_mix2)
            p300.dispense(master_mix_volume, well.top())
            mm2 -= master_mix_volume
        elif mm3 >= master_mix_volume:
            p300.mix(1,10,master_mix3)
            p300.aspirate(master_mix_volume, master_mix3)
            p300.dispense(master_mix_volume, well.top())
            mm3 -= master_mix_volume   
        else:
            p300.mix(1,10,master_mix4)
            p300.aspirate(master_mix_volume, master_mix4)
            p300.dispense(master_mix_volume, well.top())                     
    p300.drop_tip()

    # Thermocycling program definition
    pcr_program = [
        {'temperature': denaturation_temp, 'hold_time_seconds': denaturation_time_seconds},   # Denaturation
        {'temperature': annealing_temp, 'hold_time_seconds': annealing_time_seconds},   # Annealing
        {'temperature': extension_temp, 'hold_time_seconds': extension_time_seconds},   # Extension
    ]

    # Run thermocycler
    protocol.comment("Running thermocycler...")
    tc_mod.close_lid()
    tc_mod.set_lid_temperature(105)
    if colony_pcr:
        tc_mod.set_block_temperature(temperature=lysis_temp,hold_time_seconds=lysis_time_seconds,block_max_volume=pcr_volume)
    tc_mod.set_block_temperature(temperature=denaturation_temp,hold_time_seconds= initial_denaturation_time_seconds, block_max_volume=pcr_volume) # Initial denaturation
    tc_mod.execute_profile(steps=pcr_program, repetitions=num_cycles, block_max_volume=pcr_volume)
    tc_mod.set_block_temperature(temperature=extension_temp, hold_time_seconds= final_extension_time_seconds, block_max_volume=pcr_volume) # Final extension
    tc_mod.set_block_temperature(4)
    tc_mod.deactivate_lid()
    tc_mod.open_lid()
    


