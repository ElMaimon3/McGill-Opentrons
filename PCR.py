# imports
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'PCR',
}
requirements = {"robotType": "OT-2", "apiLevel": "2.15"}
def run(protocol: protocol_api.ProtocolContext):
	
    # pcr parameters
    template_dna_in_wells = False
    centrifuge = False
    pcr_volume = 80 # volume in each well, uL
    denaturation_temp = 95
    annealing_temp = 60
    extension_temp = 72

    # labware
    tc_mod = protocol.load_module('thermocycler module')
    tc_plate = tc_mod.load_labware('nest_96_wellplate_100ul_pcr_full_skirt')
    reservoir = protocol.load_labware('usascientific_12_reservoir_22ml', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_300ul', '3')

    # pipettes
    left_pipette = protocol.load_instrument(
        'p300_multi', 'left', tip_racks=[tiprack])

    # commands
    master_mix = reservoir.wells_by_name()['A1']
    destination_wells = tc_plate.rows_by_name()['A']
    
    left_pipette.pick_up_tip()
    for well in destination_wells:
        left_pipette.aspirate(20, master_mix)
        left_pipette.dispense(20, well)
    left_pipette.drop_tip()

    '''This section is applicable if the template DNA is the same for all wells'''
    # dna_template = reservoir.wells_by_name()['A2']

    left_pipette.pick_up_tip()
    for well in destination_wells:
        left_pipette.aspirate(5, dna_template)
        left_pipette.dispense(5, well)
        left_pipette.mix(3, 10, well)  # Mix the contents 3 times with a volume of 10uL
    left_pipette.drop_tip()

	
    ''' This section is only applicable when centrifuging, it should be included if
    the door lock is disabled, otherwise the PCR has to be divided in two protocols'''
    # protocol.pause('Centrifuge and interact to continue')

    # thermocycling parameters
    
    pcr_program = [
        {'temperature': denaturation_temp, 'hold_time_seconds': 10},   # Denaturation
        {'temperature': annealing_temp, 'hold_time_seconds': 30},   # Annealing
        {'temperature': extension_temp, 'hold_time_seconds': 30},   # Extension
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


