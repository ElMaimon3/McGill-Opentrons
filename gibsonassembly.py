# imports
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'Gibson Assembly',
    'description': 'Opentrons protocol for Gibson Assembly (OT-2)',
}
requirements = {"robotType": "OT-2", "apiLevel": "2.15"}
def run(protocol: protocol_api.ProtocolContext):
     # labware
    temp_mod = protocol.load_module('temperature module gen2','5')
    temp_tubes = temp_mod.load_labware('opentrons_24_aluminumblock_nest_1.5ml_snapcap')
    tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '3')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '1')
     # pipettes
    left_pipette = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack])
    
    #loaction definitions
    master_mix = tube_rack.wells_by_name()['A1'].top(-34)
    h2o = tube_rack.wells_by_name()['A2'].top(-34)
    linearized_vector  = tube_rack.wells_by_name()['B1'].top(-34)
    fragment1 = tube_rack.wells_by_name()['B2'].top(-34)
    fragment2 = tube_rack.wells_by_name()['B3'].top(-34)
    assembly_tube = temp_tubes.wells_by_name()['A1']

    #commands
    temp_mod.set_temperature(4)
    left_pipette.pick_up_tip()
    left_pipette.aspirate(5,h2o)
    left_pipette.dispense(5,assembly_tube)
    left_pipette.drop_tip()
    left_pipette.pick_up_tip()
    left_pipette.aspirate(1,linearized_vector)
    left_pipette.dispense(1,assembly_tube)
    left_pipette.drop_tip()
    left_pipette.pick_up_tip()
    left_pipette.aspirate(2,fragment1)
    left_pipette.dispense(2,assembly_tube)
    left_pipette.drop_tip()
    left_pipette.pick_up_tip()
    left_pipette.aspirate(2,fragment2)
    left_pipette.dispense(2,assembly_tube)
    left_pipette.drop_tip()
    left_pipette.pick_up_tip()
    left_pipette.aspirate(10,master_mix)
    left_pipette.dispense(10,assembly_tube)
    left_pipette.drop_tip()
    temp_mod.set_temperature(50)
    protocol.delay(minutes=15)
    temp_mod.deactivate()
