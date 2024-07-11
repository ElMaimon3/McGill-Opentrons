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
def run(protocol: protocol_api.ProtocolContext):

    # Define sample locations by column, row and/or well
    # Any duplicated locations will be removed and raise a warning
    sample_columns = ['1','2'] # eg. ['1', '2']
    sample_rows = [] #eg. ['A', 'B']
    sample_wells = ['A3'] # eg. ['A1', 'B1']
    # PCR parameters
    sample_volume = 40 # Volume of sample loaded in each well, uL
    master_mix_volume = 40 # Volume of master mix to add to each well, uL
    primer_volume = 10 # Volume of primers for each well, uL. Depending on primers_loaded it might be pre-loaded or might be added by the robot
    denaturation_temp = 98
    initial_denaturation_time_seconds = 15
    denaturation_time_seconds = 10
    annealing_temp = 63
    annealing_time_seconds = 20
    extension_temp = 72
    extension_time_seconds = 210
    final_extension_time_seconds = 120
    num_cycles = 30
    primers_loaded = False # Set to True if the appropriate primer is already in each well (aplicable if different primers are being used in each sample)
    # Otherwise, the robot will load the same primers in each well
    colony_pcr = False # Set to True for Colony PCR
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
    


