# imports
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'Plasmid ligation (WIP)',
    "author": "Gabriel Straface (Ignea Lab @ McGill University)",
    'description': 'Meant to start with gel extracts and end with an assembled plamsid',
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
        'p20_single_gen2', 'right', tip_racks=[tiprack])
    
    # Gel extraction

    # Ligation
