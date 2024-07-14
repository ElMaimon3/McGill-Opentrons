# imports
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': '',
    "author": "",
    'description': '',
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

# Runtime Parameters (Recommended)
def add_parameters(parameters: protocol_api.Parameters):
    parameters.add_int(
        variable_name = "some_number",
        display_name = "Some Number",
        description = "",
        default = 40,
        minimum = 20,
        maximum = 50,
        unit = "µL"
    )
    parameters.add_bool(
        variable_name = "debug",
        display_name = "Debugging Mode",
        description = "",
        default = False
    )

def run(protocol: protocol_api.ProtocolContext):
     # labware
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '1')

     # pipettes
    left_pipette = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[tiprack])

     # loaction definitions

     # commands
    some_number = protocol.params.some_number
    if  not protocol.params.debug:
        # Protocol goes here
        pass
    else:
        #Debugging code goes here
        pass
    
