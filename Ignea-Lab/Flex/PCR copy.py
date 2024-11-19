# imports
from opentrons import protocol_api
import csv
import io

# metadata
metadata = {
    'protocolName': 'Customizable PCR',
    "author": "Gabriel Straface (Ignea Lab @ McGill University)",
    'description': '''Fully customizable PCR for the Openteons Flex
    with template DNA pre loaded on the PCR plate. Depending on the use 
    case, primers have to be added to each sample or left in the reservoir'''
}
requirements = {"robotType": "Flex", "apiLevel": "2.20"}


# Runtime Parameters
def add_parameters(parameters: protocol_api.Parameters):
    parameters.add_string(
        variable_name = "location_mode",
        display_name = "96-well Plate Location Definiton",
        choices=[
        {"display_name": "Simple", "value": "simple"},
        {"display_name": "Custom", "value": "custom"},
        ],
        default="simple",
        description = "Simple: Columns, starting from the left \n Custom: Requires PCR_locations.csv. May save tips"
    )
    parameters.add_int(
        variable_name = "columns",
        display_name = "Columns (Simple Location Definition Only)",
        default = 2,
        minimum = 1,
        maximum = 12
    )
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

    # PCR parameters
    mode = protocol.params.location_mode
    cols = protocol.params.columns
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
    lysis_temp = protocol.params.lysis_temp
    lysis_time_seconds = protocol.params.lysis_time

    # Labware definitions
    # Thermocycler simulataneously occupies A1 and B1
    tiprack = protocol.load_labware('opentrons_flex_96_tiprack_50ul', 'D1')
    tiprack2 = protocol.load_labware('opentrons_flex_96_tiprack_200ul', 'D2')
    res = protocol.load_labware('nest_12_reservoir_15ml','C1')
    tc_mod = protocol.load_module('thermocyclerModuleV2')
    tc_plate = tc_mod.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt')

    # Pipettes
    p50 = protocol.load_instrument(
        'flex_8channel_50', 'left', tip_racks=[tiprack])
    p200 = protocol.load_instrument(
        'flex_8channel_1000', 'right', tip_racks=[tiprack2])
    pcr_volume = sample_volume + master_mix_volume + primer_volume
    master_mix = res.wells_by_name()['A1'].top(-34)
    primers = res.wells_by_name()['A2'].top(-34)
    p1 = 7.5
    mm1 = 7.5

    # Thermocycling program definition
    pcr_program = [
        {'temperature': denaturation_temp, 'hold_time_seconds': denaturation_time_seconds},   # Denaturation
        {'temperature': annealing_temp, 'hold_time_seconds': annealing_time_seconds},   # Annealing
        {'temperature': extension_temp, 'hold_time_seconds': extension_time_seconds},   # Extension
    ]
    # Commands
    tc_mod.open_lid()

    if mode == 'simple':
        # Transfer appropriate reagents to pcr plate
        if not primers_loaded:
            if primer_volume < 50:
                primer_pipette = p50
            else:
                primer_pipette = p200
            primer_pipette.pick_up_tip()
            for c in tc_plate.columns[:cols]:
                primer_pipette.aspirate(primer_volume,primers.top(-vol_to_height(p1)))
                primer_pipette.dispense(primer_volume,c.top())
                p1 -= 8 * 0.001 * primer_volume

            primer_pipette.drop_tip()

        if master_mix_volume < 50:
            master_pipette = p50
        else:
            master_pipette = p200

        master_pipette.pick_up_tip()
        for c in tc_plate.columns[:cols]:
            master_pipette.mix(1,master_mix_volume,master_mix)
            master_pipette.aspirate(master_mix_volume, master_mix.top(-vol_to_height(mm1)))
            master_pipette.dispense(master_mix_volume, well.top())
            mm1 -= 8 * 0.001 * master_mix_volume                     
        master_pipette.drop_tip()
    else:
        bundled_data = protocol.bundled_data['PCR_locations.csv']
        sample_columns, sample_rows, sample_wells = add_locations(bundled_data)
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


    # Run thermocycler
    protocol.comment("Running thermocycler...")
    tc_mod.close_lid()
    tc_mod.set_lid_temperature(105)
    if colony_pcr:
        tc_mod.set_block_temperature(temperature=lysis_temp,hold_time_seconds=lysis_time_seconds,block_max_volume=pcr_volume)
    tc_mod.set_block_temperature(temperature=denaturation_temp,hold_time_seconds= initial_denaturation_time_seconds, block_max_volume=pcr_volume) # Initial denaturation
    tc_mod.execute_profile(steps=pcr_program, repetitions=num_cycles, block_max_volume=pcr_volume)
    tc_mod.set_block_temperature(temperature=extension_temp, hold_time_seconds= final_extension_time_seconds, block_max_volume=pcr_volume) # Final extension
    tc_mod.deactivate_lid()
    tc_mod.open_lid()
    tc_mod.set_block_temperature(4)
    

def vol_to_height(vol):
    full_depth = 40
    if vol > 0:
        return round(-2.6*vol + full_depth)
    else:
        return full_depth

def add_locations(bytes):
    # Define sample locations by column, row and/or well in a csv file
    sample_columns = [] # eg. ['1', '2']
    sample_rows = [] # eg. ['A', 'B']
    sample_wells = [] # eg. ['A1', 'B1']
    # Decode the bytes object into a string
    csv_string = bytes.decode('utf-8')

    # Use io.StringIO to create a file-like object for csv.reader
    csv_file = io.StringIO(csv_string)
    reader = csv.reader(csv_file)
    header = next(reader)
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
