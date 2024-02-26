# imports
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'Restriction Enzyme based digestion',
    'description': 'Must load 500ng of each plasmid into the themocycler plates'
}
requirements = {"robotType": "OT-2", "apiLevel": "2.15"}
def run(protocol: protocol_api.ProtocolContext):
     # Load pipettes
    RE1concentration = 100 # U/uL
    RE2concentration = 20
    p300 = protocol.load_instrument('p300_single_gen2', 'left', tip_racks=[protocol.load_labware('opentrons_96_tiprack_300ul', '5')])
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[protocol.load_labware('opentrons_96_tiprack_20ul', '8')])
    tc_mod = protocol.load_module('thermocyclerModuleV2')
    tc_plate = tc_mod.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt')

    temp_mod = protocol.load_module('temperature module gen2','5')
    temp_tubes = temp_mod.load_labware('opentrons_24_aluminumblock_nest_1.5ml_snapcap')
    tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '3')

    enzyme1 = temp_tubes.wells_by_name()['A1']
    enzyme2 = temp_tubes.wells_by_name()['A2']
    temp_mod.set_block_temperature(4)
    tc_mod.set_block_temperature(37)

    vector = tc_plate.wells_by_name()['A1']
    insert = tc_plate.wells_by_name()['A2']
    cutsmart = tube_rack.wells_by_name()['A3']
    h2o = tube_rack.wells_by_name()['A4']

    p20.transfer(9.5,h2o.top(-30),vector)
    p20.transfer(9.5,h2o.top(-30),insert)
    p20.transfer(2.5,cutsmart.top(-30),vector)
    p20.transfer(2.5,cutsmart.top(-30),insert)
    p20.transfer(50/RE1concentration,enzyme1.top(-30),vector)
    p20.transfer(50/RE1concentration,enzyme1.top(-30),insert)
    p20.transfer(50/RE2concentration,enzyme2.top(-30),vector)
    p20.transfer(50/RE2concentration,enzyme2.top(-30),insert)
    protocol.delay(minutes = 30)
    temp_mod.deactivate()
    tc_mod.deactivate()
    protocol.comment('Done')