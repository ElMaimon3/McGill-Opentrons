# imports
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'PCR',
    'description': '''OT-2 PCR with template DNA pre loaded on the PCR plate.
    Depending on the use case, primers have to be added to each sample or left in the tube rack'''
}
requirements = {"robotType": "OT-2", "apiLevel": "2.15"}
def run(protocol: protocol_api.ProtocolContext):
	
    # pcr parameters
    pcr_volume = 80 # volume in each well, uL
    denaturation_temp = 98
    initial_denaturation_time_seconds = 15
    denaturation_time_seconds = 10
    annealing_temp = 63
    annealing_time_seconds = 20
    extension_temp = 72
    extension_time_seconds = 210
    final_extension_time_seconds = 120
    num_cycles = 30
    primers_loaded = True # Set to true if the appropriate primer is already in each well (aplicable if different primers are being used in each sample)

    # labware
    tc_mod = protocol.load_module('thermocyclerModuleV2')
    tc_plate = tc_mod.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt')
    tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '3')
    tiprack = protocol.load_labware('opentrons_96_tiprack_300ul', '1')

    # pipettes
    left_pipette = protocol.load_instrument(
        'p300_single_gen2', 'left', tip_racks=[tiprack])

    # commands
    tc_mod.open_lid()
    master_mix = tube_rack.wells_by_name()['A1'].top(-34)
    primers = tube_rack.wells_by_name()['A2'].top(-34)
    destination_wells = [tc_plate.wells_by_name()['A1'],tc_plate.wells_by_name()['B1'],tc_plate.wells_by_name()['C1'],tc_plate.wells_by_name()['D1']]
    
    if not primers_loaded:
        left_pipette.pick_up_tip()
        for well in destination_wells:
            left_pipette.aspirate(10,primers)
            left_pipette.dispense(10,well)
        left_pipette.drop_tip()


    left_pipette.pick_up_tip()
    for well in destination_wells:
        left_pipette.mix(1,10,master_mix)
        left_pipette.aspirate(44, master_mix)
        left_pipette.dispense(44, well)
    left_pipette.drop_tip()


    # thermocycling program definition
    pcr_program = [
        {'temperature': denaturation_temp, 'hold_time_seconds': denaturation_time_seconds},   # Denaturation
        {'temperature': annealing_temp, 'hold_time_seconds': annealing_time_seconds},   # Annealing
        {'temperature': extension_temp, 'hold_time_seconds': extension_time_seconds},   # Extension
    ]

    # run thermocycler
    protocol.comment("Running thermocycler...")
    tc_mod.close_lid()
    tc_mod.set_lid_temperature(105)
    tc_mod.set_block_temperature(temperature=denaturation_temp,hold_time_seconds= initial_denaturation_time_seconds, block_max_volume=pcr_volume) # Initial denaturation
    tc_mod.execute_profile(steps=pcr_program, repetitions=num_cycles, block_max_volume=pcr_volume)
    tc_mod.set_block_temperature(temperature=extension_temp, hold_time_seconds= final_extension_time_seconds, block_max_volume=pcr_volume) # Final extension
    tc_mod.set_block_temperature(4)
    tc_mod.deactivate_lid()
    tc_mod.open_lid()
    


