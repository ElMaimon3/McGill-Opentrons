# imports
from opentrons import protocol_api
from opentrons.protocol_api import SINGLE, PARTIAL_COLUMN, ALL
import csv


# metadata
metadata = {
    'protocolName': 'Customizable PCR (CSV)',
    "author": "Gabriel Straface (Ignea Lab @ McGill University)",
    'description': '''Fully customizable PCR for the Openteons Flex
    with template DNA pre loaded on the PCR plate. Depending on the use 
    case, primers have to be manually added to each sample or left in the reservoir'''
}
requirements = {"robotType": "Flex", "apiLevel": "2.21"}


# Runtime Parameters
def add_parameters(parameters: protocol_api.Parameters):
    parameters.add_csv_file(
        variable_name="well_csv",
        display_name="PCR loactions csv",
        description=(
            "Table with three columns:"
            " rows (e.g. 1), columns (e.g. B)"
            " and wells (e.g. B1)"
        )
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
    parameters.add_bool(
        variable_name = "debug",
        display_name = "Debugging Mode",
        description = "",
        default = False
    )

def run(protocol: protocol_api.ProtocolContext):

    # PCR parameters
    well_csv = protocol.params.well_csv
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
    debug = protocol.params.debug

    # Labware definitions
    # Thermocycler simulataneously occupies A1 and B1
    chute = protocol.load_waste_chute()
    tiprack50 = protocol.load_labware('opentrons_flex_96_tiprack_50ul', 'D1')
    tips50 = list(tiprack50.wells_by_name().keys())
    tiprack200 = protocol.load_labware('opentrons_flex_96_tiprack_200ul', 'D2')
    tips200 = list(tiprack200.wells_by_name().keys())
    res = protocol.load_labware('nest_12_reservoir_15ml','C1')
    tc_mod = protocol.load_module('thermocyclerModuleV2')
    tc_plate = tc_mod.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt')

    # Pipettes
    p50 = protocol.load_instrument(
        'flex_8channel_50', 'left')
    p200 = protocol.load_instrument(
        'flex_8channel_1000', 'right')
    pcr_volume = sample_volume + master_mix_volume + primer_volume
    master_mix = res.wells_by_name()['A1']
    primers = res.wells_by_name()['A2']
    p1 = 4
    mm1 = 4

    # Thermocycling program definition
    pcr_program = [
        {'temperature': denaturation_temp, 'hold_time_seconds': denaturation_time_seconds},   # Denaturation
        {'temperature': annealing_temp, 'hold_time_seconds': annealing_time_seconds},   # Annealing
        {'temperature': extension_temp, 'hold_time_seconds': extension_time_seconds},   # Extension
    ]
    # Commands
    tc_mod.open_lid()

    if not debug:
        well_data = well_csv.parse_as_csv()
        sample_columns, sample_rows, sample_wells = add_locations(well_data)

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
               unique_wells.append(well_str)
               # And add it to the dictionary
               occurrences[well_str] = True
           else:
                # If the well is already in the dictionary, it's a duplicate
                protocol.comment(f"Duplicate location found and removed: {well_str}")
        # Replace destination_wells with the list of unique wells
        destination_wells = unique_wells

        # Group wells and sort them by size
        grouped_wells = group_wells(unique_wells)

        # Go through groups and adjust the pipette settings
        last_size = 0
        tip_attached = False
        if not primers_loaded:
            for group in grouped_wells:
                keep_tips = False
                group_size = len(group)
                loc = tc_plate.wells_by_name()[group[-1]]
                if group_size == last_size:
                    keep_tips = True
                elif group_size == 1:
                    p50.configure_nozzle_layout(
                        style=SINGLE,
                        start="H1"
                    )
                    p200.configure_nozzle_layout(
                        style=SINGLE,
                        start="H1"
                    )
                elif group_size == 8:
                    p50.configure_nozzle_layout(
                        style=ALL
                    )
                    p200.configure_nozzle_layout(
                        style=ALL
                    )
                else:
                    last = ["G1", "F1", "E1", "D1", "C1", "B1"][group_size-2]
                    p50.configure_nozzle_layout(
                        style=PARTIAL_COLUMN,
                        start="H1",
                        end=last
                    )
                    p200.configure_nozzle_layout(
                        style=PARTIAL_COLUMN,
                        start="H1",
                        end=last
                    )
                # Select primer pipette
                if primer_volume < 50:
                    primer_pipette = p50
                    rack = tiprack50
                    tips = tips50
                else:
                    primer_pipette = p200
                    rack = tiprack200
                    tips = tips200

                # Pick up a different number of tips if needed
                if not keep_tips:
                    if tip_attached:
                        primer_pipette.drop_tip()
                    tip_loc , tips = smart_pick_up(group_size, tips)
                    primer_pipette.pick_up_tip(rack.wells_by_name()[tip_loc])
                    tip_attached = True

                # Add primers to PCR plate
                primer_pipette.aspirate(primer_volume,primers.top(-vol_to_height(p1)))
                primer_pipette.dispense(primer_volume,loc.top())
                p1 -= group_size * 0.001 * primer_volume

                primer_pipette.drop_tip()
                last_size = group_size
            
            # Update available tip data
            if primer_volume < 50:
                tips50 = tips
            else:
                tips200 = tips

        # PASTE ALL GROUP CODE HERE AND MODIFY MASTER MIX ADDITION ACCORDINGLY
            if master_mix_volume < 50:
                master_pipette = p50
            else:
                master_pipette = p200

            master_pipette.pick_up_tip()
            for c in tc_plate.columns()[:cols]:
                c = c[0]
                master_pipette.mix(1,master_mix_volume,master_mix)
                master_pipette.aspirate(master_mix_volume, master_mix.top(-vol_to_height(mm1)))
                master_pipette.dispense(master_mix_volume, c.top())
                mm1 -= 8 * 0.001 * master_mix_volume                     
            master_pipette.drop_tip()
    else:
        pass
        

    if not debug:
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
    ''''''
    full_depth = 40
    if vol > 0:
        return round(-2.6*vol + full_depth)
    else:
        return full_depth

def add_locations(list):
    # Define sample locations by column, row and/or well in a csv file
    sample_columns = [] # eg. ['1', '2']
    sample_rows = [] # eg. ['A', 'B']
    sample_wells = [] # eg. ['A1', 'B1']
    for row in list[1:]:
        for i in range(3):
           if len(row[i]) != 0:
                if i == 0:
                    sample_columns.append(row[i])
                elif i == 1:
                    sample_rows.append(row[i])
                elif i == 2:
                    sample_wells.append(row[i])
    return sample_columns, sample_rows, sample_wells

def group_wells(unique_wells):
    # Sort wells in ascending order
    unique_wells.sort(key=lambda x: (ord(x[0]), int(x[1:])))

    grouped_wells = []
    
    for well in unique_wells:
        if not grouped_wells:
            grouped_wells.append([well])
        else:
            added = False
            for group in grouped_wells:
                last_well = group[-1]
                # Check if the current well is vertically adjacent to the last well in the group
                if ord(well[0]) - ord(last_well[0]) == 1 and int(well[1:]) == int(last_well[1:]):
                    group.append(well)
                    added = True
                    break
            if not added:
                grouped_wells.append([well])
    
    grouped_wells.sort(key=lambda group: len(group), reverse=True)
    return grouped_wells

def smart_pick_up(size, tips):
    loc = "A1"

    return loc, tips
