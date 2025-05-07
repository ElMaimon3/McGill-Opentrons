# imports
from opentrons import protocol_api
from opentrons.protocol_api import SINGLE, PARTIAL_COLUMN, ALL
from typing import List, Dict, Tuple, Set, Optional, Any


# metadata
metadata = {
    'protocolName': 'Eppendorf depth testing for reagent storage',
    "author": "Gabriel Straface (Ignea Lab @ McGill University)",
    'description': '''Test the depth of a 1.5mL Eppendorf for reagent storage in small volume reactions'''
}
requirements = {"robotType": "Flex", "apiLevel": "2.21"}


# Runtime Parameters
def add_parameters(parameters: protocol_api.Parameters):
    parameters.add_int(
        variable_name="depth",
        display_name="Eppendorf testing depth",
        description="Depth to test pipette tip at",
        default=36,
        minimum=1,
        maximum=50,
        unit="mm"
    )

def run(protocol: protocol_api.ProtocolContext):
    # Get PCR parameters from runtime inputs
    depth = protocol.params.depth


    # Load labware
    chute = protocol.load_waste_chute()
    tiprack50 = protocol.load_labware('opentrons_flex_96_tiprack_50ul', 'C2')
    tiprack200 = protocol.load_labware('opentrons_flex_96_tiprack_200ul', 'C3')
    tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 'C1')
    location = tube_rack.wells_by_name()['A1'].top(-depth)

    # Load pipettes
    p50 = protocol.load_instrument('flex_8channel_50', 'left')
    p200 = protocol.load_instrument('flex_8channel_1000', 'right')
    
    p200.configure_nozzle_layout(
        style=SINGLE,
        start="H1"
    )

    p200.pick_up_tip(tiprack200.wells_by_name()['A1'])

    p200.move_to(location)
    protocol.pause("Look at depth")

    p200.drop_tip()


