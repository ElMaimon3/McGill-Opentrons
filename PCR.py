# imports
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'PCR',
}
requirements = {"robotType": "OT-2", "apiLevel": "2.15"}
def run(protocol: protocol_api.ProtocolContext):
	
    # pcr parameters
    template_dna_in_wells = True
    pcr_volume = 80 # volume in each well, uL
    denaturation_temp = 95
    annealing_temp = 63
    extension_temp = 72

    # labware
    tc_mod = protocol.load_module('thermocycler module')
    tc_plate = tc_mod.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt')
    tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '3')
    tiprack = protocol.load_labware('opentrons_96_tiprack_300ul', '1')

    # pipettes
    left_pipette = protocol.load_instrument(
        'p300_single', 'left', tip_racks=[tiprack])

    # commands
    tc_mod.open_lid()
    master_mix = tube_rack.wells_by_name()['A1']
    destination_wells = [tc_plate.wells_by_name()['A1'],tc_plate.wells_by_name()['A2'],tc_plate.wells_by_name()['A3'],tc_plate.wells_by_name()['A4']]
    
    left_pipette.pick_up_tip()
    for well in destination_wells:
        left_pipette.mix(1,10,master_mix)
        left_pipette.aspirate(20, master_mix)
        left_pipette.dispense(20, well)
    left_pipette.drop_tip()

    if not template_dna_in_wells:
        dna_template = tube_rack.wells_by_name()['A2']
        left_pipette.pick_up_tip()
        for well in destination_wells:
            left_pipette.aspirate(5, dna_template)
            left_pipette.dispense(5, well)
            left_pipette.mix(3, 10, well)  # Mix the contents 3 times with a volume of 10uL
        left_pipette.drop_tip()

    # thermocycling parameters
    
    pcr_program = [
        {'temperature': denaturation_temp, 'hold_time_seconds': 10},   # Denaturation
        {'temperature': annealing_temp, 'hold_time_seconds': 30},   # Annealing
        {'temperature': extension_temp, 'hold_time_seconds': 210},   # Extension
    ]

    # run thermocycler
    protocol.comment("Running thermocycler...")
    tc_mod.close_lid()
    tc_mod.set_lid_temperature(105)
    tc_mod.set_block_temperature(temperature=denaturation_temp,hold_time_seconds= 30, block_max_volume=pcr_volume) # Initial denaturation
    tc_mod.execute_profile(steps=pcr_program, repetitions=35, block_max_volume=pcr_volume)
    tc_mod.set_block_temperature(temperature=extension_temp, hold_time_seconds= 60, block_max_volume=pcr_volume) # Final extension
    tc_mod.open_lid()
    tc_mod.set_block_temperature(4)


