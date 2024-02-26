# imports
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'Restriction Enzyme based digestion',
}
requirements = {"robotType": "OT-2", "apiLevel": "2.15"}
def run(protocol: protocol_api.ProtocolContext):
     # Load pipettes
    p300 = protocol.load_instrument('p300_single_gen2', 'left', tip_racks=[protocol.load_labware('opentrons_96_tiprack_300ul', '5')])
    
    temp_mod = protocol.load_module('temperature module gen2','5')
    temp_tubes = temp_mod.load_labware('opentrons_24_aluminumblock_nest_1.5ml_snapcap')
    tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '3')
    