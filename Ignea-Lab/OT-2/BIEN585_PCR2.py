# imports
from opentrons import protocol_api
import csv
import io

# metadata
metadata = {
    'protocolName': 'BIEN 585 PCR 2',
    "author": "Gabriel Straface (Ignea Lab @ McGill University)",
    'description': ''''''
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

def add_locations(bytes):
    # Define sample locations by column, row and/or well in a csv file
    sample_columns = [] # eg. ['1', '2']
    sample_rows = [] #eg. ['A', 'B']
    sample_wells = [] # eg. ['A1', 'B1']
    # Decode the bytes object into a string
    csv_string = bytes.decode('utf-8')

    # Use io.StringIO to create a file-like object for csv.reader
    csv_file = io.StringIO(csv_string)
    reader = csv.reader(csv_file)
    header = next(reader)
    for row in reader:
        for i in range(3):
           if len(row[i]) != 0:
                if i == 0:
                    sample_columns.append(row[i])
                elif i == 1:
                    sample_rows.append(row[i])
                elif i == 2:
                    sample_wells.append(row[i])
    return sample_columns, sample_rows, sample_wells

# Runtime Parameters (Recommended)
def add_parameters(parameters: protocol_api.Parameters):
    parameters.add_int(
        variable_name = "sample_volume",
        display_name = "Sample Volume",
        description = "The volume of template DNA (or colony for colony PCR)",
        default = 40,
        minimum = 20,
        maximum = 50,
        unit = "µL"
    )
    parameters.add_int(
        variable_name = "master_volume",
        display_name = "Master Mix Volume",
        description = "The volume of master mix to add to each sample",
        default = 20,
        minimum = 10,
        maximum = 25,
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
        default = 20,
        minimum = 10,
        maximum = 25,
        unit = "µL"
    )

def run(protocol: protocol_api.ProtocolContext):
    bundled_data = protocol.bundled_data['PCR_locations.csv']
    sample_columns, sample_rows, sample_wells = add_locations(bundled_data)


    # PCR parameters
    sample_volume = protocol.params.sample_volume # Volume of sample loaded in each well, uL
    master_mix_volume = protocol.params.master_volume # Volume of master mix to add to each well, uL
    primer_volume = protocol.params.primer_volume # Volume of primers for each well, uL. Depending on primers_loaded it might be pre-loaded or might be added by the robot
    denaturation_temp = 95
    initial_denaturation_time_seconds = 180
    denaturation_time_seconds = 30
    annealing_temp = 55
    annealing_time_seconds = 30
    extension_temp = 72
    extension_time_seconds = 150
    final_extension_time_seconds = 120
    num_cycles = 35
    primers_loaded = protocol.params.primers_loaded # Set to True if the appropriate primer is already in each well (aplicable if different primers are being used in each sample)
    # Otherwise, the robot will load the same primers in each well
    colony_pcr = False # Set to True for Colony PCR
    # The following parameters are applicable if colony PCR is set to True
    lysis_temp = 1
    lysis_time_seconds = 1



    # Labware definitions
    tiprack = protocol.load_labware('opentrons_96_tiprack_300ul', '1')
    tiprack2 = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '3')
    tc_mod = protocol.load_module('thermocyclerModuleV2')
    tc_plate = tc_mod.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt')

    # Define wells and remove duplicates
    destination_wells = []
    for col in sample_columns:
       destination_wells.extend(tc_plate.columns_by_name()[col])
    for row in sample_rows:
       destination_wells.extend(tc_plate.rows_by_name()[row])
    destination_wells.extend([tc_plate.wells_by_name()[well] for well in sample_wells])

    # Initialize an empty dictionary to track occurrences
    occurrences = {}
    # Initialize an empty list to store the unique wells
    unique_wells = []
    for well in destination_wells:
       # Convert the well object to a string to use it as a dictionary key
       well_str = str(well)
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
        'p20_single_gen2', 'right', tip_racks=[tiprack2])
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

    if master_mix_volume <20:
        master_pipette = p20
    else:
        master_pipette = p300

    master_pipette.pick_up_tip()
    for well in destination_wells:
        if mm1 >= master_mix_volume:
            master_pipette.mix(1,20,master_mix)
            master_pipette.aspirate(master_mix_volume, master_mix)
            master_pipette.dispense(master_mix_volume, well.top())
            mm1 -= master_mix_volume
        elif mm2 >= master_mix_volume:
            master_pipette.mix(1,20,master_mix2)
            master_pipette.aspirate(master_mix_volume, master_mix2)
            master_pipette.dispense(master_mix_volume, well.top())
            mm2 -= master_mix_volume
        elif mm3 >= master_mix_volume:
            master_pipette.mix(1,20,master_mix3)
            master_pipette.aspirate(master_mix_volume, master_mix3)
            master_pipette.dispense(master_mix_volume, well.top())
            mm3 -= master_mix_volume   
        else:
            master_pipette.mix(1,20,master_mix4)
            master_pipette.aspirate(master_mix_volume, master_mix4)
            master_pipette.dispense(master_mix_volume, well.top())                     
    master_pipette.drop_tip()

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
    tc_mod.set_block_temperature(temperature=98,hold_time_seconds= initial_denaturation_time_seconds, block_max_volume=pcr_volume) # Initial denaturation
    tc_mod.execute_profile(steps=pcr_program, repetitions=num_cycles, block_max_volume=pcr_volume)
    tc_mod.set_block_temperature(temperature=extension_temp, hold_time_seconds= final_extension_time_seconds, block_max_volume=pcr_volume) # Final extension
    tc_mod.set_block_temperature(4)
    tc_mod.deactivate_lid()
    tc_mod.open_lid()
    


